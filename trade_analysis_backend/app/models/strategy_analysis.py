from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class StrategyAnalysis(SQLModel, table=True):
    __tablename__ = "strategy_analysis"
    __table_args__ = (
        UniqueConstraint("contract_id", name="uq_strategy_analysis_contract_id"),
    )

    strategy_id: int | None = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contracts.contract_id", index=True)
    strategy: str = Field(
        default="{}",
        sa_column=Column(Text, nullable=False),
    )
