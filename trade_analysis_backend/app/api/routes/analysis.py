from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import AnalysisServiceDep
from app.schemas.analysis import AnalysisOut, _FractalOut, _SegmentOut, _SegmentPointOut

router = APIRouter()


@router.get("", response_model=AnalysisOut)
def get_analysis(
    symbol: str,
    interval: int,
    service: AnalysisServiceDep,
    limit: Annotated[int, Query(ge=1, le=5000)] = 2000,
) -> AnalysisOut:
    result = service.analyze(
        symbol=symbol,
        interval_seconds=interval,
        limit=limit,
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
    )
