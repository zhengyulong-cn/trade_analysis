"""交易区间构建（增量版本）。

遍历每个大级别线段覆盖的本级别线段，找连续 a-b-c 三段：
- 大级别上涨 → 下跌a - 上涨b - 下跌c（a、c 为特征序列）
- 大级别下跌 → 上涨a - 下跌b - 上涨c
不做左右延申。
"""

from dataclasses import dataclass, field

from .types import AnalysisBar, BaseSegment, FenxingPoint, HigherLevelSegment, TradingRange

_INITIAL_OVERLAP = 0.4


@dataclass
class TradingRangeState:
    ranges: list[TradingRange] = field(default_factory=list)
    prev_higher_count: int = 0


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


def _seg_inside_higher(seg: BaseSegment, hs: HigherLevelSegment) -> bool:
    """本级别线段是否完全在大级别段范围内。"""
    s_s = min(seg.start.index, seg.end.index)
    s_e = max(seg.start.index, seg.end.index)
    h_s = min(hs.start.index, hs.end.index)
    h_e = max(hs.start.index, hs.end.index)
    return h_s <= s_s and s_e <= h_e


def _make_range(seg_a: BaseSegment, seg_c: BaseSegment, bars: list[AnalysisBar]) -> TradingRange | None:
    highs = [_seg_high(seg_a), _seg_high(seg_c)]
    lows = [_seg_low(seg_a), _seg_low(seg_c)]
    top = _second_val(highs, reverse=True)
    bottom = _second_val(lows, reverse=False)
    if top is None or bottom is None or top <= bottom:
        return None

    # left = a 段起点 bar，right = c 段终点 bar（不做左右延申）
    a_start_idx = min(seg_a.start.index, seg_a.end.index)
    c_end_idx = max(seg_c.start.index, seg_c.end.index)
    lb = bars[a_start_idx]
    rb = bars[c_end_idx]

    return TradingRange(
        top=top, bottom=bottom,
        left=FenxingPoint(index=lb.index, price=lb.low, time=lb.time),
        right=FenxingPoint(index=rb.index, price=rb.high, time=rb.time),
    )


def _check_abc(
    seg_a: BaseSegment,
    seg_b: BaseSegment,
    seg_c: BaseSegment,
    higher_dir: str,
) -> bool:
    """验证 a-b-c 是否符合交易区间条件。

    higher_dir='up' → a=down, b=up, c=down
    higher_dir='down' → a=up, b=down, c=up
    """
    feature_dir = _opposite(higher_dir)
    if seg_a.direction != feature_dir or seg_c.direction != feature_dir:
        return False
    if seg_b.direction == feature_dir:
        return False

    sh = max(_seg_high(seg_a), _seg_high(seg_b), _seg_high(seg_c))
    sl = min(_seg_low(seg_a), _seg_low(seg_b), _seg_low(seg_c))
    sr = sh - sl
    if sr <= 0:
        return False
    ov = _overlap(_seg_low(seg_a), _seg_high(seg_a), _seg_low(seg_c), _seg_high(seg_c))
    return ov / sr >= _INITIAL_OVERLAP


def advance_trading_range(
    state: TradingRangeState,
    bars: list[AnalysisBar],
    base_segments: list[BaseSegment],
    higher_segments: list[HigherLevelSegment],
) -> None:
    """增量推进：大级别段数量变化时重建全部交易区间。

    只在当前已知的大级别段和本级别段范围内计算，
    不使用未来的线段信息。
    """
    if len(higher_segments) == state.prev_higher_count:
        return
    state.prev_higher_count = len(higher_segments)

    ranges: list[TradingRange] = []

    for hs in higher_segments:
        # 收集该大级别段完全覆盖的本级别线段
        inside = [s for s in base_segments if _seg_inside_higher(s, hs)]
        if len(inside) < 3:
            continue

        # 连续三段滑动窗口
        for i in range(len(inside) - 2):
            a, b, c = inside[i], inside[i + 1], inside[i + 2]
            if _check_abc(a, b, c, hs.direction):
                rng = _make_range(a, c, bars)
                if rng is not None:
                    ranges.append(rng)

    state.ranges = ranges
