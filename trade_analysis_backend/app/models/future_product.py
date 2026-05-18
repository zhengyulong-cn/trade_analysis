from datetime import datetime, timezone

from sqlalchemy import Column
from sqlalchemy.dialects.mysql import JSON
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FutureProduct(SQLModel, table=True):
    __tablename__ = "future_products"

    product_id: int | None = Field(default=None, primary_key=True)
    product_code: str = Field(index=True, min_length=1, max_length=50)
    display_name: str = Field(min_length=1, max_length=100)
    alias_names: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    create_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
