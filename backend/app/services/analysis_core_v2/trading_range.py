from dataclasses import dataclass, field

from .types import AnalysisBar, BaseSegment, SegmentPoint, TradingRange

_INITIAL_OVERLAP = 0.4


@dataclass
class TradingRangeState:
    ranges: list[TradingRange] = field(default_factory=list)
    processed_count: int = 0


def create_trading_range_state() -> TradingRangeState:
    return TradingRangeState()


def _opposite(direction: str) -> str:
    return "up" if direction == "down" else "down"


def _seg_high(seg: BaseSegment) -> float:
    return max(seg.start.price, seg.end.price)


def _seg_low(seg: BaseSegment) -> float:
    return min(seg.start.price, seg.end.price)


def _overlap(al: float, ah: float, bl: float, bh: float) -> float:
    return max(0.0, min(ah, bh) - max(al, bl))


def _second_val(values: list[float], reverse: bool) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values, reverse=reverse)
    return sorted_values[min(1, len(sorted_values) - 1)]


def _check_abc(
    seg_a: BaseSegment,
    seg_b: BaseSegment,
    seg_c: BaseSegment,
    higher_dir: str,
) -> bool:
    feature_dir = _opposite(higher_dir)
    if seg_a.direction != feature_dir or seg_c.direction != feature_dir:
        return False
    if seg_b.direction == feature_dir:
        return False

    sequence_high = max(_seg_high(seg_a), _seg_high(seg_b), _seg_high(seg_c))
    sequence_low = min(_seg_low(seg_a), _seg_low(seg_b), _seg_low(seg_c))
    sequence_range = sequence_high - sequence_low
    if sequence_range <= 0:
        return False

    overlap = _overlap(
        _seg_low(seg_a),
        _seg_high(seg_a),
        _seg_low(seg_c),
        _seg_high(seg_c),
    )
    return overlap / sequence_range >= _INITIAL_OVERLAP


def _make_range(
    seg_a: BaseSegment,
    seg_c: BaseSegment,
    bars: list[AnalysisBar],
) -> TradingRange | None:
    highs = [_seg_high(seg_a), _seg_high(seg_c)]
    lows = [_seg_low(seg_a), _seg_low(seg_c)]
    top = _second_val(highs, reverse=True)
    bottom = _second_val(lows, reverse=False)
    if top is None or bottom is None or top <= bottom:
        return None

    a_start = min(seg_a.start.index, seg_a.end.index)
    c_end = max(seg_c.start.index, seg_c.end.index)
    left_bar = bars[a_start]
    right_bar = bars[c_end]

    return TradingRange(
        top=top,
        bottom=bottom,
        left=SegmentPoint(
            merged_index=seg_a.start.merged_index,
            index=left_bar.index,
            price=left_bar.low,
            time=left_bar.time,
        ),
        right=SegmentPoint(
            merged_index=seg_c.end.merged_index,
            index=right_bar.index,
            price=right_bar.high,
            time=right_bar.time,
        ),
    )


def _merge_overlapping(ranges: list[TradingRange]) -> list[TradingRange]:
    if len(ranges) < 2:
        return ranges

    sorted_ranges = sorted(ranges, key=lambda trading_range: trading_range.left.time)
    merged: list[TradingRange] = [sorted_ranges[0]]

    for trading_range in sorted_ranges[1:]:
        last = merged[-1]
        if trading_range.left.time <= last.right.time:
            merged[-1] = TradingRange(
                top=max(last.top, trading_range.top),
                bottom=min(last.bottom, trading_range.bottom),
                left=last.left if last.left.time <= trading_range.left.time else trading_range.left,
                right=last.right if last.right.time >= trading_range.right.time else trading_range.right,
            )
        else:
            merged.append(trading_range)

    return merged


def advance_trading_range(
    state: TradingRangeState,
    bars: list[AnalysisBar],
    base_segments: list[BaseSegment],
    current_higher_dir: str | None,
) -> None:
    new_ranges: list[TradingRange] = []

    for i in range(state.processed_count, len(base_segments)):
        if current_higher_dir is None:
            break
        if i < 2:
            continue
        a = base_segments[i - 2]
        b = base_segments[i - 1]
        c = base_segments[i]
        if _check_abc(a, b, c, current_higher_dir):
            trading_range = _make_range(a, c, bars)
            if trading_range is not None:
                new_ranges.append(trading_range)

    state.processed_count = len(base_segments)

    if new_ranges:
        state.ranges = _merge_overlapping(state.ranges + new_ranges)
