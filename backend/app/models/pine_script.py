from datetime import datetime, timezone

from sqlalchemy import Column
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PineScript(SQLModel, table=True):
    __tablename__ = "pine_scripts"

    script_id: int | None = Field(default=None, primary_key=True)
    script_name: str = Field(max_length=200, nullable=False, index=True)
    script_content: str = Field(sa_column=Column(LONGTEXT, nullable=False))
    script_type: str = Field(max_length=20, nullable=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
