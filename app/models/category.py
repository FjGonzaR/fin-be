import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, Index, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# Slugs that have hardcoded behavior in code (KPIs, dashboard exclusions, etc.).
# Categories with these slugs are seeded with is_system=True and cannot be
# renamed or deleted from the admin UI.
SYSTEM_SLUGS: set[str] = {
    "INGRESO",
    "INVERSION",
    "PAGO",
    "MOVIMIENTO_ENTRE_BANCOS",
    "OTROS",
}


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    keywords: Mapped[list["CategoryKeyword"]] = relationship(  # noqa: F821
        "CategoryKeyword", back_populates="category", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_categories_slug", "slug"),
    )
