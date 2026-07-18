from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.database.session import get_session
from app.schemas.changeset import (
    ChangeSetApplyRead,
    ChangeSetApplyRequest,
    ChangeSetCreate,
    ChangeSetRead,
)
from app.schemas.manuscript import SceneWorkingDraftRead
from app.services.changeset_service import ChangeSetService

router = APIRouter()


@router.post("/scenes/{scene_id}/change-sets")
async def create_change_set(
    scene_id: str,
    payload: ChangeSetCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    value = await ChangeSetService(session).create(scene_id, payload)
    return success(ChangeSetRead.model_validate(value), request)


@router.get("/scenes/{scene_id}/change-sets")
async def list_change_sets(
    scene_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    values = await ChangeSetService(session).list_for_scene(scene_id)
    return success([ChangeSetRead.model_validate(item) for item in values], request)


@router.get("/change-sets/{change_set_id}")
async def get_change_set(
    change_set_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    value = await ChangeSetService(session).get(change_set_id)
    return success(ChangeSetRead.model_validate(value), request)


@router.post("/change-sets/{change_set_id}/apply")
async def apply_change_set(
    change_set_id: str,
    payload: ChangeSetApplyRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    change_set, draft = await ChangeSetService(session).apply(change_set_id, payload)
    return success(
        ChangeSetApplyRead(
            change_set=ChangeSetRead.model_validate(change_set),
            draft=SceneWorkingDraftRead.model_validate(draft) if draft is not None else None,
        ),
        request,
    )
