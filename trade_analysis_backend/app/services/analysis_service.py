import math
from datetime import datetime

from app.core.kline_intervals import is_supported_kline_interval
from app.services.analysis import AnalysisBar, build_base_segments, build_fractals, calc_ema


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
    ) -> dict:
        """一次调用返回全部分析结果。"""
        if not is_supported_kline_interval(interval_seconds):
            raise ValueError(f"Unsupported kline interval: {interval_seconds}")

        kline_result = self._kline_service.list_klines(
            symbol=symbol,
            interval_seconds=interval_seconds,
            limit=limit,
        )
        items = kline_result.kline_data
        if not items:
            return {"bar_count": 0, "fractals": [], "segments": []}

        bars = _build_analysis_bars(items)
        _attach_ema(bars, 20, "ema20")
        _attach_ema(bars, 120, "ema120")

        _, signals = build_fractals(bars)
        segments = build_base_segments(bars, signals)

        fractals = [
            {
                "index": s.point.index,
                "time": s.point.time,
                "price": s.point.price,
                "type": s.type,
            }
            for s in signals
        ]
        segment_dicts = [
            {
                "direction": s.direction,
                "start": {"index": s.start.index, "time": s.start.time, "price": s.start.price},
                "end": {"index": s.end.index, "time": s.end.time, "price": s.end.price},
            }
            for s in segments
        ]

        return {
            "bar_count": len(bars),
            "fractals": fractals,
            "segments": segment_dicts,
        }


def _build_analysis_bars(items) -> list[AnalysisBar]:
    bars: list[AnalysisBar] = []
    for i, item in enumerate(items):
        t = _datetime_to_unix(item.date_time)
        bars.append(
            AnalysisBar(
                index=i,
                time=t,
                open=float(item.open),
                high=float(item.high),
                low=float(item.low),
                close=float(item.close),
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
