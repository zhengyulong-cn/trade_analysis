from fastapi import APIRouter, File, Form, UploadFile

from app.api.dependencies import UploadServiceDep
from app.schemas.upload import ImageUploadResult

router = APIRouter()


@router.post("/image", response_model=ImageUploadResult)
async def upload_image(
    service: UploadServiceDep,
    file: UploadFile = File(...),
    scope: str = Form(...),
) -> ImageUploadResult:
    return await service.save_image(file=file, scope=scope)
