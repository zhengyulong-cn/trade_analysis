from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader

from app.core.config import settings


class ReportDocumentStorageService:
    allowed_content_types = {"application/pdf"}
    allowed_suffixes = {".pdf"}
    max_file_size = 20 * 1024 * 1024

    def __init__(self):
        self.storage_root = Path(settings.storage_root)
        self.report_document_dir = Path(settings.report_document_storage_dir)
        self.report_document_dir.mkdir(parents=True, exist_ok=True)

    async def save_and_extract(self, file: UploadFile) -> dict[str, str | int]:
        original_name = file.filename or "report.pdf"
        suffix = Path(original_name).suffix.lower()
        content_type = file.content_type or "application/pdf"
        if suffix not in self.allowed_suffixes and content_type not in self.allowed_content_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported report file type, only pdf is supported",
            )

        content = await file.read()
        size = len(content)
        if size <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Report file is empty",
            )
        if size > self.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Report file exceeds 20 MB limit",
            )

        filename = f"{uuid4().hex}.pdf"
        relative_dir = Path("report_documents")
        relative_path = relative_dir / filename
        target_path = self.storage_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)

        raw_text = self._clean_text(self._extract_pdf_text(content))
        if not raw_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to extract text from report file",
            )

        return {
            "file_name": filename,
            "original_name": original_name,
            "content_type": "application/pdf",
            "file_size": size,
            "storage_path": relative_path.as_posix(),
            "title": Path(original_name).stem.strip() or filename,
            "raw_text": raw_text,
            "parse_status": "success",
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

    def _extract_pdf_text(self, content: bytes) -> str:
        reader = PdfReader(BytesIO(content))
        page_texts: list[str] = []
        for page in reader.pages:
            page_texts.append(page.extract_text() or "")
        return "\n\n".join(text.strip() for text in page_texts if text and text.strip())

    def _clean_text(self, raw_text: str) -> str:
        lines = [line.strip() for line in raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        non_empty_lines = [line for line in lines if line]
        if not non_empty_lines:
            return ""

        repeated_noise = self._find_repeated_noise_lines(non_empty_lines)
        cleaned_lines: list[str] = []
        previous_blank = False
        for original_line in lines:
            line = original_line.strip()
            if not line:
                if cleaned_lines and not previous_blank:
                    cleaned_lines.append("")
                previous_blank = True
                continue
            if line in repeated_noise:
                continue
            cleaned_lines.append(line)
            previous_blank = False

        while cleaned_lines and cleaned_lines[0] == "":
            cleaned_lines.pop(0)
        while cleaned_lines and cleaned_lines[-1] == "":
            cleaned_lines.pop()
        return "\n".join(cleaned_lines).strip()

    def _find_repeated_noise_lines(self, lines: list[str]) -> set[str]:
        line_counts: dict[str, int] = {}
        for line in lines:
            line_counts[line] = line_counts.get(line, 0) + 1

        repeated: set[str] = set()
        threshold = 3 if len(lines) >= 12 else 2
        for line, count in line_counts.items():
            if count < threshold:
                continue
            if len(line) > 40:
                continue
            if self._looks_like_page_noise(line):
                repeated.add(line)
        return repeated

    def _looks_like_page_noise(self, line: str) -> bool:
        lowered = line.lower()
        if "research" in lowered or "please refer" in lowered or "免责声明" in line:
            return True
        if "页" in line and any(char.isdigit() for char in line):
            return True
        if "page" in lowered and any(char.isdigit() for char in line):
            return True
        if any(token in line for token in ("www.", "http://", "https://", "@")):
            return True
        if len(line) <= 20 and any(char.isdigit() for char in line):
            return True
        return False
