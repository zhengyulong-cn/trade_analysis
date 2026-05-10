from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.trade_record import TradeRecord
from app.schemas.trade_record import (
    TradeRecordCreate,
    TradeRecordListQuery,
    TradeRecordUpdate,
)
from app.services.trade_record_storage import TradeRecordStorageService


class TradeRecordService:
    def __init__(self, session: Session, storage_service: TradeRecordStorageService):
        self.session = session
        self.storage_service = storage_service

    def list_trade_records(self, query: TradeRecordListQuery) -> list[TradeRecord]:
        statement = select(TradeRecord)

        if query.contract:
            statement = statement.where(TradeRecord.contract.contains(query.contract.strip()))
        if query.segment_type:
            statement = statement.where(TradeRecord.segment_type == query.segment_type)
        if query.open_time_start:
            statement = statement.where(TradeRecord.open_time >= query.open_time_start)
        if query.open_time_end:
            statement = statement.where(TradeRecord.open_time <= query.open_time_end)
        if query.close_time_start:
            statement = statement.where(TradeRecord.close_time >= query.close_time_start)
        if query.close_time_end:
            statement = statement.where(TradeRecord.close_time <= query.close_time_end)

        statement = statement.order_by(TradeRecord.open_time.desc(), TradeRecord.trade_record_id.desc())
        return list(self.session.exec(statement).all())

    def create_trade_record(self, payload: TradeRecordCreate) -> TradeRecord:
        trade_record = TradeRecord.model_validate(payload)
        self.session.add(trade_record)
        self.session.commit()
        self.session.refresh(trade_record)
        return trade_record

    def update_trade_record(self, payload: TradeRecordUpdate) -> TradeRecord:
        trade_record = self.get_trade_record_by_id(payload.trade_record_id)
        update_data = payload.model_dump(exclude={"trade_record_id"}, exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No trade record fields to update",
            )

        old_screenshot_path = trade_record.screenshot_path
        remove_screenshot = bool(update_data.pop("remove_screenshot", False))

        for field_name, value in update_data.items():
            setattr(trade_record, field_name, value)

        if remove_screenshot:
            trade_record.screenshot_path = None
            trade_record.screenshot_original_name = None
            trade_record.screenshot_content_type = None
            trade_record.screenshot_size = None

        self._validate_time_range(trade_record.open_time, trade_record.close_time)

        trade_record.updated_at = datetime.now(timezone.utc)
        self.session.add(trade_record)
        self.session.commit()
        self.session.refresh(trade_record)

        if remove_screenshot and old_screenshot_path:
            self.storage_service.delete_relative_path(old_screenshot_path)
        elif (
            trade_record.screenshot_path
            and old_screenshot_path
            and trade_record.screenshot_path != old_screenshot_path
        ):
            self.storage_service.delete_relative_path(old_screenshot_path)

        return trade_record

    def delete_trade_record(self, trade_record_id: int) -> None:
        trade_record = self.get_trade_record_by_id(trade_record_id)
        screenshot_path = trade_record.screenshot_path
        self.session.delete(trade_record)
        self.session.commit()
        if screenshot_path:
            self.storage_service.delete_relative_path(screenshot_path)

    def get_trade_record_by_id(self, trade_record_id: int) -> TradeRecord:
        trade_record = self.session.get(TradeRecord, trade_record_id)
        if trade_record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade record not found: {trade_record_id}",
            )
        return trade_record

    def _validate_time_range(self, open_time: datetime, close_time: datetime) -> None:
        if close_time < open_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="close_time must be greater than or equal to open_time",
            )
