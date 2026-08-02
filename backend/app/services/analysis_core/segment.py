"""本级别线段构建（增量版本）。"""

from dataclasses import dataclass, field

from .types import AnalysisBar, BaseSegment, FenxingPoint, FenxingSignal


@dataclass
class SegmentState:
    historical: list[BaseSegment] = field(default_factory=list)
    active: BaseSegment | None = None
    seed_bottom: FenxingSignal | None = None
    seed_top: FenxingSignal | None = None
    processed_signal_count: int = 0


def create_segment_state() -> SegmentState:
    return SegmentState()


def all_segments(state: SegmentState) -> list[BaseSegment]:
    if state.active is None:
        return list(state.historical)
    return [*state.historical, state.active]


def _get_ema20(bars: list[AnalysisBar], signal: FenxingSignal) -> float | None:
    bar = bars[signal.point.index] if signal.point.index < len(bars) else None
    return bar.ema20 if bar else None


def _is_top_above_ema20(bars: list[AnalysisBar], s: FenxingSignal) -> bool:
    ema = _get_ema20(bars, s)
    return s.type == "top" and ema is not None and s.point.price > ema


def _is_bottom_below_ema20(bars: list[AnalysisBar], s: FenxingSignal) -> bool:
    ema = _get_ema20(bars, s)
    return s.type == "bottom" and ema is not None and s.point.price < ema


def _enough_distance(start: FenxingSignal, end: FenxingSignal, min_dist: int) -> bool:
    return abs(end.point.index - start.point.index) > min_dist


def _bypass_down(active: BaseSegment, end: FenxingSignal) -> bool:
    return active.direction == "up" and end.point.price < active.start.price


def _bypass_up(active: BaseSegment, end: FenxingSignal) -> bool:
    return active.direction == "down" and end.point.price > active.start.price


def _valid_up(
    bars: list[AnalysisBar], signals: list[FenxingSignal],
    start_sig: FenxingSignal, end_sig: FenxingSignal,
    min_dist: int, allow_bypass: bool = False,
) -> bool:
    if not _is_bottom_below_ema20(bars, start_sig) or not _is_top_above_ema20(bars, end_sig):
        return False
    if not allow_bypass and not _enough_distance(start_sig, end_sig, min_dist):
        return False
    for i in range(start_sig.index, end_sig.index + 1):
        s = signals[i]
        if s.type == "top" and s.point.price > end_sig.point.price:
            return False
        if s.type == "bottom" and s.point.price < start_sig.point.price:
            return False
    return True


def _valid_down(
    bars: list[AnalysisBar], signals: list[FenxingSignal],
    start_sig: FenxingSignal, end_sig: FenxingSignal,
    min_dist: int, allow_bypass: bool = False,
) -> bool:
    if not _is_top_above_ema20(bars, start_sig) or not _is_bottom_below_ema20(bars, end_sig):
        return False
    if not allow_bypass and not _enough_distance(start_sig, end_sig, min_dist):
        return False
    for i in range(start_sig.index, end_sig.index + 1):
        s = signals[i]
        if s.type == "top" and s.point.price > start_sig.point.price:
            return False
        if s.type == "bottom" and s.point.price < end_sig.point.price:
            return False
    return True


def _make_seg(direction: str, start: FenxingSignal, end: FenxingSignal) -> BaseSegment:
    return BaseSegment(
        direction=direction,
        start=FenxingPoint(index=start.point.index, price=start.point.price, time=start.point.time),
        end=FenxingPoint(index=end.point.index, price=end.point.price, time=end.point.time),
        start_signal_index=start.index, end_signal_index=end.index,
    )


def advance_segment(
    state: SegmentState,
    bars: list[AnalysisBar],
    signals: list[FenxingSignal],
    signal: FenxingSignal,
    min_distance: int = 3,
) -> BaseSegment | None:
    """处理一个新确认的分型，返回新完成的历史段（或 None）。"""
    completed: BaseSegment | None = None

    if state.active is None:
        # 种子阶段
        if _is_bottom_below_ema20(bars, signal):
            if state.seed_top is not None and _valid_down(bars, signals, state.seed_top, signal, min_distance):
                state.active = _make_seg("down", state.seed_top, signal)
                state.seed_bottom = None
                state.seed_top = None
            elif state.seed_bottom is None or signal.point.price < state.seed_bottom.point.price:
                state.seed_bottom = signal
            state.processed_signal_count += 1
            return None

        if _is_top_above_ema20(bars, signal):
            if state.seed_bottom is not None and _valid_up(bars, signals, state.seed_bottom, signal, min_distance):
                state.active = _make_seg("up", state.seed_bottom, signal)
                state.seed_top = None
                state.seed_bottom = None
            elif state.seed_top is None or signal.point.price > state.seed_top.point.price:
                state.seed_top = signal
            state.processed_signal_count += 1
            return None

        state.processed_signal_count += 1
        return None

    # 活动段阶段
    if state.active.direction == "up":
        if _is_top_above_ema20(bars, signal) and signal.point.price > state.active.end.price:
            state.active = _make_seg("up", signals[state.active.start_signal_index], signal)
            state.processed_signal_count += 1
            return None

        if _is_bottom_below_ema20(bars, signal):
            start_sig = signals[state.active.end_signal_index]
            bypass = _bypass_down(state.active, signal)
            if _valid_down(bars, signals, start_sig, signal, min_distance, bypass):
                completed = state.active
                state.active = _make_seg("down", start_sig, signal)
                state.historical.append(completed)
        state.processed_signal_count += 1
        return completed

    # active.direction == 'down'
    if _is_bottom_below_ema20(bars, signal) and signal.point.price < state.active.end.price:
        state.active = _make_seg("down", signals[state.active.start_signal_index], signal)
        state.processed_signal_count += 1
        return None

    if _is_top_above_ema20(bars, signal):
        start_sig = signals[state.active.end_signal_index]
        bypass = _bypass_up(state.active, signal)
        if _valid_up(bars, signals, start_sig, signal, min_distance, bypass):
            completed = state.active
            state.active = _make_seg("up", start_sig, signal)
            state.historical.append(completed)
    state.processed_signal_count += 1
    return completed
