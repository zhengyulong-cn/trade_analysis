from datetime import datetime

from pydantic import ConfigDict, field_validator
from sqlmodel import SQLModel


class FutureFundamentalAnalysisBase(SQLModel):
    product_id: int
    report_id: int
    supply_side: str | None = None
    demand_side: str | None = None
    inventory_side: str | None = None
    industry_profit: str | None = None
    substitution_linkage: str | None = None
    policy_macro: str | None = None
    conclusion: str | None = None

    @field_validator(
        "supply_side",
        "demand_side",
        "inventory_side",
        "industry_profit",
        "substitution_linkage",
        "policy_macro",
        "conclusion",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("field must be a string")
        cleaned = value.strip()
        return cleaned or None


class FutureFundamentalAnalysisCreate(FutureFundamentalAnalysisBase):
    pass


class FutureFundamentalAnalysisUpdate(SQLModel):
    analysis_id: int
    product_id: int | None = None
    report_id: int | None = None
    supply_side: str | None = None
    demand_side: str | None = None
    inventory_side: str | None = None
    industry_profit: str | None = None
    substitution_linkage: str | None = None
    policy_macro: str | None = None
    conclusion: str | None = None

    @field_validator(
        "supply_side",
        "demand_side",
        "inventory_side",
        "industry_profit",
        "substitution_linkage",
        "policy_macro",
        "conclusion",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("field must be a string")
        cleaned = value.strip()
        return cleaned or None


class FutureFundamentalAnalysisDeleteRequest(SQLModel):
    analysis_id: int


class FutureFundamentalAnalysisRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: int
    product_id: int
    report_id: int
    supply_side: str | None
    demand_side: str | None
    inventory_side: str | None
    industry_profit: str | None
    substitution_linkage: str | None
    policy_macro: str | None
    conclusion: str | None
    create_at: datetime
    updated_at: datetime


class FutureFundamentalAnalysisListItem(FutureFundamentalAnalysisRead):
    product_code: str
    product_display_name: str
    report_name: str
    report_storage_path: str
