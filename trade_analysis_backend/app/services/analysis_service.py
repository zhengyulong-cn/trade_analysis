import math
from datetime import datetime

from app.core.kline_intervals import is_supported_kline_interval
from app.services.analysis_core import AnalysisBar, analyze, calc_ema


def _datetime_to_unix(dt: datetime) -> int:
    return int(dt.timestamp())


class AnalysisService:
    def __init__(self, kline_service):
        self._kline_service = kline_service

    def analyze(
        self,
        symbol: str,
        interval_seconds: int,
        limit: int = 2000,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict:
        """增量分析，无未来函数。"""
        if not is_supported_kline_interval(interval_seconds):
            raise ValueError(f"Unsupported kline interval: {interval_seconds}")

        kline_result = self._kline_service.list_klines(
            symbol=symbol,
            interval_seconds=interval_seconds,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )
        items = kline_result.kline_data
        if not items:
            return {"bar_count": 0, "fractals": [], "segments": [], "higher_segments": [], "trading_ranges": []}

        bars = _build_analysis_bars(items)
        _attach_ema(bars, 20, "ema20")
        _attach_ema(bars, 120, "ema120")

        return analyze(bars)


def _build_analysis_bars(items) -> list[AnalysisBar]:
    bars: list[AnalysisBar] = []
    for i, item in enumerate(items):
        t = _datetime_to_unix(item.date_time)
        bars.append(
            AnalysisBar(
                index=i, time=t,
                open=float(item.open), high=float(item.high),
                low=float(item.low), close=float(item.close),
            )
        )
    return bars


def _attach_ema(bars: list[AnalysisBar], length: int, field: str) -> None:
    closes = [b.close for b in bars]
    ema_list = calc_ema(closes, length)
    for i, bar in enumerate(bars):
        ema_val = ema_list[i]
        if ema_val is not None and not math.isnan(ema_val):
            setattr(bar, field, ema_val)
