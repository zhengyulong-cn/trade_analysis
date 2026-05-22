from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TradeThought(SQLModel, table=True):
    __tablename__ = "trade_thoughts"

    thought_id: int | None = Field(default=None, primary_key=True)
    title: str | None = Field(default=None, max_length=200)
    categories: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1, max_length=5000)
    codes: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    images: list[dict] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
