import math
from datetime import datetime
from app.core.kline_intervals import (
    FIVE_MINUTES_SECONDS,
    THIRTY_MINUTES_SECONDS,
    is_supported_kline_interval,
)
from app.services.analysis_core_v2 import analyze, AnalysisBar, calc_ema, calc_macd


def datetime_to_unix(dt: datetime) -> int:
    return int(dt.timestamp())

class AnalysisServiceV2:
    def __init__(self, kline_service):
        self._kline_service = kline_service

    def _resolve_engine_params(self, interval_seconds: int) -> tuple[int, int]:
        """
        不同周期使用不同的线段构建参数：
        1. 5F 继续使用 engine 默认值。
        2. 30F 使用更收紧的包含与最小间隔参数。
        3. 其他周期暂时也保持 engine 默认值。
        """
        if interval_seconds == THIRTY_MINUTES_SECONDS:
            return 1, 5
        return 1, 5

    def build_analysis_bars(self, items) -> list[AnalysisBar]:
        bars: list[AnalysisBar] = []
        for i, item in enumerate(items):
            t = datetime_to_unix(item.date_time)
            bars.append(
                AnalysisBar(
                    index=i, time=t,
                    open=float(item.open), high=float(item.high),
                    low=float(item.low), close=float(item.close),
                )
            )
        return bars

    def attach_ema(self, bars: list[AnalysisBar], length: int, field: str) -> None:
        closes = [b.close for b in bars]
        ema_list = calc_ema(closes, length)
        for i, bar in enumerate(bars):
            ema_val = ema_list[i]
            if ema_val is not None and not math.isnan(ema_val):
                setattr(bar, field, ema_val)

    def attach_macd(self, bars: list[AnalysisBar]) -> None:
        closes = [b.close for b in bars]
        diff, dea, hist = calc_macd(closes, short=4, long=20, mid=20)
        for i, bar in enumerate(bars):
            if diff[i] is not None:
                bar.macd_diff = diff[i]
            if dea[i] is not None:
                bar.macd_dea = dea[i]
            if hist[i] is not None:
                bar.macd_histogram = hist[i]

    def analyze(
        self,
        symbol: str,
        interval_seconds: int,
        limit: int = 2000,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        max_included: int | None = None,
        min_distance: int | None = None,
    ) -> dict:
        # 对于不支持分析的周期，抛出异常
        if not is_supported_kline_interval(interval_seconds):
            raise ValueError(f"Unsupported kline interval: {interval_seconds}")
        kline_result = self._kline_service.list_klines(
            symbol=symbol,
            interval_seconds=interval_seconds,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )
        data = kline_result.kline_data
        if not data:
            return {
                "bar_count": 0,
                "fractals": [],
                "segments": [],
                "higher_segments": [],
                "trading_ranges": [],
                "momentum_exhaustions": []
            }
        bars = self.build_analysis_bars(data)
        self.attach_ema(bars, 20, "ema20")
        self.attach_ema(bars, 120, "ema120")
        self.attach_macd(bars)
        resolved_max_included, resolved_min_distance = self._resolve_engine_params(interval_seconds)
        return analyze(
            bars,
            max_included=resolved_max_included,
            min_distance=resolved_min_distance,
        )
