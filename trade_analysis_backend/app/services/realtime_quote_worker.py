import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from threading import Event, Thread
from time import monotonic

from sqlmodel import Session, select

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import engine
from app.models.contract import Contract
from app.services.market_data import MarketQuote, create_quote_provider
from app.services.realtime_bar_service import RealtimeBarService
from app.services.redis_client import redis_client_manager

logger = get_logger(__name__)


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
        poll_interval = max(settings.realtime_quote_poll_interval_seconds, 0.2)
        while not self._stop_event.is_set():
            started_at = monotonic()
            try:
                self._poll_once()
            except Exception:
                logger.exception("Realtime quote polling failed")

            elapsed = monotonic() - started_at
            wait_seconds = max(poll_interval - elapsed, 0.1)
            self._stop_event.wait(wait_seconds)

    def _poll_once(self) -> None:
        with Session(engine) as session:
            contracts = self._list_contracts(session)
            if not contracts:
                return

            provider = create_quote_provider()
            quote_result = provider.get_quotes(
                [(contract.symbol, contract.exchange) for contract in contracts]
            )
            redis_client = redis_client_manager.get_client()
            service = RealtimeBarService(
                session=session,
                redis_client=redis_client,
                kline_provider=provider,
            )

            for quote in quote_result.quotes:
                redis_client.set(self._quote_key(quote.symbol), self._encode_quote(quote))
                service.process_quote(quote)

    def _list_contracts(self, session: Session) -> list[Contract]:
        statement = select(Contract).order_by(Contract.symbol)
        return list(session.exec(statement).all())

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
