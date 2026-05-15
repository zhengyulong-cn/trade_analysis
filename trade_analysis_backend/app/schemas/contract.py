from datetime import datetime

from pydantic import ConfigDict
from sqlmodel import SQLModel


class ContractBase(SQLModel):
    symbol: str
    exchange: str
    name: str
    is_favorite: int = 0


class ContractCreate(ContractBase):
    pass


class ContractUpdate(SQLModel):
    contract_id: int
    symbol: str | None = None
    exchange: str | None = None
    name: str | None = None
    is_favorite: int | None = None


class MainContractCandidateRead(SQLModel):
    symbol: str
    exchange: str
    provider_symbol: str
    name: str


class MainContractSyncItem(SQLModel):
    symbol: str
    exchange: str
    name: str


class MainContractSyncPayload(SQLModel):
    items: list[MainContractSyncItem]


class ContractRead(ContractBase):
    model_config = ConfigDict(from_attributes=True)

    contract_id: int
    create_at: datetime
    updated_at: datetime


class MainContractSyncResult(SQLModel):
    created: int
    updated: int
    items: list[ContractRead]
