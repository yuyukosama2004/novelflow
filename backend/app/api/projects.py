from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.database.session import get_session
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects")


@router.post("")
async def create_project(
    payload: ProjectCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    project = await ProjectService(session).create(payload)
    return success(ProjectRead.model_validate(project), request)


@router.get("")
async def list_projects(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    projects = await ProjectService(session).list()
    return success([ProjectRead.model_validate(project) for project in projects], request)


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    project = await ProjectService(session).get(project_id)
    return success(ProjectRead.model_validate(project), request)


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    project = await ProjectService(session).update(project_id, payload)
    return success(ProjectRead.model_validate(project), request)


@router.delete("/{project_id}")
async def archive_project(
    project_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    project = await ProjectService(session).archive(project_id)
    return success(ProjectRead.model_validate(project), request)
