from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import request_id_from, success
from app.database.session import get_session
from app.services.export_service import ExportService

router = APIRouter(prefix="/projects/{project_id}/exports")


@router.get("/markdown")
async def export_markdown(
    project_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> PlainTextResponse:
    markdown = await ExportService(session).markdown(project_id)
    return PlainTextResponse(
        markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"x-request-id": request_id_from(request)},
    )


@router.get("/json")
async def export_json(
    project_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    backup = await ExportService(session).backup_json(project_id)
    return success(backup, request)
