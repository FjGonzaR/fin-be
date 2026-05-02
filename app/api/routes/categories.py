from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.models import Category
from app.schemas.category import CategoryRead

router = APIRouter()

_SPENDING_EXCLUDE_SLUGS = {"INGRESO", "INVERSION"}


@router.get("", response_model=list[CategoryRead])
def list_categories(
    db: DbSession,
    spending_only: bool = Query(False, description="Exclude INGRESO and INVERSION"),
):
    q = db.query(Category).filter(Category.is_active.is_(True))
    if spending_only:
        q = q.filter(~Category.slug.in_(_SPENDING_EXCLUDE_SLUGS))
    return q.order_by(Category.name).all()
