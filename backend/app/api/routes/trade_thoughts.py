from fastapi import APIRouter, File, UploadFile, status

from app.api.dependencies import TradeThoughtServiceDep, TradeThoughtStorageServiceDep
from app.schemas.trade_thought import (
    TradeThoughtCreate,
    TradeThoughtDeleteRequest,
    TradeThoughtImageUploadResult,
    TradeThoughtRead,
    TradeThoughtUpdate,
)

router = APIRouter()


@router.get("", response_model=list[TradeThoughtRead])
def list_trade_thoughts(service: TradeThoughtServiceDep) -> list[TradeThoughtRead]:
    return [TradeThoughtRead.model_validate(item) for item in service.list_trade_thoughts()]


@router.post("/create", response_model=TradeThoughtRead, status_code=status.HTTP_201_CREATED)
def create_trade_thought(
    payload: TradeThoughtCreate,
    service: TradeThoughtServiceDep,
) -> TradeThoughtRead:
    return TradeThoughtRead.model_validate(service.create_trade_thought(payload))


@router.post("/update", response_model=TradeThoughtRead)
def update_trade_thought(
    payload: TradeThoughtUpdate,
    service: TradeThoughtServiceDep,
) -> TradeThoughtRead:
    return TradeThoughtRead.model_validate(service.update_trade_thought(payload))


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade_thought(
    payload: TradeThoughtDeleteRequest,
    service: TradeThoughtServiceDep,
) -> None:
    service.delete_trade_thought(payload.thought_id)


@router.post("/upload-image", response_model=TradeThoughtImageUploadResult)
async def upload_trade_thought_image(
    storage_service: TradeThoughtStorageServiceDep,
    file: UploadFile = File(...),
) -> TradeThoughtImageUploadResult:
    result = await storage_service.save_image(file)
    return TradeThoughtImageUploadResult(**result)
