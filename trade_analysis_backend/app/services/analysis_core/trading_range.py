"""交易区间构建（增量版本）。

特征序列 = 与当前大级别方向相反的本级别线段。
每完成一条本级别线段，立即用前两条进行 a-b-c 判定：
- 当前大级别上涨 → 下跌a - 上涨b - 下跌c
- 当前大级别下跌 → 上涨a - 下跌b - 上涨c
不做左右延申。
"""

from dataclasses import dataclass, field

from .types import AnalysisBar, BaseSegment, FenxingPoint, TradingRange

_INITIAL_OVERLAP = 0.4


@dataclass
class TradingRangeState:
    ranges: list[TradingRange] = field(default_factory=list)
    processed_count: int = 0  # 已处理过的线段数


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


def _check_abc(
    seg_a: BaseSegment,
    seg_b: BaseSegment,
    seg_c: BaseSegment,
    higher_dir: str,
) -> bool:
    """a-b-c 三段是否符合交易区间条件。"""
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
    lb = bars[a_start]
    rb = bars[c_end]

    return TradingRange(
        top=top, bottom=bottom,
        left=FenxingPoint(index=lb.index, price=lb.low, time=lb.time),
        right=FenxingPoint(index=rb.index, price=rb.high, time=rb.time),
    )


def _merge_overlapping(ranges: list[TradingRange]) -> list[TradingRange]:
    """合并时间重叠的交易区间。"""
    if len(ranges) < 2:
        return ranges

    # 按左边界时间排序
    sorted_ranges = sorted(ranges, key=lambda r: r.left.time)
    merged: list[TradingRange] = [sorted_ranges[0]]

    for r in sorted_ranges[1:]:
        last = merged[-1]
        if r.left.time <= last.right.time:
            # 重叠：合并为更宽的范围
            merged[-1] = TradingRange(
                top=max(last.top, r.top),
                bottom=min(last.bottom, r.bottom),
                left=last.left if last.left.time <= r.left.time else r.left,
                right=last.right if last.right.time >= r.right.time else r.right,
            )
        else:
            merged.append(r)

    return merged


def advance_trading_range(
    state: TradingRangeState,
    bars: list[AnalysisBar],
    base_segments: list[BaseSegment],
    current_higher_dir: str | None,
) -> None:
    """本级别线段完成后立即判定，不等大级别反转。"""
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
            rng = _make_range(a, c, bars)
            if rng is not None:
                new_ranges.append(rng)

    state.processed_count = len(base_segments)

    if new_ranges:
        # 新找到的区间和已有的合并
        all_ranges = state.ranges + new_ranges
        state.ranges = _merge_overlapping(all_ranges)

