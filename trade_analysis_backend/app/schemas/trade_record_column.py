from datetime import datetime
from typing import Any, Literal

from pydantic import ConfigDict, Field, field_validator
from sqlmodel import SQLModel


TradeRecordColumnDataType = Literal[
    "bool",
    "string",
    "number",
    "datetime",
    "single_select",
    "multi_select",
    "images",
]
TradeRecordColumnOptionSourceType = Literal["static", "outer"]

class TradeRecordColumnBase(SQLModel):
    column_key: str = Field(min_length=1, max_length=100)
    column_label: str = Field(min_length=1, max_length=100)
    data_type: TradeRecordColumnDataType
    option_source_type: TradeRecordColumnOptionSourceType = "static"
    is_required: bool = False
    is_enabled: bool = True
    sort_order: int = 0
    options_json: list[dict[str, Any]] = Field(default_factory=list)
    option_source_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("column_key", "column_label", mode="before")
    @classmethod
    def strip_string_value(cls, value: str):
        return value.strip() if isinstance(value, str) else value

    @field_validator("column_key")
    @classmethod
    def normalize_column_key(cls, value: str):
        return value.strip()

    @field_validator("options_json", mode="before")
    @classmethod
    def normalize_options(cls, value: Any):
        if value is None:
            return []
        return value

    @field_validator("option_source_config", mode="before")
    @classmethod
    def normalize_option_source_config(cls, value: Any):
        if value is None:
            return {}
        return value


class TradeRecordColumnCreate(TradeRecordColumnBase):
    pass


class TradeRecordColumnUpdate(SQLModel):
    column_id: int
    column_key: str | None = Field(default=None, min_length=1, max_length=100)
    column_label: str | None = Field(default=None, min_length=1, max_length=100)
    data_type: TradeRecordColumnDataType | None = None
    option_source_type: TradeRecordColumnOptionSourceType | None = None
    is_required: bool | None = None
    is_enabled: bool | None = None
    sort_order: int | None = None
    options_json: list[dict[str, Any]] | None = None
    option_source_config: dict[str, Any] | None = None

    @field_validator("column_key", "column_label", mode="before")
    @classmethod
    def strip_string_value(cls, value: str | None):
        return value.strip() if isinstance(value, str) else value

    @field_validator("option_source_config", mode="before")
    @classmethod
    def normalize_update_option_source_config(cls, value: Any):
        if value is None:
            return None
        return value


class TradeRecordColumnDeleteRequest(SQLModel):
    column_id: int


class TradeRecordColumnRead(TradeRecordColumnBase):
    model_config = ConfigDict(from_attributes=True)

    column_id: int
    created_at: datetime
    updated_at: datetime
