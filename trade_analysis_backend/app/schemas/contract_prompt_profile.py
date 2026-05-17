from datetime import datetime

from pydantic import ConfigDict, field_validator
from sqlmodel import Field, SQLModel


class ContractPromptProfileBase(SQLModel):
    contract_id: int
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

        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("focus_dimensions items must be strings")
            cleaned = item.strip()
            if cleaned:
                normalized.append(cleaned)
        return normalized

    @field_validator("analysis_style", "extra_instruction", "output_preference", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ContractPromptProfileCreate(ContractPromptProfileBase):
    pass


class ContractPromptProfileUpdate(SQLModel):
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

        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("focus_dimensions items must be strings")
            cleaned = item.strip()
            if cleaned:
                normalized.append(cleaned)
        return normalized

    @field_validator("analysis_style", "extra_instruction", "output_preference", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ContractPromptProfileDeleteRequest(SQLModel):
    profile_id: int


class ContractPromptProfileRead(ContractPromptProfileBase):
    model_config = ConfigDict(from_attributes=True)

    profile_id: int
    create_at: datetime
    updated_at: datetime
