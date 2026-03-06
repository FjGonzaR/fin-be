import uuid
from datetime import datetime, timezone

from sqlalchemy import Enum, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import Category

_category_col = Enum(Category, name="category_enum", create_type=False)


class CategoryExample(Base):
    __tablename__ = "category_examples"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description_clean: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Category] = mapped_column(_category_col, nullable=False)
    merchant: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_sign: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("description_clean", "category", name="uq_category_examples_desc_cat"),
    )
