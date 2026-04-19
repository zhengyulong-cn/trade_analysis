from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class ContractInterval(SQLModel, table=True):
    __tablename__ = "contracts_intervals"
    __table_args__ = (
        UniqueConstraint(
            "contract_interval_name",
            name="uq_contract_interval_name",
        ),
        UniqueConstraint("seconds", name="uq_contract_interval_seconds"),
    )

    contract_interval_id: int | None = Field(default=None, primary_key=True)
    contract_interval_name: str = Field(index=True, min_length=1, max_length=50)
    seconds: int = Field(index=True, gt=0)
    description: str | None = Field(default=None, max_length=255)
