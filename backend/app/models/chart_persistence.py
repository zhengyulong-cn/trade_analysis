from datetime import datetime, timezone

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChartPersistence(SQLModel, table=True):
    __tablename__ = "chart_persistences"
    __table_args__ = (
        UniqueConstraint(
            "user_key",
            "symbol",
            "interval",
            name="uq_chart_persistence_user_symbol_interval",
        ),
    )

    persistence_id: int | None = Field(default=None, primary_key=True)
    user_key: str = Field(default="default", max_length=100, nullable=False)
    symbol: str = Field(index=True, min_length=1, max_length=100)
    interval: str = Field(index=True, min_length=1, max_length=50)
    drawings_content: str | None = Field(
        default=None,
        sa_column=Column(LONGTEXT, nullable=True),
    )
    create_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
