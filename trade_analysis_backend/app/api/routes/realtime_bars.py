from fastapi import APIRouter

from app.api.dependencies import RealtimeBarServiceDep
from app.schemas.realtime_bar import RealtimeBarListResult, RealtimeBarResult

router = APIRouter()


@router.get("/current", response_model=RealtimeBarResult)
def get_current_realtime_bar(
    symbol: str,
    interval: int,
    service: RealtimeBarServiceDep,
) -> RealtimeBarResult:
    return RealtimeBarResult(
        symbol=symbol,
        interval=interval,
        bar=service.get_current_bar(symbol=symbol, interval=interval),
    )


@router.get("/current/list", response_model=RealtimeBarListResult)
def list_current_realtime_bars(
    service: RealtimeBarServiceDep,
) -> RealtimeBarListResult:
    items = service.list_current_bars()
    return RealtimeBarListResult(count=len(items), items=items)
