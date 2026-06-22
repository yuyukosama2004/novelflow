from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.database.session import get_session
from app.schemas.character import (
    CharacterCreate,
    CharacterKnowledgeCreate,
    CharacterKnowledgeRead,
    CharacterRead,
    CharacterStateCreate,
    CharacterStateRead,
    CharacterUpdate,
)
from app.services.character_service import CharacterService

router = APIRouter()


@router.post("/projects/{project_id}/characters")
async def create_character(
    project_id: str,
    payload: CharacterCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    character = await CharacterService(session).create(project_id, payload)
    return success(CharacterRead.model_validate(character), request)


@router.get("/projects/{project_id}/characters")
async def list_characters(
    project_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    characters = await CharacterService(session).list_by_project(project_id)
    return success([CharacterRead.model_validate(item) for item in characters], request)


@router.get("/characters/{character_id}")
async def get_character(
    character_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    character = await CharacterService(session).get(character_id)
    return success(CharacterRead.model_validate(character), request)


@router.patch("/characters/{character_id}")
async def update_character(
    character_id: str,
    payload: CharacterUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    character = await CharacterService(session).update(character_id, payload)
    return success(CharacterRead.model_validate(character), request)


@router.delete("/characters/{character_id}")
async def delete_character(
    character_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await CharacterService(session).delete(character_id)
    return success({"deleted": True}, request)


@router.post("/characters/{character_id}/states")
async def create_character_state(
    character_id: str,
    payload: CharacterStateCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    state = await CharacterService(session).create_state(character_id, payload)
    return success(CharacterStateRead.model_validate(state), request)


@router.get("/characters/{character_id}/states")
async def list_character_states(
    character_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    states = await CharacterService(session).list_states(character_id)
    return success([CharacterStateRead.model_validate(item) for item in states], request)


@router.get("/characters/{character_id}/current-state")
async def current_character_state(
    character_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    state = await CharacterService(session).current_state(character_id)
    return success(CharacterStateRead.model_validate(state) if state else None, request)


@router.post("/characters/{character_id}/knowledge")
async def create_character_knowledge(
    character_id: str,
    payload: CharacterKnowledgeCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    item = await CharacterService(session).create_knowledge(character_id, payload)
    return success(CharacterKnowledgeRead.model_validate(item), request)


@router.get("/characters/{character_id}/knowledge")
async def list_character_knowledge(
    character_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    items = await CharacterService(session).list_knowledge(character_id)
    return success([CharacterKnowledgeRead.model_validate(item) for item in items], request)
