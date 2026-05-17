from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.report_document import ReportDocument


class ReportDocumentService:
    def __init__(self, session: Session):
        self.session = session

    def create_document(self, document: ReportDocument) -> ReportDocument:
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def list_documents(self) -> list[ReportDocument]:
        statement = select(ReportDocument).order_by(ReportDocument.create_at.desc())
        return list(self.session.exec(statement).all())

    def get_document_by_id(self, report_id: int) -> ReportDocument:
        document = self.session.get(ReportDocument, report_id)
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report document not found: {report_id}",
            )
        return document

    def delete_document(self, report_id: int) -> ReportDocument:
        document = self.get_document_by_id(report_id)
        self.session.delete(document)
        self.session.commit()
        return document

    def touch_document(self, document: ReportDocument) -> ReportDocument:
        document.updated_at = datetime.now(timezone.utc)
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document
