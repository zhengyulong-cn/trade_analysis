from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol


# Provider names are intentionally constrained so configuration errors fail early.
MarketDataProviderName = Literal["tqsdk"]


class MarketDataError(Exception):
    pass


@dataclass(frozen=True)
class MarketKlineBar:
    # Unified kline shape used by the application, regardless of the upstream SDK.
    open: Decimal
    close: Decimal
    high: Decimal
    low: Decimal
    volume: Decimal
    hold: Decimal
    date_time: datetime


@dataclass(frozen=True)
class KlineFetchResult:
    # The service layer uses provider metadata for logging and future fallback logic.
    provider: MarketDataProviderName
    provider_symbol: str
    bars: list[MarketKlineBar]


class KlineProvider(Protocol):
    # Concrete providers adapt external SDKs into the application's kline contract.
    provider: MarketDataProviderName

    def get_klines(
        self,
        symbol: str,
        exchange: str,
        interval_seconds: int,
    ) -> KlineFetchResult:
        ...
