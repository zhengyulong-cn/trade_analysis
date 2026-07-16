from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import SignalFilterServiceDep
from app.schemas.signal_filter import AllContractSignalResult, ContractSignalResult


router = APIRouter()


@router.get("/item", response_model=ContractSignalResult)
def filter_signals(
    symbol: str,
    interval: int,
    service: SignalFilterServiceDep,
    limit: Annotated[int, Query(ge=2, le=5000)] = 50,
) -> ContractSignalResult:
    return service.filter_signals(symbol, interval, limit)


@router.get("/all", response_model=AllContractSignalResult)
def filter_all_signals(
    interval: int,
    service: SignalFilterServiceDep,
    limit: Annotated[int, Query(ge=2, le=5000)] = 50,
) -> AllContractSignalResult:
    return service.filter_all_signals(interval, limit)
