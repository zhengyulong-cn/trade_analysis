from datetime import date, datetime, timezone

from sqlalchemy import Column
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReportDocument(SQLModel, table=True):
    __tablename__ = "report_documents"

    report_id: int | None = Field(default=None, primary_key=True)
    file_name: str = Field(min_length=1, max_length=255, nullable=False)
    original_name: str = Field(min_length=1, max_length=255, nullable=False)
    content_type: str = Field(min_length=1, max_length=100, nullable=False)
    file_size: int = Field(ge=0, nullable=False)
    storage_path: str = Field(min_length=1, max_length=255, nullable=False)
    title: str | None = Field(default=None, max_length=255)
    published_at: date | None = Field(default=None, nullable=True)
    source: str | None = Field(default=None, max_length=255)
    raw_text: str = Field(sa_column=Column(LONGTEXT, nullable=False))
    parse_status: str = Field(default="success", min_length=1, max_length=50, nullable=False)
    create_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
