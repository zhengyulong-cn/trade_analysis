from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import ConfigDict
from sqlmodel import Field, SQLModel

from app.schemas.kline_data import KlineBarInput


class SegmentDirection(str, Enum):
    UP = "up"
    DOWN = "down"


class SegmentStatus(str, Enum):
    BUILDING = "building"
    CONFIRMED = "confirmed"


class EmaRelation(str, Enum):
    ABOVE = "above"
    BELOW = "below"
    ON = "on"


class EmaBuildState(SQLModel):
    period: int = 20
    seed_closes: list[Decimal] = Field(default_factory=list)
    last_ema: Decimal | None = None
    last_relation: EmaRelation | None = None
    warmup_bars: list[KlineBarInput] = Field(default_factory=list)


class TrendSegment(SQLModel):
    segment_index: int
    direction: SegmentDirection
    status: SegmentStatus = SegmentStatus.BUILDING
    trigger_time: datetime
    first_kline_time: datetime
    last_kline_time: datetime
    start_time: datetime
    start_price: Decimal
    end_time: datetime
    end_price: Decimal
    kline_count: int = 1
    bars_since_end: int = 0
    confirmed_at: datetime | None = None


class IntervalStrategy(SQLModel):
    interval: int
    interval_name: str | None = None
    ema_state: EmaBuildState = Field(default_factory=EmaBuildState)
    confirmed_segments: list[TrendSegment] = Field(default_factory=list)
    current_segment: TrendSegment | None = None
    pending_segment: TrendSegment | None = None
    processed_kline_count: int = 0
    last_processed_at: datetime | None = None


class StrategyContent(SQLModel):
    intervals: dict[str, IntervalStrategy] = Field(default_factory=dict)


class SegmentBuildRequest(SQLModel):
    symbol: str
    interval: int
    reset: bool = False


class SegmentBuildResult(SQLModel):
    strategy_id: int
    contract_id: int
    symbol: str
    exchange: str
    contract_name: str
    interval: int
    interval_name: str | None = None
    strategy: StrategyContent
    interval_strategy: IntervalStrategy


class StrategyAnalysisRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    strategy_id: int
    contract_id: int
    strategy: str


class StrategyAnalysisDetail(SQLModel):
    strategy_id: int
    contract_id: int
    symbol: str
    exchange: str
    contract_name: str
    strategy: StrategyContent
