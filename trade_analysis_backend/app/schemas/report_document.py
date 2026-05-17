from datetime import datetime

from pydantic import ConfigDict
from sqlmodel import SQLModel


class ReportDocumentRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: int
    file_name: str
    original_name: str
    content_type: str
    file_size: int
    storage_path: str
    title: str | None = None
    raw_text: str
    parse_status: str
    create_at: datetime
    updated_at: datetime


class ReportDocumentListItem(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: int
    file_name: str
    original_name: str
    content_type: str
    file_size: int
    title: str | None = None
    parse_status: str
    create_at: datetime
    updated_at: datetime


class ReportDocumentDeleteRequest(SQLModel):
    report_id: int
