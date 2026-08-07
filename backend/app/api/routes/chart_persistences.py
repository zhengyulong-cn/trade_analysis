from fastapi import APIRouter

from app.api.dependencies import ChartPersistenceServiceDep
from app.schemas.chart_persistence import ChartPersistenceRead, ChartPersistenceSave

router = APIRouter()


@router.get("", response_model=ChartPersistenceRead)
def get_chart_persistence(
    symbol: str,
    interval: str,
    service: ChartPersistenceServiceDep,
) -> ChartPersistenceRead:
    return ChartPersistenceRead.model_validate(
        service.get_persistence(symbol=symbol, interval=interval)
    )


@router.post("/save", response_model=ChartPersistenceRead)
def save_chart_persistence(
    payload: ChartPersistenceSave,
    service: ChartPersistenceServiceDep,
) -> ChartPersistenceRead:
    return ChartPersistenceRead.model_validate(service.save_persistence(payload))
