import re
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminUser, DbSession
from app.models import Category, CategoryKeyword, Invitation, Transaction, User
from app.models.category import SYSTEM_SLUGS
from app.models.category_keyword import KeywordOrigin
from app.schemas.category import (
    CategoryCreate,
    CategoryKeywordCreate,
    CategoryKeywordRead,
    CategoryRead,
    CategoryUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Invites + users (existing)
# ---------------------------------------------------------------------------


class InviteResponse(BaseModel):
    invite_token: str
    expires_at: datetime


class UserSummary(BaseModel):
    id: UUID
    username: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/invite", response_model=InviteResponse, status_code=201)
def create_invite(db: DbSession, current_user: AdminUser):
    """Generate a one-time invite token valid for 7 days."""
    token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    invitation = Invitation(
        token=token,
        invited_by_id=current_user.id,
        expires_at=expires_at,
    )
    db.add(invitation)
    db.commit()
    return InviteResponse(invite_token=token, expires_at=expires_at)


@router.get("/users", response_model=list[UserSummary])
def list_users(db: DbSession, current_user: AdminUser):
    """List all registered users."""
    return db.query(User).order_by(User.created_at).all()


@router.patch("/users/{user_id}/promote", response_model=UserSummary)
def promote_user(user_id: UUID, db: DbSession, current_user: AdminUser):
    """Grant admin rights to a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = True
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Category management
# ---------------------------------------------------------------------------


_SLUG_RE = re.compile(r"[^A-Z0-9_]+")


def _slugify(name: str) -> str:
    cleaned = _SLUG_RE.sub("_", name.upper()).strip("_")
    if not cleaned:
        raise HTTPException(status_code=422, detail="slug cannot be derived from name")
    return cleaned


def _get_category_or_404(db, category_id: UUID) -> Category:
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat


@router.post("/categories", response_model=CategoryRead, status_code=201)
def create_category(body: CategoryCreate, db: DbSession, current_user: AdminUser):
    slug = (body.slug or _slugify(body.name)).upper()
    if db.query(Category).filter(Category.slug == slug).first():
        raise HTTPException(status_code=409, detail=f"Category with slug '{slug}' already exists")

    cat = Category(
        slug=slug,
        name=body.name,
        description=body.description,
        is_system=False,
        created_by_id=current_user.id,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.get("/categories", response_model=list[CategoryRead])
def list_categories_admin(
    db: DbSession,
    current_user: AdminUser,
    include_inactive: bool = Query(False),
):
    q = db.query(Category)
    if not include_inactive:
        q = q.filter(Category.is_active.is_(True))
    return q.order_by(Category.is_system.desc(), Category.name).all()


@router.patch("/categories/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: UUID,
    body: CategoryUpdate,
    db: DbSession,
    current_user: AdminUser,
):
    cat = _get_category_or_404(db, category_id)

    if body.slug is not None:
        new_slug = body.slug.upper()
        if cat.is_system and new_slug != cat.slug:
            raise HTTPException(status_code=409, detail="Cannot change slug of a system category")
        if new_slug != cat.slug and db.query(Category).filter(Category.slug == new_slug).first():
            raise HTTPException(status_code=409, detail=f"slug '{new_slug}' already in use")
        cat.slug = new_slug

    if body.name is not None:
        cat.name = body.name
    if body.description is not None:
        cat.description = body.description
    if body.is_active is not None:
        if cat.is_system and not body.is_active:
            raise HTTPException(status_code=409, detail="Cannot deactivate a system category")
        cat.is_active = body.is_active

    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(
    category_id: UUID,
    db: DbSession,
    current_user: AdminUser,
    reassign_to: UUID | None = Query(None, description="Category to reassign existing transactions to"),
):
    cat = _get_category_or_404(db, category_id)
    if cat.is_system or cat.slug in SYSTEM_SLUGS:
        raise HTTPException(status_code=409, detail="Cannot delete a system category")

    in_use = db.query(Transaction).filter(Transaction.category_id == cat.id).count()
    if in_use:
        if not reassign_to:
            raise HTTPException(
                status_code=409,
                detail=f"Category has {in_use} transactions. Provide reassign_to=<category_id> to delete.",
            )
        target = _get_category_or_404(db, reassign_to)
        if target.id == cat.id:
            raise HTTPException(status_code=422, detail="reassign_to must be a different category")
        db.query(Transaction).filter(Transaction.category_id == cat.id).update(
            {"category_id": target.id}, synchronize_session=False
        )

    db.delete(cat)
    db.commit()


# ---------------------------------------------------------------------------
# Category keywords
# ---------------------------------------------------------------------------


@router.get("/categories/{category_id}/keywords", response_model=list[CategoryKeywordRead])
def list_category_keywords(category_id: UUID, db: DbSession, current_user: AdminUser):
    _get_category_or_404(db, category_id)
    return (
        db.query(CategoryKeyword)
        .filter(CategoryKeyword.category_id == category_id)
        .order_by(CategoryKeyword.origin, CategoryKeyword.weight.desc(), CategoryKeyword.keyword)
        .all()
    )


@router.post("/categories/{category_id}/keywords", response_model=CategoryKeywordRead, status_code=201)
def add_category_keyword(
    category_id: UUID,
    body: CategoryKeywordCreate,
    db: DbSession,
    current_user: AdminUser,
):
    _get_category_or_404(db, category_id)
    kw = CategoryKeyword(
        category_id=category_id,
        keyword=body.keyword,
        origin=KeywordOrigin.MANUAL,
        weight=1,
        is_active=True,
    )
    db.add(kw)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Keyword already exists for this category")
    db.refresh(kw)
    return kw


@router.delete("/categories/{category_id}/keywords/{keyword_id}", status_code=204)
def delete_category_keyword(
    category_id: UUID,
    keyword_id: UUID,
    db: DbSession,
    current_user: AdminUser,
):
    kw = (
        db.query(CategoryKeyword)
        .filter(CategoryKeyword.id == keyword_id, CategoryKeyword.category_id == category_id)
        .first()
    )
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    db.delete(kw)
    db.commit()
