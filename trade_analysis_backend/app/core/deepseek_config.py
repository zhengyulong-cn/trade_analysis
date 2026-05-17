import json
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import settings


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str
    base_url: str
    model: str
    reasoning_effort: str = "high"
    thinking_enabled: bool = True


def load_deepseek_config() -> DeepSeekConfig:
    config_path = Path(settings.deepseek_config_path)
    if not config_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "DeepSeek config file not found. Please create "
                "trade_analysis_backend/config/deepseek_config.json from the example file."
            ),
        )

    try:
        raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"DeepSeek config file is invalid JSON: {exc}",
        ) from exc

    api_key = str(raw_config.get("api_key", "")).strip()
    base_url = str(raw_config.get("base_url", "https://api.deepseek.com")).strip()
    model = str(raw_config.get("model", "deepseek-v4-pro")).strip()
    reasoning_effort = str(raw_config.get("reasoning_effort", "high")).strip() or "high"
    thinking_enabled = bool(raw_config.get("thinking_enabled", True))

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DeepSeek api_key is missing in deepseek_config.json",
        )
    if not base_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DeepSeek base_url is missing in deepseek_config.json",
        )
    if not model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DeepSeek model is missing in deepseek_config.json",
        )

    return DeepSeekConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        reasoning_effort=reasoning_effort,
        thinking_enabled=thinking_enabled,
    )
