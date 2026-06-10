from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TradeAccount(SQLModel, table=True):
    __tablename__ = "trade_accounts"

    account_id: int | None = Field(default=None, primary_key=True)
    account_name: str = Field(min_length=1, max_length=100, nullable=False)
    account_type: str = Field(min_length=1, max_length=20, nullable=False, index=True)
    account_no: str = Field(min_length=1, max_length=100, nullable=False)
    password: str = Field(min_length=1, max_length=255, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
