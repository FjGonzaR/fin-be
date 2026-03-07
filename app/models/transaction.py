import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Category, CategoryMethod

_category_col = Enum(Category, name="category_enum", create_type=False)
_category_method_col = Enum(CategoryMethod, name="category_method_enum", create_type=False)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_files.id"), nullable=False
    )
    posted_at: Mapped[date] = mapped_column(Date, nullable=False)
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    description_clean: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    merchant_guess: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    details_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    category: Mapped[Category | None] = mapped_column(_category_col, nullable=True)
    category_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    category_method: Mapped[CategoryMethod | None] = mapped_column(_category_method_col, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    source_file: Mapped["SourceFile"] = relationship("SourceFile")  # noqa: F821

    __table_args__ = (
        Index("ix_transactions_posted", "posted_at"),
    )
