from datetime import datetime, timedelta
from typing import Literal

from app.schemas.signal_filter import (
    AdxRisingSignalItem,
    AdxRisingSignalResult,
    AllEntrySignalItem,
    AllHoldingWarningSignalItem,
    AllContractSignalResult,
    EntrySignalItem,
    ContractSignalResult,
    EmaTrendSignalItem,
    EmaTrendState,
    HoldingWarningSignalItem,
    AdxSlopeEnmu,
    MACDSignalFilterItem,
    SignalFilterResult,
)
from app.services.kline_service import KlineService
from app.services.contract_service import ContractService


SignalDirection = Literal["all", "long", "short"]


class SignalFilterService:
    def __init__(
        self,
        kline_service: KlineService,
        contract_service: ContractService | None = None,
    ):
        self.kline_service = kline_service
        self.contract_service = contract_service

    def filter_macd_ema20_signals(
        self,
        symbol: str,
        interval_seconds: int,
        limit: int,
        direction: SignalDirection = "all",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> SignalFilterResult:
        calculation_limit = min(5000, limit + 500 * 5)
        result = self.kline_service.list_klines(
            symbol=symbol,
            interval_seconds=interval_seconds,
            limit=calculation_limit,
        )
        bars = result.kline_data
        closes = [float(bar.close) for bar in bars]
        ema20 = self._ema(closes, 20)
        ema4 = self._ema(closes, 4)
        diff = [short - long for short, long in zip(ema4, ema20)]
        dea = self._ema(diff, 20)
        macd = [(current_diff - current_dea) * 2 for current_diff, current_dea in zip(diff, dea)]
        boundary = self._ema([abs(value) for value in macd], 500)

        signals: list[MACDSignalFilterItem] = []
        search_start_index = max(2, len(bars) - limit)
        for index in range(search_start_index, len(bars)):
            bar = bars[index]
            within_boundary = abs(macd[index]) < abs(boundary[index])
            green_shrinking = (
                macd[index] <= 0
                and macd[index - 1] < macd[index]
                and macd[index - 2] < macd[index - 1]
                and closes[index] > ema20[index]
            )
            green_growing = (
                macd[index] <= 0
                and macd[index - 1] > macd[index]
                and macd[index - 2] > macd[index - 1]
                and closes[index] < ema20[index]
            )
            red_shrinking = (
                macd[index] >= 0
                and macd[index - 1] > macd[index]
                and macd[index - 2] > macd[index - 1]
                and closes[index] < ema20[index]
            )
            red_growing = (
                macd[index] >= 0
                and macd[index - 1] < macd[index]
                and macd[index - 2] < macd[index - 1]
                and closes[index] > ema20[index]
            )
            is_long = (green_shrinking and within_boundary) or red_growing
            is_short = (red_shrinking and within_boundary) or green_growing

            signal_type: Literal["long", "short"] | None = None
            if is_long:
                signal_type = "long"
            elif is_short:
                signal_type = "short"
            if signal_type is None or (direction != "all" and signal_type != direction):
                continue
            if start_time is not None and bar.date_time < start_time:
                continue
            if end_time is not None and bar.date_time > end_time:
                continue

            signals.append(
                MACDSignalFilterItem(
                    signal_type=signal_type,
                    date_time=bar.date_time,
                    open=float(bar.open),
                    close=float(bar.close),
                    high=float(bar.high),
                    low=float(bar.low),
                    ema20=ema20[index],
                    diff=diff[index],
                    dea=dea[index],
                    macd=macd[index],
                    boundary=boundary[index],
                    within_boundary=within_boundary,
                )
            )

        signals.reverse()
        return SignalFilterResult(
            symbol=result.symbol,
            exchange=result.exchange,
            name=result.name,
            interval=interval_seconds,
            bar_count=min(limit, len(bars)),
            signal_count=len(signals),
            signals=signals,
        )

    def filter_adx_rising_signals(
        self,
        symbol: str,
        interval_seconds: int,
        limit: int,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> AdxRisingSignalResult:
        calculation_limit = min(5000, limit + 20 * 10)
        period = 20
        threshold = 20
        result = self.kline_service.list_klines(
            symbol=symbol,
            interval_seconds=interval_seconds,
            limit=calculation_limit,
        )
        bars = result.kline_data
        true_ranges: list[float] = []
        dm_plus: list[float] = []
        dm_minus: list[float] = []

        for index, bar in enumerate(bars):
            high = float(bar.high)
            low = float(bar.low)
            if index == 0:
                true_ranges.append(high - low)
                dm_plus.append(0)
                dm_minus.append(0)
                continue

            previous_bar = bars[index - 1]
            previous_close = float(previous_bar.close)
            high_move = high - float(previous_bar.high)
            low_move = float(previous_bar.low) - low
            true_ranges.append(
                max(high - low, abs(high - previous_close), abs(low - previous_close))
            )
            dm_plus.append(max(high_move, 0) if high_move > low_move else 0)
            dm_minus.append(max(low_move, 0) if low_move > high_move else 0)

        smooth_tr = self._ema(true_ranges, period)
        smooth_dm_plus = self._ema(dm_plus, period)
        smooth_dm_minus = self._ema(dm_minus, period)
        di_plus = [
            current_dm / current_tr * 100 if current_tr != 0 else 0
            for current_dm, current_tr in zip(smooth_dm_plus, smooth_tr)
        ]
        di_minus = [
            current_dm / current_tr * 100 if current_tr != 0 else 0
            for current_dm, current_tr in zip(smooth_dm_minus, smooth_tr)
        ]
        dx = [
            abs(plus - minus) / (plus + minus) * 100 if plus + minus != 0 else 0
            for plus, minus in zip(di_plus, di_minus)
        ]
        adx = self._ema(dx, period)

        signals: list[AdxRisingSignalItem] = []
        search_start_index = max(1, len(bars) - limit)
        for index in range(search_start_index, len(bars)):
            bar = bars[index]
            adx_slope = AdxSlopeEnmu.Zero
            if adx[index - 1] > adx[index]:
                adx_slope = AdxSlopeEnmu.Negative
            if adx[index - 1] < adx[index]:
                adx_slope = AdxSlopeEnmu.Positive
            if start_time is not None and bar.date_time < start_time:
                continue
            if end_time is not None and bar.date_time > end_time:
                continue
            signals.append(
                AdxRisingSignalItem(
                    date_time=bar.date_time,
                    open=float(bar.open),
                    close=float(bar.close),
                    high=float(bar.high),
                    low=float(bar.low),
                    tr=true_ranges[index],
                    di_plus=di_plus[index],
                    di_minus=di_minus[index],
                    dx=dx[index],
                    adx=adx[index],
                    previous_adx=adx[index - 1],
                    threshold=threshold,
                    above_threshold=adx[index] >= threshold,
                    adx_slope=adx_slope
                )
            )

        signals.reverse()
        return AdxRisingSignalResult(
            symbol=result.symbol,
            exchange=result.exchange,
            name=result.name,
            interval=interval_seconds,
            period=period,
            threshold=threshold,
            bar_count=min(limit, len(bars)),
            signal_count=len(signals),
            signals=signals,
        )

    @staticmethod
    def _ema(values: list[float], period: int) -> list[float]:
        if not values:
            return []
        alpha = 2 / (period + 1)
        result = [values[0]]
        for value in values[1:]:
            result.append(alpha * value + (1 - alpha) * result[-1])
        return result
    
    @staticmethod
    def build_entry_signals(
        macd_signals: list[MACDSignalFilterItem],
        adx_signals: list[AdxRisingSignalItem],
        ema_trend_signals: list[EmaTrendSignalItem],
        interval_seconds: int,
    ) -> list[EntrySignalItem]:
        interval = timedelta(seconds=interval_seconds)
        entry_signals: list[EntrySignalItem] = []
        ema_trend_by_time = {signal.date_time: signal for signal in ema_trend_signals}
        allowed_direction = {
            EmaTrendState.BullTrend: "long",
            EmaTrendState.BullExpanding: "long",
            EmaTrendState.BullContracting: "short",
            EmaTrendState.BearTrend: "short",
            EmaTrendState.BearExpanding: "short",
            EmaTrendState.BearContracting: "long",
        }
        for macd_signal in macd_signals:
            ema_trend = ema_trend_by_time.get(macd_signal.date_time)
            if ema_trend is None or allowed_direction.get(ema_trend.state) != macd_signal.signal_type:
                continue
            candidates = [
                adx_signal
                for adx_signal in adx_signals
                if macd_signal.date_time - interval <= adx_signal.date_time <= macd_signal.date_time + interval
                and adx_signal.adx_slope in (AdxSlopeEnmu.Positive, AdxSlopeEnmu.Zero)
            ]
            if not candidates:
                continue
            selected = min(
                candidates,
                key=lambda item: (
                    item.above_threshold,
                    abs((item.date_time - macd_signal.date_time).total_seconds()),
                ),
            )
            entry_signals.append(
                EntrySignalItem(
                    signal_type=macd_signal.signal_type,
                    date_time=macd_signal.date_time,
                    open=macd_signal.open,
                    close=macd_signal.close,
                    high=macd_signal.high,
                    low=macd_signal.low,
                    adx_signal_date_time=selected.date_time,
                    adx=selected.adx,
                    above_threshold=selected.above_threshold,
                    ema20=ema_trend.ema20,
                    ema120=ema_trend.ema120,
                    gap_strength=ema_trend.gap_strength,
                    ema_trend_state=ema_trend.state,
                )
            )
        return entry_signals

    def build_ema_trend_signals(
        self,
        symbol: str,
        interval_seconds: int,
        limit: int,
    ) -> list[EmaTrendSignalItem]:
        calculation_limit = min(5000, limit + 120 * 10)
        result = self.kline_service.list_klines(
            symbol=symbol,
            interval_seconds=interval_seconds,
            limit=calculation_limit,
        )
        bars = result.kline_data
        closes = [float(bar.close) for bar in bars]
        ema20 = self._ema(closes, 20)
        ema120 = self._ema(closes, 120)
        true_ranges: list[float] = []
        for index, bar in enumerate(bars):
            high = float(bar.high)
            low = float(bar.low)
            if index == 0:
                true_ranges.append(high - low)
                continue
            previous_close = float(bars[index - 1].close)
            true_ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
        atr20 = self._ema(true_ranges, 20)
        gap_strength = [
            abs(short - long) / atr if atr > 0 else 0
            for short, long, atr in zip(ema20, ema120, atr20)
        ]

        signals: list[EmaTrendSignalItem] = []
        for index in range(max(3, len(bars) - limit), len(bars)):
            gap_change = gap_strength[index] - gap_strength[index - 3]
            is_bull = ema20[index] > ema120[index]
            is_bear = ema20[index] < ema120[index]
            if gap_strength[index] >= 1.0:
                state = EmaTrendState.BullTrend if is_bull else EmaTrendState.BearTrend
            elif gap_change > 0.05:
                state = EmaTrendState.BullExpanding if is_bull else EmaTrendState.BearExpanding
            elif gap_change < -0.05:
                state = EmaTrendState.BullContracting if is_bull else EmaTrendState.BearContracting
            else:
                state = EmaTrendState.Neutral
            if not is_bull and not is_bear:
                state = EmaTrendState.Neutral
            signals.append(
                EmaTrendSignalItem(
                    date_time=bars[index].date_time,
                    ema20=ema20[index],
                    ema120=ema120[index],
                    atr20=atr20[index],
                    gap_strength=gap_strength[index],
                    gap_change=gap_change,
                    state=state,
                )
            )
        signals.reverse()
        return signals

    @staticmethod
    def build_holding_warning_signals(
        macd_signals: list[MACDSignalFilterItem],
        ema_trend_signals: list[EmaTrendSignalItem],
    ) -> list[HoldingWarningSignalItem]:
        ema_trend_by_time = {signal.date_time: signal for signal in ema_trend_signals}
        warnings: list[HoldingWarningSignalItem] = []
        for macd_signal in macd_signals:
            ema_trend = ema_trend_by_time.get(macd_signal.date_time)
            if ema_trend is None:
                continue
            position_direction: Literal["long", "short"] | None = None
            if (
                ema_trend.state in (EmaTrendState.BullTrend, EmaTrendState.BullExpanding)
                and macd_signal.signal_type == "short"
            ):
                position_direction = "long"
            elif (
                ema_trend.state in (EmaTrendState.BearTrend, EmaTrendState.BearExpanding)
                and macd_signal.signal_type == "long"
            ):
                position_direction = "short"
            if position_direction is None:
                continue
            warnings.append(
                HoldingWarningSignalItem(
                    position_direction=position_direction,
                    macd_signal_type=macd_signal.signal_type,
                    date_time=macd_signal.date_time,
                    close=macd_signal.close,
                    ema_trend_state=ema_trend.state,
                )
            )
        return warnings

    def filter_signals(self, symbol: str, interval_seconds: int, limit: int) -> ContractSignalResult:
        macd_result = self.filter_macd_ema20_signals(symbol, interval_seconds, limit)
        adx_result = self.filter_adx_rising_signals(symbol, interval_seconds, limit)
        ema_trend_signals = self.build_ema_trend_signals(symbol, interval_seconds, limit)
        return ContractSignalResult(
            symbol=macd_result.symbol,
            exchange=macd_result.exchange,
            name=macd_result.name,
            interval=interval_seconds,
            bar_count=min(macd_result.bar_count, adx_result.bar_count),
            macd_signals=macd_result.signals,
            adx_signals=adx_result.signals,
            ema_trend_signals=ema_trend_signals,
            entry_signals=self.build_entry_signals(
                macd_result.signals,
                adx_result.signals,
                ema_trend_signals,
                interval_seconds,
            ),
            holding_warning_signals=self.build_holding_warning_signals(
                macd_result.signals,
                ema_trend_signals,
            ),
        )

    def filter_all_signals(
        self,
        interval_seconds: int,
        limit: int,
    ) -> AllContractSignalResult:
        if self.contract_service is None:
            raise RuntimeError("ContractService is required to filter all signals")
        items = [
            self.filter_signals(contract.symbol, interval_seconds, limit)
            for contract in self.contract_service.list_contracts()
        ]
        entry_signals = [
            AllEntrySignalItem(
                symbol=item.symbol,
                exchange=item.exchange,
                name=item.name,
                interval=item.interval,
                **signal.model_dump(),
            )
            for item in items
            for signal in item.entry_signals
        ]
        entry_signals.sort(key=lambda signal: signal.date_time, reverse=True)
        holding_warning_signals = [
            AllHoldingWarningSignalItem(
                symbol=item.symbol,
                exchange=item.exchange,
                name=item.name,
                interval=item.interval,
                **signal.model_dump(),
            )
            for item in items
            for signal in item.holding_warning_signals
        ]
        holding_warning_signals.sort(key=lambda signal: signal.date_time, reverse=True)
        return AllContractSignalResult(
            interval=interval_seconds,
            contract_count=len(items),
            items=items,
            entry_signals=entry_signals,
            holding_warning_signals=holding_warning_signals,
        )
