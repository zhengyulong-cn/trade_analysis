from datetime import datetime

from pydantic import ConfigDict
from sqlmodel import SQLModel


class ChartPersistenceSave(SQLModel):
    symbol: str
    interval: str
    drawings_content: str | None = None


class ChartPersistenceRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    persistence_id: int | None = None
    user_key: str = "default"
    symbol: str
    interval: str
    drawings_content: str | None = None
    create_at: datetime | None = None
    updated_at: datetime | None = None
