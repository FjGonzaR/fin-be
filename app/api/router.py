from fastapi import APIRouter

from app.api.routes import accounts, etl, files, transactions

api_router = APIRouter()

api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(etl.router, prefix="/etl", tags=["etl"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
