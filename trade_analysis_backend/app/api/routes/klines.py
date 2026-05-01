from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import KlineServiceDep
from app.schemas.kline_data import (
    KlineBatchCreate,
    KlineBatchWriteResult,
    KlineDataQueryResult,
    KlineDeleteRequest,
    KlineDeleteResult,
    KlineItemsDeleteRequest,
    KlineItemsDeleteResult,
    KlineListResult,
    KlinePage,
    MarketDataSyncRequest,
    MarketDataSyncResult,
)

router = APIRouter()


@router.post(
    "/batch",
    response_model=KlineBatchWriteResult,
    status_code=status.HTTP_201_CREATED,
)
def create_klines_batch(
    payload: KlineBatchCreate,
    service: KlineServiceDep,
) -> KlineBatchWriteResult:
    return service.create_klines_batch(payload)


@router.post(
    "/sync/market-data",
    response_model=MarketDataSyncResult,
    status_code=status.HTTP_201_CREATED,
)
def sync_klines_from_market_data(
    payload: MarketDataSyncRequest,
    service: KlineServiceDep,
) -> MarketDataSyncResult:
    return service.sync_from_market_data(payload)


@router.post("/delete", response_model=KlineDeleteResult)
def delete_klines(
    payload: KlineDeleteRequest,
    service: KlineServiceDep,
) -> KlineDeleteResult:
    return service.delete_klines(payload)


@router.post("/delete/items", response_model=KlineItemsDeleteResult)
def delete_kline_items(
    payload: KlineItemsDeleteRequest,
    service: KlineServiceDep,
) -> KlineItemsDeleteResult:
    return service.delete_kline_items(payload)


@router.get("", response_model=KlineListResult)
def list_klines(
    symbol: str,
    interval: int,
    service: KlineServiceDep,
    limit: Annotated[int, Query(ge=1, le=5000)] = 5000,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> KlineListResult:
    return service.list_klines(
        symbol=symbol,
        interval_seconds=interval,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/page", response_model=KlinePage)
def paginate_klines(
    symbol: str,
    interval: int,
    service: KlineServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=1000)] = 200,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> KlinePage:
    return service.paginate_klines(
        symbol=symbol,
        interval_seconds=interval,
        page=page,
        page_size=page_size,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/latest", response_model=KlineDataQueryResult)
def get_latest_kline(
    symbol: str,
    interval: int,
    service: KlineServiceDep,
) -> KlineDataQueryResult:
    return service.get_latest_kline(symbol=symbol, interval_seconds=interval)
