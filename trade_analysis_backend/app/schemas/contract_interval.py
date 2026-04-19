from pydantic import ConfigDict
from sqlmodel import SQLModel


class ContractIntervalBase(SQLModel):
    contract_interval_name: str
    seconds: int
    description: str | None = None


class ContractIntervalCreate(ContractIntervalBase):
    pass


class ContractIntervalRead(ContractIntervalBase):
    model_config = ConfigDict(from_attributes=True)

    contract_interval_id: int
