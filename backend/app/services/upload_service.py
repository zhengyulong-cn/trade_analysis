import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas.upload import ImageUploadResult


class UploadService:
    IMAGE_CONTENT_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    SCOPES = {
        "trade_records_v2": Path("trade_records_v2"),
        "opportunity_reviews": Path("opportunity_reviews"),
    }

    def __init__(self):
        self.storage_root = Path(settings.storage_root)

    async def save_image(self, file: UploadFile, scope: str) -> ImageUploadResult:
        relative_dir = self.SCOPES.get(scope)
        if relative_dir is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported upload scope: {scope}",
            )

        content_type = file.content_type or ""
        suffix = self.IMAGE_CONTENT_TYPES.get(content_type)
        if suffix is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only JPG, PNG, WEBP and GIF images are supported",
            )

        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )

        target_dir = self.storage_root / relative_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid.uuid4().hex}{suffix}"
        target_path = target_dir / filename
        target_path.write_bytes(content)

        relative_path = (relative_dir / filename).as_posix()
        return ImageUploadResult(
            path=relative_path,
            original_name=file.filename or filename,
            content_type=content_type,
            size=len(content),
            url=f"/storage/{relative_path}",
        )
