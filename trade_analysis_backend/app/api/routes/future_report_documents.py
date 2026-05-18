from datetime import datetime

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.dependencies import (
    FutureReportDocumentServiceDep,
    FutureReportDocumentStorageServiceDep,
)
from app.schemas.future_report_document import (
    FutureReportDocumentCreate,
    FutureReportDocumentDeleteRequest,
    FutureReportDocumentRead,
    FutureReportUploadResult,
)

router = APIRouter()


@router.get("", response_model=list[FutureReportDocumentRead])
def list_future_report_documents(
    service: FutureReportDocumentServiceDep,
) -> list[FutureReportDocumentRead]:
    return [FutureReportDocumentRead.model_validate(item) for item in service.list_reports()]


@router.post("/upload", response_model=FutureReportUploadResult, status_code=status.HTTP_201_CREATED)
async def upload_future_report_document(
    service: FutureReportDocumentServiceDep,
    storage_service: FutureReportDocumentStorageServiceDep,
    published_at: datetime = Form(...),
    report_source: str = Form(...),
    file: UploadFile = File(...),
) -> FutureReportUploadResult:
    upload_result = await storage_service.save_pdf(file)
    created = service.create_report(
        FutureReportDocumentCreate(
            report_name=str(upload_result["report_name"]),
            published_at=published_at,
            report_source=report_source,
            storage_path=str(upload_result["storage_path"]),
            original_filename=str(upload_result["original_filename"]),
            content_type=str(upload_result["content_type"]),
            file_size=int(upload_result["file_size"]),
        )
    )
    return FutureReportUploadResult(
        report_id=created.report_id,
        report_name=created.report_name,
        published_at=created.published_at,
        report_source=created.report_source,
        storage_path=created.storage_path,
        original_filename=created.original_filename,
        content_type=created.content_type,
        file_size=created.file_size,
        create_at=created.create_at,
        updated_at=created.updated_at,
        url=str(upload_result["url"]),
    )


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_future_report_document(
    payload: FutureReportDocumentDeleteRequest,
    service: FutureReportDocumentServiceDep,
) -> None:
    service.delete_report(payload.report_id)
