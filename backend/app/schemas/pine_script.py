from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field, field_validator
from sqlmodel import SQLModel


PineScriptType = Literal["indicator", "strategy", "scanner"]


class PineScriptBase(SQLModel):
    script_name: str = Field(min_length=1, max_length=200)
    script_content: str = Field(min_length=1)
    script_type: PineScriptType

    @field_validator("script_name", mode="before")
    @classmethod
    def strip_script_name(cls, value: str):
        return value.strip() if isinstance(value, str) else value

    @field_validator("script_content", mode="before")
    @classmethod
    def validate_script_content(cls, value: str):
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("Script content cannot be blank")
            return value
        return value


class PineScriptCreate(PineScriptBase):
    pass


class PineScriptUpdate(SQLModel):
    script_id: int
    script_name: str | None = Field(default=None, min_length=1, max_length=200)
    script_content: str | None = Field(default=None, min_length=1)
    script_type: PineScriptType | None = None

    @field_validator("script_name", mode="before")
    @classmethod
    def strip_script_name(cls, value: str | None):
        return value.strip() if isinstance(value, str) else value

    @field_validator("script_content", mode="before")
    @classmethod
    def validate_script_content(cls, value: str | None):
        if value is None:
            return value
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("Script content cannot be blank")
            return value
        return value


class PineScriptDeleteRequest(SQLModel):
    script_id: int


class PineScriptRead(PineScriptBase):
    model_config = ConfigDict(from_attributes=True)

    script_id: int
    created_at: datetime
    updated_at: datetime
