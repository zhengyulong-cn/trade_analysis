from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field, field_validator
from sqlmodel import SQLModel


TradeAccountType = Literal["real", "simulated"]


class TradeAccountBase(SQLModel):
    account_name: str = Field(min_length=1, max_length=100)
    account_type: TradeAccountType
    account_no: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=255)

    @field_validator("account_name", "account_no", "password", mode="before")
    @classmethod
    def strip_string_value(cls, value: str):
        return value.strip() if isinstance(value, str) else value


class TradeAccountCreate(TradeAccountBase):
    pass


class TradeAccountUpdate(SQLModel):
    account_id: int
    account_name: str | None = Field(default=None, min_length=1, max_length=100)
    account_type: TradeAccountType | None = None
    account_no: str | None = Field(default=None, min_length=1, max_length=100)
    password: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("account_name", "account_no", "password", mode="before")
    @classmethod
    def strip_string_value(cls, value: str | None):
        return value.strip() if isinstance(value, str) else value


class TradeAccountDeleteRequest(SQLModel):
    account_id: int


class TradeAccountRead(TradeAccountBase):
    model_config = ConfigDict(from_attributes=True)

    account_id: int
    created_at: datetime
    updated_at: datetime
