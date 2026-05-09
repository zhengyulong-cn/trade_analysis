"""动能衰竭判断（增量版本）。

在 MACD 金叉/死叉位置，往前找最近 3 条本级别线段，比较 a 段和 c 段的
MACD 面积来判断动能是否衰竭。

金叉 → 判断下跌衰竭：a=down, b=up, c=down
死叉 → 判断上涨衰竭：a=up, b=down, c=up
"""

from dataclasses import dataclass, field

from .types import AnalysisBar, BaseSegment, FenxingPoint, MomentumExhaustionSignal


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
    s = min(seg.start.index, seg.end.index)
    e = max(seg.start.index, seg.end.index)
    return s, e


def _recent_three(
    base_segments: list[BaseSegment],
    bar_index: int,
) -> list[BaseSegment] | None:
    """找到在 bar_index 之前结束的最近 3 条线段。"""
    available = [s for s in base_segments if _seg_closed_interval(s)[1] <= bar_index]
    if len(available) < 3:
        return None
    return available[-3:]


def _macd_area(bars: list[AnalysisBar], seg: BaseSegment) -> float:
    """计算线段区间内同向 MACD 柱面积。"""
    si, ei = _seg_closed_interval(seg)
    area = 0.0
    for i in range(si, ei + 1):
        h = bars[i].macd_histogram if i < len(bars) else None
        if h is None:
            continue
        if seg.direction == "up":
            area += max(h, 0.0)
        else:
            area += abs(min(h, 0.0))
    return area


def _seg_high(seg: BaseSegment) -> float:
    return max(seg.start.price, seg.end.price)


def _seg_low(seg: BaseSegment) -> float:
    return min(seg.start.price, seg.end.price)


def _is_up_exhausted(
    a: BaseSegment, c: BaseSegment, area_a: float, area_c: float,
) -> bool:
    """判断上涨衰竭：a、c 都是上涨段。"""
    a_low = _seg_low(a)
    a_high = _seg_high(a)
    c_low = _seg_low(c)
    c_high = _seg_high(c)

    # c 突破 a 高点：需要面积缩小才衰竭
    if a_low <= c_low and a_high < c_high:
        return area_c < area_a
    # c 没突破 a 高点：一定衰竭
    if a_low <= c_low and a_high >= c_high:
        return True
    # c 完全包裹 a：不衰竭
    if a_low > c_low and a_high < c_high:
        return False
    return False


def _is_down_exhausted(
    a: BaseSegment, c: BaseSegment, area_a: float, area_c: float,
) -> bool:
    """判断下跌衰竭：a、c 都是下跌段。"""
    a_low = _seg_low(a)
    a_high = _seg_high(a)
    c_low = _seg_low(c)
    c_high = _seg_high(c)

    # c 跌破 a 低点：需要面积缩小才衰竭
    if a_high >= c_high and a_low > c_low:
        return area_c < area_a
    # c 没跌破 a 低点：一定衰竭
    if a_high >= c_high and a_low <= c_low:
        return True
    # c 完全包裹 a：不衰竭
    if a_high < c_high and a_low > c_low:
        return False
    return False


def _check_current_bar(
    bars: list[AnalysisBar],
    base_segments: list[BaseSegment],
    i: int,
) -> MomentumExhaustionSignal | None:
    """检查当前 K 线是否形成 MACD 交叉并判断衰竭。"""
    prev = bars[i - 1]
    curr = bars[i]

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
            point=FenxingPoint(index=curr.index, price=curr.high, time=curr.time),
            previous_strength=area_a,
            current_strength=area_c,
        )

    if not _is_down_exhausted(a, c, area_a, area_c):
        return None
    return MomentumExhaustionSignal(
        direction="down",
        point=FenxingPoint(index=curr.index, price=curr.low, time=curr.time),
        previous_strength=area_a,
        current_strength=area_c,
    )


def advance_momentum_exhaustion(
    state: MomentumExhaustionState,
    bars: list[AnalysisBar],
    base_segments: list[BaseSegment],
    current_bar_index: int,
) -> None:
    """检查当前 K 线是否有 MACD 交叉并判断衰竭。"""
    if current_bar_index < 1 or current_bar_index < state.processed_bar_count:
        return

    signal = _check_current_bar(bars, base_segments, current_bar_index)
    if signal is not None:
        state.signals.append(signal)

    state.processed_bar_count = current_bar_index + 1
