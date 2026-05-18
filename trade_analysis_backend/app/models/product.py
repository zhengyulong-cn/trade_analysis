from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Product(SQLModel, table=True):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("product_code", "exchange", name="uq_product_code_exchange"),
    )

    product_id: int | None = Field(default=None, primary_key=True)
    product_code: str = Field(index=True, min_length=1, max_length=50)
    exchange: str = Field(index=True, min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    create_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
