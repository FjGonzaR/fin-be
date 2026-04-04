from fastapi import APIRouter, Depends

from app.api.deps import require_auth
from app.api.routes import accounts, auth, categories, dashboard, etl, files, transactions

api_router = APIRouter()

_auth = [Depends(require_auth)]

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"], dependencies=_auth)
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"], dependencies=_auth)
api_router.include_router(files.router, prefix="/files", tags=["files"], dependencies=_auth)
api_router.include_router(etl.router, prefix="/etl", tags=["etl"], dependencies=_auth)
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"], dependencies=_auth)
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"], dependencies=_auth)
