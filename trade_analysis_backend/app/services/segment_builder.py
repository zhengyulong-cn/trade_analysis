from datetime import datetime
from decimal import Decimal

from app.schemas.kline_data import KlineBarInput
from app.schemas.strategy_analysis import (
    EmaBuildState,
    EmaRelation,
    IntervalStrategy,
    SegmentDirection,
    SegmentStatus,
    TrendSegment,
)


class SegmentBuilder:
    """线段构建器。

    这个类负责按 K 线时间升序，增量地构建线段。

    它维护三类核心状态：
    - current_segment：当前正在延展的线段
    - pending_segment：出现反向迹象后，暂时观察中的候选线段
    - ema_state：EMA20 及最近振幅等辅助状态

    整体思路是：
    - 先根据 K 线与 EMA20 的关系判断当前更偏向上涨还是下跌；
    - 若方向与 current_segment 一致，则延续当前段；
    - 若方向相反，则先构建 pending_segment；
    - 当普通规则或强波动旁路规则满足时，再把 pending_segment 扶正。
    """

    def __init__(
        self,
        ema_period: int = 20,
        min_segment_kline_count: int = 5,
        impulse_amplitude_lookback: int = 20,
        impulse_amplitude_multiplier: Decimal | int | str = 3,
    ):
        # ema_period: EMA 周期，当前默认 20。
        self.ema_period = ema_period
        # min_segment_kline_count: 普通确认规则下，至少需要观察的 K 线数量门槛。
        self.min_segment_kline_count = min_segment_kline_count
        # impulse_amplitude_lookback: 计算平均振幅时，回看最近多少根 K 线。
        self.impulse_amplitude_lookback = impulse_amplitude_lookback
        # impulse_amplitude_multiplier: 强波动旁路确认的倍数阈值，例如 3 倍。
        self.impulse_amplitude_multiplier = Decimal(
            str(impulse_amplitude_multiplier)
        )
        # multiplier: EMA 递推公式里的平滑系数。
        self.multiplier = Decimal("2") / Decimal(str(ema_period + 1))

    def build(
        self,
        klines: list[KlineBarInput],
        existing: IntervalStrategy | None = None,
        interval: int | None = None,
        interval_name: str | None = None,
    ) -> IntervalStrategy:
        """基于已有状态继续构建线段。"""
        # strategy: 当前周期的完整分析状态。
        strategy = existing.model_copy(deep=True) if existing is not None else None
        if strategy is None:
            strategy = IntervalStrategy(
                interval=interval or 0,
                interval_name=interval_name,
                ema_state=EmaBuildState(period=self.ema_period),
            )

        if interval is not None:
            strategy.interval = interval
        if interval_name is not None:
            strategy.interval_name = interval_name
        strategy.ema_state.period = self.ema_period

        # 所有 K 线必须严格按时间升序处理，避免未来函数。
        for kline in sorted(klines, key=lambda item: item.date_time):
            self._apply_kline(strategy, kline)

        return strategy

    def _apply_kline(
        self,
        strategy: IntervalStrategy,
        kline: KlineBarInput,
    ) -> None:
        """处理单根 K 线。

        主体逻辑：
        1. 更新 EMA20；
        2. 判断当前 K 线相对 EMA 的方向意义；
        3. 若方向与 current_segment 一致，则延续当前段；
        4. 若方向相反，则构建或更新 pending_segment；
        5. 再按普通确认规则或强波动旁路规则判断是否切换为新段。
        """
        if strategy.current_segment is None:
            # 第一条线段尚未成形前，先缓存预热 K 线。
            strategy.ema_state.warmup_bars.append(kline.model_copy(deep=True))

        # average_amplitude: 最近若干根 K 线的平均振幅，用于识别强波动旁路确认。
        average_amplitude = self._get_average_kline_amplitude(strategy.ema_state)
        current_ema = self._update_ema(strategy.ema_state, kline.close)
        current_relation = (
            self._resolve_relation(
                kline=kline,
                ema_price=current_ema,
                current_segment=strategy.current_segment,
            )
            if current_ema is not None
            else None
        )

        if current_relation is not None:
            if strategy.current_segment is None:
                # 尚无 current_segment 时，用当前 relation 决定第一条线段方向。
                initial_direction = self._relation_to_direction(current_relation)
                if initial_direction is not None:
                    strategy.current_segment = self._replay_initial_segment(
                        bars=strategy.ema_state.warmup_bars,
                        direction=initial_direction,
                        segment_index=len(strategy.confirmed_segments) + 1,
                        trigger_time=kline.date_time,
                    )
                    strategy.ema_state.warmup_bars = []
            else:
                # relation_direction: 当前 K 线在方向意义上更偏向上涨还是下跌。
                relation_direction = self._relation_to_direction(current_relation)
                if relation_direction == strategy.current_segment.direction:
                    # 方向一致，说明 current_segment 延续，之前的候选反向段失效。
                    strategy.pending_segment = None
                    strategy.current_segment = self._extend_segment(
                        segment=strategy.current_segment,
                        kline=kline,
                    )
                else:
                    # 方向相反时，不立刻切段，而是进入“候选反向段观察”阶段。
                    strategy.current_segment = self._touch_segment(
                        segment=strategy.current_segment,
                        kline=kline,
                    )
                    strategy.pending_segment = self._build_pending_segment(
                        strategy=strategy,
                        kline=kline,
                        direction=relation_direction,
                    )
                    if (
                        current_ema is not None
                        and (
                            self._should_confirm_pending_segment(
                                strategy=strategy,
                                kline=kline,
                                ema_price=current_ema,
                            )
                            or self._should_confirm_impulse_segment(
                                strategy=strategy,
                                average_amplitude=average_amplitude,
                            )
                        )
                    ):
                        strategy.confirmed_segments.append(
                            self._confirm_segment(
                                strategy.current_segment,
                                confirmed_at=kline.date_time,
                            )
                        )
                        # pending_segment 一旦确认成立，就扶正为新的 current_segment。
                        strategy.current_segment = self._finalize_pending_segment(
                            strategy=strategy,
                            kline=kline,
                        )
                        strategy.current_segment.segment_index = (
                            len(strategy.confirmed_segments) + 1
                        )
                        strategy.current_segment.bars_since_end = 0
                        strategy.pending_segment = None

        # 这些字段用于保存增量进度，保证下一次能从上次处理位置继续往后跑。
        strategy.ema_state.last_relation = current_relation
        strategy.last_processed_at = kline.date_time
        strategy.processed_kline_count += 1
        self._update_recent_kline_amplitudes(strategy.ema_state, kline)

    def _update_ema(
        self,
        ema_state: EmaBuildState,
        close_price: Decimal,
    ) -> Decimal | None:
        """增量更新 EMA20。

        前 ema_period 根 K 线不足时，只累计 seed_closes；
        满足数量后，用简单平均初始化 EMA；
        之后使用 EMA 递推公式持续更新。
        """
        if ema_state.last_ema is None:
            ema_state.seed_closes.append(close_price)
            if len(ema_state.seed_closes) < self.ema_period:
                return None
            if len(ema_state.seed_closes) > self.ema_period:
                ema_state.seed_closes = ema_state.seed_closes[-self.ema_period :]
            ema_state.last_ema = sum(ema_state.seed_closes) / Decimal(
                str(self.ema_period)
            )
            return ema_state.last_ema

        ema_state.last_ema = (
            (close_price - ema_state.last_ema) * self.multiplier
        ) + ema_state.last_ema
        return ema_state.last_ema

    def _resolve_relation(
        self,
        kline: KlineBarInput,
        ema_price: Decimal,
        current_segment: TrendSegment | None,
    ) -> EmaRelation:
        """判断当前 K 线与 EMA20 的关系。

        这里不是简单比较 close 与 EMA，而是结合 current_segment 的方向：
        - 当前为下跌段时，优先判断是否出现潜在上涨；
        - 当前为上涨段时，优先判断是否出现潜在下跌。
        """
        if current_segment is not None:
            if current_segment.direction == SegmentDirection.DOWN:
                if kline.low <= current_segment.end_price:
                    return EmaRelation.BELOW
                if kline.high > ema_price:
                    return EmaRelation.ABOVE
                return EmaRelation.BELOW

            if kline.high >= current_segment.end_price:
                return EmaRelation.ABOVE
            if kline.low < ema_price:
                return EmaRelation.BELOW
            return EmaRelation.ABOVE

        if kline.close > ema_price:
            return EmaRelation.ABOVE
        if kline.close < ema_price:
            return EmaRelation.BELOW
        return EmaRelation.ON

    def _relation_to_direction(
        self,
        relation: EmaRelation | None,
    ) -> SegmentDirection | None:
        """把 EMA 相对关系映射成线段方向。"""
        if relation == EmaRelation.ABOVE:
            return SegmentDirection.UP
        if relation == EmaRelation.BELOW:
            return SegmentDirection.DOWN
        return None

    def _build_pending_segment(
        self,
        strategy: IntervalStrategy,
        kline: KlineBarInput,
        direction: SegmentDirection | None,
    ) -> TrendSegment | None:
        """构建或更新 pending_segment。

        pending_segment 表示“已出现反向迹象，但还没有完成确认”的候选线段。
        """
        if strategy.current_segment is None or direction is None:
            return None

        pending_segment = strategy.pending_segment
        if (
            pending_segment is None
            or pending_segment.direction != direction
            or pending_segment.start_time != strategy.current_segment.end_time
            or pending_segment.start_price != strategy.current_segment.end_price
        ):
            return self._create_pending_segment(
                anchor_segment=strategy.current_segment,
                kline=kline,
                direction=direction,
                segment_index=strategy.current_segment.segment_index + 1,
                trigger_time=kline.date_time,
            )

        return self._extend_pending_segment(
            segment=pending_segment,
            kline=kline,
        )

    def _should_confirm_pending_segment(
        self,
        strategy: IntervalStrategy,
        kline: KlineBarInput,
        ema_price: Decimal,
    ) -> bool:
        """按普通规则判断 pending_segment 是否可以转正。

        这里是主规则：
        - 先要求当前 K 线仍满足反向穿越 EMA 的条件；
        - 再要求距离 current_segment 结束点经过足够多的 K 线；
        - 如果当前 K 线已经刷新候选段极值，则允许确认；
        - 若候选段内部更早已有更极端的高点/低点，则继续观察更长窗口。
        """
        if strategy.current_segment is None or strategy.pending_segment is None:
            return False

        if strategy.pending_segment.direction == SegmentDirection.UP:
            if kline.high <= ema_price:
                return False
            if strategy.current_segment.bars_since_end <= self.min_segment_kline_count:
                return False
            if strategy.pending_segment.end_price <= kline.high:
                return True
            return (
                strategy.current_segment.bars_since_end
                > self.min_segment_kline_count * 2
            )

        if kline.low >= ema_price:
            return False
        if strategy.current_segment.bars_since_end <= self.min_segment_kline_count:
            return False
        if strategy.pending_segment.end_price >= kline.low:
            return True
        return (
            strategy.current_segment.bars_since_end
            > self.min_segment_kline_count * 2
        )

    def _should_confirm_impulse_segment(
        self,
        strategy: IntervalStrategy,
        average_amplitude: Decimal | None,
    ) -> bool:
        """按强波动旁路规则判断是否提前确认。

        这个规则不替代主规则，只在“候选反向区间振幅显著大于平均振幅”时提供补充入口。
        """
        if strategy.current_segment is None or strategy.pending_segment is None:
            return False
        if average_amplitude is None or average_amplitude <= 0:
            return False
        if strategy.current_segment.bars_since_end >= self.min_segment_kline_count:
            return False

        # candidate_amplitude: 候选反向区间的整体振幅，而不是单根 K 线振幅。
        candidate_amplitude = self._get_segment_amplitude(strategy.pending_segment)
        return (
            candidate_amplitude
            > average_amplitude * self.impulse_amplitude_multiplier
        )

    def _finalize_pending_segment(
        self,
        strategy: IntervalStrategy,
        kline: KlineBarInput,
    ) -> TrendSegment:
        """将 pending_segment 最终收敛成新的 current_segment。"""
        if strategy.pending_segment is None:
            raise ValueError("Pending segment is required before finalizing")

        updated = strategy.pending_segment.model_copy(deep=True)
        updated.last_kline_time = kline.date_time

        if updated.direction == SegmentDirection.UP:
            if updated.end_price > kline.high:
                updated.end_time = kline.date_time
                updated.end_price = kline.high
            return updated

        if updated.end_price < kline.low:
            updated.end_time = kline.date_time
            updated.end_price = kline.low
        return updated

    def _get_segment_amplitude(
        self,
        segment: TrendSegment,
    ) -> Decimal:
        """计算线段振幅。"""
        if segment.direction == SegmentDirection.UP:
            return segment.end_price - segment.start_price
        return segment.start_price - segment.end_price

    def _get_average_kline_amplitude(
        self,
        ema_state: EmaBuildState,
    ) -> Decimal | None:
        """计算最近若干根 K 线的平均振幅。"""
        if not ema_state.recent_kline_amplitudes:
            return None
        return sum(ema_state.recent_kline_amplitudes) / Decimal(
            str(len(ema_state.recent_kline_amplitudes))
        )

    def _update_recent_kline_amplitudes(
        self,
        ema_state: EmaBuildState,
        kline: KlineBarInput,
    ) -> None:
        """维护最近若干根 K 线的振幅缓存。"""
        ema_state.recent_kline_amplitudes.append(kline.high - kline.low)
        if len(ema_state.recent_kline_amplitudes) > self.impulse_amplitude_lookback:
            ema_state.recent_kline_amplitudes = ema_state.recent_kline_amplitudes[
                -self.impulse_amplitude_lookback :
            ]

    def _detect_cross(
        self,
        previous_relation: EmaRelation | None,
        current_relation: EmaRelation,
    ) -> SegmentDirection | None:
        """保留的辅助方法：根据前后 relation 判断是否发生方向切换。"""
        if current_relation == EmaRelation.ABOVE and previous_relation in {
            EmaRelation.BELOW,
            EmaRelation.ON,
        }:
            return SegmentDirection.UP
        if current_relation == EmaRelation.BELOW and previous_relation in {
            EmaRelation.ABOVE,
            EmaRelation.ON,
        }:
            return SegmentDirection.DOWN
        return None

    def _touch_segment(
        self,
        segment: TrendSegment,
        kline: KlineBarInput,
    ) -> TrendSegment:
        """在候选反向段观察阶段，只推进 current_segment 的计数与时间。

        这里不会修改 current_segment 的端点极值，
        因为此时只是“正在观察反向是否成立”，还没有确认当前段结束。
        """
        updated = segment.model_copy(deep=True)
        updated.last_kline_time = kline.date_time
        updated.kline_count += 1
        updated.bars_since_end += 1
        return updated

    def _replay_initial_segment(
        self,
        bars: list[KlineBarInput],
        direction: SegmentDirection,
        segment_index: int,
        trigger_time: datetime,
    ) -> TrendSegment:
        """用预热 K 线回放出第一条线段。"""
        if not bars:
            raise ValueError("Warmup bars cannot be empty when building initial segment")

        segment = self._create_segment_from_kline(
            kline=bars[0],
            direction=direction,
            segment_index=segment_index,
            trigger_time=trigger_time,
        )
        for bar in bars[1:]:
            segment = self._extend_segment(segment, bar)
        return segment

    def _create_segment_from_kline(
        self,
        kline: KlineBarInput,
        direction: SegmentDirection,
        segment_index: int,
        trigger_time: datetime,
    ) -> TrendSegment:
        """从单根 K 线初始化线段。

        变量意义：
        - start_price: 线段起点价格
        - end_price: 线段终点价格
        - segment_index: 当前周期内的线段编号
        - trigger_time: 触发这条线段构建的时间
        """
        if direction == SegmentDirection.UP:
            start_price = kline.low
            end_price = kline.high
        else:
            start_price = kline.high
            end_price = kline.low

        return TrendSegment(
            segment_index=segment_index,
            direction=direction,
            status=SegmentStatus.BUILDING,
            trigger_time=trigger_time,
            first_kline_time=kline.date_time,
            last_kline_time=kline.date_time,
            start_time=kline.date_time,
            start_price=start_price,
            end_time=kline.date_time,
            end_price=end_price,
            kline_count=1,
            bars_since_end=0,
        )

    def _create_pending_segment(
        self,
        anchor_segment: TrendSegment,
        kline: KlineBarInput,
        direction: SegmentDirection,
        segment_index: int,
        trigger_time: datetime,
    ) -> TrendSegment:
        """以当前段结束点为起点，创建候选反向段。"""
        end_price = kline.high if direction == SegmentDirection.UP else kline.low
        return TrendSegment(
            segment_index=segment_index,
            direction=direction,
            status=SegmentStatus.BUILDING,
            trigger_time=trigger_time,
            first_kline_time=anchor_segment.end_time,
            last_kline_time=kline.date_time,
            start_time=anchor_segment.end_time,
            start_price=anchor_segment.end_price,
            end_time=kline.date_time,
            end_price=end_price,
            kline_count=1,
            bars_since_end=0,
        )

    def _extend_pending_segment(
        self,
        segment: TrendSegment,
        kline: KlineBarInput,
    ) -> TrendSegment:
        """延展候选反向段，只更新候选方向上的极值。"""
        updated = segment.model_copy(deep=True)
        updated.last_kline_time = kline.date_time
        updated.kline_count += 1

        if updated.direction == SegmentDirection.UP:
            if kline.high >= updated.end_price:
                updated.end_time = kline.date_time
                updated.end_price = kline.high
                updated.bars_since_end = 0
                return updated

            updated.bars_since_end += 1
            return updated

        if kline.low <= updated.end_price:
            updated.end_time = kline.date_time
            updated.end_price = kline.low
            updated.bars_since_end = 0
            return updated

        updated.bars_since_end += 1
        return updated

    def _extend_segment(
        self,
        segment: TrendSegment,
        kline: KlineBarInput,
    ) -> TrendSegment:
        """延展当前已成立的线段。

        变量与逻辑说明：
        - 对上涨段：维护段内最低价和最高价；
        - 对下跌段：维护段内最高价和最低价；
        - bars_since_end：距离当前段终点极值已经过去多少根 K 线。
        """
        updated = segment.model_copy(deep=True)
        updated.last_kline_time = kline.date_time

        if updated.direction == SegmentDirection.UP:
            if kline.low <= updated.start_price:
                updated.first_kline_time = kline.date_time
                updated.start_time = kline.date_time
                updated.start_price = kline.low
                updated.end_time = kline.date_time
                updated.end_price = kline.high
                updated.kline_count = 1
                updated.bars_since_end = 0
                return updated

            updated.kline_count += 1
            if kline.high >= updated.end_price:
                updated.end_time = kline.date_time
                updated.end_price = kline.high
                updated.bars_since_end = 0
                return updated

            updated.bars_since_end += 1
            return updated

        if kline.high >= updated.start_price:
            updated.first_kline_time = kline.date_time
            updated.start_time = kline.date_time
            updated.start_price = kline.high
            updated.end_time = kline.date_time
            updated.end_price = kline.low
            updated.kline_count = 1
            updated.bars_since_end = 0
            return updated

        updated.kline_count += 1
        if kline.low <= updated.end_price:
            updated.end_time = kline.date_time
            updated.end_price = kline.low
            updated.bars_since_end = 0
            return updated

        updated.bars_since_end += 1
        return updated

    def _confirm_segment(
        self,
        segment: TrendSegment,
        confirmed_at: datetime,
    ) -> TrendSegment:
        """将当前段标记为已确认段。"""
        updated = segment.model_copy(deep=True)
        updated.status = SegmentStatus.CONFIRMED
        updated.confirmed_at = confirmed_at
        return updated
