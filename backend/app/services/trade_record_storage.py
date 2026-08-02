from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


class TradeRecordStorageService:
    allowed_content_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    max_file_size = 10 * 1024 * 1024

    def __init__(self):
        self.storage_root = Path(settings.storage_root)
        self.trade_record_dir = self.storage_root / "trade_records_v2"
        self.trade_record_dir.mkdir(parents=True, exist_ok=True)

    async def save_image(self, file: UploadFile) -> dict[str, str | int]:
        content_type = file.content_type or ""
        if content_type not in self.allowed_content_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported image file type",
            )

        extension = self._guess_extension(file.filename or "", content_type)
        relative_dir = Path("trade_records_v2")
        filename = f"{uuid4().hex}{extension}"
        relative_path = relative_dir / filename
        target_path = self.storage_root / relative_path

        content = await file.read()
        size = len(content)
        if size <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image file is empty",
            )
        if size > self.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image file exceeds 10 MB limit",
            )

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)

        return {
            "path": relative_path.as_posix(),
            "original_name": file.filename or filename,
            "content_type": content_type,
            "size": size,
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

    def _guess_extension(self, filename: str, content_type: str) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            return suffix

        mapping = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }
        return mapping.get(content_type, ".bin")
