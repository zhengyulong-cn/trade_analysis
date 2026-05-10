from sqlmodel import SQLModel


class _FractalOut(SQLModel):
    index: int
    time: int
    price: float
    type: str  # 'top' | 'bottom'


class _SegmentPointOut(SQLModel):
    index: int
    time: int
    price: float


class _SegmentOut(SQLModel):
    direction: str  # 'up' | 'down'
    start: _SegmentPointOut
    end: _SegmentPointOut
    is_momentum_exhaustion_segment: bool = False


class _HigherSegmentOut(SQLModel):
    direction: str  # 'up' | 'down'
    start: _SegmentPointOut
    end: _SegmentPointOut


class _TradingRangeOut(SQLModel):
    top: float
    bottom: float
    left: _SegmentPointOut
    right: _SegmentPointOut


class _MomentumExhaustionOut(SQLModel):
    direction: str  # 'up' | 'down'
    point: _SegmentPointOut
    previous_strength: float
    current_strength: float


class AnalysisOut(SQLModel):
    symbol: str
    interval: int
    bar_count: int
    fractals: list[_FractalOut]
    segments: list[_SegmentOut]
    higher_segments: list[_HigherSegmentOut]
    trading_ranges: list[_TradingRangeOut]
    momentum_exhaustions: list[_MomentumExhaustionOut]


class OpportunityAnalysisItemOut(SQLModel):
    symbol: str
    exchange: str
    name: str
    analysis_message: str | None = None
    latest_price: float | None = None
    latest_time: int | None = None
    latest_30f_time: int | None = None
    current_30f_segment_type: str | None = None
    current_30f_segment_direction: str | None = None
    current_4h_segment_direction: str | None = None
    current_5f_segment_direction: str | None = None
    latest_30f_momentum_exhaustion_direction: str | None = None
    latest_30f_momentum_exhaustion_time: int | None = None
    latest_30f_momentum_exhaustion_price: float | None = None
    latest_5f_momentum_exhaustion_direction: str | None = None
    latest_5f_momentum_exhaustion_time: int | None = None
    latest_5f_momentum_exhaustion_price: float | None = None
    current_30f_momentum_check_direction: str | None = None
    current_30f_momentum_exhausted: bool | None = None
    current_5f_momentum_check_direction: str | None = None
    current_5f_momentum_exhausted: bool | None = None
    current_5f_wait_direction: str | None = None
    open_side: str | None = None
    in_open_zone: bool
    has_opportunity: bool
    opportunity_action: str | None = None
    zone_source: str | None = None
    zone_low: float | None = None
    zone_high: float | None = None
    trading_range_top: float | None = None
    trading_range_bottom: float | None = None
    current_30f_segment_start_time: int | None = None
    current_30f_segment_end_time: int | None = None
    current_5f_zone_segment_start_time: int | None = None
    current_5f_zone_segment_end_time: int | None = None


class OpportunityAnalysisListOut(SQLModel):
    items: list[OpportunityAnalysisItemOut]
