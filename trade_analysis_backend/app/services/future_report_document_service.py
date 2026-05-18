from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.future_report_document import FutureReportDocument
from app.models.future_fundamental_analysis import FutureFundamentalAnalysis
from app.schemas.future_report_document import (
    FutureReportDocumentCreate,
)
from app.services.future_report_document_storage import FutureReportDocumentStorageService


class FutureReportDocumentService:
    def __init__(
        self,
        session: Session,
        storage_service: FutureReportDocumentStorageService,
    ):
        self.session = session
        self.storage_service = storage_service

    def list_reports(self) -> list[FutureReportDocument]:
        statement = select(FutureReportDocument).order_by(FutureReportDocument.create_at.desc())
        return list(self.session.exec(statement).all())

    def get_report_by_id(self, report_id: int) -> FutureReportDocument:
        report = self.session.get(FutureReportDocument, report_id)
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Future report document not found: {report_id}",
            )
        return report

    def create_report(self, payload: FutureReportDocumentCreate) -> FutureReportDocument:
        report = FutureReportDocument(**payload.model_dump())
        self.session.add(report)
        self.session.commit()
        self.session.refresh(report)
        return report

    def delete_report(self, report_id: int) -> None:
        report = self.get_report_by_id(report_id)
        linked_items = self.session.exec(
            select(FutureFundamentalAnalysis).where(
                FutureFundamentalAnalysis.report_id == report_id
            )
        ).all()
        for item in linked_items:
            self.session.delete(item)
        self.storage_service.delete_relative_path(report.storage_path)
        self.session.delete(report)
        self.session.commit()
