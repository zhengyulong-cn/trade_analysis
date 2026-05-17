import json
from typing import TypeVar

from fastapi import HTTPException, status
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from app.core.deepseek_config import load_deepseek_config

T = TypeVar("T", bound=BaseModel)


class DeepSeekLLMService:
    def __init__(self):
        self.config = load_deepseek_config()
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        extra_body = {"thinking": {"type": "enabled"}} if self.config.thinking_enabled else None
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False,
            reasoning_effort=self.config.reasoning_effort,
            extra_body=extra_body,
        )
        content = response.choices[0].message.content or ""
        parsed = self._parse_json_content(content)
        try:
            return response_model.model_validate(parsed)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"DeepSeek response schema validation failed: {exc}",
            ) from exc

    def _parse_json_content(self, content: str) -> dict | list:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```JSON").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"DeepSeek returned invalid JSON: {exc}",
            ) from exc
