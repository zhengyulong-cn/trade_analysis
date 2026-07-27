from typing import Any

from pydantic import Field
from sqlmodel import SQLModel


class PineIndicatorExecuteRequest(SQLModel):
    script_id: int = Field(gt=0)
    symbol: str = Field(min_length=1, max_length=100)
    interval: int = Field(gt=0)
    limit: int = Field(default=1000, ge=1, le=5000)


class PineIndicatorExecuteResponse(SQLModel):
    script_id: int
    script_name: str
    symbol: str
    interval: int
    bar_count: int
    indicator: dict[str, Any]
    plots: list[dict[str, Any]]
    drawings: dict[str, list[dict[str, Any]]]
    warnings: list[dict[str, Any]]
