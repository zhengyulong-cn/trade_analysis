from dataclasses import dataclass, field

from .types import AnalysisBar, BaseSegment, MomentumExhaustionSignal, SegmentPoint


@dataclass
class MomentumExhaustionState:
    signals: list[MomentumExhaustionSignal] = field(default_factory=list)
    processed_bar_count: int = 0


def create_momentum_exhaustion_state() -> MomentumExhaustionState:
    return MomentumExhaustionState()


def _is_golden_cross(prev: AnalysisBar, curr: AnalysisBar) -> bool:
    if prev.macd_diff is None or prev.macd_dea is None:
        return False
    if curr.macd_diff is None or curr.macd_dea is None:
        return False
    return prev.macd_diff <= prev.macd_dea and curr.macd_diff > curr.macd_dea


def _is_dead_cross(prev: AnalysisBar, curr: AnalysisBar) -> bool:
    if prev.macd_diff is None or prev.macd_dea is None:
        return False
    if curr.macd_diff is None or curr.macd_dea is None:
        return False
    return prev.macd_diff >= prev.macd_dea and curr.macd_diff < curr.macd_dea


def _seg_closed_interval(seg: BaseSegment) -> tuple[int, int]:
    return min(seg.start.index, seg.end.index), max(seg.start.index, seg.end.index)


def _recent_three(
    base_segments: list[BaseSegment],
    bar_index: int,
) -> list[BaseSegment] | None:
    available = [seg for seg in base_segments if _seg_closed_interval(seg)[1] <= bar_index]
    if len(available) < 3:
        return None
    return available[-3:]


def _macd_area(bars: list[AnalysisBar], seg: BaseSegment) -> float:
    start_index, end_index = _seg_closed_interval(seg)
    area = 0.0
    for i in range(start_index, end_index + 1):
        histogram = bars[i].macd_histogram if i < len(bars) else None
        if histogram is None:
            continue
        if seg.direction == "up":
            area += max(histogram, 0.0)
        else:
            area += abs(min(histogram, 0.0))
    return area


def _seg_high(seg: BaseSegment) -> float:
    return max(seg.start.price, seg.end.price)


def _seg_low(seg: BaseSegment) -> float:
    return min(seg.start.price, seg.end.price)


def _is_up_exhausted(
    a: BaseSegment,
    c: BaseSegment,
    area_a: float,
    area_c: float,
) -> bool:
    a_low = _seg_low(a)
    a_high = _seg_high(a)
    c_low = _seg_low(c)
    c_high = _seg_high(c)

    if a_low <= c_low and a_high < c_high:
        return area_c < area_a
    if a_low <= c_low and a_high >= c_high:
        return True
    if a_low > c_low and a_high < c_high:
        return False
    return False


def _is_down_exhausted(
    a: BaseSegment,
    c: BaseSegment,
    area_a: float,
    area_c: float,
) -> bool:
    a_low = _seg_low(a)
    a_high = _seg_high(a)
    c_low = _seg_low(c)
    c_high = _seg_high(c)

    if a_high >= c_high and a_low > c_low:
        return area_c < area_a
    if a_high >= c_high and a_low <= c_low:
        return True
    if a_high < c_high and a_low > c_low:
        return False
    return False


def _check_current_bar(
    bars: list[AnalysisBar],
    base_segments: list[BaseSegment],
    index: int,
) -> MomentumExhaustionSignal | None:
    prev = bars[index - 1]
    curr = bars[index]

    cross_type: str | None = None
    if _is_golden_cross(prev, curr):
        cross_type = "golden"
    elif _is_dead_cross(prev, curr):
        cross_type = "dead"

    if cross_type is None:
        return None

    recent = _recent_three(base_segments, curr.index)
    if recent is None:
        return None

    a, b, c = recent

    if cross_type == "golden":
        if not (a.direction == "down" and b.direction == "up" and c.direction == "down"):
            return None
    else:
        if not (a.direction == "up" and b.direction == "down" and c.direction == "up"):
            return None

    area_a = _macd_area(bars, a)
    area_c = _macd_area(bars, c)

    if cross_type == "dead":
        if not _is_up_exhausted(a, c, area_a, area_c):
            return None
        return MomentumExhaustionSignal(
            direction="up",
            point=SegmentPoint(
                merged_index=curr.index,
                index=curr.index,
                price=curr.high,
                time=curr.time,
            ),
            previous_strength=area_a,
            current_strength=area_c,
        )

    if not _is_down_exhausted(a, c, area_a, area_c):
        return None
    return MomentumExhaustionSignal(
        direction="down",
        point=SegmentPoint(
            merged_index=curr.index,
            index=curr.index,
            price=curr.low,
            time=curr.time,
        ),
        previous_strength=area_a,
        current_strength=area_c,
    )


def advance_momentum_exhaustion(
    state: MomentumExhaustionState,
    bars: list[AnalysisBar],
    base_segments: list[BaseSegment],
    current_bar_index: int,
) -> None:
    if current_bar_index < 1 or current_bar_index < state.processed_bar_count:
        return

    signal = _check_current_bar(bars, base_segments, current_bar_index)
    if signal is not None:
        state.signals.append(signal)

    state.processed_bar_count = current_bar_index + 1
