from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from math import ceil
from typing import Protocol

from app.core.kline_intervals import FIVE_MINUTES_SECONDS

BASE_KLINE_INTERVAL_SECONDS = FIVE_MINUTES_SECONDS


class KlineLike(Protocol):
    open: Decimal
    close: Decimal
    high: Decimal
    low: Decimal
    volume: Decimal
    hold: Decimal
    date_time: datetime


@dataclass(frozen=True)
class AggregatedKlineBar:
    open: Decimal
    close: Decimal
    high: Decimal
    low: Decimal
    volume: Decimal
    hold: Decimal
    date_time: datetime


def aggregate_klines(
    bars: list[KlineLike],
    target_interval_seconds: int,
) -> list[AggregatedKlineBar]:
    if target_interval_seconds <= BASE_KLINE_INTERVAL_SECONDS:
        return [
            AggregatedKlineBar(
                open=bar.open,
                close=bar.close,
                high=bar.high,
                low=bar.low,
                volume=bar.volume,
                hold=bar.hold,
                date_time=bar.date_time,
            )
            for bar in bars
        ]

    sorted_bars = sorted(bars, key=lambda item: item.date_time)
    groups: dict[datetime, list[KlineLike]] = {}

    for bar in sorted_bars:
        bucket_key = _get_trading_bucket_key(bar.date_time, target_interval_seconds)
        groups.setdefault(bucket_key, []).append(bar)

    return [_aggregate_group(group) for _, group in sorted(groups.items()) if group]


def _aggregate_group(group: list[KlineLike]) -> AggregatedKlineBar:
    first_bar = group[0]
    last_bar = group[-1]
    return AggregatedKlineBar(
        open=first_bar.open,
        close=last_bar.close,
        high=max(bar.high for bar in group),
        low=min(bar.low for bar in group),
        volume=sum((bar.volume for bar in group), Decimal("0")),
        hold=last_bar.hold,
        date_time=last_bar.date_time,
    )


def _get_trading_bucket_key(
    close_time: datetime,
    target_interval_seconds: int,
) -> datetime:
    session_segments = _get_session_segments(close_time)
    if not session_segments:
        return close_time

    elapsed_minutes = _get_elapsed_trading_minutes(close_time, session_segments)
    if elapsed_minutes <= 0:
        return close_time

    target_minutes = max(target_interval_seconds // 60, 1)
    bucket_minutes = ceil(elapsed_minutes / target_minutes) * target_minutes
    return _get_time_at_trading_minutes(bucket_minutes, session_segments)


def _get_session_segments(close_time: datetime) -> list[tuple[datetime, datetime]]:
    current_time = close_time.time()
    if current_time >= time(21, 0) or current_time < time(3, 0):
        start_date = close_time.date()
        if current_time < time(3, 0):
            start_date = start_date - timedelta(days=1)
        start = datetime.combine(start_date, time(21, 0))
        return [(start, start + timedelta(hours=6))]

    trade_date = close_time.date()
    return [
        (
            datetime.combine(trade_date, time(9, 0)),
            datetime.combine(trade_date, time(10, 15)),
        ),
        (
            datetime.combine(trade_date, time(10, 30)),
            datetime.combine(trade_date, time(11, 30)),
        ),
        (
            datetime.combine(trade_date, time(13, 30)),
            datetime.combine(trade_date, time(15, 0)),
        ),
    ]


def _get_elapsed_trading_minutes(
    close_time: datetime,
    session_segments: list[tuple[datetime, datetime]],
) -> int:
    elapsed = 0
    for segment_start, segment_end in session_segments:
        if close_time <= segment_start:
            break
        if close_time >= segment_end:
            elapsed += int((segment_end - segment_start).total_seconds() // 60)
            continue
        elapsed += int((close_time - segment_start).total_seconds() // 60)
        break
    return elapsed


def _get_time_at_trading_minutes(
    target_minutes: int,
    session_segments: list[tuple[datetime, datetime]],
) -> datetime:
    remaining_minutes = target_minutes
    for segment_start, segment_end in session_segments:
        segment_minutes = int((segment_end - segment_start).total_seconds() // 60)
        if remaining_minutes <= segment_minutes:
            return segment_start + timedelta(minutes=remaining_minutes)
        remaining_minutes -= segment_minutes
    return session_segments[-1][1] + timedelta(minutes=remaining_minutes)
