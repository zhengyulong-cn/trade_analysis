from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import ConfigDict, Field, model_validator
from sqlmodel import SQLModel

SegmentType = Literal["趋势推动段", "趋势回调段", "区间内部段"]


class TradeRecordBase(SQLModel):
    contract: str = Field(min_length=1, max_length=50)
    lots: int = Field(ge=0)
    open_time: datetime
    open_price: Decimal
    close_time: datetime
    close_price: Decimal
    segment_type: SegmentType
    actual_pnl: Decimal
    screenshot_path: str | None = Field(default=None, max_length=255)
    screenshot_original_name: str | None = Field(default=None, max_length=255)
    screenshot_content_type: str | None = Field(default=None, max_length=100)
    screenshot_size: int | None = Field(default=None, ge=0)
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.close_time < self.open_time:
            raise ValueError("close_time must be greater than or equal to open_time")
        return self


class TradeRecordCreate(TradeRecordBase):
    pass


class TradeRecordUpdate(SQLModel):
    trade_record_id: int
    contract: str | None = Field(default=None, min_length=1, max_length=50)
    lots: int | None = Field(default=None, ge=0)
    open_time: datetime | None = None
    open_price: Decimal | None = None
    close_time: datetime | None = None
    close_price: Decimal | None = None
    segment_type: SegmentType | None = None
    actual_pnl: Decimal | None = None
    screenshot_path: str | None = Field(default=None, max_length=255)
    screenshot_original_name: str | None = Field(default=None, max_length=255)
    screenshot_content_type: str | None = Field(default=None, max_length=100)
    screenshot_size: int | None = Field(default=None, ge=0)
    comment: str | None = Field(default=None, max_length=2000)
    remove_screenshot: bool = False


class TradeRecordDeleteRequest(SQLModel):
    trade_record_id: int


class TradeRecordRead(TradeRecordBase):
    model_config = ConfigDict(from_attributes=True)

    trade_record_id: int
    created_at: datetime
    updated_at: datetime


class TradeRecordListQuery(SQLModel):
    contract: str | None = None
    segment_type: SegmentType | None = None
    open_time_start: datetime | None = None
    open_time_end: datetime | None = None
    close_time_start: datetime | None = None
    close_time_end: datetime | None = None


class TradeRecordScreenshotUploadResult(SQLModel):
    path: str
    original_name: str
    content_type: str
    size: int
    url: str
