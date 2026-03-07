import uuid
from datetime import datetime, timezone

from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import AccountTypeEnum, BankEnum, OwnerEnum

_bank_col = Enum(BankEnum, name="bank_enum", create_type=False)
_owner_col = Enum(OwnerEnum, name="owner_enum", create_type=False)
_account_type_col = Enum(AccountTypeEnum, name="account_type_enum", create_type=False)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bank_name: Mapped[BankEnum] = mapped_column(_bank_col, nullable=False)
    account_name: Mapped[str] = mapped_column(nullable=False)
    owner: Mapped[OwnerEnum] = mapped_column(_owner_col, nullable=False)
    account_type: Mapped[AccountTypeEnum] = mapped_column(_account_type_col, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
