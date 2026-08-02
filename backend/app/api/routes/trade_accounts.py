from fastapi import APIRouter, status

from app.api.dependencies import TradeAccountServiceDep
from app.schemas.trade_account import (
    TradeAccountCreate,
    TradeAccountDeleteRequest,
    TradeAccountRead,
    TradeAccountUpdate,
)

router = APIRouter()


@router.get("", response_model=list[TradeAccountRead])
def list_trade_accounts(service: TradeAccountServiceDep) -> list[TradeAccountRead]:
    return [TradeAccountRead.model_validate(item) for item in service.list_trade_accounts()]


@router.post("/create", response_model=TradeAccountRead, status_code=status.HTTP_201_CREATED)
def create_trade_account(
    payload: TradeAccountCreate,
    service: TradeAccountServiceDep,
) -> TradeAccountRead:
    return TradeAccountRead.model_validate(service.create_trade_account(payload))


@router.post("/update", response_model=TradeAccountRead)
def update_trade_account(
    payload: TradeAccountUpdate,
    service: TradeAccountServiceDep,
) -> TradeAccountRead:
    return TradeAccountRead.model_validate(service.update_trade_account(payload))


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade_account(
    payload: TradeAccountDeleteRequest,
    service: TradeAccountServiceDep,
) -> None:
    service.delete_trade_account(payload.account_id)
