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

        previous_relation = strategy.ema_state.last_relation
        current_ema = self._update_ema(strategy.ema_state, kline.close)
        current_relation = (
            self._resolve_relation(kline.close, current_ema)
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
                cross_direction = self._detect_cross(
                    previous_relation=previous_relation,
                    current_relation=current_relation,
                )
                if (
                    cross_direction is not None
                    and cross_direction != strategy.current_segment.direction
                ):
                    if (
                        strategy.current_segment.kline_count
                        >= self.min_segment_kline_count
                    ):
                        strategy.confirmed_segments.append(
                            self._confirm_segment(
                                strategy.current_segment,
                                confirmed_at=kline.date_time,
                            )
                        )
                    strategy.current_segment = self._create_segment_from_kline(
                        kline=kline,
                        direction=cross_direction,
                        segment_index=len(strategy.confirmed_segments) + 1,
                        trigger_time=kline.date_time,
                    )
                else:
                    strategy.current_segment = self._extend_segment(
                        segment=strategy.current_segment,
                        kline=kline,
                    )

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
        close_price: Decimal,
        ema_price: Decimal,
    ) -> EmaRelation:
        if close_price > ema_price:
            return EmaRelation.ABOVE
        if close_price < ema_price:
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
        )

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
                return updated

            updated.kline_count += 1
            if kline.high >= updated.end_price:
                updated.end_time = kline.date_time
                updated.end_price = kline.high
            return updated

        if kline.high >= updated.start_price:
            updated.first_kline_time = kline.date_time
            updated.start_time = kline.date_time
            updated.start_price = kline.high
            updated.end_time = kline.date_time
            updated.end_price = kline.low
            updated.kline_count = 1
            return updated

        updated.kline_count += 1
        if kline.low <= updated.end_price:
            updated.end_time = kline.date_time
            updated.end_price = kline.low
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
