"""
包含处理规则

这一步只做 K 线包含合并，不做分型、线段或后续分析。

当前实现规则如下：

1. 每根原始 K 线先转换成一个 MergedBar。
   - 初始 high/low 就是原始 K 线的 high/low。
   - 记录高低点来源的原始 bar index/time。
   - 记录 source_start_index/source_end_index，表示这根合并 K 线覆盖的原始 K 线范围。

2. 新来的 K 线只和“当前最后一根 merged_bar”比较。
   - 如果两者没有包含关系，则直接新开一根 merged_bar。
   - 如果两者存在包含关系，则尝试继续合并。

3. 包含关系定义：
   - first.high >= second.high and first.low <= second.low
   - 或 first.high <= second.high and first.low >= second.low

4. 连续包含合并受 max_included 限制。
   - 计算方式：
     second.source_end_index - first.source_start_index + 1 <= max_included
   - 默认最多让一根 merged_bar 覆盖 10 根原始 K 线。

5. 遇到包含时，不再看 EMA20，而是看 k1 和 k2 的相对关系决定合并方向。
   - 这里：
     k1 = 当前 merged_bar 的前一根 merged_bar
     k2 = 当前最后一根 merged_bar
     k3 = 新来的 K 线
   - k1 和 k2 不会再有包含关系，因为 k2 进入 merged_bars 前已经处理过。

6. 如果 k2 相对 k1 高点、低点都抬高：
   - merged_high = max(k2.high, k3.high)
   - merged_low = max(k2.low, k3.low)

7. 如果 k2 相对 k1 高点、低点都降低：
   - merged_high = min(k2.high, k3.high)
   - merged_low = min(k2.low, k3.low)

8. high/low 的来源索引和时间，跟随最终被采用的高低点一起更新。

注意：
- 只有在能明确判断 k2 相对 k1 是整体抬高或整体降低时，才按对应方向合并。
- 如果当前没有 k1，或者 k1/k2 既不是同步抬高也不是同步降低，则当前实现退化为：
  high 取 first/second 的更大值，low 取 first/second 的更小值。
"""

from dataclasses import dataclass, field

from .types import AnalysisBar, MergedBar


@dataclass
class InclusionState:
    merged_bars: list[MergedBar] = field(default_factory=list)
    processed_count: int = 0


def create_inclusion_state() -> InclusionState:
    return InclusionState()


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
        ema20=bar.ema20,
    )


def _has_inclusion(first: MergedBar, second: MergedBar) -> bool:
    return (first.high >= second.high and first.low <= second.low) or (
        first.high <= second.high and first.low >= second.low
    )


def _can_merge(first: MergedBar, second: MergedBar, max_count: int) -> bool:
    return second.source_end_index - first.source_start_index + 1 <= max_count


def _merge(
    previous: MergedBar | None,
    current: MergedBar,
    incoming: MergedBar,
) -> MergedBar:
    merged_high = max(current.high, incoming.high)
    merged_low = min(current.low, incoming.low)
    use_incoming_high = incoming.high > current.high
    use_incoming_low = incoming.low < current.low

    if previous is not None:
        is_rising = current.high > previous.high and current.low > previous.low
        is_falling = current.high < previous.high and current.low < previous.low

        if is_rising:
            merged_high = max(current.high, incoming.high)
            merged_low = max(current.low, incoming.low)
            use_incoming_high = incoming.high > current.high
            use_incoming_low = incoming.low > current.low
        elif is_falling:
            merged_high = min(current.high, incoming.high)
            merged_low = min(current.low, incoming.low)
            use_incoming_high = incoming.high < current.high
            use_incoming_low = incoming.low < current.low

    return MergedBar(
        first_bar_close_below_ema20=current.first_bar_close_below_ema20,
        high=merged_high,
        high_source_index=incoming.high_source_index if use_incoming_high else current.high_source_index,
        high_source_time=incoming.high_source_time if use_incoming_high else current.high_source_time,
        index=current.index,
        low=merged_low,
        low_source_index=incoming.low_source_index if use_incoming_low else current.low_source_index,
        low_source_time=incoming.low_source_time if use_incoming_low else current.low_source_time,
        source_start_index=current.source_start_index,
        source_start_time=current.source_start_time,
        source_end_index=incoming.source_end_index,
        source_end_time=incoming.source_end_time,
        time=current.time,
        ema20=incoming.ema20,
    )


def _should_abort_merge(
    previous: MergedBar | None,
    current: MergedBar,
    incoming: MergedBar,
) -> bool:
    if previous is None:
        return False

    is_rising = current.high > previous.high and current.low > previous.low
    is_falling = current.high < previous.high and current.low < previous.low

    if is_rising and incoming.low < previous.low:
        return True

    if is_falling and incoming.high > previous.high:
        return True

    return False


def advance_inclusion(
    state: InclusionState,
    bar: AnalysisBar,
    max_included: int = 10,
) -> MergedBar | None:
    if bar.ema20 is None:
        return None

    next_bar = _create_merged_bar(bar)
    previous = state.merged_bars[-1] if state.merged_bars else None
    before_previous = state.merged_bars[-2] if len(state.merged_bars) >= 2 else None

    if previous is None:
        state.merged_bars.append(next_bar)
        state.processed_count += 1
        return next_bar

    if _has_inclusion(previous, next_bar) and _can_merge(previous, next_bar, max_included):
        if _should_abort_merge(before_previous, previous, next_bar):
            state.merged_bars.append(next_bar)
            state.merged_bars[-1].index = len(state.merged_bars) - 1
            state.processed_count += 1
            return next_bar
        merged = _merge(before_previous, previous, next_bar)
        state.merged_bars[-1] = merged
        state.processed_count += 1
        return merged

    state.merged_bars.append(next_bar)
    state.merged_bars[-1].index = len(state.merged_bars) - 1
    state.processed_count += 1
    return next_bar
