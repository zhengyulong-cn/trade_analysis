import json
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from redis import Redis
from sqlmodel import Session, select
from tqsdk.datetime import _get_trading_timestamp, _is_in_trading_time

from app.models.contract import Contract
from app.models.contract_interval import ContractInterval
from app.models.kline_data import KlineData
from app.schemas.kline_data import KlineBarInput, KlineBatchCreate
from app.schemas.realtime_bar import RealtimeBar
from app.services.kline_service import KlineService
from app.services.market_data import KlineProvider, MarketQuote, MarketTradingTime

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


class RealtimeBarService:
    def __init__(
        self,
        session: Session,
        redis_client: Redis,
        kline_provider: KlineProvider,
    ):
        self.session = session
        self.redis_client = redis_client
        self.kline_provider = kline_provider
        self.kline_service = KlineService(session, kline_provider=kline_provider)

    def get_current_bar(self, symbol: str, interval: int) -> RealtimeBar | None:
        raw_bar = self.redis_client.get(self._bar_key(symbol=symbol, interval=interval))
        if not raw_bar:
            return None
        return self._decode_bar(raw_bar)

    def list_current_bars(self) -> list[RealtimeBar]:
        bars: list[RealtimeBar] = []
        for key in self.redis_client.scan_iter("realtime:bar:*"):
            raw_bar = self.redis_client.get(key)
            if raw_bar:
                bars.append(self._decode_bar(raw_bar))
        return sorted(bars, key=lambda item: (item.symbol, item.interval))

    def process_quote_for_interval(
        self,
        quote: MarketQuote,
        interval: ContractInterval,
    ) -> RealtimeBar:
        current_time = self._get_current_time()
        if not self._is_in_trading_time(quote.trading_time, current_time):
            current_bar = self.get_current_bar(
                symbol=quote.symbol,
                interval=interval.seconds,
            )
            if current_bar is None:
                raise RuntimeError("outside trading time")
            return current_bar

        quote_time = self._normalize_datetime(quote.quote_time)
        bucket_start = self._get_bucket_start(quote_time, interval.seconds)
        current_bar = self.get_current_bar(
            symbol=quote.symbol,
            interval=interval.seconds,
        )

        if current_bar is None:
            current_bar = self._create_initial_bar(
                quote=quote,
                interval=interval,
                bucket_start=bucket_start,
            )
            self._save_bar(current_bar)
            return current_bar

        if bucket_start < current_bar.bucket_start:
            return current_bar

        if bucket_start == current_bar.bucket_start:
            updated_bar = self._update_bar_with_quote(current_bar, quote)
            self._save_bar(updated_bar)
            return updated_bar

        self._persist_completed_bar(current_bar)
        previous_close = current_bar.close
        next_bucket_start = current_bar.bucket_start + timedelta(
            seconds=interval.seconds
        )

        while next_bucket_start < bucket_start:
            if self._is_bucket_start_in_trading_time(
                quote.trading_time,
                current_time,
                next_bucket_start,
            ):
                flat_bar = self._create_flat_completed_bar(
                    quote=quote,
                    interval=interval,
                    bucket_start=next_bucket_start,
                    price=previous_close,
                )
                self._persist_completed_bar(flat_bar)
                previous_close = flat_bar.close
            next_bucket_start += timedelta(seconds=interval.seconds)

        next_bar = self._create_realtime_bar(
            quote=quote,
            interval=interval,
            bucket_start=bucket_start,
            open_price=previous_close,
            bucket_start_quote_volume=quote.volume,
        )
        next_bar = self._update_bar_with_quote(next_bar, quote)
        self._save_bar(next_bar)
        return next_bar

    def process_quote(self, quote: MarketQuote) -> list[RealtimeBar]:
        current_time = self._get_current_time()
        if not self._is_in_trading_time(quote.trading_time, current_time):
            return []
        intervals = self._list_intervals()
        return [
            self.process_quote_for_interval(quote=quote, interval=interval)
            for interval in intervals
        ]

    def clear_current_bar(self, symbol: str, interval: int) -> None:
        self.redis_client.delete(self._bar_key(symbol=symbol, interval=interval))

    def _create_initial_bar(
        self,
        quote: MarketQuote,
        interval: ContractInterval,
        bucket_start: datetime,
    ) -> RealtimeBar:
        latest_kline = self._get_latest_kline_row(
            symbol=quote.symbol,
            interval_id=interval.contract_interval_id,
        )
        open_price = latest_kline.close if latest_kline is not None else quote.last_price
        if latest_kline is not None:
            current_time = self._get_current_time()
            next_bucket_start = self._normalize_datetime(latest_kline.date_time)
            while next_bucket_start < bucket_start:
                if self._is_bucket_start_in_trading_time(
                    quote.trading_time,
                    current_time,
                    next_bucket_start,
                ):
                    flat_bar = self._create_flat_completed_bar(
                        quote=quote,
                        interval=interval,
                        bucket_start=next_bucket_start,
                        price=open_price,
                    )
                    self._persist_completed_bar(flat_bar)
                    open_price = flat_bar.close
                next_bucket_start += timedelta(seconds=interval.seconds)

        return self._create_realtime_bar(
            quote=quote,
            interval=interval,
            bucket_start=bucket_start,
            open_price=open_price,
            bucket_start_quote_volume=quote.volume,
        )

    def _create_realtime_bar(
        self,
        quote: MarketQuote,
        interval: ContractInterval,
        bucket_start: datetime,
        open_price: Decimal,
        bucket_start_quote_volume: Decimal,
    ) -> RealtimeBar:
        bucket_end = bucket_start + timedelta(seconds=interval.seconds)
        return RealtimeBar(
            symbol=quote.symbol,
            exchange=quote.exchange,
            interval=interval.seconds,
            bucket_start=bucket_start,
            bucket_end=bucket_end,
            date_time=bucket_end,
            open=open_price,
            high=open_price,
            low=open_price,
            close=open_price,
            volume=Decimal("0"),
            hold=quote.hold,
            quote_volume=bucket_start_quote_volume,
            quote_time=self._normalize_datetime(quote.quote_time),
            provider=None,
            provider_symbol=quote.provider_symbol,
        )

    def _create_flat_completed_bar(
        self,
        quote: MarketQuote,
        interval: ContractInterval,
        bucket_start: datetime,
        price: Decimal,
    ) -> RealtimeBar:
        bucket_end = bucket_start + timedelta(seconds=interval.seconds)
        return RealtimeBar(
            symbol=quote.symbol,
            exchange=quote.exchange,
            interval=interval.seconds,
            bucket_start=bucket_start,
            bucket_end=bucket_end,
            date_time=bucket_end,
            open=price,
            high=price,
            low=price,
            close=price,
            volume=Decimal("0"),
            hold=quote.hold,
            quote_volume=quote.volume,
            quote_time=bucket_end,
            provider=None,
            provider_symbol=quote.provider_symbol,
        )

    def _update_bar_with_quote(
        self,
        bar: RealtimeBar,
        quote: MarketQuote,
    ) -> RealtimeBar:
        quote_volume_delta = quote.volume - bar.quote_volume
        if quote_volume_delta < 0:
            quote_volume_delta = Decimal("0")

        return bar.model_copy(
            update={
                "high": max(bar.high, quote.last_price),
                "low": min(bar.low, quote.last_price),
                "close": quote.last_price,
                "volume": quote_volume_delta,
                "hold": quote.hold,
                "quote_time": self._normalize_datetime(quote.quote_time),
                "provider_symbol": quote.provider_symbol,
            }
        )

    def _persist_completed_bar(self, bar: RealtimeBar) -> None:
        self.kline_service.create_klines_batch(
            KlineBatchCreate(
                symbol=bar.symbol,
                interval=bar.interval,
                items=[
                    KlineBarInput(
                        open=bar.open,
                        close=bar.close,
                        high=bar.high,
                        low=bar.low,
                        volume=bar.volume,
                        hold=bar.hold,
                        date_time=bar.date_time,
                    )
                ],
            )
        )

    def _get_latest_kline_row(
        self,
        symbol: str,
        interval_id: int | None,
    ) -> KlineData | None:
        if interval_id is None:
            return None
        statement = (
            select(KlineData)
            .join(Contract, Contract.contract_id == KlineData.contract_id)
            .where(Contract.symbol == symbol)
            .where(KlineData.interval_id == interval_id)
            .order_by(KlineData.date_time.desc())
            .limit(1)
        )
        return self.session.exec(statement).first()

    def _list_intervals(self) -> list[ContractInterval]:
        statement = select(ContractInterval).order_by(ContractInterval.seconds)
        return list(self.session.exec(statement).all())

    def _save_bar(self, bar: RealtimeBar) -> None:
        self.redis_client.set(
            self._bar_key(symbol=bar.symbol, interval=bar.interval),
            self._encode_bar(bar),
        )

    def _bar_key(self, symbol: str, interval: int) -> str:
        return f"realtime:bar:{symbol}:{interval}"

    def _encode_bar(self, bar: RealtimeBar) -> str:
        return json.dumps(
            bar.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def _decode_bar(self, raw_bar: str | bytes) -> RealtimeBar:
        if isinstance(raw_bar, bytes):
            raw_bar = raw_bar.decode("utf-8")
        return RealtimeBar.model_validate(json.loads(raw_bar))

    def _get_bucket_start(self, quote_time: datetime, interval_seconds: int) -> datetime:
        normalized = self._normalize_datetime(quote_time)
        timestamp = int(normalized.replace(tzinfo=SHANGHAI_TZ).timestamp())
        bucket_timestamp = timestamp - (timestamp % interval_seconds)
        return datetime.fromtimestamp(bucket_timestamp, SHANGHAI_TZ).replace(
            tzinfo=None
        )

    def _normalize_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is not None:
            return value.astimezone(SHANGHAI_TZ).replace(tzinfo=None)
        return value.replace(tzinfo=None)

    def _get_current_time(self) -> datetime:
        return datetime.now(SHANGHAI_TZ).replace(tzinfo=None)

    def _is_in_trading_time(
        self,
        trading_time: MarketTradingTime,
        current_time: datetime,
    ) -> bool:
        return _is_in_trading_time(
            self._build_tqsdk_quote_payload(trading_time),
            current_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
            float("nan"),
        )

    def _is_bucket_start_in_trading_time(
        self,
        trading_time: MarketTradingTime,
        current_time: datetime,
        bucket_start: datetime,
    ) -> bool:
        trading_timestamp = _get_trading_timestamp(
            self._build_tqsdk_quote_payload(trading_time),
            current_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
        )
        bucket_timestamp = int(
            bucket_start.replace(tzinfo=SHANGHAI_TZ).timestamp() * 1_000_000_000
        )
        for periods in trading_timestamp.values():
            for period_start, period_end in periods:
                if period_start <= bucket_timestamp < period_end:
                    return True
        return False

    def _build_tqsdk_quote_payload(
        self,
        trading_time: MarketTradingTime,
    ) -> dict[str, object]:
        return {
            "trading_time": {
                "day": trading_time.day,
                "night": trading_time.night,
            }
        }
