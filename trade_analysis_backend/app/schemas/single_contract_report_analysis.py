from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field as PydanticField
from sqlmodel import SQLModel


class SingleContractReportAnalysisRunRequest(SQLModel):
    contract_id: int
    report_id: int


class SingleContractReportAnalysisResult(BaseModel):
    relevance: Literal["high", "medium", "low", "none"] = "medium"
    stance: Literal["bullish", "bearish", "neutral", "mixed"] = "neutral"
    horizon: str = "未明确"
    confidence: int = PydanticField(default=50, ge=0, le=100)
    summary: str
    drivers: list[str] = PydanticField(default_factory=list)
    risks: list[str] = PydanticField(default_factory=list)
    evidence: list[str] = PydanticField(default_factory=list)


class SingleContractReportAnalysisListItem(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: int
    contract_id: int
    report_id: int
    profile_id: int | None = None
    contract_symbol: str
    contract_name: str
    report_title: str
    report_source: str | None = None
    status: str
    error_message: str | None = None
    matched_snippets: list[str]
    result_json: dict | None = None
    create_at: datetime
    updated_at: datetime


class SingleContractReportAnalysisRead(SingleContractReportAnalysisListItem):
    profile_snapshot: dict | None = None
    system_prompt: str
    user_prompt: str
