from datetime import datetime

from pydantic import ConfigDict
from sqlmodel import SQLModel


class ContractBase(SQLModel):
    symbol: str
    exchange: str
    name: str
    auto_load_segments: int = 0


class ContractCreate(ContractBase):
    pass


class ContractUpdate(SQLModel):
    contract_id: int
    symbol: str | None = None
    exchange: str | None = None
    name: str | None = None
    auto_load_segments: int | None = None


class ContractRead(ContractBase):
    model_config = ConfigDict(from_attributes=True)

    contract_id: int
    create_at: datetime
    updated_at: datetime
