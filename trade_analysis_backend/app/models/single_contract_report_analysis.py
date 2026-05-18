from datetime import datetime, timezone

from sqlalchemy import Column
from sqlalchemy.dialects.mysql import JSON, LONGTEXT
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SingleContractReportAnalysis(SQLModel, table=True):
    __tablename__ = "single_product_report_analyses"

    analysis_id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.product_id", index=True, nullable=False)
    report_id: int = Field(foreign_key="report_documents.report_id", index=True, nullable=False)
    profile_id: int | None = Field(
        default=None,
        foreign_key="product_prompt_profiles.profile_id",
        index=True,
        nullable=True,
    )
    product_code: str = Field(min_length=1, max_length=50, nullable=False)
    product_name: str = Field(min_length=1, max_length=100, nullable=False)
    report_title: str = Field(min_length=1, max_length=255, nullable=False)
    report_source: str | None = Field(default=None, max_length=255)
    status: str = Field(default="success", min_length=1, max_length=50, nullable=False)
    error_message: str | None = Field(
        default=None,
        sa_column=Column(LONGTEXT, nullable=True),
    )
    profile_snapshot: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    matched_snippets: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    result_json: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    system_prompt: str = Field(sa_column=Column(LONGTEXT, nullable=False))
    user_prompt: str = Field(sa_column=Column(LONGTEXT, nullable=False))
    create_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
