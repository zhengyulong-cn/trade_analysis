from fastapi import APIRouter, status

from app.api.dependencies import TradeRecordColumnServiceDep
from app.schemas.trade_record_column import (
    TradeRecordColumnCreate,
    TradeRecordColumnDeleteRequest,
    TradeRecordColumnRead,
    TradeRecordColumnUpdate,
)

router = APIRouter()


@router.get("", response_model=list[TradeRecordColumnRead])
def list_trade_record_columns(service: TradeRecordColumnServiceDep) -> list[TradeRecordColumnRead]:
    return [TradeRecordColumnRead.model_validate(item) for item in service.list_trade_record_columns()]


@router.post("/create", response_model=TradeRecordColumnRead, status_code=status.HTTP_201_CREATED)
def create_trade_record_column(
    payload: TradeRecordColumnCreate,
    service: TradeRecordColumnServiceDep,
) -> TradeRecordColumnRead:
    return TradeRecordColumnRead.model_validate(service.create_trade_record_column(payload))


@router.post("/update", response_model=TradeRecordColumnRead)
def update_trade_record_column(
    payload: TradeRecordColumnUpdate,
    service: TradeRecordColumnServiceDep,
) -> TradeRecordColumnRead:
    return TradeRecordColumnRead.model_validate(service.update_trade_record_column(payload))


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade_record_column(
    payload: TradeRecordColumnDeleteRequest,
    service: TradeRecordColumnServiceDep,
) -> None:
    service.delete_trade_record_column(payload.column_id)
