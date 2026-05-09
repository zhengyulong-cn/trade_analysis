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
