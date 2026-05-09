from dataclasses import dataclass


@dataclass
class FenxingPoint:
    index: int
    price: float
    time: int  # unix timestamp, 与前端 FenxingBar.time 对齐


@dataclass
class FenxingSignal:
    index: int
    merged_bar_index: int
    point: FenxingPoint
    type: str  # 'top' | 'bottom'


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


@dataclass
class AnalysisBar:
    index: int
    time: int  # unix timestamp
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
class BaseSegment:
    direction: str  # 'up' | 'down'
    start: FenxingPoint
    end: FenxingPoint
    start_signal_index: int  # 起点分型在 signals 列表中的序号
    end_signal_index: int    # 终点分型在 signals 列表中的序号


@dataclass
class HigherLevelSegment:
    direction: str  # 'up' | 'down'
    start: FenxingPoint
    end: FenxingPoint


@dataclass
class TradingRange:
    top: float
    bottom: float
    left: FenxingPoint
    right: FenxingPoint


@dataclass
class MomentumExhaustionSignal:
    direction: str  # 'up' | 'down'
    point: FenxingPoint
    previous_strength: float  # segment A 的 MACD 面积
    current_strength: float   # segment C 的 MACD 面积
