from datetime import datetime, timezone

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FutureFundamentalAnalysis(SQLModel, table=True):
    __tablename__ = "future_fundamental_analyses"

    analysis_id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(index=True, nullable=False, foreign_key="future_products.product_id")
    report_id: int = Field(
        index=True,
        nullable=False,
        foreign_key="future_report_documents.report_id",
    )
    supply_side: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    demand_side: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    inventory_side: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    industry_profit: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    substitution_linkage: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    policy_macro: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    conclusion: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    create_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
