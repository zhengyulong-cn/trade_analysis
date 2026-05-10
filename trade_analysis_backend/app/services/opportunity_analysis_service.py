from dataclasses import dataclass

from fastapi import HTTPException

from app.core.kline_intervals import FIVE_MINUTES_SECONDS, THIRTY_MINUTES_SECONDS
from app.models.contract import Contract
from app.services.analysis_service import AnalysisService
from app.services.contract_service import ContractService
from app.services.kline_service import KlineService
import math


@dataclass
class OpportunityAnalysisSummary:
    symbol: str
    exchange: str
    name: str
    analysis_status: str
    analysis_message: str | None
    latest_price: float | None
    latest_time: int | None
    latest_30f_time: int | None
    current_30f_segment_type: str | None
    current_30f_segment_direction: str | None
    current_4h_segment_direction: str | None
    current_5f_segment_direction: str | None
    latest_30f_momentum_exhaustion_direction: str | None
    latest_30f_momentum_exhaustion_time: int | None
    latest_30f_momentum_exhaustion_price: float | None
    latest_5f_momentum_exhaustion_direction: str | None
    latest_5f_momentum_exhaustion_time: int | None
    latest_5f_momentum_exhaustion_price: float | None
    open_side: str | None
    in_open_zone: bool
    zone_source: str | None
    zone_low: float | None
    zone_high: float | None
    trading_range_top: float | None
    trading_range_bottom: float | None
    current_30f_segment_start_time: int | None
    current_30f_segment_end_time: int | None
    current_5f_zone_segment_start_time: int | None
    current_5f_zone_segment_end_time: int | None


class OpportunityAnalysisService:
    def __init__(
        self,
        contract_service: ContractService,
        kline_service: KlineService,
        analysis_service: AnalysisService,
    ):
        self._contract_service = contract_service
        self._kline_service = kline_service
        self._analysis_service = analysis_service

    def analyze_item(self, symbol: str) -> OpportunityAnalysisSummary:
        contract = self._contract_service.get_contract_by_symbol(symbol)
        return self._analyze_contract(contract)

    def analyze_all(self) -> list[OpportunityAnalysisSummary]:
        results: list[OpportunityAnalysisSummary] = []
        for contract in self._contract_service.list_contracts():
            results.append(self._analyze_contract(contract))
        return results

    def _analyze_contract(self, contract: Contract) -> OpportunityAnalysisSummary:
        try:
            latest_30f_result = self._kline_service.list_klines(
                symbol=contract.symbol,
                interval_seconds=THIRTY_MINUTES_SECONDS,
                limit=1,
            )
        except HTTPException as exc:
            return self._build_unavailable_result(contract, "no_data", exc.detail)

        if not latest_30f_result.kline_data:
            return self._build_unavailable_result(contract, "no_data", "缺少 30F K 线数据")

        try:
            analysis_5f = self._analysis_service.analyze(
                symbol=contract.symbol,
                interval_seconds=FIVE_MINUTES_SECONDS,
                limit=2000,
            )
            analysis_30f = self._analysis_service.analyze(
                symbol=contract.symbol,
                interval_seconds=THIRTY_MINUTES_SECONDS,
                limit=2000,
            )
        except HTTPException as exc:
            return self._build_unavailable_result(contract, "analysis_error", exc.detail)
        except Exception as exc:
            return self._build_unavailable_result(contract, "analysis_error", str(exc))

        latest_30f_bar = latest_30f_result.kline_data[-1]
        latest_price = float(latest_30f_bar.close)
        latest_time = int(latest_30f_bar.date_time.timestamp())

        current_30f_segment = self._last_item(analysis_30f["segments"])
        current_4h_segment = self._last_item(analysis_30f["higher_segments"])
        current_5f_segment = self._last_item(analysis_5f["segments"])
        latest_range = self._last_item(analysis_30f["trading_ranges"])
        latest_30f_momentum_exhaustion = self._last_item(analysis_30f["momentum_exhaustions"])
        latest_5f_momentum_exhaustion = self._last_item(analysis_5f["momentum_exhaustions"])

        if current_30f_segment is None or current_4h_segment is None:
            return OpportunityAnalysisSummary(
                symbol=contract.symbol,
                exchange=contract.exchange,
                name=contract.name,
                analysis_status="insufficient_data",
                analysis_message="线段数量不足，暂时无法判定开仓区域",
                latest_price=latest_price,
                latest_time=latest_time,
                latest_30f_time=latest_time,
                current_30f_segment_type=None,
                current_30f_segment_direction=current_30f_segment["direction"] if current_30f_segment else None,
                current_4h_segment_direction=current_4h_segment["direction"] if current_4h_segment else None,
                current_5f_segment_direction=current_5f_segment["direction"] if current_5f_segment else None,
                latest_30f_momentum_exhaustion_direction=self._momentum_direction(latest_30f_momentum_exhaustion),
                latest_30f_momentum_exhaustion_time=self._momentum_time(latest_30f_momentum_exhaustion),
                latest_30f_momentum_exhaustion_price=self._momentum_price(latest_30f_momentum_exhaustion),
                latest_5f_momentum_exhaustion_direction=self._momentum_direction(latest_5f_momentum_exhaustion),
                latest_5f_momentum_exhaustion_time=self._momentum_time(latest_5f_momentum_exhaustion),
                latest_5f_momentum_exhaustion_price=self._momentum_price(latest_5f_momentum_exhaustion),
                open_side=None,
                in_open_zone=False,
                zone_source=None,
                zone_low=None,
                zone_high=None,
                trading_range_top=latest_range["top"] if latest_range else None,
                trading_range_bottom=latest_range["bottom"] if latest_range else None,
                current_30f_segment_start_time=self._segment_start_time(current_30f_segment),
                current_30f_segment_end_time=self._segment_end_time(current_30f_segment),
                current_5f_zone_segment_start_time=None,
                current_5f_zone_segment_end_time=None,
            )

        if (
            latest_range is not None
            and self._price_in_range(latest_price, latest_range)
            and self._is_current_segment_near_trading_range(
                current_segment=current_30f_segment,
                all_segments=analysis_30f["segments"],
                trading_range=latest_range,
            )
        ):
            return self._build_range_internal_result(
                contract=contract,
                latest_price=latest_price,
                latest_time=latest_time,
                latest_range=latest_range,
                current_30f_segment=current_30f_segment,
                current_4h_segment=current_4h_segment,
                current_5f_segment=current_5f_segment,
                latest_30f_momentum_exhaustion=latest_30f_momentum_exhaustion,
                latest_5f_momentum_exhaustion=latest_5f_momentum_exhaustion,
            )

        if current_30f_segment["direction"] == current_4h_segment["direction"]:
            return self._build_trend_push_result(
                contract=contract,
                latest_price=latest_price,
                latest_time=latest_time,
                analysis_5f=analysis_5f,
                latest_range=latest_range,
                current_30f_segment=current_30f_segment,
                current_4h_segment=current_4h_segment,
                current_5f_segment=current_5f_segment,
                latest_30f_momentum_exhaustion=latest_30f_momentum_exhaustion,
                latest_5f_momentum_exhaustion=latest_5f_momentum_exhaustion,
            )

        return self._build_trend_pullback_result(
            contract=contract,
            latest_price=latest_price,
            latest_time=latest_time,
            latest_range=latest_range,
            current_30f_segment=current_30f_segment,
            current_4h_segment=current_4h_segment,
            current_5f_segment=current_5f_segment,
            latest_30f_momentum_exhaustion=latest_30f_momentum_exhaustion,
            latest_5f_momentum_exhaustion=latest_5f_momentum_exhaustion,
        )

    def _build_range_internal_result(
        self,
        contract: Contract,
        latest_price: float,
        latest_time: int,
        latest_range: dict,
        current_30f_segment: dict,
        current_4h_segment: dict,
        current_5f_segment: dict | None,
        latest_30f_momentum_exhaustion: dict | None,
        latest_5f_momentum_exhaustion: dict | None,
    ) -> OpportunityAnalysisSummary:
        top = float(latest_range["top"])
        bottom = float(latest_range["bottom"])
        range_size = top - bottom
        lower_threshold = bottom + math.ceil(range_size / 3)
        upper_threshold = top - math.ceil(range_size / 3)

        open_side: str | None = None
        in_open_zone = False
        zone_low: float | None = None
        zone_high: float | None = None
        if range_size > 0 and latest_price <= lower_threshold:
            open_side = "long"
            in_open_zone = True
            zone_low = bottom
            zone_high = lower_threshold
        elif range_size > 0 and latest_price >= upper_threshold:
            open_side = "short"
            in_open_zone = True
            zone_low = upper_threshold
            zone_high = top

        return OpportunityAnalysisSummary(
            symbol=contract.symbol,
            exchange=contract.exchange,
            name=contract.name,
            analysis_status="ok",
            analysis_message=None,
            latest_price=latest_price,
            latest_time=latest_time,
            latest_30f_time=latest_time,
            current_30f_segment_type="range_internal",
            current_30f_segment_direction=current_30f_segment["direction"],
            current_4h_segment_direction=current_4h_segment["direction"],
            current_5f_segment_direction=current_5f_segment["direction"] if current_5f_segment else None,
            latest_30f_momentum_exhaustion_direction=self._momentum_direction(latest_30f_momentum_exhaustion),
            latest_30f_momentum_exhaustion_time=self._momentum_time(latest_30f_momentum_exhaustion),
            latest_30f_momentum_exhaustion_price=self._momentum_price(latest_30f_momentum_exhaustion),
            latest_5f_momentum_exhaustion_direction=self._momentum_direction(latest_5f_momentum_exhaustion),
            latest_5f_momentum_exhaustion_time=self._momentum_time(latest_5f_momentum_exhaustion),
            latest_5f_momentum_exhaustion_price=self._momentum_price(latest_5f_momentum_exhaustion),
            open_side=open_side,
            in_open_zone=in_open_zone,
            zone_source="30f_trading_range_third",
            zone_low=zone_low,
            zone_high=zone_high,
            trading_range_top=top,
            trading_range_bottom=bottom,
            current_30f_segment_start_time=self._segment_start_time(current_30f_segment),
            current_30f_segment_end_time=self._segment_end_time(current_30f_segment),
            current_5f_zone_segment_start_time=None,
            current_5f_zone_segment_end_time=None,
        )

    def _build_trend_pullback_result(
        self,
        contract: Contract,
        latest_price: float,
        latest_time: int,
        latest_range: dict | None,
        current_30f_segment: dict,
        current_4h_segment: dict,
        current_5f_segment: dict | None,
        latest_30f_momentum_exhaustion: dict | None,
        latest_5f_momentum_exhaustion: dict | None,
    ) -> OpportunityAnalysisSummary:
        open_side = "long" if current_4h_segment["direction"] == "up" else "short"
        zone_low, zone_high = self._segment_price_bounds(current_30f_segment)

        return OpportunityAnalysisSummary(
            symbol=contract.symbol,
            exchange=contract.exchange,
            name=contract.name,
            analysis_status="ok",
            analysis_message=None,
            latest_price=latest_price,
            latest_time=latest_time,
            latest_30f_time=latest_time,
            current_30f_segment_type="trend_pullback",
            current_30f_segment_direction=current_30f_segment["direction"],
            current_4h_segment_direction=current_4h_segment["direction"],
            current_5f_segment_direction=current_5f_segment["direction"] if current_5f_segment else None,
            latest_30f_momentum_exhaustion_direction=self._momentum_direction(latest_30f_momentum_exhaustion),
            latest_30f_momentum_exhaustion_time=self._momentum_time(latest_30f_momentum_exhaustion),
            latest_30f_momentum_exhaustion_price=self._momentum_price(latest_30f_momentum_exhaustion),
            latest_5f_momentum_exhaustion_direction=self._momentum_direction(latest_5f_momentum_exhaustion),
            latest_5f_momentum_exhaustion_time=self._momentum_time(latest_5f_momentum_exhaustion),
            latest_5f_momentum_exhaustion_price=self._momentum_price(latest_5f_momentum_exhaustion),
            open_side=open_side,
            in_open_zone=True,
            zone_source="30f_pullback_segment",
            zone_low=zone_low,
            zone_high=zone_high,
            trading_range_top=float(latest_range["top"]) if latest_range else None,
            trading_range_bottom=float(latest_range["bottom"]) if latest_range else None,
            current_30f_segment_start_time=self._segment_start_time(current_30f_segment),
            current_30f_segment_end_time=self._segment_end_time(current_30f_segment),
            current_5f_zone_segment_start_time=None,
            current_5f_zone_segment_end_time=None,
        )

    def _build_trend_push_result(
        self,
        contract: Contract,
        latest_price: float,
        latest_time: int,
        analysis_5f: dict,
        latest_range: dict | None,
        current_30f_segment: dict,
        current_4h_segment: dict,
        current_5f_segment: dict | None,
        latest_30f_momentum_exhaustion: dict | None,
        latest_5f_momentum_exhaustion: dict | None,
    ) -> OpportunityAnalysisSummary:
        counter_direction = self._opposite_direction(current_30f_segment["direction"])
        push_start_time = self._segment_start_time(current_30f_segment)
        counter_segments = [
            segment
            for segment in analysis_5f["segments"]
            if segment["direction"] == counter_direction
            and self._segment_overlaps(segment, push_start_time, latest_time)
        ]

        current_counter_segment = None
        if (
            current_5f_segment is not None
            and current_5f_segment["direction"] == counter_direction
            and self._segment_overlaps(current_5f_segment, push_start_time, latest_time)
        ):
            current_counter_segment = current_5f_segment
        elif counter_segments:
            current_counter_segment = counter_segments[-1]

        in_open_zone = current_5f_segment is not None and current_counter_segment is current_5f_segment
        zone_low: float | None = None
        zone_high: float | None = None
        zone_start_time: int | None = None
        zone_end_time: int | None = None
        if current_counter_segment is not None:
            zone_low, zone_high = self._segment_price_bounds(current_counter_segment)
            zone_start_time = self._segment_start_time(current_counter_segment)
            zone_end_time = self._segment_end_time(current_counter_segment)

        open_side = "long" if current_30f_segment["direction"] == "up" else "short"
        return OpportunityAnalysisSummary(
            symbol=contract.symbol,
            exchange=contract.exchange,
            name=contract.name,
            analysis_status="ok",
            analysis_message=None,
            latest_price=latest_price,
            latest_time=latest_time,
            latest_30f_time=latest_time,
            current_30f_segment_type="trend_push",
            current_30f_segment_direction=current_30f_segment["direction"],
            current_4h_segment_direction=current_4h_segment["direction"],
            current_5f_segment_direction=current_5f_segment["direction"] if current_5f_segment else None,
            latest_30f_momentum_exhaustion_direction=self._momentum_direction(latest_30f_momentum_exhaustion),
            latest_30f_momentum_exhaustion_time=self._momentum_time(latest_30f_momentum_exhaustion),
            latest_30f_momentum_exhaustion_price=self._momentum_price(latest_30f_momentum_exhaustion),
            latest_5f_momentum_exhaustion_direction=self._momentum_direction(latest_5f_momentum_exhaustion),
            latest_5f_momentum_exhaustion_time=self._momentum_time(latest_5f_momentum_exhaustion),
            latest_5f_momentum_exhaustion_price=self._momentum_price(latest_5f_momentum_exhaustion),
            open_side=open_side,
            in_open_zone=in_open_zone,
            zone_source="5f_counter_segment_in_30f_push",
            zone_low=zone_low,
            zone_high=zone_high,
            trading_range_top=float(latest_range["top"]) if latest_range else None,
            trading_range_bottom=float(latest_range["bottom"]) if latest_range else None,
            current_30f_segment_start_time=self._segment_start_time(current_30f_segment),
            current_30f_segment_end_time=self._segment_end_time(current_30f_segment),
            current_5f_zone_segment_start_time=zone_start_time,
            current_5f_zone_segment_end_time=zone_end_time,
        )

    def _build_unavailable_result(
        self,
        contract: Contract,
        status: str,
        message: str,
    ) -> OpportunityAnalysisSummary:
        return OpportunityAnalysisSummary(
            symbol=contract.symbol,
            exchange=contract.exchange,
            name=contract.name,
            analysis_status=status,
            analysis_message=message,
            latest_price=None,
            latest_time=None,
            latest_30f_time=None,
            current_30f_segment_type=None,
            current_30f_segment_direction=None,
            current_4h_segment_direction=None,
            current_5f_segment_direction=None,
            latest_30f_momentum_exhaustion_direction=None,
            latest_30f_momentum_exhaustion_time=None,
            latest_30f_momentum_exhaustion_price=None,
            latest_5f_momentum_exhaustion_direction=None,
            latest_5f_momentum_exhaustion_time=None,
            latest_5f_momentum_exhaustion_price=None,
            open_side=None,
            in_open_zone=False,
            zone_source=None,
            zone_low=None,
            zone_high=None,
            trading_range_top=None,
            trading_range_bottom=None,
            current_30f_segment_start_time=None,
            current_30f_segment_end_time=None,
            current_5f_zone_segment_start_time=None,
            current_5f_zone_segment_end_time=None,
        )

    def _last_item(self, items: list[dict]) -> dict | None:
        if not items:
            return None
        return items[-1]

    def _price_in_range(self, price: float, trading_range: dict) -> bool:
        return float(trading_range["bottom"]) <= price <= float(trading_range["top"])

    def _segment_price_bounds(self, segment: dict) -> tuple[float, float]:
        prices = [float(segment["start"]["price"]), float(segment["end"]["price"])]
        return min(prices), max(prices)

    def _segment_start_time(self, segment: dict | None) -> int | None:
        if segment is None:
            return None
        return int(segment["start"]["time"])

    def _segment_end_time(self, segment: dict | None) -> int | None:
        if segment is None:
            return None
        return int(segment["end"]["time"])

    def _segment_overlaps(self, segment: dict, window_start: int | None, window_end: int) -> bool:
        start_time = self._segment_start_time(segment)
        end_time = self._segment_end_time(segment)
        if start_time is None or end_time is None:
            return False
        if window_start is None:
            return end_time <= window_end
        return end_time >= window_start and start_time <= window_end

    def _opposite_direction(self, direction: str) -> str:
        return "down" if direction == "up" else "up"

    def _momentum_direction(self, momentum_signal: dict | None) -> str | None:
        if momentum_signal is None:
            return None
        return momentum_signal.get("direction")

    def _momentum_time(self, momentum_signal: dict | None) -> int | None:
        if momentum_signal is None:
            return None
        point = momentum_signal.get("point")
        if not point:
            return None
        return int(point["time"])

    def _momentum_price(self, momentum_signal: dict | None) -> float | None:
        if momentum_signal is None:
            return None
        point = momentum_signal.get("point")
        if not point:
            return None
        return float(point["price"])

    def _is_current_segment_near_trading_range(
        self,
        current_segment: dict,
        all_segments: list[dict],
        trading_range: dict,
    ) -> bool:
        """
        间隔线段数 >= 2，就不再按区间内部段处理，而是继续走趋势推动/趋势回调逻辑
        """
        current_index = self._find_segment_index(all_segments, current_segment)
        range_segment_index = self._find_latest_range_related_segment_index(all_segments, trading_range)
        if current_index is None or range_segment_index is None:
            return False
        return current_index - range_segment_index < 2

    def _find_segment_index(self, all_segments: list[dict], target_segment: dict) -> int | None:
        target_start_time = self._segment_start_time(target_segment)
        target_end_time = self._segment_end_time(target_segment)
        target_direction = target_segment.get("direction")
        for index, segment in enumerate(all_segments):
            if (
                segment.get("direction") == target_direction
                and self._segment_start_time(segment) == target_start_time
                and self._segment_end_time(segment) == target_end_time
            ):
                return index
        return None

    def _find_latest_range_related_segment_index(
        self,
        all_segments: list[dict],
        trading_range: dict,
    ) -> int | None:
        range_right_time = int(trading_range["right"]["time"])
        matched_index: int | None = None
        for index, segment in enumerate(all_segments):
            segment_end_time = self._segment_end_time(segment)
            if segment_end_time is None:
                continue
            if segment_end_time <= range_right_time:
                matched_index = index
        return matched_index
