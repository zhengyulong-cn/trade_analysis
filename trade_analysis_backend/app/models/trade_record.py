from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TradeRecord(SQLModel, table=True):
    __tablename__ = "trade_records"

    trade_record_id: int | None = Field(default=None, primary_key=True)
    contract: str = Field(index=True, min_length=1, max_length=50)
    lots: int = Field(nullable=False, ge=0)
    open_time: datetime = Field(index=True)
    open_price: Decimal = Field(max_digits=20, decimal_places=2)
    close_time: datetime = Field(index=True)
    close_price: Decimal = Field(max_digits=20, decimal_places=2)
    segment_type: str = Field(index=True, min_length=1, max_length=20)
    actual_pnl: Decimal = Field(max_digits=20, decimal_places=2)
    screenshot_path: str | None = Field(default=None, max_length=255)
    screenshot_original_name: str | None = Field(default=None, max_length=255)
    screenshot_content_type: str | None = Field(default=None, max_length=100)
    screenshot_size: int | None = Field(default=None, ge=0)
    comment: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
