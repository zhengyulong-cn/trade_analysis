from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TradeFillRecord(SQLModel, table=True):
    __tablename__ = "trade_fill_records"

    trade_fill_record_id: int | None = Field(default=None, primary_key=True)
    trade_no: str = Field(index=True, unique=True, min_length=1, max_length=32)
    contract: str = Field(index=True, min_length=1, max_length=50)
    side: str = Field(nullable=False, max_length=16)
    offset: str = Field(nullable=False, index=True, max_length=16)
    trade_time: datetime = Field(index=True)
    price: Decimal = Field(max_digits=20, decimal_places=2)
    lots: int = Field(nullable=False, ge=0)
    fee: Decimal = Field(default=0, max_digits=20, decimal_places=2)
    matched_open_trade_no: str | None = Field(default=None, index=True, max_length=32)
    close_pnl: Decimal | None = Field(default=None, max_digits=20, decimal_places=2)
    source_file_name: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
