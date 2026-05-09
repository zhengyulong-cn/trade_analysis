"""包含处理 + 分型构建。

后端全量批量计算版本，不需要增量推进/截断重建那套状态机。
从左到右扫描一遍即出结果。
"""

from .types import AnalysisBar, FenxingPoint, FenxingSignal, MergedBar


def _create_merged_bar(bar: AnalysisBar) -> MergedBar:
    close_below = bar.close < bar.ema20 if bar.ema20 is not None else False
    return MergedBar(
        first_bar_close_below_ema20=close_below,
        high=bar.high,
        high_source_index=bar.index,
        high_source_time=bar.time,
        index=bar.index,
        low=bar.low,
        low_source_index=bar.index,
        low_source_time=bar.time,
        source_start_index=bar.index,
        source_start_time=bar.time,
        source_end_index=bar.index,
        source_end_time=bar.time,
        time=bar.time,
    )


def _has_inclusion(first: MergedBar, second: MergedBar) -> bool:
    return (first.high >= second.high and first.low <= second.low) or (
        first.high <= second.high and first.low >= second.low
    )


def _can_merge_within_limit(
    first: MergedBar, second: MergedBar, max_included_bar_count: int
) -> bool:
    return second.source_end_index - first.source_start_index + 1 <= max_included_bar_count


def _merge_included_bars(first: MergedBar, second: MergedBar) -> MergedBar:
    if first.first_bar_close_below_ema20:
        merged_high = min(first.high, second.high)
        merged_low = min(first.low, second.low)
        use_second_high = second.high < first.high
        use_second_low = second.low < first.low
    else:
        merged_high = max(first.high, second.high)
        merged_low = max(first.low, second.low)
        use_second_high = second.high > first.high
        use_second_low = second.low > first.low

    return MergedBar(
        first_bar_close_below_ema20=first.first_bar_close_below_ema20,
        high=merged_high,
        high_source_index=(
            second.high_source_index if use_second_high else first.high_source_index
        ),
        high_source_time=(
            second.high_source_time if use_second_high else first.high_source_time
        ),
        index=first.index,
        low=merged_low,
        low_source_index=(
            second.low_source_index if use_second_low else first.low_source_index
        ),
        low_source_time=(
            second.low_source_time if use_second_low else first.low_source_time
        ),
        source_end_index=second.source_end_index,
        source_end_time=second.source_end_time,
        source_start_index=first.source_start_index,
        source_start_time=first.source_start_time,
        time=first.time,
    )


def _build_fenxing_signal(
    left: MergedBar, middle: MergedBar, right: MergedBar
) -> FenxingSignal | None:
    is_top = (
        middle.high >= left.high
        and middle.high >= right.high
        and middle.low >= left.low
        and middle.low >= right.low
    )
    if is_top:
        return FenxingSignal(
            index=-1,  # 外部统一编入序号
            merged_bar_index=middle.index,
            point=FenxingPoint(
                index=middle.high_source_index,
                price=middle.high,
                time=middle.high_source_time,
            ),
            type="top",
        )

    is_bottom = (
        middle.high <= left.high
        and middle.high <= right.high
        and middle.low <= left.low
        and middle.low <= right.low
    )
    if is_bottom:
        return FenxingSignal(
            index=-1,
            merged_bar_index=middle.index,
            point=FenxingPoint(
                index=middle.low_source_index,
                price=middle.low,
                time=middle.low_source_time,
            ),
            type="bottom",
        )

    return None


def build_fractals(
    bars: list[AnalysisBar],
    max_included_bar_count: int = 10,
) -> tuple[list[MergedBar], list[FenxingSignal]]:
    """从原始 K 线构建分型。

    Args:
        bars: 包含 EMA20 的 K 线列表，按时间升序。
        max_included_bar_count: 递归包含最多允许覆盖的原始 K 线数。

    Returns:
        (merged_bars, signals): 处理后 K 线列表 + 确认的分型列表。
    """
    merged_bars: list[MergedBar] = []
    signals: list[FenxingSignal] = []

    for bar in bars:
        if bar.ema20 is None:
            # 无 EMA20 的 bar 直接跳过（与前端行为一致）
            continue

        next_bar = _create_merged_bar(bar)
        prev_bar = merged_bars[-1] if merged_bars else None

        if prev_bar is None:
            merged_bars.append(next_bar)
            continue

        if _has_inclusion(prev_bar, next_bar) and _can_merge_within_limit(
            prev_bar, next_bar, max_included_bar_count
        ):
            merged_bars[-1] = _merge_included_bars(prev_bar, next_bar)
            continue

        merged_bars.append(next_bar)
        merged_bars[-1].index = len(merged_bars) - 1

        # 检查倒数第二根是否构成新的分型中心
        center_idx = len(merged_bars) - 2
        if center_idx < 1:
            continue

        left = merged_bars[center_idx - 1]
        middle = merged_bars[center_idx]
        right = merged_bars[center_idx + 1]
        signal = _build_fenxing_signal(left, middle, right)
        if signal is not None:
            signal.index = len(signals)
            signals.append(signal)

    return merged_bars, signals
