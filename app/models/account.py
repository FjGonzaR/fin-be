import uuid
from datetime import datetime, timezone

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import AccountTypeEnum, BankEnum

_bank_col = Enum(BankEnum, name="bank_enum", create_type=False)
_account_type_col = Enum(AccountTypeEnum, name="account_type_enum", create_type=False)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bank_name: Mapped[BankEnum] = mapped_column(_bank_col, nullable=False)
    account_name: Mapped[str] = mapped_column(nullable=False)
    owner: Mapped[str] = mapped_column(Text, nullable=False)
    account_type: Mapped[AccountTypeEnum] = mapped_column(_account_type_col, nullable=False)
    file_password: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
