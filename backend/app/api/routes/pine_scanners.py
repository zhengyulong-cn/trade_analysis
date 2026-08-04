from fastapi import APIRouter

from app.api.dependencies import PineScannerServiceDep
from app.schemas.pine_indicator import (
    PineScannerExecuteRequest,
    PineScannerExecuteResponse,
)

router = APIRouter()


@router.post("/execute", response_model=PineScannerExecuteResponse)
def execute_pine_scanner(
    payload: PineScannerExecuteRequest,
    service: PineScannerServiceDep,
) -> PineScannerExecuteResponse:
    return service.execute(payload)
