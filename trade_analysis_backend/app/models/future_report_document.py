from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FutureReportDocument(SQLModel, table=True):
    __tablename__ = "future_report_documents"

    report_id: int | None = Field(default=None, primary_key=True)
    report_name: str = Field(min_length=1, max_length=255)
    published_at: datetime = Field(nullable=False)
    report_source: str = Field(min_length=1, max_length=255)
    storage_path: str = Field(min_length=1, max_length=500)
    original_filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    file_size: int = Field(nullable=False, ge=1)
    create_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
