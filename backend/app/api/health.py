from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.responses import success
from app.database.session import get_session

router = APIRouter(prefix="/health")


@router.get("")
async def health(request: Request, session: AsyncSession = Depends(get_session)) -> dict:
    await session.execute(text("select 1"))
    settings = get_settings()
    return success(
        {
            "status": "ok",
            "database": "ok",
            "version": settings.app_version,
            "models": settings.model_configuration_status,
        },
        request,
    )
