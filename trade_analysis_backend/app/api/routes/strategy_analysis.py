from fastapi import APIRouter, status

from app.api.dependencies import StrategyAnalysisServiceDep
from app.schemas.strategy_analysis import (
    SegmentBatchDeleteRequest,
    SegmentBatchDeleteResult,
    SegmentBuildRequest,
    SegmentBuildResult,
    SegmentCreateRequest,
    SegmentListResult,
    SegmentUpdateRequest,
    StrategyAnalysisDetail,
)

router = APIRouter()


@router.get("", response_model=StrategyAnalysisDetail)
def get_strategy_analysis(
    symbol: str,
    service: StrategyAnalysisServiceDep,
) -> StrategyAnalysisDetail:
    return service.get_strategy_by_symbol(symbol)


@router.get("/segments", response_model=SegmentListResult)
def list_interval_segments(
    symbol: str,
    interval: int,
    service: StrategyAnalysisServiceDep,
) -> SegmentListResult:
    return service.list_interval_segments(symbol=symbol, interval_seconds=interval)


@router.post(
    "/segments/create",
    response_model=SegmentListResult,
    status_code=status.HTTP_201_CREATED,
)
def create_interval_segment(
    payload: SegmentCreateRequest,
    service: StrategyAnalysisServiceDep,
) -> SegmentListResult:
    return service.create_interval_segment(payload)


@router.post("/segments/update", response_model=SegmentListResult)
def update_interval_segment(
    payload: SegmentUpdateRequest,
    service: StrategyAnalysisServiceDep,
) -> SegmentListResult:
    return service.update_interval_segment(payload)


@router.post("/segments/delete", response_model=SegmentBatchDeleteResult)
def delete_interval_segments(
    payload: SegmentBatchDeleteRequest,
    service: StrategyAnalysisServiceDep,
) -> SegmentBatchDeleteResult:
    return service.delete_interval_segments(payload)


@router.post(
    "/segments/build",
    response_model=SegmentBuildResult,
    status_code=status.HTTP_201_CREATED,
)
def build_single_interval_segments(
    payload: SegmentBuildRequest,
    service: StrategyAnalysisServiceDep,
) -> SegmentBuildResult:
    return service.build_single_interval_segments(payload)
