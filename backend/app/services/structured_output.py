from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.llm.base import LLMMessage, LLMRequest
from app.llm.router import LLMRouter, ModelResponseError

ItemT = TypeVar("ItemT", bound=BaseModel)


def parse_json_array(content: str, item_model: type[ItemT]) -> list[ItemT]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError("structured model output must be a JSON array")
    return [item_model.model_validate(item) for item in data]


async def generate_json_array(
    llm: LLMRouter,
    provider: str,
    request: LLMRequest,
    item_model: type[ItemT],
) -> list[ItemT]:
    settings = get_settings()
    messages = list(request.messages)
    last_error = "unknown structured output error"

    for attempt in range(settings.workflow_max_json_repairs + 1):
        active_request = LLMRequest(
            messages=messages,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop=request.stop,
            extra=request.extra,
        )
        response = await llm.generate(active_request, provider)
        try:
            return parse_json_array(response.content, item_model)
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as exc:
            last_error = str(exc)
            if attempt >= settings.workflow_max_json_repairs:
                break
            messages = [
                *messages,
                LLMMessage(role="assistant", content=response.content),
                LLMMessage(
                    role="user",
                    content=(
                        "The previous response was invalid. Return only a valid JSON array "
                        "matching the requested schema. Do not use Markdown fences or commentary."
                    ),
                ),
            ]

    raise ModelResponseError(
        "model returned invalid structured JSON",
        {"provider": provider, "error": last_error},
    )
