from fastapi import APIRouter, status

from app.api.dependencies import TradeRecordServiceDep
from app.schemas.trade_record import (
    TradeRecordCreate,
    TradeRecordDeleteRequest,
    TradeRecordRead,
    TradeRecordUpdate,
)

router = APIRouter()


@router.get("", response_model=list[TradeRecordRead])
def list_trade_records(service: TradeRecordServiceDep) -> list[TradeRecordRead]:
    return [TradeRecordRead.model_validate(item) for item in service.list_trade_records()]


@router.post("/create", response_model=TradeRecordRead, status_code=status.HTTP_201_CREATED)
def create_trade_record(
    payload: TradeRecordCreate,
    service: TradeRecordServiceDep,
) -> TradeRecordRead:
    return TradeRecordRead.model_validate(service.create_trade_record(payload))


@router.post("/update", response_model=TradeRecordRead)
def update_trade_record(
    payload: TradeRecordUpdate,
    service: TradeRecordServiceDep,
) -> TradeRecordRead:
    return TradeRecordRead.model_validate(service.update_trade_record(payload))


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade_record(
    payload: TradeRecordDeleteRequest,
    service: TradeRecordServiceDep,
) -> None:
    service.delete_trade_record(payload.trade_record_id)
