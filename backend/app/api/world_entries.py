from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.database.session import get_session
from app.schemas.world import WorldEntryCreate, WorldEntryRead, WorldEntryUpdate
from app.services.world_service import WorldService

router = APIRouter()


@router.post("/projects/{project_id}/world-entries")
async def create_world_entry(
    project_id: str,
    payload: WorldEntryCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    entry = await WorldService(session).create(project_id, payload)
    return success(WorldEntryRead.model_validate(entry), request)


@router.get("/projects/{project_id}/world-entries")
async def list_world_entries(
    project_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    entries = await WorldService(session).list_by_project(project_id)
    return success([WorldEntryRead.model_validate(item) for item in entries], request)


@router.get("/world-entries/{entry_id}")
async def get_world_entry(
    entry_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    entry = await WorldService(session).get(entry_id)
    return success(WorldEntryRead.model_validate(entry), request)


@router.patch("/world-entries/{entry_id}")
async def update_world_entry(
    entry_id: str,
    payload: WorldEntryUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    entry = await WorldService(session).update(entry_id, payload)
    return success(WorldEntryRead.model_validate(entry), request)


@router.delete("/world-entries/{entry_id}")
async def delete_world_entry(
    entry_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await WorldService(session).delete(entry_id)
    return success({"deleted": True}, request)


@router.post("/world-entries/{entry_id}/approve")
async def approve_world_entry(
    entry_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    entry = await WorldService(session).set_status(entry_id, "approved")
    return success(WorldEntryRead.model_validate(entry), request)


@router.post("/world-entries/{entry_id}/deprecate")
async def deprecate_world_entry(
    entry_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    entry = await WorldService(session).set_status(entry_id, "deprecated")
    return success(WorldEntryRead.model_validate(entry), request)
