from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import ConfigDict, Field, model_validator
from sqlmodel import SQLModel

SegmentType = Literal["trend_push", "trend_pullback", "range_internal", "false_break_range_transition"]
OpenSignalType = Literal[
    "ema20_resistance_key_level_confirmed",
    "ema120_resistance_head_shoulders",
    "ema120_resistance_three_push_wedge",
    "ema120_resistance_range_break_pullback",
    "range_edge_multiple_breakout_failures",
    "not_matching_open_signal",
]
TradeRecordOpenDirection = Literal["long", "short"]
TradeRecordSource = Literal["manual", "import"]


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
    close_time: datetime | None = None
    close_price: Decimal | None = None
    segment_type: SegmentType | None = None
    open_signal: OpenSignalType | None = None
    fee: Decimal = 0
    actual_pnl: Decimal | None = None
    screenshots: list[TradeRecordScreenshot] = Field(default_factory=list)
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_time_range(self):
        has_close_time = self.close_time is not None
        has_close_price = self.close_price is not None
        if has_close_time != has_close_price:
            raise ValueError("close_time and close_price must both be provided or both be empty")
        if self.close_time is not None and self.close_time < self.open_time:
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
    open_signal: OpenSignalType | None = None
    fee: Decimal | None = None
    actual_pnl: Decimal | None = None
    screenshots: list[TradeRecordScreenshot] | None = None
    comment: str | None = Field(default=None, max_length=2000)


class TradeRecordDeleteRequest(SQLModel):
    trade_record_id: int


class TradeRecordMergeRequest(SQLModel):
    trade_record_ids: list[int] = Field(min_length=2)


class TradeRecordRead(TradeRecordBase):
    model_config = ConfigDict(from_attributes=True)

    trade_record_id: int
    source: TradeRecordSource
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
