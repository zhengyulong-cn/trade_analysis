from datetime import datetime

from pydantic import ConfigDict, field_validator
from sqlmodel import Field, SQLModel


class ProductPromptProfileBase(SQLModel):
    product_id: int
    focus_dimensions: list[str] = Field(default_factory=list)
    analysis_style: str | None = None
    extra_instruction: str | None = None
    output_preference: str | None = None
    is_active: int = 1

    @field_validator("focus_dimensions", mode="before")
    @classmethod
    def normalize_focus_dimensions(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("focus_dimensions must be a list")
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    @field_validator("analysis_style", "extra_instruction", "output_preference", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ProductPromptProfileCreate(ProductPromptProfileBase):
    pass


class ProductPromptProfileUpdate(SQLModel):
    profile_id: int
    focus_dimensions: list[str] | None = None
    analysis_style: str | None = None
    extra_instruction: str | None = None
    output_preference: str | None = None
    is_active: int | None = None

    @field_validator("focus_dimensions", mode="before")
    @classmethod
    def normalize_focus_dimensions(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("focus_dimensions must be a list")
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    @field_validator("analysis_style", "extra_instruction", "output_preference", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ProductPromptProfileDeleteRequest(SQLModel):
    profile_id: int


class ProductPromptProfileRead(ProductPromptProfileBase):
    model_config = ConfigDict(from_attributes=True)

    profile_id: int
    create_at: datetime
    updated_at: datetime
