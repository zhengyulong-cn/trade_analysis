from dataclasses import dataclass

from fastapi import HTTPException

from app.core.kline_intervals import FIVE_MINUTES_SECONDS, THIRTY_MINUTES_SECONDS
from app.models.contract import Contract
from app.services.analysis_service_v2 import AnalysisServiceV2
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
    current_4h_segment_direction: str | None
    current_30f_segment_direction: str | None
    current_30f_segment_type: str | None
    current_5f_segment_direction: str | None
    trading_range_top: float | None
    trading_range_bottom: float | None
    is_in_30f_trading_range: bool
    trading_range_position: str | None
    current_30f_momentum_check_direction: str | None
    current_30f_momentum_exhausted: bool | None
    current_5f_momentum_check_direction: str | None
    current_5f_momentum_exhausted: bool | None
    open_side: str | None
    has_opportunity: bool
    opportunity_action: str | None
    opportunity_mode: str | None


class OpportunityAnalysisService:
    def __init__(
        self,
        contract_service: ContractService,
        kline_service: KlineService,
        analysis_service: AnalysisServiceV2,
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

        if not latest_30f_result.kline_data:
            return self._build_unavailable_result(contract, "missing 30F kline data")

        latest_30f_bar = latest_30f_result.kline_data[-1]
        latest_price = float(latest_30f_bar.close)
        latest_time = int(latest_30f_bar.date_time.timestamp())

        current_30f_segment = self._last_item(analysis_30f["segments"])
        current_4h_segment = self._last_item(analysis_30f["higher_segments"])
        current_5f_segment = self._last_item(analysis_5f["segments"])
        latest_range = self._last_item(analysis_30f["trading_ranges"])

        if current_30f_segment is None or current_4h_segment is None or current_5f_segment is None:
            return OpportunityAnalysisSummary(
                symbol=contract.symbol,
                exchange=contract.exchange,
                name=contract.name,
                analysis_message="insufficient segment data",
                latest_price=latest_price,
                latest_time=latest_time,
                latest_30f_time=latest_time,
                current_4h_segment_direction=current_4h_segment["direction"] if current_4h_segment else None,
                current_30f_segment_direction=current_30f_segment["direction"] if current_30f_segment else None,
                current_30f_segment_type=None,
                current_5f_segment_direction=current_5f_segment["direction"] if current_5f_segment else None,
                trading_range_top=float(latest_range["top"]) if latest_range else None,
                trading_range_bottom=float(latest_range["bottom"]) if latest_range else None,
                is_in_30f_trading_range=False,
                trading_range_position=None,
                current_30f_momentum_check_direction=None,
                current_30f_momentum_exhausted=None,
                current_5f_momentum_check_direction=None,
                current_5f_momentum_exhausted=None,
                open_side=None,
                has_opportunity=False,
                opportunity_action=None,
                opportunity_mode=None,
            )

        in_trading_range = self._is_in_recent_trading_range(
            latest_price=latest_price,
            trading_range=latest_range,
            current_segment=current_30f_segment,
            all_segments=analysis_30f["segments"],
        )
        trading_range_position = (
            self._resolve_range_position(latest_price, latest_range) if in_trading_range else None
        )

        current_30f_segment_type = self._classify_30f_segment(
            in_trading_range=in_trading_range,
            current_30f_direction=current_30f_segment["direction"],
            current_4h_direction=current_4h_segment["direction"],
        )

        current_30f_momentum_check_direction: str | None = None
        current_30f_momentum_exhausted: bool | None = None
        if not in_trading_range:
            current_30f_momentum_check_direction = current_4h_segment["direction"]
            current_30f_momentum_exhausted = self._latest_direction_segment_exhausted(
                segments=analysis_30f["segments"],
                direction=current_30f_momentum_check_direction,
                latest_time=latest_time,
            )

        open_side = self._resolve_open_side(
            in_trading_range=in_trading_range,
            trading_range_position=trading_range_position,
            current_4h_direction=current_4h_segment["direction"],
            current_30f_momentum_exhausted=current_30f_momentum_exhausted,
        )
        opportunity_mode = self._resolve_mode(
            current_30f_segment_type=current_30f_segment_type,
            current_30f_direction=current_30f_segment["direction"],
            current_4h_direction=current_4h_segment["direction"],
        )

        current_5f_momentum_check_direction = current_30f_segment["direction"]
        current_5f_momentum_exhausted = self._latest_direction_segment_exhausted(
            segments=analysis_5f["segments"],
            direction=current_5f_momentum_check_direction,
            latest_time=latest_time,
        )

        has_opportunity, opportunity_action, opportunity_mode = self._resolve_opportunity(
            open_side=open_side,
            opportunity_mode=opportunity_mode,
            current_5f_direction=current_5f_segment["direction"],
            current_5f_momentum_exhausted=current_5f_momentum_exhausted,
        )

        return OpportunityAnalysisSummary(
            symbol=contract.symbol,
            exchange=contract.exchange,
            name=contract.name,
            analysis_message=None,
            latest_price=latest_price,
            latest_time=latest_time,
            latest_30f_time=latest_time,
            current_4h_segment_direction=current_4h_segment["direction"],
            current_30f_segment_direction=current_30f_segment["direction"],
            current_30f_segment_type=current_30f_segment_type,
            current_5f_segment_direction=current_5f_segment["direction"],
            trading_range_top=float(latest_range["top"]) if latest_range else None,
            trading_range_bottom=float(latest_range["bottom"]) if latest_range else None,
            is_in_30f_trading_range=in_trading_range,
            trading_range_position=trading_range_position,
            current_30f_momentum_check_direction=current_30f_momentum_check_direction,
            current_30f_momentum_exhausted=current_30f_momentum_exhausted,
            current_5f_momentum_check_direction=current_5f_momentum_check_direction,
            current_5f_momentum_exhausted=current_5f_momentum_exhausted,
            open_side=open_side,
            has_opportunity=has_opportunity,
            opportunity_action=opportunity_action,
            opportunity_mode=opportunity_mode,
        )

    def _build_unavailable_result(self, contract: Contract, message: str) -> OpportunityAnalysisSummary:
        return OpportunityAnalysisSummary(
            symbol=contract.symbol,
            exchange=contract.exchange,
            name=contract.name,
            analysis_message=message,
            latest_price=None,
            latest_time=None,
            latest_30f_time=None,
            current_4h_segment_direction=None,
            current_30f_segment_direction=None,
            current_30f_segment_type=None,
            current_5f_segment_direction=None,
            trading_range_top=None,
            trading_range_bottom=None,
            is_in_30f_trading_range=False,
            trading_range_position=None,
            current_30f_momentum_check_direction=None,
            current_30f_momentum_exhausted=None,
            current_5f_momentum_check_direction=None,
            current_5f_momentum_exhausted=None,
            open_side=None,
            has_opportunity=False,
            opportunity_action=None,
            opportunity_mode=None,
        )

    def _classify_30f_segment(
        self,
        in_trading_range: bool,
        current_30f_direction: str,
        current_4h_direction: str,
    ) -> str:
        if in_trading_range:
            return "range_internal"
        if current_30f_direction == current_4h_direction:
            return "trend_push"
        return "trend_pullback"

    def _resolve_open_side(
        self,
        in_trading_range: bool,
        trading_range_position: str | None,
        current_4h_direction: str,
        current_30f_momentum_exhausted: bool | None,
    ) -> str | None:
        if in_trading_range:
            if trading_range_position == "upper_third":
                return "short"
            if trading_range_position == "lower_third":
                return "long"
            return None

        base_side = "long" if current_4h_direction == "up" else "short"
        if current_30f_momentum_exhausted:
            return self._opposite_side(base_side)
        return base_side

    def _resolve_mode(
        self,
        current_30f_segment_type: str,
        current_30f_direction: str,
        current_4h_direction: str,
    ) -> str | None:
        if current_30f_segment_type == "trend_push":
            return "mode_1"
        if current_30f_segment_type == "trend_pullback":
            return "mode_2"
        if current_30f_segment_type == "range_internal":
            if current_30f_direction == current_4h_direction:
                return "mode_3"
            return "mode_4"
        return None

    def _resolve_opportunity(
        self,
        open_side: str | None,
        opportunity_mode: str | None,
        current_5f_direction: str,
        current_5f_momentum_exhausted: bool,
    ) -> tuple[bool, str | None, str | None]:
        if open_side is None or opportunity_mode is None:
            return False, None, None

        wait_direction = self._opposite_direction(open_side)
        trend_direction = self._side_to_direction(open_side)

        if opportunity_mode == "mode_1":
            if current_5f_momentum_exhausted:
                return False, None, opportunity_mode
            if current_5f_direction == wait_direction:
                return True, self._wait_action(open_side), opportunity_mode
            return False, None, opportunity_mode

        if opportunity_mode == "mode_2":
            if not current_5f_momentum_exhausted:
                return False, None, opportunity_mode
            if current_5f_direction == wait_direction:
                return True, self._wait_action(open_side), opportunity_mode
            if current_5f_direction == trend_direction:
                return True, self._follow_action(open_side), opportunity_mode
            return False, None, opportunity_mode

        if opportunity_mode == "mode_3":
            if current_5f_direction == wait_direction:
                if current_5f_momentum_exhausted:
                    return False, None, opportunity_mode
                return True, self._wait_action(open_side), opportunity_mode
            return False, None, opportunity_mode

        if opportunity_mode == "mode_4":
            if not current_5f_momentum_exhausted:
                return False, None, opportunity_mode
            return True, self._reverse_structure_action(open_side), opportunity_mode

        return False, None, None

    def _is_in_recent_trading_range(
        self,
        latest_price: float,
        trading_range: dict | None,
        current_segment: dict,
        all_segments: list[dict],
    ) -> bool:
        if trading_range is None:
            return False
        if not self._price_in_range(latest_price, trading_range):
            return False
        current_index = self._find_segment_index(all_segments, current_segment)
        range_segment_index = self._find_latest_range_related_segment_index(all_segments, trading_range)
        if current_index is None or range_segment_index is None:
            return False
        return current_index - range_segment_index <= 2

    def _resolve_range_position(self, latest_price: float, trading_range: dict | None) -> str | None:
        if trading_range is None:
            return None
        top = float(trading_range["top"])
        bottom = float(trading_range["bottom"])
        range_size = top - bottom
        if range_size <= 0:
            return None
        lower_limit = bottom + range_size / 3
        upper_limit = top - range_size / 3
        if latest_price >= upper_limit:
            return "upper_third"
        if latest_price <= lower_limit:
            return "lower_third"
        return "middle_third"

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

    def _opposite_direction(self, side: str) -> str:
        return "down" if side == "long" else "up"

    def _side_to_direction(self, side: str) -> str:
        return "up" if side == "long" else "down"

    def _wait_action(self, open_side: str) -> str:
        if open_side == "long":
            return "open_long_wait_5f_down_end"
        return "open_short_wait_5f_up_end"

    def _follow_action(self, open_side: str) -> str:
        if open_side == "long":
            return "open_long_follow_5f_up"
        return "open_short_follow_5f_down"

    def _reverse_structure_action(self, open_side: str) -> str:
        if open_side == "long":
            return "open_long_reverse_5f_down_structure"
        return "open_short_reverse_5f_up_structure"
