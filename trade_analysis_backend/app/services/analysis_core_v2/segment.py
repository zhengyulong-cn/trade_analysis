from dataclasses import dataclass, field

from .types import AnalysisBar, BaseSegment, SegmentPoint


MIN_REVERSAL_PCT = 0.004


@dataclass
class SegmentState:
    historical: list[BaseSegment] = field(default_factory=list)
    active: BaseSegment | None = None
    processed_merged_count: int = 0
    last_processed_bar_signature: tuple[int, int, float, float] | None = None


def create_segment_state() -> SegmentState:
    return SegmentState()


def all_segments(state: SegmentState) -> list[BaseSegment]:
    if state.active is None:
        return list(state.historical)
    return [*state.historical, state.active]


def _high_point(bar: AnalysisBar) -> SegmentPoint:
    return SegmentPoint(
        merged_index=bar.index,
        index=bar.index,
        price=bar.high,
        time=bar.time,
    )


def _low_point(bar: AnalysisBar) -> SegmentPoint:
    return SegmentPoint(
        merged_index=bar.index,
        index=bar.index,
        price=bar.low,
        time=bar.time,
    )


def _make_segment(direction: str, start: SegmentPoint, end: SegmentPoint) -> BaseSegment:
    return BaseSegment(direction=direction, start=start, end=end)


def _distance_enough(active: BaseSegment, bar: AnalysisBar, min_distance: int) -> bool:
    return bar.index - active.end.merged_index + 1 >= min_distance


def _price_move_enough(active: BaseSegment, bar: AnalysisBar, min_reversal_pct: float = MIN_REVERSAL_PCT) -> bool:
    base_price = active.end.price
    if base_price <= 0:
        return True
    if active.direction == "down":
        return (bar.high - base_price) / base_price >= min_reversal_pct
    return (base_price - bar.low) / base_price > min_reversal_pct


def _has_higher_kline(active: BaseSegment, bar: AnalysisBar, bars: list[AnalysisBar]) -> bool:
    higher_count = 0
    for item_k in bars[active.end.merged_index : bar.index + 1]:
        if item_k.high > bar.high:
            higher_count += 1
            if higher_count >= 2:
                return True
    return False


def _has_lower_kline(active: BaseSegment, bar: AnalysisBar, bars: list[AnalysisBar]) -> bool:
    lower_count = 0
    for item_k in bars[active.end.merged_index : bar.index + 1]:
        if item_k.low < bar.low:
            lower_count += 1
            if lower_count >= 2:
                return True
    return False


def _can_reverse_to_up(
    active: BaseSegment,
    bar: AnalysisBar,
    bars: list[AnalysisBar],
    min_distance: int,
) -> bool:
    if bar.ema20 is None:
        return False
    return (
        bar.high > bar.ema20
        and not _has_higher_kline(active, bar, bars)
        and _distance_enough(active, bar, min_distance)
        and _price_move_enough(active, bar)
    )


def _can_reverse_to_down(
    active: BaseSegment,
    bar: AnalysisBar,
    bars: list[AnalysisBar],
    min_distance: int,
) -> bool:
    if bar.ema20 is None:
        return False
    return (
        bar.low < bar.ema20
        and not _has_lower_kline(active, bar, bars)
        and _distance_enough(active, bar, min_distance)
        and _price_move_enough(active, bar)
    )


def _extend_active_segment(state: SegmentState, bar: AnalysisBar) -> None:
    active = state.active
    if active is None:
        return

    if active.direction == "up" and bar.high > active.end.price:
        active.end = _high_point(bar)
        return

    if active.direction == "down" and bar.low < active.end.price:
        active.end = _low_point(bar)


def _try_seed_segment(state: SegmentState, bars: list[AnalysisBar], bar: AnalysisBar, min_distance: int) -> None:
    if bar.ema20 is None:
        return

    for start_bar in bars[: bar.index]:
        if bar.index - start_bar.index + 1 < min_distance:
            continue
        if bar.high > bar.ema20:
            state.active = _make_segment("up", _low_point(start_bar), _high_point(bar))
            return
        if bar.low < bar.ema20:
            state.active = _make_segment("down", _high_point(start_bar), _low_point(bar))
            return


def _reverse_segment(state: SegmentState, direction: str, bar: AnalysisBar) -> BaseSegment:
    completed = state.active
    assert completed is not None
    state.historical.append(completed)
    if direction == "up":
        state.active = _make_segment("up", completed.end, _high_point(bar))
    else:
        state.active = _make_segment("down", completed.end, _low_point(bar))
    return completed


def _bar_signature(bar: AnalysisBar) -> tuple[int, int, float, float]:
    return (
        bar.index,
        bar.time,
        bar.high,
        bar.low,
    )

def _is_active_segment_broken(active: BaseSegment, bar: AnalysisBar) -> bool:
    if active.direction == "up":
        return active.start.price > bar.close
    return active.start.price < bar.close


def _rollback_active_segment(state: SegmentState, bar: AnalysisBar) -> bool:
    if len(state.historical) == 0:
        return False
    last_confirmed_seg = state.historical.pop()
    if last_confirmed_seg.direction == "up":
        state.active = _make_segment("up", last_confirmed_seg.start, _high_point(bar))
        return True
    state.active = _make_segment("down", last_confirmed_seg.start, _low_point(bar))
    return True


def advance_segment(
    state: SegmentState,
    bars: list[AnalysisBar],
    min_distance: int = 4,
) -> BaseSegment | None:
    completed: BaseSegment | None = None
    start_index = state.processed_merged_count

    if bars and state.processed_merged_count >= len(bars):
        last_bar = bars[-1]
        last_signature = _bar_signature(last_bar)
        if last_signature != state.last_processed_bar_signature:
            start_index = len(bars) - 1

    for bar_index in range(start_index, len(bars)):
        bar = bars[bar_index]

        if state.active is None:
            _try_seed_segment(state, bars, bar, min_distance)
            state.processed_merged_count = bar_index + 1
            state.last_processed_bar_signature = _bar_signature(bar)
            continue

        _extend_active_segment(state, bar)

        active = state.active
        if active is None:
            state.processed_merged_count = bar_index + 1
            state.last_processed_bar_signature = _bar_signature(bar)
            continue

        if active.direction == "down" and _can_reverse_to_up(active, bar, bars, min_distance):
            completed = _reverse_segment(state, "up", bar)
        elif active.direction == "up" and _can_reverse_to_down(active, bar, bars, min_distance):
            completed = _reverse_segment(state, "down", bar)
        elif _is_active_segment_broken(active, bar):
            op_res = _rollback_active_segment(state, bar)
            if op_res:
                state.processed_merged_count = bar_index + 1
                state.last_processed_bar_signature = _bar_signature(bar)
                continue

        state.processed_merged_count = bar_index + 1
        state.last_processed_bar_signature = _bar_signature(bar)

    return completed
