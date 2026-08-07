from datetime import datetime
from typing import Any, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator
from sqlmodel import SQLModel


OpportunityReviewColumnDataType = Literal[
    "bool",
    "string",
    "number",
    "datetime",
    "single_select",
    "multi_select",
    "images",
]


class OpportunityReviewColumnBase(SQLModel):
    column_key: str = Field(min_length=1, max_length=100)
    column_label: str = Field(min_length=1, max_length=100)
    data_type: OpportunityReviewColumnDataType
    table_column_width: int | None = Field(default=None)
    is_required: bool = False
    is_enabled: bool = True
    sort_order: int = 0
    options_json: list[dict[str, Any]] = Field(default_factory=list)

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

    @model_validator(mode="after")
    def force_empty_options_for_images(self):
        if self.data_type == "images":
            self.options_json = []
        return self


class OpportunityReviewColumnCreate(OpportunityReviewColumnBase):
    pass


class OpportunityReviewColumnUpdate(SQLModel):
    column_id: int
    column_key: str | None = Field(default=None, min_length=1, max_length=100)
    column_label: str | None = Field(default=None, min_length=1, max_length=100)
    data_type: OpportunityReviewColumnDataType | None = None
    table_column_width: int | None = Field(default=None)
    is_required: bool | None = None
    is_enabled: bool | None = None
    sort_order: int | None = None
    options_json: list[dict[str, Any]] | None = None

    @field_validator("column_key", "column_label", mode="before")
    @classmethod
    def strip_string_value(cls, value: str | None):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def force_empty_options_for_images(self):
        if self.data_type == "images":
            self.options_json = []
        return self


class OpportunityReviewColumnDeleteRequest(SQLModel):
    column_id: int


class OpportunityReviewColumnRead(OpportunityReviewColumnBase):
    model_config = ConfigDict(from_attributes=True)

    column_id: int
    created_at: datetime
    updated_at: datetime
