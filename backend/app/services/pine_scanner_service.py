from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.schemas.pine_indicator import (
    PineScannerExecuteRequest,
    PineScannerExecuteResponse,
    PineScannerMatch,
)
from app.services.contract_service import ContractService
from app.services.kline_service import KlineService
from app.services.pine_indicator_service import PineIndicatorService
from app.services.pine_runner_client import PineRunnerClient
from app.services.pine_script_service import PineScriptService


class PineScannerService:
    def __init__(
        self,
        pine_script_service: PineScriptService,
        contract_service: ContractService,
        kline_service: KlineService,
        pine_runner_client: PineRunnerClient,
    ):
        self._pine_script_service = pine_script_service
        self._contract_service = contract_service
        self._kline_service = kline_service
        self._pine_runner_client = pine_runner_client

    def execute(self, payload: PineScannerExecuteRequest) -> PineScannerExecuteResponse:
        script = self._pine_script_service.get_pine_script_by_id(payload.script_id)
        if script.script_type != "scanner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Pine script {payload.script_id} is not a scanner.",
            )

        contracts = self._contract_service.list_contracts()
        scanner_contracts: list[dict[str, Any]] = []
        contract_ids: dict[str, int] = {}
        for contract in contracts:
            kline_result = self._kline_service.list_klines(
                symbol=contract.symbol,
                interval_seconds=payload.interval,
                limit=payload.limit,
            )
            bars = [
                self._to_pine_bar(item.date_time, item, payload.interval)
                for item in kline_result.kline_data
            ]
            if not bars:
                continue

            scanner_contracts.append(
                {
                    "symbol": contract.symbol,
                    "exchange": contract.exchange,
                    "name": contract.name,
                    "bars": bars,
                }
            )
            if contract.contract_id is not None:
                contract_ids[contract.symbol] = contract.contract_id

        result = self._pine_runner_client.execute_scanner(
            script.script_content,
            scanner_contracts,
        )
        scanned_count = result.get("scannedCount")
        matches = result.get("matches")
        if not isinstance(scanned_count, int) or not isinstance(matches, list):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Pine runner returned an invalid scanner result.",
            )

        response_matches = [self._to_match(item, contract_ids) for item in matches]
        return PineScannerExecuteResponse(
            script_id=payload.script_id,
            script_name=script.script_name,
            interval=payload.interval,
            contract_count=len(contracts),
            scanned_count=scanned_count,
            matches=[item for item in response_matches if item is not None],
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
    def _to_match(
        value: Any,
        contract_ids: dict[str, int],
    ) -> PineScannerMatch | None:
        if not isinstance(value, dict):
            return None
        symbol = value.get("symbol")
        exchange = value.get("exchange")
        name = value.get("name")
        message = value.get("message")
        triggered_at = value.get("triggeredAt")
        if (
            not isinstance(symbol, str)
            or not isinstance(exchange, str)
            or not isinstance(name, str)
            or not isinstance(message, str)
            or not isinstance(triggered_at, (int, float))
            or symbol not in contract_ids
        ):
            return None
        return PineScannerMatch(
            contract_id=contract_ids[symbol],
            symbol=symbol,
            exchange=exchange,
            name=name,
            message=message,
            triggered_at=datetime.fromtimestamp(triggered_at / 1000, tz=timezone.utc),
        )
