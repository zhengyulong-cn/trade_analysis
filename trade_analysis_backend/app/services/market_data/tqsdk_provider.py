from datetime import datetime
from decimal import Decimal
import time

import pandas as pd

from app.core.config import settings
from app.services.market_data.base import (
    KlineFetchResult,
    MarketDataProviderName,
    MarketKlineBar,
    MarketQuote,
    MarketTradingTime,
    QuoteFetchResult,
)
from app.services.market_data.tqsdk_client import tqsdk_client_manager

SHANGHAI_TIMEZONE = "Asia/Shanghai"


class TqSdkMarketDataProvider:
    provider: MarketDataProviderName = "tqsdk"

    def get_klines(
        self,
        symbol: str,
        exchange: str,
        interval_seconds: int,
    ) -> KlineFetchResult:
        provider_symbol = self._build_symbol(symbol=symbol, exchange=exchange)
        dataframe = self._fetch_kline_dataframe(
            provider_symbol=provider_symbol,
            interval_seconds=interval_seconds,
        )
        return KlineFetchResult(
            provider=self.provider,
            provider_symbol=provider_symbol,
            bars=self._convert_klines_to_bars(
                dataframe=dataframe,
                interval_seconds=interval_seconds,
            ),
        )

    def get_quotes(self, symbols: list[tuple[str, str]]) -> QuoteFetchResult:
        provider_symbols = [
            self._build_symbol(symbol=symbol, exchange=exchange)
            for symbol, exchange in symbols
        ]
        if not provider_symbols:
            return QuoteFetchResult(provider=self.provider, quotes=[])

        with tqsdk_client_manager.session() as api:
            quote_list = api.get_quote_list(provider_symbols)
            deadline = time.time() + settings.tqsdk_wait_timeout_seconds
            api.wait_update(deadline=deadline)

            quotes: list[MarketQuote] = []
            for (symbol, exchange), provider_symbol, quote in zip(
                symbols,
                provider_symbols,
                quote_list,
            ):
                last_price = self._to_decimal(getattr(quote, "last_price", None))
                if last_price <= 0:
                    continue

                quotes.append(
                    MarketQuote(
                        symbol=symbol,
                        exchange=exchange,
                        provider_symbol=provider_symbol,
                        last_price=last_price,
                        volume=self._to_decimal(getattr(quote, "volume", 0)),
                        hold=self._to_decimal(
                            getattr(quote, "open_interest", 0)
                        ),
                        quote_time=self._normalize_quote_datetime(
                            getattr(quote, "datetime", "")
                        ),
                        trading_time=MarketTradingTime(
                            day=[
                                [str(item[0]), str(item[1])]
                                for item in getattr(quote.trading_time, "day", [])
                            ],
                            night=[
                                [str(item[0]), str(item[1])]
                                for item in getattr(quote.trading_time, "night", [])
                            ],
                        ),
                    )
                )
            return QuoteFetchResult(provider=self.provider, quotes=quotes)

    def _fetch_kline_dataframe(
        self,
        provider_symbol: str,
        interval_seconds: int,
    ) -> pd.DataFrame:
        with tqsdk_client_manager.session() as api:
            dataframe = api.get_kline_serial(
                provider_symbol,
                interval_seconds,
                data_length=settings.tqsdk_kline_length,
            )
            deadline = time.time() + settings.tqsdk_wait_timeout_seconds
            api.wait_update(deadline=deadline)
            return dataframe.copy()

    def _convert_klines_to_bars(
        self,
        dataframe: pd.DataFrame,
        interval_seconds: int,
    ) -> list[MarketKlineBar]:
        bars: list[MarketKlineBar] = []
        if dataframe.empty:
            return bars

        datetime_column = "datetime"
        hold_column = "close_oi" if "close_oi" in dataframe.columns else "hold"
        filtered = dataframe.dropna(
            subset=[datetime_column, "open", "close", "high", "low"]
        ).tail(settings.tqsdk_kline_length)
        for row in filtered.to_dict(orient="records"):
            bars.append(
                MarketKlineBar(
                    open=self._to_decimal(row["open"]),
                    close=self._to_decimal(row["close"]),
                    high=self._to_decimal(row["high"]),
                    low=self._to_decimal(row["low"]),
                    volume=self._to_decimal(row.get("volume", 0)),
                    hold=self._to_decimal(row.get(hold_column, 0)),
                    date_time=self._get_kline_close_time(
                        row[datetime_column],
                        interval_seconds,
                    ),
                )
            )
        return bars

    def _normalize_datetime(self, raw_datetime: object) -> datetime:
        if isinstance(raw_datetime, (int, float)) and not pd.isna(raw_datetime):
            timestamp = pd.to_datetime(
                raw_datetime,
                unit="ns",
                utc=True,
                errors="coerce",
            )
        else:
            timestamp = pd.to_datetime(raw_datetime, errors="coerce")
        if pd.isna(timestamp):
            raise ValueError(f"Invalid tqsdk datetime value: {raw_datetime}")
        if timestamp.tzinfo is not None:
            timestamp = timestamp.tz_convert(SHANGHAI_TIMEZONE)
        return timestamp.to_pydatetime().replace(tzinfo=None)

    def _normalize_quote_datetime(self, raw_datetime: object) -> datetime:
        if not raw_datetime:
            return datetime.now()
        return self._normalize_datetime(raw_datetime)

    def _get_kline_close_time(
        self,
        raw_datetime: object,
        interval_seconds: int,
    ) -> datetime:
        open_time = self._normalize_datetime(raw_datetime)
        return open_time + pd.Timedelta(seconds=interval_seconds).to_pytimedelta()

    def _build_symbol(self, symbol: str, exchange: str) -> str:
        if "." in symbol:
            return symbol
        return f"{exchange.upper()}.{symbol}"

    def _to_decimal(self, value: object) -> Decimal:
        if value is None or pd.isna(value):
            return Decimal("0")
        return Decimal(str(value))
