import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import AdminUser, DbSession
from app.models.invitation import Invitation
from app.models.user import User

router = APIRouter()


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
