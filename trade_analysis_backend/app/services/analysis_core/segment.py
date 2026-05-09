"""本级别线段构建。

基于已确认分型 + EMA20 构建本级别线段。
后端全量批量计算，不需要前端那套增量/截断状态机。
"""

from .types import AnalysisBar, BaseSegment, FenxingPoint, FenxingSignal


def _get_ema20(bars: list[AnalysisBar], signal: FenxingSignal) -> float | None:
    bar = bars[signal.point.index] if signal.point.index < len(bars) else None
    return bar.ema20 if bar else None


def _is_top_above_ema20(bars: list[AnalysisBar], signal: FenxingSignal) -> bool:
    ema20 = _get_ema20(bars, signal)
    return signal.type == "top" and ema20 is not None and signal.point.price > ema20


def _is_bottom_below_ema20(bars: list[AnalysisBar], signal: FenxingSignal) -> bool:
    ema20 = _get_ema20(bars, signal)
    return signal.type == "bottom" and ema20 is not None and signal.point.price < ema20


def _has_enough_distance(
    start: FenxingSignal, end: FenxingSignal, min_distance: int
) -> bool:
    return abs(end.point.index - start.point.index) > min_distance


def _can_bypass_for_down_reversal(
    active: BaseSegment, end_signal: FenxingSignal
) -> bool:
    return active.direction == "up" and end_signal.point.price < active.start.price


def _can_bypass_for_up_reversal(
    active: BaseSegment, end_signal: FenxingSignal
) -> bool:
    return active.direction == "down" and end_signal.point.price > active.start.price


def _is_valid_up_segment(
    bars: list[AnalysisBar],
    signals: list[FenxingSignal],
    start_signal: FenxingSignal,
    end_signal: FenxingSignal,
    min_distance: int,
    allow_bypass: bool = False,
) -> bool:
    if (
        not _is_bottom_below_ema20(bars, start_signal)
        or not _is_top_above_ema20(bars, end_signal)
    ):
        return False

    if not allow_bypass and not _has_enough_distance(
        start_signal, end_signal, min_distance
    ):
        return False

    # 区间内不允许有更高的顶分型，也不允许有更低的底分型
    for i in range(start_signal.index, end_signal.index + 1):
        s = signals[i]
        if s.type == "top" and s.point.price > end_signal.point.price:
            return False
        if s.type == "bottom" and s.point.price < start_signal.point.price:
            return False

    return True


def _is_valid_down_segment(
    bars: list[AnalysisBar],
    signals: list[FenxingSignal],
    start_signal: FenxingSignal,
    end_signal: FenxingSignal,
    min_distance: int,
    allow_bypass: bool = False,
) -> bool:
    if (
        not _is_top_above_ema20(bars, start_signal)
        or not _is_bottom_below_ema20(bars, end_signal)
    ):
        return False

    if not allow_bypass and not _has_enough_distance(
        start_signal, end_signal, min_distance
    ):
        return False

    for i in range(start_signal.index, end_signal.index + 1):
        s = signals[i]
        if s.type == "top" and s.point.price > start_signal.point.price:
            return False
        if s.type == "bottom" and s.point.price < end_signal.point.price:
            return False

    return True


def _make_segment(
    direction: str,
    start: FenxingSignal,
    end: FenxingSignal,
) -> BaseSegment:
    return BaseSegment(
        direction=direction,
        start=FenxingPoint(
            index=start.point.index,
            price=start.point.price,
            time=start.point.time,
        ),
        end=FenxingPoint(
            index=end.point.index,
            price=end.point.price,
            time=end.point.time,
        ),
        start_signal_index=start.index,
        end_signal_index=end.index,
    )


def build_base_segments(
    bars: list[AnalysisBar],
    signals: list[FenxingSignal],
    min_bar_distance: int = 3,
) -> list[BaseSegment]:
    """从分型信号构建本级别线段。

    Args:
        bars: K 线数据（需带 EMA20）。
        signals: 已确认的分型列表。
        min_bar_distance: 线段起止极值 K 线最小间距。

    Returns:
        本级别线段列表（历史段 + 当前活动段）。
    """
    if not signals:
        return []

    historical: list[BaseSegment] = []
    active: BaseSegment | None = None
    seed_bottom: FenxingSignal | None = None
    seed_top: FenxingSignal | None = None

    for signal in signals:
        # ---- 种子阶段：还没形成活动段 ----
        if active is None:
            if _is_bottom_below_ema20(bars, signal):
                if seed_top is not None and _is_valid_down_segment(
                    bars, signals, seed_top, signal, min_bar_distance
                ):
                    active = _make_segment("down", seed_top, signal)
                    seed_bottom = None
                    seed_top = None
                else:
                    if (
                        seed_bottom is None
                        or signal.point.price < seed_bottom.point.price
                    ):
                        seed_bottom = signal
                continue

            if _is_top_above_ema20(bars, signal):
                if seed_bottom is not None and _is_valid_up_segment(
                    bars, signals, seed_bottom, signal, min_bar_distance
                ):
                    active = _make_segment("up", seed_bottom, signal)
                    seed_top = None
                    seed_bottom = None
                else:
                    if seed_top is None or signal.point.price > seed_top.point.price:
                        seed_top = signal
                continue

            continue

        # ---- 活动段阶段 ----
        if active.direction == "up":
            # 同向延续：更高的顶分型
            if _is_top_above_ema20(bars, signal) and signal.point.price > active.end.price:
                active = _make_segment(
                    "up",
                    signals[active.start_signal_index],
                    signal,
                )
                continue

            # 反向翻段：底分型 → 潜在下跌段
            if _is_bottom_below_ema20(bars, signal):
                start_sig = signals[active.end_signal_index]
                bypass = _can_bypass_for_down_reversal(active, signal)
                if _is_valid_down_segment(
                    bars, signals, start_sig, signal, min_bar_distance, bypass,
                ):
                    historical.append(active)
                    active = _make_segment("down", start_sig, signal)
            continue

        # active.direction == 'down'
        if _is_bottom_below_ema20(bars, signal) and signal.point.price < active.end.price:
            active = _make_segment(
                "down",
                signals[active.start_signal_index],
                signal,
            )
            continue

        if _is_top_above_ema20(bars, signal):
            start_sig = signals[active.end_signal_index]
            bypass = _can_bypass_for_up_reversal(active, signal)
            if _is_valid_up_segment(
                bars, signals, start_sig, signal, min_bar_distance, bypass,
            ):
                historical.append(active)
                active = _make_segment("up", start_sig, signal)

    if active is not None:
        historical.append(active)

    return historical
