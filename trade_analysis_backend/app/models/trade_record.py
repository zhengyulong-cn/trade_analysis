from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import JSON, Column
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
    segment_type: str | None = Field(default=None, index=True, max_length=32)
    fee: Decimal = Field(default=0, max_digits=20, decimal_places=2)
    actual_pnl: Decimal = Field(max_digits=20, decimal_places=2)
    import_open_trade_no: str | None = Field(default=None, index=True, max_length=32)
    import_close_trade_no: str | None = Field(default=None, index=True, max_length=32)
    screenshots: list[dict] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    comment: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
