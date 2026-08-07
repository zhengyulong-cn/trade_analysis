from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, field_validator
from sqlmodel import SQLModel


class OpportunityReviewBase(SQLModel):
    data_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("data_json", mode="before")
    @classmethod
    def normalize_data_json(cls, value: Any):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise TypeError("data_json must be an object")
        return value


class OpportunityReviewCreate(OpportunityReviewBase):
    pass


class OpportunityReviewUpdate(SQLModel):
    opportunity_review_id: int
    data_json: dict[str, Any] | None = None

    @field_validator("data_json", mode="before")
    @classmethod
    def normalize_data_json(cls, value: Any):
        if value is None:
            return None
        if not isinstance(value, dict):
            raise TypeError("data_json must be an object")
        return value


class OpportunityReviewDeleteRequest(SQLModel):
    opportunity_review_id: int


class OpportunityReviewRead(OpportunityReviewBase):
    model_config = ConfigDict(from_attributes=True)

    opportunity_review_id: int
    created_at: datetime
    updated_at: datetime
