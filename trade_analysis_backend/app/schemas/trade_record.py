from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import ConfigDict, Field, model_validator
from sqlmodel import SQLModel

SegmentType = Literal["trend_push", "trend_pullback", "range_internal"]
TradeRecordOpenDirection = Literal["long", "short"]


class TradeRecordScreenshot(SQLModel):
    path: str = Field(min_length=1, max_length=255)
    original_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    size: int = Field(ge=0)


class TradeRecordBase(SQLModel):
    contract: str = Field(min_length=1, max_length=50)
    open_direction: TradeRecordOpenDirection
    lots: int = Field(ge=0)
    open_time: datetime
    open_price: Decimal
    close_time: datetime
    close_price: Decimal
    segment_type: SegmentType | None = None
    fee: Decimal = 0
    actual_pnl: Decimal
    screenshots: list[TradeRecordScreenshot] = Field(default_factory=list)
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.close_time < self.open_time:
            raise ValueError("close_time must be greater than or equal to open_time")
        return self


class TradeRecordCreate(TradeRecordBase):
    segment_type: SegmentType


class TradeRecordUpdate(SQLModel):
    trade_record_id: int
    contract: str | None = Field(default=None, min_length=1, max_length=50)
    open_direction: TradeRecordOpenDirection | None = None
    lots: int | None = Field(default=None, ge=0)
    open_time: datetime | None = None
    open_price: Decimal | None = None
    close_time: datetime | None = None
    close_price: Decimal | None = None
    segment_type: SegmentType | None = None
    fee: Decimal | None = None
    actual_pnl: Decimal | None = None
    screenshots: list[TradeRecordScreenshot] | None = None
    comment: str | None = Field(default=None, max_length=2000)


class TradeRecordDeleteRequest(SQLModel):
    trade_record_id: int


class TradeRecordRead(TradeRecordBase):
    model_config = ConfigDict(from_attributes=True)

    trade_record_id: int
    import_open_trade_no: str | None = None
    import_close_trade_no: str | None = None
    created_at: datetime
    updated_at: datetime


class TradeRecordListQuery(SQLModel):
    contract: str | None = None
    open_direction: TradeRecordOpenDirection | None = None
    segment_type: SegmentType | None = None
    open_time_start: datetime | None = None
    open_time_end: datetime | None = None
    close_time_start: datetime | None = None
    close_time_end: datetime | None = None


class TradeRecordScreenshotUploadResult(TradeRecordScreenshot):
    url: str


class TradeRecordImportResult(SQLModel):
    imported: int
    skipped: int
    failed: int
    message: str
