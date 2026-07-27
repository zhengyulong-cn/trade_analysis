import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PineRunnerClient:
    def execute_indicator(self, source: str, bars: list[dict[str, float | int]]) -> dict[str, Any]:
        payload = json.dumps({"source": source, "bars": bars}).encode("utf-8")
        request = Request(
            url=f"{settings.pine_runner_url.rstrip('/')}/v1/pine/execute",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=settings.pine_runner_timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = self._read_error_detail(exc)
            logger.warning("Pine runner rejected indicator execution: %s", detail)
            raise HTTPException(status_code=exc.code, detail=detail) from exc
        except (TimeoutError, URLError) as exc:
            logger.error("Pine runner is unavailable: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Pine runner is unavailable.",
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error("Pine runner returned an invalid response: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Pine runner returned an invalid response.",
            ) from exc

        if not isinstance(result, dict):
            logger.error("Pine runner returned a non-object response")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Pine runner returned an invalid response.",
            )

        return result

    @staticmethod
    def _read_error_detail(error: HTTPError) -> str:
        try:
            payload = json.loads(error.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return "Pine runner rejected the request."

        if isinstance(payload, dict) and isinstance(payload.get("message"), str):
            return payload["message"]
        return "Pine runner rejected the request."
