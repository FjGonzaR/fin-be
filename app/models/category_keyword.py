import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KeywordOrigin(str, enum.Enum):
    MANUAL = "MANUAL"
    LEARNED = "LEARNED"


_origin_col = Enum(KeywordOrigin, name="keyword_origin_enum", create_type=False)


class CategoryKeyword(Base):
    __tablename__ = "category_keywords"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[KeywordOrigin] = mapped_column(_origin_col, nullable=False, default=KeywordOrigin.MANUAL)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    category: Mapped["Category"] = relationship("Category", back_populates="keywords")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("category_id", "keyword", name="uq_category_keyword"),
        Index("ix_category_keywords_keyword", "keyword"),
    )
