from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel


class RealtimeBar(SQLModel):
    symbol: str
    exchange: str
    interval: int
    bucket_start: datetime
    bucket_end: datetime
    date_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = 0
    hold: Decimal = 0
    quote_volume: Decimal = 0
    quote_time: datetime
    provider: str | None = None
    provider_symbol: str | None = None


class RealtimeBarResult(SQLModel):
    symbol: str
    interval: int
    bar: RealtimeBar | None = None


class RealtimeBarListResult(SQLModel):
    count: int
    items: list[RealtimeBar]
