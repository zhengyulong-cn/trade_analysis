from datetime import datetime

from pydantic import ConfigDict, Field, field_validator
from sqlmodel import SQLModel


class TradeThoughtImage(SQLModel):
    path: str = Field(min_length=1, max_length=255)
    original_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    size: int = Field(ge=0)


class TradeThoughtBase(SQLModel):
    title: str | None = Field(default=None, max_length=200)
    categories: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1, max_length=5000)
    codes: list[str] = Field(default_factory=list)
    images: list[TradeThoughtImage] = Field(default_factory=list)

    @field_validator("title", "categories", "content", mode="before")
    @classmethod
    def strip_string_value(cls, value: str | None):
        if value is None:
            return None
        return value.strip()

    @field_validator("codes", mode="before")
    @classmethod
    def normalize_codes(cls, value: list[str] | None):
        if not value:
            return []
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            text = str(item).strip()
            if not text or text in seen:
                continue
            normalized.append(text)
            seen.add(text)
        return normalized


class TradeThoughtCreate(TradeThoughtBase):
    pass


class TradeThoughtUpdate(SQLModel):
    thought_id: int
    title: str | None = Field(default=None, max_length=200)
    categories: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=5000)
    codes: list[str] | None = None
    images: list[TradeThoughtImage] | None = None

    @field_validator("title", "categories", "content", mode="before")
    @classmethod
    def strip_string_value(cls, value: str | None):
        if value is None:
            return None
        return value.strip()

    @field_validator("codes", mode="before")
    @classmethod
    def normalize_codes(cls, value: list[str] | None):
        if value is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            text = str(item).strip()
            if not text or text in seen:
                continue
            normalized.append(text)
            seen.add(text)
        return normalized


class TradeThoughtDeleteRequest(SQLModel):
    thought_id: int


class TradeThoughtRead(TradeThoughtBase):
    model_config = ConfigDict(from_attributes=True)

    thought_id: int
    created_at: datetime
    updated_at: datetime


class TradeThoughtImageUploadResult(TradeThoughtImage):
    url: str
