"""交易区间构建。

特征序列 = 与大级别方向相反的本级别线段。
只做首次 a-b-c 三段确认，不做后续延申。
"""

from dataclasses import dataclass

from .types import AnalysisBar, BaseSegment, FenxingPoint, HigherLevelSegment, TradingRange

_INITIAL_OVERLAP = 0.4


@dataclass
class _Feature:
    base_index: int  # index in base_segments list
    higher_direction: str
    seg: BaseSegment


def _opposite(direction: str) -> str:
    return "up" if direction == "down" else "down"


def _seg_high(seg: BaseSegment) -> float:
    return max(seg.start.price, seg.end.price)


def _seg_low(seg: BaseSegment) -> float:
    return min(seg.start.price, seg.end.price)


def _overlap(a_low: float, a_high: float, b_low: float, b_high: float) -> float:
    return max(0.0, min(a_high, b_high) - max(a_low, b_low))


def _second_value(values: list[float], reverse: bool) -> float | None:
    if not values:
        return None
    sorted_vals = sorted(values, reverse=reverse)
    return sorted_vals[min(1, len(sorted_vals) - 1)]


def _find_higher_direction(
    seg: BaseSegment,
    higher_segments: list[HigherLevelSegment],
) -> str | None:
    """找到包含本级别线段的大级别线段，返回其方向。"""
    base_start = min(seg.start.index, seg.end.index)
    base_end = max(seg.start.index, seg.end.index)

    for hs in reversed(higher_segments):
        hs_start = min(hs.start.index, hs.end.index)
        hs_end = max(hs.start.index, hs.end.index)
        if hs_start <= base_start and hs_end >= base_end:
            return hs.direction

    for hs in reversed(higher_segments):
        hs_start = min(hs.start.index, hs.end.index)
        if hs_start <= base_start:
            return hs.direction

    return higher_segments[-1].direction if higher_segments else None


def _calc_range(features: list[_Feature], bars: list[AnalysisBar]) -> TradingRange | None:
    if not features:
        return None

    highs = [_seg_high(f.seg) for f in features]
    lows = [_seg_low(f.seg) for f in features]
    top = _second_value(highs, reverse=True)
    bottom = _second_value(lows, reverse=False)
    if top is None or bottom is None or top <= bottom:
        return None

    first = features[0]
    last = features[-1]
    left_bar = bars[first.seg.start.index]

    return TradingRange(
        top=top,
        bottom=bottom,
        left=FenxingPoint(
            index=left_bar.index,
            price=first.seg.start.price,
            time=left_bar.time,
        ),
        right=FenxingPoint(
            index=last.seg.end.index,
            price=last.seg.end.price,
            time=last.seg.end.time,
        ),
    )


def _can_create(prev: _Feature, middle: BaseSegment | None, curr: _Feature) -> bool:
    if middle is None:
        return False
    if prev.higher_direction != curr.higher_direction:
        return False
    if prev.seg.direction != curr.seg.direction:
        return False
    if middle.direction == curr.seg.direction:
        return False

    structure_high = max(_seg_high(prev.seg), _seg_high(middle), _seg_high(curr.seg))
    structure_low = min(_seg_low(prev.seg), _seg_low(middle), _seg_low(curr.seg))
    structure_range = structure_high - structure_low
    if structure_range <= 0:
        return False

    ov = _overlap(
        _seg_low(prev.seg), _seg_high(prev.seg),
        _seg_low(curr.seg), _seg_high(curr.seg),
    )
    return ov / structure_range >= _INITIAL_OVERLAP


def build_trading_ranges(
    bars: list[AnalysisBar],
    base_segments: list[BaseSegment],
    higher_segments: list[HigherLevelSegment],
) -> list[TradingRange]:
    """构建交易区间。只做首次 a-b-c 三段确认。"""
    if not higher_segments:
        return []

    ranges: list[TradingRange] = []
    last_feature: _Feature | None = None

    for i, seg in enumerate(base_segments):
        h_dir = _find_higher_direction(seg, higher_segments)
        if h_dir is None or seg.direction != _opposite(h_dir):
            continue

        feat = _Feature(base_index=i, higher_direction=h_dir, seg=seg)

        if last_feature is not None and i == last_feature.base_index + 2:
            middle = base_segments[last_feature.base_index + 1]
            if _can_create(last_feature, middle, feat):
                rng = _calc_range([last_feature, feat], bars)
                if rng is not None:
                    ranges.append(rng)

        last_feature = feat

    return ranges
