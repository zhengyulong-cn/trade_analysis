from datetime import datetime

from fastapi import APIRouter, File, Query, UploadFile, status

from app.api.dependencies import TradeRecordServiceDep, TradeRecordStorageServiceDep
from app.schemas.trade_record import (
    TradeRecordCreate,
    TradeRecordDeleteRequest,
    TradeRecordImportResult,
    TradeRecordListQuery,
    TradeRecordMergeRequest,
    TradeRecordRead,
    TradeRecordScreenshotUploadResult,
    TradeRecordUpdate,
)

router = APIRouter()


@router.get("", response_model=list[TradeRecordRead])
def list_trade_records(
    service: TradeRecordServiceDep,
    contract: str | None = Query(default=None),
    open_direction: str | None = Query(default=None),
    segment_type: str | None = Query(default=None),
    open_time_start: datetime | None = Query(default=None),
    open_time_end: datetime | None = Query(default=None),
    close_time_start: datetime | None = Query(default=None),
    close_time_end: datetime | None = Query(default=None),
) -> list[TradeRecordRead]:
    query = TradeRecordListQuery(
        contract=contract,
        open_direction=open_direction,
        segment_type=segment_type,
        open_time_start=open_time_start,
        open_time_end=open_time_end,
        close_time_start=close_time_start,
        close_time_end=close_time_end,
    )
    return [
        TradeRecordRead.model_validate(record)
        for record in service.list_trade_records(query)
    ]


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


@router.post("/merge", response_model=TradeRecordRead)
def merge_trade_records(
    payload: TradeRecordMergeRequest,
    service: TradeRecordServiceDep,
) -> TradeRecordRead:
    return TradeRecordRead.model_validate(service.merge_trade_records(payload))


@router.post("/upload-screenshot", response_model=TradeRecordScreenshotUploadResult)
async def upload_trade_record_screenshot(
    storage_service: TradeRecordStorageServiceDep,
    file: UploadFile = File(...),
) -> TradeRecordScreenshotUploadResult:
    result = await storage_service.save_screenshot(file)
    return TradeRecordScreenshotUploadResult(**result)


@router.post("/import", response_model=TradeRecordImportResult)
async def import_trade_records(
    service: TradeRecordServiceDep,
    file: UploadFile = File(...),
) -> TradeRecordImportResult:
    file_bytes = await file.read()
    return service.import_trade_records_from_excel(file_bytes, file.filename)
