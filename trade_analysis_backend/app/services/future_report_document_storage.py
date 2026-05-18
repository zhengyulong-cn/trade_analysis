from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


class FutureReportDocumentStorageService:
    allowed_content_types = {"application/pdf"}
    max_file_size = 50 * 1024 * 1024

    def __init__(self):
        self.storage_root = Path(settings.storage_root)
        self.report_dir = Path(settings.future_report_storage_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    async def save_pdf(self, file: UploadFile) -> dict[str, str | int]:
        content_type = (file.content_type or "").lower()
        filename = file.filename or ""
        if content_type not in self.allowed_content_types and not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are supported",
            )

        content = await file.read()
        size = len(content)
        if size <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF file is empty",
            )
        if size > self.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF file exceeds 50 MB limit",
            )

        relative_dir = Path("future_reports")
        stored_name = f"{uuid4().hex}.pdf"
        relative_path = relative_dir / stored_name
        target_path = self.storage_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)

        safe_content_type = content_type or "application/pdf"
        return {
            "report_name": Path(filename).stem or stored_name,
            "storage_path": relative_path.as_posix(),
            "original_filename": filename or stored_name,
            "content_type": safe_content_type,
            "file_size": size,
            "url": f"/storage/{relative_path.as_posix()}",
        }

    def delete_relative_path(self, relative_path: str | None) -> None:
        if not relative_path:
            return

        target_path = (self.storage_root / relative_path).resolve()
        storage_root = self.storage_root.resolve()
        if storage_root not in target_path.parents:
            return
        if target_path.is_file():
            target_path.unlink(missing_ok=True)
