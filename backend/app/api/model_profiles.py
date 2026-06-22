from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.responses import success
from app.llm.base import LLMMessage, LLMRequest
from app.llm.router import LLMRouter

router = APIRouter()


class ModelTestRequest(BaseModel):
    provider: str = ""
    message: str = "Hello, please respond with just the word pong."


class ModelTestResponse(BaseModel):
    provider: str
    connected: bool
    response: str = ""
    error: str = ""


def _default_messages() -> list[LLMMessage]:
    return [LLMMessage(role="user", content="Hello!")]


class GenerateRequest(BaseModel):
    provider: str = ""
    model: str = ""
    messages: list[LLMMessage] = Field(default_factory=_default_messages)
    max_tokens: int = 4096
    temperature: float = 0.7


class GenerateResponse(BaseModel):
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str


class ProviderStatus(BaseModel):
    models: dict[str, bool]
    default_provider: str


@router.get("/model/providers")
async def list_providers(request: Request) -> dict:
    settings = get_settings()
    return success(
        ProviderStatus(
            models=settings.model_configuration_status,
            default_provider=settings.default_model_provider,
        ),
        request,
    )


@router.post("/model/test")
async def test_model_connection(
    payload: ModelTestRequest,
    request: Request,
) -> dict:
    settings = get_settings()
    provider = payload.provider or settings.default_model_provider
    router_instance = LLMRouter()
    connected = await router_instance.validate_connection(provider)
    response_text = ""
    error = ""
    if connected:
        try:
            llm_request = LLMRequest(
                messages=[LLMMessage(role="user", content=payload.message)],
                max_tokens=50,
                temperature=0.0,
            )
            llm_response = await router_instance.generate(llm_request, provider)
            response_text = llm_response.content
        except Exception as exc:
            error = str(exc)
    return success(
        ModelTestResponse(
            provider=provider,
            connected=connected,
            response=response_text,
            error=error,
        ),
        request,
    )


@router.post("/model/generate")
async def generate_text(
    payload: GenerateRequest,
    request: Request,
) -> dict:
    settings = get_settings()
    provider = payload.provider or settings.default_model_provider
    router_instance = LLMRouter()
    llm_request = LLMRequest(
        messages=payload.messages,
        model=payload.model,
        max_tokens=payload.max_tokens,
        temperature=payload.temperature,
    )
    llm_response = await router_instance.generate(llm_request, provider)
    return success(
        GenerateResponse(
            content=llm_response.content,
            model=llm_response.model,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            finish_reason=llm_response.finish_reason,
        ),
        request,
    )
