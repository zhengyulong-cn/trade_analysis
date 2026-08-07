from dataclasses import dataclass


@dataclass
class MergedBar:
    first_bar_close_below_ema20: bool
    high: float
    high_source_index: int
    high_source_time: int
    index: int
    low: float
    low_source_index: int
    low_source_time: int
    source_start_index: int
    source_start_time: int
    source_end_index: int
    source_end_time: int
    time: int
    ema20: float | None = None


@dataclass
class AnalysisBar:
    index: int
    time: int
    open: float
    high: float
    low: float
    close: float
    ema20: float | None = None
    ema120: float | None = None
    macd_diff: float | None = None
    macd_dea: float | None = None
    macd_histogram: float | None = None


@dataclass
class SegmentPoint:
    merged_index: int
    index: int
    price: float
    time: int


@dataclass
class BaseSegment:
    direction: str
    start: SegmentPoint
    end: SegmentPoint


@dataclass
class HigherLevelSegment:
    direction: str
    start: SegmentPoint
    end: SegmentPoint


@dataclass
class TradingRange:
    top: float
    bottom: float
    left: SegmentPoint
    right: SegmentPoint


@dataclass
class MomentumExhaustionSignal:
    direction: str
    point: SegmentPoint
    previous_strength: float
    current_strength: float
