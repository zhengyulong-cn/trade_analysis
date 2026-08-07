import asyncio
import json
from collections.abc import Iterable
from threading import RLock

from fastapi import WebSocket

from app.services.market_data import MarketQuote
from app.schemas.realtime_bar import RealtimeBar
from app.services.redis_client import redis_client_manager


class RealtimeMarketHub:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, set[str]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = RLock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self._loop = asyncio.get_running_loop()
            self._connections[websocket] = set()

    def disconnect(self, websocket: WebSocket) -> None:
        with self._lock:
            self._connections.pop(websocket, None)

    async def subscribe(self, websocket: WebSocket, symbols: Iterable[str]) -> None:
        normalized_symbols = {symbol.strip() for symbol in symbols if symbol.strip()}
        with self._lock:
            if websocket not in self._connections:
                return
            self._connections[websocket] = normalized_symbols

        await websocket.send_json(
            {
                "type": "snapshot",
                "quotes": self._get_quote_snapshot(normalized_symbols),
                "bars": self._get_bar_snapshot(normalized_symbols),
            }
        )

    def publish_quote(self, quote: MarketQuote) -> None:
        self._publish(
            quote.symbol,
            {
                "type": "quote",
                "data": {
                    "symbol": quote.symbol,
                    "exchange": quote.exchange,
                    "last_price": str(quote.last_price),
                    "volume": str(quote.volume),
                    "hold": str(quote.hold),
                    "quote_time": quote.quote_time.isoformat(),
                },
            },
        )

    def publish_bar(self, bar: RealtimeBar) -> None:
        self._publish(
            bar.symbol,
            {
                "type": "bar",
                "data": bar.model_dump(mode="json"),
            },
        )

    def _publish(self, symbol: str, message: dict[str, object]) -> None:
        with self._lock:
            loop = self._loop
        if loop is None or loop.is_closed():
            return
        loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self._broadcast(symbol, message))
        )

    async def _broadcast(self, symbol: str, message: dict[str, object]) -> None:
        with self._lock:
            recipients = [
                websocket
                for websocket, symbols in self._connections.items()
                if symbol in symbols
            ]

        disconnected: list[WebSocket] = []
        for websocket in recipients:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(websocket)

    def _get_quote_snapshot(self, symbols: set[str]) -> list[dict[str, object]]:
        redis_client = redis_client_manager.get_client()
        quotes: list[dict[str, object]] = []
        for symbol in symbols:
            raw_quote = redis_client.get(f"realtime:quote:{symbol}")
            if raw_quote:
                quotes.append(self._decode_json(raw_quote))
        return quotes

    def _get_bar_snapshot(self, symbols: set[str]) -> list[dict[str, object]]:
        redis_client = redis_client_manager.get_client()
        bars: list[dict[str, object]] = []
        for symbol in symbols:
            for interval in (300, 1800, 3600):
                raw_bar = redis_client.get(f"realtime:bar:{symbol}:{interval}")
                if raw_bar:
                    bars.append(self._decode_json(raw_bar))
        return bars

    def _decode_json(self, raw_value: str | bytes) -> dict[str, object]:
        if isinstance(raw_value, bytes):
            raw_value = raw_value.decode("utf-8")
        return json.loads(raw_value)


realtime_market_hub = RealtimeMarketHub()
