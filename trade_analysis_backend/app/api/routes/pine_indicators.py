from fastapi import APIRouter

from app.api.dependencies import PineIndicatorServiceDep
from app.schemas.pine_indicator import (
    PineIndicatorExecuteRequest,
    PineIndicatorExecuteResponse,
)

router = APIRouter()


@router.post("/execute", response_model=PineIndicatorExecuteResponse)
def execute_pine_indicator(
    payload: PineIndicatorExecuteRequest,
    service: PineIndicatorServiceDep,
) -> PineIndicatorExecuteResponse:
    return service.execute(payload)
