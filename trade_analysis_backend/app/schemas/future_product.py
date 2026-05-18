from datetime import datetime

from pydantic import ConfigDict, field_validator
from sqlmodel import SQLModel


class FutureProductBase(SQLModel):
    product_code: str
    display_name: str
    alias_names: list[str] = []

    @field_validator("product_code", "display_name", mode="before")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("field must be a string")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("field cannot be empty")
        return cleaned

    @field_validator("alias_names", mode="before")
    @classmethod
    def normalize_alias_names(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("alias_names must be a list")
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                raise ValueError("alias_names items must be strings")
            cleaned = item.strip()
            lowered = cleaned.lower()
            if cleaned and lowered not in seen:
                normalized.append(cleaned)
                seen.add(lowered)
        return normalized


class FutureProductCreate(FutureProductBase):
    pass


class FutureProductUpdate(SQLModel):
    product_id: int
    product_code: str | None = None
    display_name: str | None = None
    alias_names: list[str] | None = None

    @field_validator("product_code", "display_name", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("field must be a string")
        cleaned = value.strip()
        return cleaned or None

    @field_validator("alias_names", mode="before")
    @classmethod
    def normalize_optional_alias_names(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("alias_names must be a list")
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                raise ValueError("alias_names items must be strings")
            cleaned = item.strip()
            lowered = cleaned.lower()
            if cleaned and lowered not in seen:
                normalized.append(cleaned)
                seen.add(lowered)
        return normalized


class FutureProductRead(FutureProductBase):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    create_at: datetime
    updated_at: datetime
