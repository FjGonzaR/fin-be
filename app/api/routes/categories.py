from fastapi import APIRouter, Query

from app.models.enums import Category

router = APIRouter()

_SPENDING_EXCLUDE = {Category.INGRESO, Category.INVERSION}


@router.get("", response_model=list[str])
def list_categories(
    spending_only: bool = Query(False, description="Exclude INGRESO and INVERSION"),
):
    categories = list(Category)
    if spending_only:
        categories = [c for c in categories if c not in _SPENDING_EXCLUDE]
    return [c.value for c in categories]
