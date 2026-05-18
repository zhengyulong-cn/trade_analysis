from datetime import datetime

from pydantic import ConfigDict, field_validator
from sqlmodel import SQLModel


class FutureReportDocumentRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: int
    report_name: str
    published_at: datetime
    report_source: str
    storage_path: str
    original_filename: str
    content_type: str
    file_size: int
    create_at: datetime
    updated_at: datetime


class FutureReportUploadResult(FutureReportDocumentRead):
    url: str


class FutureReportDocumentDeleteRequest(SQLModel):
    report_id: int


class FutureReportDocumentCreate(SQLModel):
    report_name: str
    published_at: datetime
    report_source: str
    storage_path: str
    original_filename: str
    content_type: str
    file_size: int

    @field_validator(
        "report_name",
        "report_source",
        "storage_path",
        "original_filename",
        "content_type",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("field must be a string")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("field cannot be empty")
        return cleaned
