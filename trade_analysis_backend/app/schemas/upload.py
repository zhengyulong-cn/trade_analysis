from sqlmodel import SQLModel


class ImageUploadResult(SQLModel):
    path: str
    original_name: str
    content_type: str
    size: int
    url: str
