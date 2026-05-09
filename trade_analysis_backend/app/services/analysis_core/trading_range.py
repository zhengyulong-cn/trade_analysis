"""交易区间构建（增量版本）。

特征序列 = 与大级别方向相反的本级别线段。
只做首次 a-b-c 三段确认，每次新线段完成后推进。
"""

from dataclasses import dataclass, field

from .types import AnalysisBar, BaseSegment, FenxingPoint, HigherLevelSegment, TradingRange

_INITIAL_OVERLAP = 0.4


@dataclass
class _Feature:
    base_index: int
    higher_direction: str
    seg: BaseSegment


@dataclass
class TradingRangeState:
    ranges: list[TradingRange] = field(default_factory=list)
    last_feature: _Feature | None = None
    processed_segment_count: int = 0


def create_trading_range_state() -> TradingRangeState:
    return TradingRangeState()


def _opposite(d: str) -> str:
    return "up" if d == "down" else "down"


def _seg_high(seg: BaseSegment) -> float:
    return max(seg.start.price, seg.end.price)


def _seg_low(seg: BaseSegment) -> float:
    return min(seg.start.price, seg.end.price)


def _overlap(al: float, ah: float, bl: float, bh: float) -> float:
    return max(0.0, min(ah, bh) - max(al, bl))


def _second_val(values: list[float], reverse: bool) -> float | None:
    if not values:
        return None
    sv = sorted(values, reverse=reverse)
    return sv[min(1, len(sv) - 1)]


def _find_higher_dir(seg: BaseSegment, higher_segs: list[HigherLevelSegment]) -> str | None:
    bs = min(seg.start.index, seg.end.index)
    be = max(seg.start.index, seg.end.index)
    for hs in reversed(higher_segs):
        if min(hs.start.index, hs.end.index) <= bs and max(hs.start.index, hs.end.index) >= be:
            return hs.direction
    for hs in reversed(higher_segs):
        if min(hs.start.index, hs.end.index) <= bs:
            return hs.direction
    return higher_segs[-1].direction if higher_segs else None


def _calc_range(features: list[_Feature], bars: list[AnalysisBar]) -> TradingRange | None:
    highs = [_seg_high(f.seg) for f in features]
    lows = [_seg_low(f.seg) for f in features]
    top = _second_val(highs, reverse=True)
    bottom = _second_val(lows, reverse=False)
    if top is None or bottom is None or top <= bottom:
        return None
    first, last = features[0], features[-1]
    lb = bars[first.seg.start.index]
    return TradingRange(
        top=top, bottom=bottom,
        left=FenxingPoint(index=lb.index, price=first.seg.start.price, time=lb.time),
        right=FenxingPoint(index=last.seg.end.index, price=last.seg.end.price, time=last.seg.end.time),
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
    sh = max(_seg_high(prev.seg), _seg_high(middle), _seg_high(curr.seg))
    sl = min(_seg_low(prev.seg), _seg_low(middle), _seg_low(curr.seg))
    sr = sh - sl
    if sr <= 0:
        return False
    ov = _overlap(_seg_low(prev.seg), _seg_high(prev.seg), _seg_low(curr.seg), _seg_high(curr.seg))
    return ov / sr >= _INITIAL_OVERLAP


def advance_trading_range(
    state: TradingRangeState,
    bars: list[AnalysisBar],
    base_segments: list[BaseSegment],
    higher_segments: list[HigherLevelSegment],
    seg_index: int,
) -> None:
    """处理一条新完成的本级别线段，尝试形成交易区间。"""
    seg = base_segments[seg_index]
    h_dir = _find_higher_dir(seg, higher_segments)
    if h_dir is None or seg.direction != _opposite(h_dir):
        state.processed_segment_count += 1
        return

    feat = _Feature(base_index=seg_index, higher_direction=h_dir, seg=seg)

    if state.last_feature is not None and seg_index == state.last_feature.base_index + 2:
        middle = base_segments[state.last_feature.base_index + 1]
        if _can_create(state.last_feature, middle, feat):
            rng = _calc_range([state.last_feature, feat], bars)
            if rng is not None:
                state.ranges.append(rng)

    state.last_feature = feat
    state.processed_segment_count += 1
