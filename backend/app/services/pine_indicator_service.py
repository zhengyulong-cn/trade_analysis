from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from app.schemas.pine_indicator import (
    PineIndicatorExecuteRequest,
    PineIndicatorExecuteResponse,
)
from app.services.kline_service import KlineService
from app.services.pine_runner_client import PineRunnerClient
from app.services.pine_script_service import PineScriptService

SHANGHAI_TIMEZONE = ZoneInfo("Asia/Shanghai")


class PineIndicatorService:
    def __init__(
        self,
        pine_script_service: PineScriptService,
        kline_service: KlineService,
        pine_runner_client: PineRunnerClient,
    ):
        self._pine_script_service = pine_script_service
        self._kline_service = kline_service
        self._pine_runner_client = pine_runner_client

    def execute(self, payload: PineIndicatorExecuteRequest) -> PineIndicatorExecuteResponse:
        script = self._pine_script_service.get_pine_script_by_id(payload.script_id)
        if script.script_type != "indicator":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Pine script {payload.script_id} is not an indicator.",
            )

        kline_result = self._kline_service.list_klines(
            symbol=payload.symbol,
            interval_seconds=payload.interval,
            limit=payload.limit,
        )
        bars = [
            self._to_pine_bar(item.date_time, item, payload.interval)
            for item in kline_result.kline_data
        ]
        result = self._pine_runner_client.execute_indicator(script.script_content, bars)

        indicator = result.get("indicator")
        plots = result.get("plots")
        drawings = result.get("drawings")
        warnings = result.get("warnings")
        if (
            not isinstance(indicator, dict)
            or not isinstance(plots, list)
            or not isinstance(drawings, dict)
            or not isinstance(warnings, list)
        ):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Pine runner returned an invalid execution result.",
            )

        return PineIndicatorExecuteResponse(
            script_id=payload.script_id,
            script_name=script.script_name,
            symbol=kline_result.symbol,
            interval=payload.interval,
            bar_count=len(bars),
            indicator=indicator,
            plots=plots,
            drawings=drawings,
            warnings=warnings,
        )

    @staticmethod
    def _to_pine_bar(
        date_time: datetime,
        item: Any,
        interval_seconds: int,
    ) -> dict[str, float | int]:
        timestamp = PineIndicatorService._to_timestamp_milliseconds(date_time)
        return {
            "timestamp": timestamp,
            "closeTime": timestamp + interval_seconds * 1000,
            "open": float(item.open),
            "high": float(item.high),
            "low": float(item.low),
            "close": float(item.close),
            "volume": float(item.volume),
        }

    @staticmethod
    def _to_timestamp_milliseconds(value: datetime) -> int:
        localized = (
            value.replace(tzinfo=SHANGHAI_TIMEZONE)
            if value.tzinfo is None
            else value
        )
        return int(localized.timestamp() * 1000)
