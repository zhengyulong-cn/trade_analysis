from datetime import datetime
from enum import Enum
from typing import Literal

from sqlmodel import SQLModel


class MACDSignalFilterItem(SQLModel):
    signal_type: Literal["long", "short"]
    date_time: datetime
    open: float
    close: float
    high: float
    low: float
    ema20: float
    diff: float
    dea: float
    macd: float
    boundary: float
    within_boundary: bool


class SignalFilterResult(SQLModel):
    symbol: str
    exchange: str
    name: str
    interval: int
    bar_count: int
    signal_count: int
    signals: list[MACDSignalFilterItem]


class AdxSlopeEnmu(Enum):
    Positive = 'positive'
    Negative = 'negative'
    Zero = 'zero'


class EmaTrendState(str, Enum):
    BullTrend = "bull_trend"
    BullExpanding = "bull_expanding"
    BullContracting = "bull_contracting"
    BearTrend = "bear_trend"
    BearExpanding = "bear_expanding"
    BearContracting = "bear_contracting"
    Neutral = "neutral"


class EmaTrendSignalItem(SQLModel):
    date_time: datetime
    ema20: float
    ema120: float
    atr20: float
    gap_strength: float
    gap_change: float
    state: EmaTrendState

class AdxRisingSignalItem(SQLModel):
    date_time: datetime
    open: float
    close: float
    high: float
    low: float
    tr: float
    di_plus: float
    di_minus: float
    dx: float
    adx: float
    previous_adx: float
    threshold: float
    above_threshold: bool
    adx_slope: AdxSlopeEnmu

class EntrySignalItem(SQLModel):
    signal_type: Literal["long", "short"]
    date_time: datetime
    open: float
    close: float
    high: float
    low: float
    adx_signal_date_time: datetime
    adx: float
    above_threshold: bool
    ema20: float
    ema120: float
    gap_strength: float
    ema_trend_state: EmaTrendState


class HoldingWarningSignalItem(SQLModel):
    position_direction: Literal["long", "short"]
    macd_signal_type: Literal["long", "short"]
    date_time: datetime
    close: float
    ema_trend_state: EmaTrendState

class AdxRisingSignalResult(SQLModel):
    symbol: str
    exchange: str
    name: str
    interval: int
    period: int
    threshold: float
    bar_count: int
    signal_count: int
    signals: list[AdxRisingSignalItem]


class ContractSignalResult(SQLModel):
    symbol: str
    exchange: str
    name: str
    interval: int
    bar_count: int
    macd_signals: list[MACDSignalFilterItem]
    adx_signals: list[AdxRisingSignalItem]
    ema_trend_signals: list[EmaTrendSignalItem]
    entry_signals: list[EntrySignalItem]
    holding_warning_signals: list[HoldingWarningSignalItem]


class AllEntrySignalItem(EntrySignalItem):
    symbol: str
    exchange: str
    name: str
    interval: int


class AllHoldingWarningSignalItem(HoldingWarningSignalItem):
    symbol: str
    exchange: str
    name: str
    interval: int


class AllContractSignalResult(SQLModel):
    interval: int
    contract_count: int
    items: list[ContractSignalResult]
    entry_signals: list[AllEntrySignalItem]
    holding_warning_signals: list[AllHoldingWarningSignalItem]
