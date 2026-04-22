from fastapi import APIRouter, status

from app.api.dependencies import StrategyAnalysisServiceDep
from app.schemas.strategy_analysis import (
    SegmentBuildRequest,
    SegmentBuildResult,
    StrategyAnalysisDetail,
)

router = APIRouter()


@router.get("", response_model=StrategyAnalysisDetail)
def get_strategy_analysis(
    symbol: str,
    service: StrategyAnalysisServiceDep,
) -> StrategyAnalysisDetail:
    return service.get_strategy_by_symbol(symbol)


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
