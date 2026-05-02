from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.category_keyword import KeywordOrigin


class CategoryRead(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str | None
    is_active: bool
    is_system: bool

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    slug: str | None = Field(default=None, max_length=64)
    description: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    is_active: bool | None = None


class CategoryKeywordRead(BaseModel):
    id: UUID
    category_id: UUID
    keyword: str
    origin: KeywordOrigin
    weight: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryKeywordCreate(BaseModel):
    keyword: str = Field(min_length=2, max_length=128)
