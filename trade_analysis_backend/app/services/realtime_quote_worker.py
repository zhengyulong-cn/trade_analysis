import json
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from threading import Event, Thread
from time import monotonic, time

from sqlmodel import Session, select
from tqsdk import TqApi, TqAuth

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import engine
from app.models.contract import Contract
from app.services.market_data import MarketQuote, MarketTradingTime
from app.services.market_data.tqsdk_provider import TqSdkMarketDataProvider
from app.services.realtime_bar_service import RealtimeBarService
from app.services.redis_client import redis_client_manager

logger = get_logger(__name__)


@dataclass(frozen=True)
class QuoteSubscriptionSpec:
    symbol: str
    exchange: str
    provider_symbol: str


class RealtimeQuoteWorker:
    def __init__(self):
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if not settings.realtime_quote_enabled:
            logger.info("Realtime quote worker is disabled")
            return
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = Thread(
            target=self._run,
            name="realtime-quote-worker",
            daemon=True,
        )
        self._thread.start()
        logger.info("Realtime quote worker started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None
        logger.info("Realtime quote worker stopped")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            api: TqApi | None = None
            try:
                specs = self._load_subscription_specs()
                if not specs:
                    self._stop_event.wait(5)
                    continue

                provider = TqSdkMarketDataProvider()
                api = self._create_api()
                self._run_subscription(api=api, provider=provider, specs=specs)
            except Exception as exc:
                logger.warning("Realtime quote subscription unavailable: %s", exc)
                self._stop_event.wait(30)
            finally:
                if api is not None:
                    try:
                        api.close()
                    except Exception:
                        logger.exception("Failed to close realtime quote TqApi")

    def _run_subscription(
        self,
        api: TqApi,
        provider: TqSdkMarketDataProvider,
        specs: list[QuoteSubscriptionSpec],
    ) -> None:
        provider_symbols = [spec.provider_symbol for spec in specs]
        quote_list = api.get_quote_list(provider_symbols)
        last_signatures: dict[str, tuple[str, str, str, str]] = {}
        refresh_seconds = max(
            settings.realtime_quote_subscription_refresh_seconds,
            5,
        )
        next_refresh_at = monotonic() + refresh_seconds

        logger.info(
            "Realtime quote subscription ready: %s contracts",
            len(provider_symbols),
        )

        while not self._stop_event.is_set():
            if monotonic() >= next_refresh_at:
                latest_specs = self._load_subscription_specs()
                latest_symbols = [spec.provider_symbol for spec in latest_specs]
                if latest_symbols != provider_symbols:
                    logger.info("Realtime quote contract list changed, resubscribing")
                    return
                next_refresh_at = monotonic() + refresh_seconds

            updated = api.wait_update(deadline=time() + 1)
            if not updated:
                continue

            quotes: list[MarketQuote] = []
            for spec, quote in zip(specs, quote_list):
                if not self._is_quote_changed(
                    spec=spec,
                    quote=quote,
                    last_signatures=last_signatures,
                ):
                    continue

                market_quote = self._convert_quote(
                    provider=provider,
                    spec=spec,
                    quote=quote,
                )
                if market_quote.last_price <= 0:
                    continue
                quotes.append(market_quote)

            if quotes:
                self._handle_quotes(provider=provider, quotes=quotes)

    def _handle_quotes(
        self,
        provider: TqSdkMarketDataProvider,
        quotes: list[MarketQuote],
    ) -> None:
        with Session(engine) as session:
            redis_client = redis_client_manager.get_client()
            service = RealtimeBarService(
                session=session,
                redis_client=redis_client,
                kline_provider=provider,
            )

            for quote in quotes:
                redis_client.set(self._quote_key(quote.symbol), self._encode_quote(quote))
                service.process_quote(quote)

    def _load_subscription_specs(self) -> list[QuoteSubscriptionSpec]:
        provider = TqSdkMarketDataProvider()
        with Session(engine) as session:
            return [
                QuoteSubscriptionSpec(
                    symbol=contract.symbol,
                    exchange=contract.exchange,
                    provider_symbol=provider._build_symbol(
                        symbol=contract.symbol,
                        exchange=contract.exchange,
                    ),
                )
                for contract in self._list_contracts(session)
            ]

    def _list_contracts(self, session: Session) -> list[Contract]:
        statement = select(Contract).order_by(Contract.symbol)
        return list(session.exec(statement).all())

    def _create_api(self) -> TqApi:
        return TqApi(
            web_gui=settings.tqsdk_web_gui,
            auth=TqAuth(settings.tqsdk_username, settings.tqsdk_password),
        )

    def _is_quote_changed(
        self,
        spec: QuoteSubscriptionSpec,
        quote: object,
        last_signatures: dict[str, tuple[str, str, str, str]],
    ) -> bool:
        signature = (
            str(getattr(quote, "last_price", "")),
            str(getattr(quote, "volume", "")),
            str(getattr(quote, "open_interest", "")),
            str(getattr(quote, "datetime", "")),
        )
        if last_signatures.get(spec.provider_symbol) == signature:
            return False
        last_signatures[spec.provider_symbol] = signature
        return True

    def _convert_quote(
        self,
        provider: TqSdkMarketDataProvider,
        spec: QuoteSubscriptionSpec,
        quote: object,
    ) -> MarketQuote:
        trading_time = getattr(quote, "trading_time", None)
        return MarketQuote(
            symbol=spec.symbol,
            exchange=spec.exchange,
            provider_symbol=spec.provider_symbol,
            last_price=provider._to_decimal(getattr(quote, "last_price", None)),
            volume=provider._to_decimal(getattr(quote, "volume", 0)),
            hold=provider._to_decimal(getattr(quote, "open_interest", 0)),
            quote_time=provider._normalize_quote_datetime(
                getattr(quote, "datetime", "")
            ),
            trading_time=MarketTradingTime(
                day=[
                    [str(item[0]), str(item[1])]
                    for item in getattr(trading_time, "day", [])
                ],
                night=[
                    [str(item[0]), str(item[1])]
                    for item in getattr(trading_time, "night", [])
                ],
            ),
        )

    def _quote_key(self, symbol: str) -> str:
        return f"realtime:quote:{symbol}"

    def _encode_quote(self, quote: MarketQuote) -> str:
        return json.dumps(
            asdict(quote),
            default=self._json_default,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def _json_default(self, value: object) -> str:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)


realtime_quote_worker = RealtimeQuoteWorker()
