from datetime import datetime

from pydantic import ConfigDict
from sqlmodel import SQLModel


class ContractBase(SQLModel):
    symbol: str
    exchange: str
    name: str
    # 0表示股票，1表示多个股票构成的指数，2表示期货合约，3表示多个期货合约构成的指数
    product_type: int


class ContractCreate(ContractBase):
    pass


class ContractRead(ContractBase):
    model_config = ConfigDict(from_attributes=True)

    contract_id: int
    create_at: datetime
    updated_at: datetime
