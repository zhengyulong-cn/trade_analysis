"""包含处理 + 分型构建（增量版本）。"""

from dataclasses import dataclass, field

from .types import AnalysisBar, FenxingPoint, FenxingSignal, MergedBar


@dataclass
class FenxingState:
    merged_bars: list[MergedBar] = field(default_factory=list)
    signals: list[FenxingSignal] = field(default_factory=list)
    processed_count: int = 0  # 已处理的原始 K 线条数


def create_fenxing_state() -> FenxingState:
    return FenxingState()


def _create_merged_bar(bar: AnalysisBar) -> MergedBar:
    close_below = bar.close < bar.ema20 if bar.ema20 is not None else False
    return MergedBar(
        first_bar_close_below_ema20=close_below,
        high=bar.high, high_source_index=bar.index, high_source_time=bar.time,
        index=bar.index, low=bar.low,
        low_source_index=bar.index, low_source_time=bar.time,
        source_start_index=bar.index, source_start_time=bar.time,
        source_end_index=bar.index, source_end_time=bar.time,
        time=bar.time,
    )


def _has_inclusion(first: MergedBar, second: MergedBar) -> bool:
    return (first.high >= second.high and first.low <= second.low) or (
        first.high <= second.high and first.low >= second.low
    )


def _can_merge(first: MergedBar, second: MergedBar, max_count: int) -> bool:
    return second.source_end_index - first.source_start_index + 1 <= max_count


def _merge(first: MergedBar, second: MergedBar) -> MergedBar:
    if first.first_bar_close_below_ema20:
        mh, ml = min(first.high, second.high), min(first.low, second.low)
        use_sh, use_sl = second.high < first.high, second.low < first.low
    else:
        mh, ml = max(first.high, second.high), max(first.low, second.low)
        use_sh, use_sl = second.high > first.high, second.low > first.low
    return MergedBar(
        first_bar_close_below_ema20=first.first_bar_close_below_ema20,
        high=mh, high_source_index=second.high_source_index if use_sh else first.high_source_index,
        high_source_time=second.high_source_time if use_sh else first.high_source_time,
        index=first.index, low=ml,
        low_source_index=second.low_source_index if use_sl else first.low_source_index,
        low_source_time=second.low_source_time if use_sl else first.low_source_time,
        source_end_index=second.source_end_index, source_end_time=second.source_end_time,
        source_start_index=first.source_start_index, source_start_time=first.source_start_time,
        time=first.time,
    )


def _build_signal(left: MergedBar, middle: MergedBar, right: MergedBar) -> FenxingSignal | None:
    is_top = (
        middle.high >= left.high and middle.high >= right.high
        and middle.low >= left.low and middle.low >= right.low
    )
    if is_top:
        return FenxingSignal(
            index=-1, merged_bar_index=middle.index,
            point=FenxingPoint(index=middle.high_source_index, price=middle.high, time=middle.high_source_time),
            type="top",
        )
    is_bottom = (
        middle.high <= left.high and middle.high <= right.high
        and middle.low <= left.low and middle.low <= right.low
    )
    if is_bottom:
        return FenxingSignal(
            index=-1, merged_bar_index=middle.index,
            point=FenxingPoint(index=middle.low_source_index, price=middle.low, time=middle.low_source_time),
            type="bottom",
        )
    return None


def advance_fenxing(
    state: FenxingState,
    bar: AnalysisBar,
    max_included: int = 10,
) -> FenxingSignal | None:
    """处理一根新 K 线，返回新确认的分型（或 None）。"""
    if bar.ema20 is None:
        return None

    next_bar = _create_merged_bar(bar)
    prev = state.merged_bars[-1] if state.merged_bars else None

    if prev is None:
        state.merged_bars.append(next_bar)
        state.processed_count += 1
        return None

    if _has_inclusion(prev, next_bar) and _can_merge(prev, next_bar, max_included):
        state.merged_bars[-1] = _merge(prev, next_bar)
        state.processed_count += 1
        return None

    state.merged_bars.append(next_bar)
    state.merged_bars[-1].index = len(state.merged_bars) - 1
    state.processed_count += 1

    center = len(state.merged_bars) - 2
    if center < 1:
        return None

    left = state.merged_bars[center - 1]
    middle = state.merged_bars[center]
    right = state.merged_bars[center + 1]
    signal = _build_signal(left, middle, right)
    if signal is not None:
        signal.index = len(state.signals)
        state.signals.append(signal)
    return signal
