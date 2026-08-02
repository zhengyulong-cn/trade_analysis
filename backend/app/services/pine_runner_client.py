import json
from pathlib import Path
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
        last_error: TimeoutError | URLError | None = None
        for runner_url in self._get_runner_urls():
            request = Request(
                url=f"{runner_url}/v1/pine/execute",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(request, timeout=settings.pine_runner_timeout_seconds) as response:
                    result = json.loads(response.read().decode("utf-8"))
                break
            except HTTPError as exc:
                detail = self._read_error_detail(exc)
                logger.warning("Pine runner rejected indicator execution: %s", detail)
                raise HTTPException(status_code=exc.code, detail=detail) from exc
            except (TimeoutError, URLError) as exc:
                last_error = exc
                logger.warning("Pine runner unavailable at %s: %s", runner_url, exc)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                logger.error("Pine runner returned an invalid response: %s", exc)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Pine runner returned an invalid response.",
                ) from exc
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Pine runner is unavailable.",
            ) from last_error

        if not isinstance(result, dict):
            logger.error("Pine runner returned a non-object response")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Pine runner returned an invalid response.",
            )

        return result

    @staticmethod
    def _get_runner_urls() -> list[str]:
        urls = [settings.pine_runner_url.rstrip("/")]
        wsl_host_url = PineRunnerClient._get_wsl_host_url()
        if wsl_host_url and wsl_host_url not in urls:
            urls.append(wsl_host_url)
        return urls

    @staticmethod
    def _get_wsl_host_url() -> str | None:
        release_path = Path("/proc/sys/kernel/osrelease")
        resolv_conf_path = Path("/etc/resolv.conf")
        if not release_path.exists() or not resolv_conf_path.exists():
            return None
        try:
            if "microsoft" not in release_path.read_text().lower():
                return None
            for line in resolv_conf_path.read_text().splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[0] == "nameserver":
                    return f"http://{parts[1]}:8001"
        except OSError:
            return None
        return None

    @staticmethod
    def _read_error_detail(error: HTTPError) -> str:
        try:
            payload = json.loads(error.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return "Pine runner rejected the request."

        if isinstance(payload, dict) and isinstance(payload.get("message"), str):
            return payload["message"]
        return "Pine runner rejected the request."
