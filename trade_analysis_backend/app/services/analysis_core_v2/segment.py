from dataclasses import dataclass, field

from .types import BaseSegment, MergedBar, SegmentPoint

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


def _high_point(bar: MergedBar) -> SegmentPoint:
    return SegmentPoint(
        merged_index=bar.index,
        index=bar.high_source_index,
        price=bar.high,
        time=bar.high_source_time,
    )


def _low_point(bar: MergedBar) -> SegmentPoint:
    return SegmentPoint(
        merged_index=bar.index,
        index=bar.low_source_index,
        price=bar.low,
        time=bar.low_source_time,
    )


def _make_segment(direction: str, start: SegmentPoint, end: SegmentPoint) -> BaseSegment:
    return BaseSegment(direction=direction, start=start, end=end)


def _distance_enough(active: BaseSegment, bar: MergedBar, min_distance: int) -> bool:
    return bar.index - active.end.merged_index > min_distance


def _has_higher_kline(active: BaseSegment, bar: MergedBar, merged_bars: list[MergedBar]) -> bool:
    for item_k in merged_bars[active.end.merged_index : bar.index + 1]:
        if item_k.high > bar.high:
            return True
    return False


def _has_lower_kline(active: BaseSegment, bar: MergedBar, merged_bars: list[MergedBar]) -> bool:
    for item_k in merged_bars[active.end.merged_index : bar.index + 1]:
        if item_k.low < bar.low:
            return True
    return False


def _can_reverse_to_up(
    active: BaseSegment,
    bar: MergedBar,
    merged_bars: list[MergedBar],
    min_distance: int,
) -> bool:
    if bar.ema20 is None:
        return False
    # if bar.high > active.start.price:
    #     return True
    return (
        bar.high > bar.ema20
        and not _has_higher_kline(active, bar, merged_bars)
        and _distance_enough(active, bar, min_distance)
    )


def _can_reverse_to_down(
    active: BaseSegment,
    bar: MergedBar,
    merged_bars: list[MergedBar],
    min_distance: int,
) -> bool:
    if bar.ema20 is None:
        return False
    # if bar.low < active.start.price:
    #     return True
    return (
        bar.low < bar.ema20
        and not _has_lower_kline(active, bar, merged_bars)
        and _distance_enough(active, bar, min_distance)
    )


def _extend_active_segment(state: SegmentState, bar: MergedBar) -> None:
    active = state.active
    if active is None:
        return

    if active.direction == "up" and bar.high > active.end.price:
        active.end = _high_point(bar)
        return

    if active.direction == "down" and bar.low < active.end.price:
        active.end = _low_point(bar)


def _try_seed_segment(state: SegmentState, bars: list[MergedBar], bar: MergedBar, min_distance: int) -> None:
    if bar.ema20 is None:
        return

    for start_bar in bars[: bar.index]:
        if bar.index - start_bar.index <= min_distance:
            continue
        if bar.high > bar.ema20:
            state.active = _make_segment("up", _low_point(start_bar), _high_point(bar))
            return
        if bar.low < bar.ema20:
            state.active = _make_segment("down", _high_point(start_bar), _low_point(bar))
            return


def _reverse_segment(state: SegmentState, direction: str, bar: MergedBar) -> BaseSegment:
    completed = state.active
    assert completed is not None
    state.historical.append(completed)
    if direction == "up":
        state.active = _make_segment("up", completed.end, _high_point(bar))
    else:
        state.active = _make_segment("down", completed.end, _low_point(bar))
    return completed


def _bar_signature(bar: MergedBar) -> tuple[int, int, float, float]:
    return (
        bar.index,
        bar.source_end_index,
        bar.high,
        bar.low,
    )


def advance_segment(
    state: SegmentState,
    merged_bars: list[MergedBar],
    min_distance: int = 4,
) -> BaseSegment | None:
    completed: BaseSegment | None = None
    start_index = state.processed_merged_count

    if merged_bars and state.processed_merged_count >= len(merged_bars):
        last_bar = merged_bars[-1]
        last_signature = _bar_signature(last_bar)
        if last_signature != state.last_processed_bar_signature:
            start_index = len(merged_bars) - 1

    for bar_index in range(start_index, len(merged_bars)):
        bar = merged_bars[bar_index]

        if state.active is None:
            _try_seed_segment(state, merged_bars, bar, min_distance)
            state.processed_merged_count = bar_index + 1
            state.last_processed_bar_signature = _bar_signature(bar)
            continue

        _extend_active_segment(state, bar)

        active = state.active
        if active is None:
            state.processed_merged_count = bar_index + 1
            state.last_processed_bar_signature = _bar_signature(bar)
            continue

        if active.direction == "down" and _can_reverse_to_up(active, bar, merged_bars, min_distance):
            completed = _reverse_segment(state, "up", bar)
        elif active.direction == "up" and _can_reverse_to_down(active, bar, merged_bars, min_distance):
            completed = _reverse_segment(state, "down", bar)

        state.processed_merged_count = bar_index + 1
        state.last_processed_bar_signature = _bar_signature(bar)

    return completed
