from dataclasses import dataclass

from fastapi import HTTPException

from app.core.kline_intervals import FIVE_MINUTES_SECONDS, THIRTY_MINUTES_SECONDS
from app.models.contract import Contract
from app.services.analysis_service_v2 import AnalysisServiceV2
from app.services.contract_service import ContractService
from app.services.kline_service import KlineService


@dataclass
class OpportunityAnalysisSummaryV2:
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


class OpportunityAnalysisServiceV2:
    def __init__(
        self,
        contract_service: ContractService,
        kline_service: KlineService,
        analysis_service: AnalysisServiceV2,
    ):
        self._contract_service = contract_service
        self._kline_service = kline_service
        self._analysis_service = analysis_service

    def analyze_item(self, symbol: str) -> OpportunityAnalysisSummaryV2:
        contract = self._contract_service.get_contract_by_symbol(symbol)
        return self._analyze_contract(contract)

    def analyze_all(self) -> list[OpportunityAnalysisSummaryV2]:
        return [self._analyze_contract(contract) for contract in self._contract_service.list_contracts()]

    def _analyze_contract(self, contract: Contract) -> OpportunityAnalysisSummaryV2:
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
            return self._build_unavailable_result(contract, "insufficient segment data")

        # 判断当前价格是否仍属于最近交易区间控制的范围。
        # 除了价格要落在区间上下沿之间，还要求当前 30F 线段距离该区间相关线段不超过 2 段。
        in_trading_range = self._is_in_recent_trading_range(
            latest_price=latest_price,
            latest_trading_range=latest_range,
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
            # 区间外时，用 4H 方向对应的 30F 同向段，判断当前 30F 是否已经衰竭。
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
            trading_range_position=trading_range_position,
            current_30f_momentum_exhausted=current_30f_momentum_exhausted,
        )
        current_5f_momentum_check_direction = self._resolve_5f_momentum_check_direction(
            opportunity_mode=opportunity_mode,
            open_side=open_side,
            current_30f_momentum_check_direction=current_30f_momentum_check_direction,
        )
        current_5f_momentum_exhausted = (
            self._latest_direction_segment_exhausted(
                segments=analysis_5f["segments"],
                direction=current_5f_momentum_check_direction,
                latest_time=latest_time,
            )
            if current_5f_momentum_check_direction is not None
            else None
        )
        has_opportunity, opportunity_action = self._resolve_5f_opportunity(
            opportunity_mode=opportunity_mode,
            open_side=open_side,
            current_5f_direction=current_5f_segment["direction"],
            current_5f_momentum_check_direction=current_5f_momentum_check_direction,
            current_5f_momentum_exhausted=current_5f_momentum_exhausted,
            current_30f_momentum_check_direction=current_30f_momentum_check_direction,
        )

        return OpportunityAnalysisSummaryV2(
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

    def _last_item(self, items: list[dict]) -> dict | None:
        if not items:
            return None
        return items[-1]

    def _is_in_recent_trading_range(
        self,
        latest_price: float,
        latest_trading_range: dict | None,
        all_segments: list[dict],
    ) -> bool:
        if latest_trading_range is None:
            return False
        if not self._price_in_horizontal_range(latest_price, latest_trading_range):
            return False

        trading_range_right_index = int(latest_trading_range["right"]["index"])
        gap = 0
        for segment in all_segments:
            segment_start_index = self._segment_start_index(segment)
            if segment_start_index is not None and trading_range_right_index <= segment_start_index:
                gap += 1
        return gap <= 2

    def _price_in_horizontal_range(self, price: float, trading_range: dict) -> bool:
        return float(trading_range["bottom"]) <= price <= float(trading_range["top"])

    def _segment_start_index(self, segment: dict | None) -> int | None:
        if segment is None:
            return None
        return int(segment["start"]["index"])

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

    def _classify_30f_segment(
        self,
        in_trading_range: bool,
        current_30f_direction: str,
        current_4h_direction: str,
    ) -> str:
        """
        range_internal: 区间内部段
        trend_push: 趋势推动段
        trend_pullback: 趋势回调段
        """
        if in_trading_range:
            return "range_internal"
        if current_30f_direction == current_4h_direction:
            return "trend_push"
        return "trend_pullback"

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

    def _resolve_open_side(
        self,
        in_trading_range: bool,
        trading_range_position: str | None,
        current_4h_direction: str,
        current_30f_momentum_exhausted: bool | None,
    ) -> str | None:
        """
        操作视角：
        1. 在交易区间内，上 1/3 做空，下 1/3 做多。
        2. 不在交易区间内且 30F 未衰竭时，跟随 4H 方向。
        3. 不在交易区间内且 30F 已衰竭时，使用 4H 反向视角。
        """
        if in_trading_range:
            if trading_range_position == "upper_third":
                return "short"
            if trading_range_position == "lower_third":
                return "long"
            return None

        base_side = "long" if current_4h_direction == "up" else "short"
        if current_30f_momentum_exhausted:
            return "short" if base_side == "long" else "long"
        return base_side

    def _resolve_mode(
        self,
        current_30f_segment_type: str | None,
        trading_range_position: str | None,
        current_30f_momentum_exhausted: bool | None,
    ) -> str | None:
        """
        这里只做 30F 级别的操作分类，5F 细化信号后续再处理。

        mode_1:
        当前是趋势推动段，30F 未衰竭，后续去 5F 找反向段结束。

        mode_2:
        当前是趋势回调段，30F 未衰竭，后续去 5F 找反向动能衰竭。

        mode_3:
        当前是区间内部段，且价格位于区间上 1/3 或下 1/3，后续去 5F 找反向动能衰竭。

        mode_4:
        当前是趋势推动段或趋势回调段，且 30F 已衰竭，后续去 5F 找同向衰竭确认。30F 和 5F 衰竭方向相同。
        """
        if current_30f_segment_type == "range_internal":
            if trading_range_position in {"upper_third", "lower_third"}:
                return "mode_3"
            return None

        if current_30f_segment_type not in {"trend_push", "trend_pullback"}:
            return None

        if current_30f_momentum_exhausted:
            return "mode_4"

        if current_30f_segment_type == "trend_push":
            return "mode_1"

        if current_30f_segment_type == "trend_pullback":
            return "mode_2"

        return None

    def _resolve_5f_momentum_check_direction(
        self,
        opportunity_mode: str | None,
        open_side: str | None,
        current_30f_momentum_check_direction: str | None,
    ) -> str | None:
        if opportunity_mode == "mode_1":
            return open_side
        if opportunity_mode in {"mode_2", "mode_3"}:
            if open_side is None:
                return None
            return self._opposite_direction(open_side)

        if opportunity_mode == "mode_4":
            return current_30f_momentum_check_direction

        return None

    def _resolve_5f_opportunity(
        self,
        opportunity_mode: str | None,
        open_side: str | None,
        current_5f_direction: str,
        current_5f_momentum_check_direction: str | None,
        current_5f_momentum_exhausted: bool | None,
        current_30f_momentum_check_direction: str | None,
    ) -> tuple[bool, str | None]:
        if opportunity_mode is None or open_side is None:
            return False, None

        reverse_direction = self._opposite_direction(open_side)

        if opportunity_mode == "mode_1":
            if current_5f_direction == reverse_direction:
                return True, self._wait_segment_end_action(open_side)
            return False, None

        if opportunity_mode in {"mode_2", "mode_3"}:
            if (
                current_5f_direction == reverse_direction
                and current_5f_momentum_check_direction == reverse_direction
                and bool(current_5f_momentum_exhausted)
            ):
                return True, self._wait_reverse_exhaustion_action(open_side)
            return False, None

        if opportunity_mode == "mode_4":
            if (
                current_30f_momentum_check_direction is not None
                and current_5f_momentum_check_direction == current_30f_momentum_check_direction
                and bool(current_5f_momentum_exhausted)
            ):
                return True, self._wait_same_direction_exhaustion_action(open_side)
            return False, None

        return False, None

    def _segment_end_time(self, segment: dict | None) -> int | None:
        if segment is None:
            return None
        return int(segment["end"]["time"])

    def _opposite_direction(self, side: str) -> str:
        return "down" if side == "long" else "up"

    def _wait_segment_end_action(self, open_side: str) -> str:
        if open_side == "long":
            return "open_long_wait_5f_down_end"
        return "open_short_wait_5f_up_end"

    def _wait_reverse_exhaustion_action(self, open_side: str) -> str:
        if open_side == "long":
            return "open_long_wait_5f_down_exhaustion"
        return "open_short_wait_5f_up_exhaustion"

    def _wait_same_direction_exhaustion_action(self, open_side: str) -> str:
        if open_side == "long":
            return "open_long_wait_5f_up_exhaustion_sync_30f"
        return "open_short_wait_5f_down_exhaustion_sync_30f"

    def _build_unavailable_result(self, contract: Contract, message: str) -> OpportunityAnalysisSummaryV2:
        return OpportunityAnalysisSummaryV2(
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
