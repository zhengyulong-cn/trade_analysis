from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import AnalysisServiceDep
from app.schemas.analysis import AnalysisOut, _FractalOut, _HigherSegmentOut, _MomentumExhaustionOut, _SegmentOut, _SegmentPointOut, _TradingRangeOut

router = APIRouter()


@router.get("/chart", response_model=AnalysisOut)
def get_analysis(
    symbol: str,
    interval: int,
    service: AnalysisServiceDep,
    limit: Annotated[int, Query(ge=1, le=5000)] = 2000,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> AnalysisOut:
    result = service.analyze(
        symbol=symbol,
        interval_seconds=interval,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
    )
    return AnalysisOut(
        symbol=symbol,
        interval=interval,
        bar_count=result["bar_count"],
        fractals=[_FractalOut(**f) for f in result["fractals"]],
        segments=[
            _SegmentOut(
                direction=s["direction"],
                start=_SegmentPointOut(**s["start"]),
                end=_SegmentPointOut(**s["end"]),
            )
            for s in result["segments"]
        ],
        higher_segments=[
            _HigherSegmentOut(
                direction=s["direction"],
                start=_SegmentPointOut(**s["start"]),
                end=_SegmentPointOut(**s["end"]),
            )
            for s in result["higher_segments"]
        ],
        trading_ranges=[
            _TradingRangeOut(
                top=r["top"],
                bottom=r["bottom"],
                left=_SegmentPointOut(**r["left"]),
                right=_SegmentPointOut(**r["right"]),
            )
            for r in result["trading_ranges"]
        ],
        momentum_exhaustions=[
            _MomentumExhaustionOut(
                direction=s["direction"],
                point=_SegmentPointOut(**s["point"]),
                previous_strength=s["previous_strength"],
                current_strength=s["current_strength"],
            )
            for s in result["momentum_exhaustions"]
        ],
    )
