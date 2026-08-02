from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.realtime_market_hub import realtime_market_hub

router = APIRouter()


@router.websocket("/market")
async def realtime_market(websocket: WebSocket) -> None:
    await realtime_market_hub.connect(websocket)
    try:
        while True:
            message = await websocket.receive_json()
            if not isinstance(message, dict):
                await websocket.send_json(
                    {"type": "error", "message": "message must be an object"}
                )
                continue
            if message.get("action") != "subscribe":
                continue
            symbols = message.get("symbols", [])
            if not isinstance(symbols, list) or not all(
                isinstance(symbol, str) for symbol in symbols
            ):
                await websocket.send_json(
                    {"type": "error", "message": "symbols must be a string list"}
                )
                continue
            await realtime_market_hub.subscribe(websocket, symbols)
    except WebSocketDisconnect:
        pass
    finally:
        realtime_market_hub.disconnect(websocket)
