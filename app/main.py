from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings

app = FastAPI(
    title="Finanzas Backend API",
    description="Personal finance ETL + API",
    version="0.1.0",
    debug=settings.debug,
)

app.include_router(api_router)


@app.get("/")
def root():
    return {"message": "Finanzas Backend API", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "ok"}
