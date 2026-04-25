from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Contract(SQLModel, table=True):
    __tablename__ = "contracts"
    __table_args__ = (
        UniqueConstraint("symbol", "exchange", name="uq_contract_symbol_exchange"),
    )

    contract_id: int | None = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, min_length=1, max_length=50)
    exchange: str = Field(index=True, min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    auto_load_segments: int = Field(default=0, nullable=False)
    create_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
