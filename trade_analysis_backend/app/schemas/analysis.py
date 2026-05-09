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


class AnalysisOut(SQLModel):
    symbol: str
    interval: int
    bar_count: int
    fractals: list[_FractalOut]
    segments: list[_SegmentOut]
