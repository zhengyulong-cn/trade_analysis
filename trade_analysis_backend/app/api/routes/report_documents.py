from datetime import date

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.dependencies import ReportDocumentServiceDep, ReportDocumentStorageServiceDep
from app.models.report_document import ReportDocument
from app.schemas.report_document import (
    ReportDocumentDeleteRequest,
    ReportDocumentListItem,
    ReportDocumentRead,
)

router = APIRouter()


@router.get("", response_model=list[ReportDocumentListItem])
def list_report_documents(service: ReportDocumentServiceDep) -> list[ReportDocumentListItem]:
    return [ReportDocumentListItem.model_validate(item) for item in service.list_documents()]


@router.get("/item/{report_id}", response_model=ReportDocumentRead)
def get_report_document(report_id: int, service: ReportDocumentServiceDep) -> ReportDocumentRead:
    return ReportDocumentRead.model_validate(service.get_document_by_id(report_id))


@router.post("/upload", response_model=ReportDocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_report_document(
    service: ReportDocumentServiceDep,
    storage_service: ReportDocumentStorageServiceDep,
    published_at: date | None = Form(default=None),
    source: str | None = Form(default=None),
    file: UploadFile = File(...),
) -> ReportDocumentRead:
    payload = await storage_service.save_and_extract(file)
    payload["published_at"] = published_at
    payload["source"] = source.strip() if source and source.strip() else None
    document = ReportDocument(**payload)
    return ReportDocumentRead.model_validate(service.create_document(document))


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_report_document(
    payload: ReportDocumentDeleteRequest,
    service: ReportDocumentServiceDep,
    storage_service: ReportDocumentStorageServiceDep,
) -> None:
    document = service.delete_document(payload.report_id)
    storage_service.delete_relative_path(document.storage_path)
