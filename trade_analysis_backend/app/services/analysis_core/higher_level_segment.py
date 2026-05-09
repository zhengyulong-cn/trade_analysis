"""大级别线段构建。

基于本级别线段 + EMA20/EMA120 相对关系构建大级别线段。
EMA20 >= EMA120 → above → up 方向。
EMA20 <  EMA120 → below → down 方向。
"""

from .types import AnalysisBar, BaseSegment, FenxingPoint, HigherLevelSegment

_CROSS_ABOVE = "above"
_CROSS_BELOW = "below"


def _get_cross_relation(bar: AnalysisBar) -> str | None:
    if bar.ema20 is None or bar.ema120 is None:
        return None
    return _CROSS_ABOVE if bar.ema20 >= bar.ema120 else _CROSS_BELOW


def _relation_direction(relation: str) -> str:
    return "up" if relation == _CROSS_ABOVE else "down"


def _clone_point(p: FenxingPoint) -> FenxingPoint:
    return FenxingPoint(index=p.index, price=p.price, time=p.time)


def _get_segment_high(seg: BaseSegment) -> FenxingPoint:
    """上涨段终点=高点, 下跌段起点=高点。"""
    return _clone_point(seg.end if seg.direction == "up" else seg.start)


def _get_segment_low(seg: BaseSegment) -> FenxingPoint:
    """上涨段起点=低点, 下跌段终点=低点。"""
    return _clone_point(seg.start if seg.direction == "up" else seg.end)


def _get_min_bar_span(min_bar_distance: int) -> int:
    return min_bar_distance * 2


def _is_valid_segment(seg: HigherLevelSegment, min_bar_distance: int) -> bool:
    return abs(seg.end.index - seg.start.index) + 1 >= _get_min_bar_span(min_bar_distance)


def _is_valid_range(start: FenxingPoint, end: FenxingPoint, min_bar_distance: int) -> bool:
    return abs(end.index - start.index) + 1 >= _get_min_bar_span(min_bar_distance)


def _get_range_extreme(
    base_segments: list[BaseSegment],
    from_index: int,
    to_index: int,
    selector,
    comparator,
) -> FenxingPoint | None:
    selected: FenxingPoint | None = None
    for seg in base_segments:
        pt = selector(seg)
        if pt.index < from_index or pt.index > to_index:
            continue
        if selected is None or comparator(pt.price, selected.price):
            selected = pt
    return _clone_point(selected) if selected else None


def _get_range_high(
    base_segments: list[BaseSegment], from_index: int, to_index: int
) -> FenxingPoint | None:
    return _get_range_extreme(
        base_segments, from_index, to_index,
        _get_segment_high,
        lambda a, b: a > b,
    )


def _get_range_low(
    base_segments: list[BaseSegment], from_index: int, to_index: int
) -> FenxingPoint | None:
    return _get_range_extreme(
        base_segments, from_index, to_index,
        _get_segment_low,
        lambda a, b: a < b,
    )


def _get_first_base_segment_index(base_segments: list[BaseSegment]) -> int | None:
    if not base_segments:
        return None
    first = base_segments[0]
    return min(first.start.index, first.end.index)


def _get_range_start(
    historical: list[HigherLevelSegment],
    base_segments: list[BaseSegment],
    last_cross_bar_index: int | None,
) -> int | None:
    last_hist_end = historical[-1].end.index if historical else None
    first_base = _get_first_base_segment_index(base_segments)

    if last_cross_bar_index is None:
        return last_hist_end or first_base

    if last_hist_end is None:
        candidates = [last_cross_bar_index]
        if first_base is not None:
            candidates.append(first_base)
        return max(candidates)

    return max(last_hist_end, last_cross_bar_index)


def _start_up_segment(
    base_segments: list[BaseSegment],
    historical: list[HigherLevelSegment],
    last_cross_bar_index: int | None,
    cross_bar_index: int,
) -> HigherLevelSegment | None:
    range_start = _get_range_start(historical, base_segments, last_cross_bar_index)
    if range_start is None:
        return None
    start_pt = _get_range_low(base_segments, range_start, cross_bar_index)
    if start_pt is None:
        return None
    end_pt = _get_range_high(base_segments, start_pt.index, cross_bar_index)
    if end_pt is None:
        end_pt = start_pt
    return HigherLevelSegment(direction="up", start=start_pt, end=end_pt)


def _start_down_segment(
    base_segments: list[BaseSegment],
    historical: list[HigherLevelSegment],
    last_cross_bar_index: int | None,
    cross_bar_index: int,
) -> HigherLevelSegment | None:
    range_start = _get_range_start(historical, base_segments, last_cross_bar_index)
    if range_start is None:
        return None
    start_pt = _get_range_high(base_segments, range_start, cross_bar_index)
    if start_pt is None:
        return None
    end_pt = _get_range_low(base_segments, start_pt.index, cross_bar_index)
    if end_pt is None:
        end_pt = start_pt
    return HigherLevelSegment(direction="down", start=start_pt, end=end_pt)


def _start_segment_for_relation(
    relation: str,
    base_segments: list[BaseSegment],
    historical: list[HigherLevelSegment],
    last_cross_bar_index: int | None,
    bar_index: int,
) -> HigherLevelSegment | None:
    if relation == _CROSS_ABOVE:
        return _start_up_segment(base_segments, historical, last_cross_bar_index, bar_index)
    return _start_down_segment(base_segments, historical, last_cross_bar_index, bar_index)


def _update_active_end(
    active: HigherLevelSegment,
    base_segments: list[BaseSegment],
    to_index: int,
) -> None:
    if active.direction == "up":
        next_end = _get_range_high(base_segments, active.start.index, to_index)
    else:
        next_end = _get_range_low(base_segments, active.start.index, to_index)
    if next_end is not None:
        active.end = next_end


def _try_reverse(
    active: HigherLevelSegment,
    current_relation: str,
    base_segments: list[BaseSegment],
    historical: list[HigherLevelSegment],
    bar_index: int,
    min_bar_distance: int,
) -> bool:
    candidate_start = _clone_point(active.end)
    if current_relation == _CROSS_ABOVE:
        candidate_end = _get_range_high(base_segments, candidate_start.index, bar_index)
    else:
        candidate_end = _get_range_low(base_segments, candidate_start.index, bar_index)

    if candidate_end is None or not _is_valid_range(candidate_start, candidate_end, min_bar_distance):
        return False

    if _is_valid_segment(active, min_bar_distance):
        historical.append(HigherLevelSegment(
            direction=active.direction,
            start=_clone_point(active.start),
            end=_clone_point(active.end),
        ))

    active.direction = _relation_direction(current_relation)
    active.start = candidate_start
    active.end = candidate_end
    return True


def build_higher_level_segments(
    bars: list[AnalysisBar],
    base_segments: list[BaseSegment],
    min_bar_distance: int = 3,
) -> list[HigherLevelSegment]:
    """构建大级别线段。

    Args:
        bars: K 线数据（需带 EMA20 + EMA120）。
        base_segments: 本级别线段列表。
        min_bar_distance: 本级别最小间距，大级别最小跨度为 min_bar_distance * 5。

    Returns:
        大级别线段列表。
    """
    if not base_segments:
        return []

    historical: list[HigherLevelSegment] = []
    active: HigherLevelSegment | None = None
    last_cross_relation: str | None = None
    last_cross_bar_index: int | None = None

    for bar in bars:
        relation = _get_cross_relation(bar)
        if relation is None:
            continue

        if active is None:
            if last_cross_relation is not None and last_cross_relation != relation:
                seg = _start_segment_for_relation(
                    relation, base_segments, historical,
                    last_cross_bar_index, bar.index,
                )
                if seg is not None:
                    active = seg
                    last_cross_bar_index = bar.index
        elif active.direction == _relation_direction(relation):
            # 同向周期：延续终点
            _update_active_end(active, base_segments, bar.index)
        else:
            # 反向周期：尝试翻段
            did_reverse = _try_reverse(
                active, relation, base_segments, historical,
                bar.index, min_bar_distance,
            )
            if did_reverse and last_cross_relation != relation:
                last_cross_bar_index = bar.index

        if last_cross_bar_index is None:
            last_cross_bar_index = bar.index

        last_cross_relation = relation

    if active is not None and _is_valid_segment(active, min_bar_distance):
        historical.append(active)

    return historical
