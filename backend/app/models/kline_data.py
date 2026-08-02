from datetime import datetime
from decimal import Decimal

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class KlineData(SQLModel, table=True):
    __tablename__ = "kline_data"
    __table_args__ = (
        UniqueConstraint(
            "contract_id",
            "date_time",
            name="uq_kline_contract_date_time",
        ),
    )

    kline_id: int | None = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contracts.contract_id", index=True)
    open: Decimal = Field(max_digits=20, decimal_places=6)
    close: Decimal = Field(max_digits=20, decimal_places=6)
    high: Decimal = Field(max_digits=20, decimal_places=6)
    low: Decimal = Field(max_digits=20, decimal_places=6)
    volume: Decimal = Field(default=0, max_digits=20, decimal_places=6)
    hold: Decimal = Field(default=0, max_digits=20, decimal_places=6)
    date_time: datetime = Field(index=True)
