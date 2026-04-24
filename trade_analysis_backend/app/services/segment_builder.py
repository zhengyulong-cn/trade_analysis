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
    def __init__(
        self,
        ema_period: int = 20,
        min_segment_kline_count: int = 5,
    ):
        self.ema_period = ema_period
        self.min_segment_kline_count = min_segment_kline_count
        self.multiplier = Decimal("2") / Decimal(str(ema_period + 1))

    def build(
        self,
        klines: list[KlineBarInput],
        existing: IntervalStrategy | None = None,
        interval: int | None = None,
        interval_name: str | None = None,
    ) -> IntervalStrategy:
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

        for kline in sorted(klines, key=lambda item: item.date_time):
            self._apply_kline(strategy, kline)

        return strategy

    def _apply_kline(
        self,
        strategy: IntervalStrategy,
        kline: KlineBarInput,
    ) -> None:
        if strategy.current_segment is None:
            strategy.ema_state.warmup_bars.append(kline.model_copy(deep=True))

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
                relation_direction = self._relation_to_direction(current_relation)
                if relation_direction == strategy.current_segment.direction:
                    strategy.pending_segment = None
                    strategy.current_segment = self._extend_segment(
                        segment=strategy.current_segment,
                        kline=kline,
                    )
                else:
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
                        and self._should_confirm_pending_segment(
                            strategy=strategy,
                            kline=kline,
                            ema_price=current_ema,
                        )
                    ):
                        strategy.confirmed_segments.append(
                            self._confirm_segment(
                                strategy.current_segment,
                                confirmed_at=kline.date_time,
                            )
                        )
                        strategy.current_segment = (
                            self._finalize_pending_segment(
                                strategy=strategy,
                                kline=kline,
                            )
                        )
                        strategy.current_segment.segment_index = (
                            len(strategy.confirmed_segments) + 1
                        )
                        strategy.current_segment.bars_since_end = 0
                        strategy.pending_segment = None

        strategy.ema_state.last_relation = current_relation
        strategy.last_processed_at = kline.date_time
        strategy.processed_kline_count += 1

    def _update_ema(
        self,
        ema_state: EmaBuildState,
        close_price: Decimal,
    ) -> Decimal | None:
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

    def _finalize_pending_segment(
        self,
        strategy: IntervalStrategy,
        kline: KlineBarInput,
    ) -> TrendSegment:
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

    def _detect_cross(
        self,
        previous_relation: EmaRelation | None,
        current_relation: EmaRelation,
    ) -> SegmentDirection | None:
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
        updated = segment.model_copy(deep=True)
        updated.status = SegmentStatus.CONFIRMED
        updated.confirmed_at = confirmed_at
        return updated
