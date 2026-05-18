from datetime import datetime, timezone

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.mysql import JSON, LONGTEXT
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProductPromptProfile(SQLModel, table=True):
    __tablename__ = "product_prompt_profiles"
    __table_args__ = (
        UniqueConstraint("product_id", name="uq_product_prompt_profile_product"),
    )

    profile_id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.product_id", index=True, nullable=False)
    focus_dimensions: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    analysis_style: str | None = Field(default=None, sa_column=Column(LONGTEXT, nullable=True))
    extra_instruction: str | None = Field(default=None, sa_column=Column(LONGTEXT, nullable=True))
    output_preference: str | None = Field(default=None, sa_column=Column(LONGTEXT, nullable=True))
    is_active: int = Field(default=1, nullable=False)
    create_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
