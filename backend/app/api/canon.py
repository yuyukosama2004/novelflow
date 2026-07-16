from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.canon.service import CanonService
from app.core.responses import success
from app.database.session import get_session
from app.schemas.canon import CanonCommitRead
from app.services.manuscript_service import ManuscriptService

router = APIRouter()


@router.get("/scenes/{scene_id}/canon-commits")
async def list_scene_canon_commits(
    scene_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await ManuscriptService(session).get_scene(scene_id)
    commits = await CanonService(session).list_scene_commits(scene_id)
    return success([CanonCommitRead.model_validate(item) for item in commits], request)
