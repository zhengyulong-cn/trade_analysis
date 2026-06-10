from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TradeRecordColumn(SQLModel, table=True):
    __tablename__ = "trade_record_columns"

    column_id: int | None = Field(default=None, primary_key=True)
    column_key: str = Field(min_length=1, max_length=100, nullable=False, index=True, unique=True)
    column_label: str = Field(min_length=1, max_length=100, nullable=False)
    data_type: str = Field(min_length=1, max_length=30, nullable=False, index=True)
    option_source_type: str = Field(default="static", min_length=1, max_length=20, nullable=False, index=True)
    is_required: bool = Field(default=False, nullable=False)
    is_enabled: bool = Field(default=True, nullable=False, index=True)
    sort_order: int = Field(default=0, nullable=False, index=True)
    options_json: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    option_source_config: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
