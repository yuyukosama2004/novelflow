from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.responses import success
from app.database.session import get_session
from app.llm.base import LLMMessage, LLMRequest
from app.llm.router import LLMRouter
from app.services.model_profile_service import ModelProfileService

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
        except Exception:
            error = "model request failed"
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


# ── Model Profile CRUD ──


class ProfileCreate(BaseModel):
    name: str = ""
    provider: Literal["deepseek", "ollama", "openai_compatible", "fake"] = "deepseek"
    base_url: str = ""
    api_key: str = ""
    model_name: str = ""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=4096, ge=1)
    timeout_seconds: int = Field(default=120, ge=1)
    is_default: bool = False
    enabled: bool = True


class ProfileUpdate(BaseModel):
    name: str | None = None
    provider: Literal["deepseek", "ollama", "openai_compatible", "fake"] | None = None
    base_url: str | None = None
    api_key: str | None = None
    model_name: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_output_tokens: int | None = Field(default=None, ge=1)
    timeout_seconds: int | None = Field(default=None, ge=1)
    is_default: bool | None = None
    enabled: bool | None = None


@router.get("/model/profiles")
async def list_profiles(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    profiles = await ModelProfileService(session).list_all()
    return success([ModelProfileService._out(p) for p in profiles], request)


@router.post("/model/profiles")
async def create_profile(
    payload: ProfileCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    p = await ModelProfileService(session).create(payload.model_dump())
    return success(ModelProfileService._out(p), request)


@router.patch("/model/profiles/{profile_id}")
async def update_profile(
    profile_id: str,
    payload: ProfileUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    p = await ModelProfileService(session).update(profile_id, payload.model_dump(exclude_unset=True))
    return success(ModelProfileService._out(p), request)


@router.delete("/model/profiles/{profile_id}")
async def delete_profile(
    profile_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await ModelProfileService(session).delete(profile_id)
    return success({"deleted": True}, request)


@router.delete("/model/profiles/{profile_id}/api-key")
async def clear_profile_api_key(
    profile_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    profile = await ModelProfileService(session).clear_api_key(profile_id)
    return success(ModelProfileService._out(profile), request)


@router.post("/model/profiles/{profile_id}/test")
async def test_profile(
    profile_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await ModelProfileService(session).test(profile_id)
    return success(result, request)


@router.get("/model/providers/{provider}/models")
async def list_provider_models(
    provider: str,
    request: Request,
) -> dict:
    models = ModelProfileService.get_provider_models(provider)
    return success({"provider": provider, "models": models}, request)
