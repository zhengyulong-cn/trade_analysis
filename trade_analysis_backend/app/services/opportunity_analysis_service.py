import math
from dataclasses import dataclass

from fastapi import HTTPException

from app.core.kline_intervals import FIVE_MINUTES_SECONDS, THIRTY_MINUTES_SECONDS
from app.models.contract import Contract
from app.services.analysis_service import AnalysisService
from app.services.contract_service import ContractService
from app.services.kline_service import KlineService


@dataclass
class OpportunityAnalysisSummary:
    symbol: str
    exchange: str
    name: str
    analysis_message: str | None
    latest_price: float | None
    latest_time: int | None
    latest_30f_time: int | None
    current_30f_segment_type: str | None
    current_30f_segment_direction: str | None
    current_4h_segment_direction: str | None
    current_5f_segment_direction: str | None
    current_30f_momentum_check_direction: str | None
    current_30f_momentum_exhausted: bool | None
    current_5f_momentum_check_direction: str | None
    current_5f_momentum_exhausted: bool | None
    current_5f_wait_direction: str | None
    open_side: str | None
    has_opportunity: bool
    opportunity_action: str | None
    zone_source: str | None
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
        return [self._analyze_contract(contract) for contract in self._contract_service.list_contracts()]

    def _analyze_contract(self, contract: Contract) -> OpportunityAnalysisSummary:
        try:
            latest_30f_result = self._kline_service.list_klines(
                symbol=contract.symbol,
                interval_seconds=THIRTY_MINUTES_SECONDS,
                limit=1,
            )
        except HTTPException as exc:
            return self._build_unavailable_result(contract, str(exc.detail))

        if not latest_30f_result.kline_data:
            return self._build_unavailable_result(contract, "缺少 30F K 线数据")

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
            return self._build_unavailable_result(contract, str(exc.detail))
        except Exception as exc:
            return self._build_unavailable_result(contract, str(exc))

        latest_30f_bar = latest_30f_result.kline_data[-1]
        latest_price = float(latest_30f_bar.close)
        latest_time = int(latest_30f_bar.date_time.timestamp())

        current_30f_segment = self._last_item(analysis_30f["segments"])
        current_4h_segment = self._last_item(analysis_30f["higher_segments"])
        current_5f_segment = self._last_item(analysis_5f["segments"])
        latest_range = self._last_item(analysis_30f["trading_ranges"])

        if current_30f_segment is None or current_4h_segment is None:
            return OpportunityAnalysisSummary(
                symbol=contract.symbol,
                exchange=contract.exchange,
                name=contract.name,
                analysis_message="线段数量不足，暂时无法判定开仓机会",
                latest_price=latest_price,
                latest_time=latest_time,
                latest_30f_time=latest_time,
                current_30f_segment_type=None,
                current_30f_segment_direction=current_30f_segment["direction"] if current_30f_segment else None,
                current_4h_segment_direction=current_4h_segment["direction"] if current_4h_segment else None,
                current_5f_segment_direction=current_5f_segment["direction"] if current_5f_segment else None,
                current_30f_momentum_check_direction=None,
                current_30f_momentum_exhausted=None,
                current_5f_momentum_check_direction=None,
                current_5f_momentum_exhausted=None,
                current_5f_wait_direction=None,
                open_side=None,
                has_opportunity=False,
                opportunity_action=None,
                zone_source=None,
                trading_range_top=float(latest_range["top"]) if latest_range else None,
                trading_range_bottom=float(latest_range["bottom"]) if latest_range else None,
                current_30f_segment_start_time=self._segment_start_time(current_30f_segment),
                current_30f_segment_end_time=self._segment_end_time(current_30f_segment),
                current_5f_zone_segment_start_time=None,
                current_5f_zone_segment_end_time=None,
            )

        summary = self._build_30f_summary(
            contract=contract,
            latest_price=latest_price,
            latest_time=latest_time,
            analysis_30f=analysis_30f,
            current_30f_segment=current_30f_segment,
            current_4h_segment=current_4h_segment,
            current_5f_segment=current_5f_segment,
            latest_range=latest_range,
        )

        return self._attach_five_minute_opportunity(
            summary=summary,
            analysis_5f=analysis_5f,
            current_5f_segment=current_5f_segment,
            latest_time=latest_time,
        )

    def _build_30f_summary(
        self,
        contract: Contract,
        latest_price: float,
        latest_time: int,
        analysis_30f: dict,
        current_30f_segment: dict,
        current_4h_segment: dict,
        current_5f_segment: dict | None,
        latest_range: dict | None,
    ) -> OpportunityAnalysisSummary:
        segment_type = self._classify_30f_segment(
            latest_price=latest_price,
            all_30f_segments=analysis_30f["segments"],
            current_30f_segment=current_30f_segment,
            current_4h_segment=current_4h_segment,
            latest_range=latest_range,
        )

        range_open_side = self._resolve_range_open_side(latest_price, latest_range) if segment_type == "range_internal" else None
        current_30f_exhausted = None
        current_30f_momentum_check_direction = None
        current_5f_momentum_check_direction = None
        current_5f_wait_direction = None
        open_side: str | None = None

        if segment_type == "range_internal":
            open_side = range_open_side
            if open_side is not None:
                current_5f_wait_direction = "down" if open_side == "long" else "up"
                current_5f_momentum_check_direction = current_5f_wait_direction
        elif segment_type == "trend_pullback":
            open_side = "long" if current_4h_segment["direction"] == "up" else "short"
            current_5f_wait_direction = "down" if open_side == "long" else "up"
            current_5f_momentum_check_direction = current_5f_wait_direction
        else:
            current_30f_momentum_check_direction = current_30f_segment["direction"]
            current_30f_exhausted = bool(current_30f_segment.get("is_momentum_exhaustion_segment", False))
            trend_side = "long" if current_30f_segment["direction"] == "up" else "short"
            open_side = self._opposite_side(trend_side) if current_30f_exhausted else trend_side
            current_5f_wait_direction = "down" if open_side == "long" else "up"
            current_5f_momentum_check_direction = (
                current_5f_wait_direction if current_30f_exhausted else current_30f_segment["direction"]
            )

        return OpportunityAnalysisSummary(
            symbol=contract.symbol,
            exchange=contract.exchange,
            name=contract.name,
            analysis_message=None,
            latest_price=latest_price,
            latest_time=latest_time,
            latest_30f_time=latest_time,
            current_30f_segment_type=segment_type,
            current_30f_segment_direction=current_30f_segment["direction"],
            current_4h_segment_direction=current_4h_segment["direction"],
            current_5f_segment_direction=current_5f_segment["direction"] if current_5f_segment else None,
            current_30f_momentum_check_direction=current_30f_momentum_check_direction,
            current_30f_momentum_exhausted=current_30f_exhausted,
            current_5f_momentum_check_direction=current_5f_momentum_check_direction,
            current_5f_momentum_exhausted=None,
            current_5f_wait_direction=current_5f_wait_direction,
            open_side=open_side,
            has_opportunity=False,
            opportunity_action=None,
            zone_source=self._resolve_zone_source(segment_type),
            trading_range_top=float(latest_range["top"]) if latest_range else None,
            trading_range_bottom=float(latest_range["bottom"]) if latest_range else None,
            current_30f_segment_start_time=self._segment_start_time(current_30f_segment),
            current_30f_segment_end_time=self._segment_end_time(current_30f_segment),
            current_5f_zone_segment_start_time=None,
            current_5f_zone_segment_end_time=None,
        )

    def _attach_five_minute_opportunity(
        self,
        summary: OpportunityAnalysisSummary,
        analysis_5f: dict,
        current_5f_segment: dict | None,
        latest_time: int,
    ) -> OpportunityAnalysisSummary:
        if summary.open_side is None or summary.current_5f_momentum_check_direction is None:
            return summary

        summary.current_5f_momentum_exhausted = self._latest_direction_segment_exhausted(
            segments=analysis_5f["segments"],
            direction=summary.current_5f_momentum_check_direction,
            latest_time=latest_time,
        )

        if (
            current_5f_segment is not None
            and summary.current_5f_wait_direction is not None
            and current_5f_segment["direction"] == summary.current_5f_wait_direction
            and bool(current_5f_segment.get("is_momentum_exhaustion_segment", False))
        ):
            summary.has_opportunity = True
            summary.opportunity_action = (
                "open_long_wait_5f_down_end" if summary.open_side == "long" else "open_short_wait_5f_up_end"
            )
            summary.current_5f_zone_segment_start_time = self._segment_start_time(current_5f_segment)
            summary.current_5f_zone_segment_end_time = self._segment_end_time(current_5f_segment)

        return summary

    def _classify_30f_segment(
        self,
        latest_price: float,
        all_30f_segments: list[dict],
        current_30f_segment: dict,
        current_4h_segment: dict,
        latest_range: dict | None,
    ) -> str:
        if (
            latest_range is not None
            and self._price_in_range(latest_price, latest_range)
            and self._is_current_segment_near_trading_range(
                current_segment=current_30f_segment,
                all_segments=all_30f_segments,
                trading_range=latest_range,
            )
        ):
            return "range_internal"
        if current_30f_segment["direction"] == current_4h_segment["direction"]:
            return "trend_push"
        return "trend_pullback"

    def _resolve_range_open_side(self, latest_price: float, latest_range: dict | None) -> str | None:
        if latest_range is None:
            return None
        top = float(latest_range["top"])
        bottom = float(latest_range["bottom"])
        range_size = top - bottom
        if range_size <= 0:
            return None
        lower_threshold = bottom + math.ceil(range_size / 3)
        upper_threshold = top - math.ceil(range_size / 3)
        if latest_price <= lower_threshold:
            return "long"
        if latest_price >= upper_threshold:
            return "short"
        return None

    def _resolve_zone_source(self, segment_type: str) -> str | None:
        if segment_type == "range_internal":
            return "30f_trading_range_third"
        if segment_type == "trend_pullback":
            return "30f_pullback_segment"
        if segment_type == "trend_push":
            return "30f_push_segment"
        return None

    def _build_unavailable_result(self, contract: Contract, message: str) -> OpportunityAnalysisSummary:
        return OpportunityAnalysisSummary(
            symbol=contract.symbol,
            exchange=contract.exchange,
            name=contract.name,
            analysis_message=message,
            latest_price=None,
            latest_time=None,
            latest_30f_time=None,
            current_30f_segment_type=None,
            current_30f_segment_direction=None,
            current_4h_segment_direction=None,
            current_5f_segment_direction=None,
            current_30f_momentum_check_direction=None,
            current_30f_momentum_exhausted=None,
            current_5f_momentum_check_direction=None,
            current_5f_momentum_exhausted=None,
            current_5f_wait_direction=None,
            open_side=None,
            has_opportunity=False,
            opportunity_action=None,
            zone_source=None,
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

    def _segment_start_time(self, segment: dict | None) -> int | None:
        if segment is None:
            return None
        return int(segment["start"]["time"])

    def _segment_end_time(self, segment: dict | None) -> int | None:
        if segment is None:
            return None
        return int(segment["end"]["time"])

    def _opposite_side(self, side: str) -> str:
        return "short" if side == "long" else "long"

    def _latest_direction_segment_exhausted(
        self,
        segments: list[dict],
        direction: str,
        latest_time: int,
    ) -> bool:
        for segment in reversed(segments):
            if segment.get("direction") != direction:
                continue
            end_time = self._segment_end_time(segment)
            if end_time is None or end_time > latest_time:
                continue
            return bool(segment.get("is_momentum_exhaustion_segment", False))
        return False

    def _is_current_segment_near_trading_range(
        self,
        current_segment: dict,
        all_segments: list[dict],
        trading_range: dict,
    ) -> bool:
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
