from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict
from sqlmodel import SQLModel


class KlineBarInput(SQLModel):
    open: Decimal
    close: Decimal
    high: Decimal
    low: Decimal
    volume: Decimal = 0
    hold: Decimal = 0
    date_time: datetime


class KlineDataCreate(KlineBarInput):
    symbol: str
    interval: int


class KlineBatchCreate(SQLModel):
    symbol: str
    interval: int
    items: list[KlineBarInput]


class KlineDataRead(KlineBarInput):
    model_config = ConfigDict(from_attributes=True)

    kline_id: int
    contract_id: int
    interval_id: int


class KlineDataQueryResult(KlineDataRead):
    symbol: str
    exchange: str
    contract_name: str
    interval: int


class KlineListItem(KlineDataRead):
    interval: int


class KlineListResult(SQLModel):
    contract_id: int
    symbol: str
    exchange: str
    name: str
    count: int
    kline_data: list[KlineListItem]


class KlinePage(SQLModel):
    items: list[KlineDataQueryResult]
    total: int
    page: int
    page_size: int


class KlineBatchWriteResult(SQLModel):
    total: int
    inserted: int
    updated: int


class KlineDeleteRequest(SQLModel):
    symbol: str
    interval: int


class KlineDeleteResult(SQLModel):
    symbol: str
    interval: int
    deleted: int


class KlineItemDeleteRequest(SQLModel):
    kline_id: int


class KlineItemDeleteResult(SQLModel):
    kline_id: int
    deleted: int


class MarketDataSyncRequest(SQLModel):
    symbol: str
    interval: int


class MarketDataSyncResult(SQLModel):
    symbol: str
    interval: int
    provider: str
    provider_symbol: str
    requested: int
    inserted: int
    updated: int


class MarketDataBulkSyncRequest(SQLModel):
    symbols: list[str] | None = None
    intervals: list[int] | None = None


class MarketDataBulkSyncError(SQLModel):
    symbol: str
    interval: int
    detail: str


class MarketDataBulkSyncResult(SQLModel):
    total: int
    succeeded: int
    failed: int
    requested: int
    inserted: int
    updated: int
    items: list[MarketDataSyncResult]
    errors: list[MarketDataBulkSyncError]


TqSdkSyncRequest = MarketDataSyncRequest
TqSdkSyncResult = MarketDataSyncResult
TqSdkBulkSyncRequest = MarketDataBulkSyncRequest
TqSdkBulkSyncResult = MarketDataBulkSyncResult
TqSdkBulkSyncError = MarketDataBulkSyncError
