"""大纲生成 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.database.session import get_session
from app.services.outline_service import OutlineService

router = APIRouter()


class ApplyOutlineRequest(BaseModel):
    outline: list[dict]


class GenerateOutlineRequest(BaseModel):
    model_profile_id: str | None = None


@router.post("/projects/{project_id}/generate-outline")
async def generate_outline(
    project_id: str,
    request: Request,
    payload: GenerateOutlineRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """根据项目圣经信息生成大纲（卷/章/场景草案）。不直接写入数据库。"""
    outline = await OutlineService(session).generate_outline(
        project_id,
        payload.model_profile_id if payload else None,
    )
    return success(outline, request)


@router.post("/projects/{project_id}/apply-outline")
async def apply_outline(
    project_id: str,
    payload: ApplyOutlineRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """将确认的大纲批量写入数据库。"""
    result = await OutlineService(session).apply_outline(project_id, payload.outline)
    return success(result, request)
