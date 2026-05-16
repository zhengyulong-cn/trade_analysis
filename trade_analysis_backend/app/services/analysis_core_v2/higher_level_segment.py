from dataclasses import dataclass, field

from .types import AnalysisBar, BaseSegment, HigherLevelSegment, SegmentPoint

_CROSS_ABOVE = "above"
_CROSS_BELOW = "below"


@dataclass
class HigherLevelState:
    historical: list[HigherLevelSegment] = field(default_factory=list)
    active: HigherLevelSegment | None = None
    last_cross_relation: str | None = None
    last_cross_bar_index: int | None = None
    processed_bar_count: int = 0


def create_higher_level_state() -> HigherLevelState:
    return HigherLevelState()


def all_higher_segments(state: HigherLevelState, min_bar_distance: int) -> list[HigherLevelSegment]:
    result = list(state.historical)
    if state.active is not None and _is_valid_seg(state.active, min_bar_distance):
        result.append(state.active)
    return result


def _get_cross_relation(bar: AnalysisBar) -> str | None:
    if bar.ema20 is None or bar.ema120 is None:
        return None
    return _CROSS_ABOVE if bar.ema20 >= bar.ema120 else _CROSS_BELOW


def _relation_dir(relation: str) -> str:
    return "up" if relation == _CROSS_ABOVE else "down"


def _clone_pt(point: SegmentPoint) -> SegmentPoint:
    return SegmentPoint(
        merged_index=point.merged_index,
        index=point.index,
        price=point.price,
        time=point.time,
    )


def _seg_high(seg: BaseSegment) -> SegmentPoint:
    return _clone_pt(seg.end if seg.direction == "up" else seg.start)


def _seg_low(seg: BaseSegment) -> SegmentPoint:
    return _clone_pt(seg.start if seg.direction == "up" else seg.end)


def _min_span(min_bar_distance: int) -> int:
    return min_bar_distance * 2


def _is_valid_seg(seg: HigherLevelSegment, min_bar_distance: int) -> bool:
    return abs(seg.end.index - seg.start.index) + 1 >= _min_span(min_bar_distance)


def _is_valid_range(start: SegmentPoint, end: SegmentPoint, min_bar_distance: int) -> bool:
    return abs(end.index - start.index) + 1 >= _min_span(min_bar_distance)


def _range_high(segments: list[BaseSegment], from_idx: int, to_idx: int) -> SegmentPoint | None:
    best: SegmentPoint | None = None
    for seg in segments:
        point = _seg_high(seg)
        if from_idx <= point.index <= to_idx:
            if best is None or point.price > best.price:
                best = point
    return best


def _range_low(segments: list[BaseSegment], from_idx: int, to_idx: int) -> SegmentPoint | None:
    best: SegmentPoint | None = None
    for seg in segments:
        point = _seg_low(seg)
        if from_idx <= point.index <= to_idx:
            if best is None or point.price < best.price:
                best = point
    return best


def _first_base_index(segments: list[BaseSegment]) -> int | None:
    if not segments:
        return None
    return min(segments[0].start.index, segments[0].end.index)


def _range_start(state: HigherLevelState, segments: list[BaseSegment]) -> int | None:
    last_end = state.historical[-1].end.index if state.historical else None
    first_base = _first_base_index(segments)
    if state.last_cross_bar_index is None:
        return last_end or first_base
    if last_end is None:
        candidates = [state.last_cross_bar_index]
        if first_base is not None:
            candidates.append(first_base)
        return max(candidates)
    return max(last_end, state.last_cross_bar_index)


def _start_up(segments: list[BaseSegment], state: HigherLevelState, bar_idx: int) -> HigherLevelSegment | None:
    range_start = _range_start(state, segments)
    if range_start is None:
        return None
    start = _range_low(segments, range_start, bar_idx)
    if start is None:
        return None
    end = _range_high(segments, start.index, bar_idx)
    if end is None:
        end = start
    return HigherLevelSegment(direction="up", start=start, end=end)


def _start_down(segments: list[BaseSegment], state: HigherLevelState, bar_idx: int) -> HigherLevelSegment | None:
    range_start = _range_start(state, segments)
    if range_start is None:
        return None
    start = _range_high(segments, range_start, bar_idx)
    if start is None:
        return None
    end = _range_low(segments, start.index, bar_idx)
    if end is None:
        end = start
    return HigherLevelSegment(direction="down", start=start, end=end)


def _try_reverse(
    state: HigherLevelState,
    relation: str,
    segments: list[BaseSegment],
    bar_idx: int,
    min_bar_distance: int,
) -> bool:
    active = state.active
    if active is None:
        return False
    current_start = _clone_pt(active.end)
    current_end = (
        _range_high(segments, current_start.index, bar_idx)
        if relation == _CROSS_ABOVE
        else _range_low(segments, current_start.index, bar_idx)
    )
    if current_end is None or not _is_valid_range(current_start, current_end, min_bar_distance):
        return False
    if _is_valid_seg(active, min_bar_distance):
        state.historical.append(
            HigherLevelSegment(
                direction=active.direction,
                start=_clone_pt(active.start),
                end=_clone_pt(active.end),
            )
        )
    state.active = HigherLevelSegment(
        direction=_relation_dir(relation),
        start=current_start,
        end=current_end,
    )
    return True


def advance_higher_level(
    state: HigherLevelState,
    bar: AnalysisBar,
    bar_index: int,
    base_segments: list[BaseSegment],
    min_bar_distance: int = 3,
) -> None:
    relation = _get_cross_relation(bar)
    if relation is None:
        state.processed_bar_count += 1
        return

    if state.active is None:
        if state.last_cross_relation is not None and state.last_cross_relation != relation:
            seg = (
                _start_up(base_segments, state, bar_index)
                if relation == _CROSS_ABOVE
                else _start_down(base_segments, state, bar_index)
            )
            if seg is not None:
                state.active = seg
                state.last_cross_bar_index = bar_index
    elif state.active.direction == _relation_dir(relation):
        next_end = (
            _range_high(base_segments, state.active.start.index, bar_index)
            if state.active.direction == "up"
            else _range_low(base_segments, state.active.start.index, bar_index)
        )
        if next_end is not None:
            state.active.end = next_end
    else:
        reversed_flag = _try_reverse(state, relation, base_segments, bar_index, min_bar_distance)
        if reversed_flag and state.last_cross_relation != relation:
            state.last_cross_bar_index = bar_index

    if state.last_cross_bar_index is None:
        state.last_cross_bar_index = bar_index
    state.last_cross_relation = relation
    state.processed_bar_count += 1
