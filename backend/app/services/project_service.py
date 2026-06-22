from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.project import NovelProject
from app.repositories.base import apply_updates
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)

    async def create(self, payload: ProjectCreate) -> NovelProject:
        project = NovelProject(**payload.model_dump())
        await self.projects.add(project)
        await self.session.commit()
        return project

    async def list(self) -> list[NovelProject]:
        return await self.projects.list_active()

    async def get(self, project_id: str) -> NovelProject:
        project = await self.projects.get(project_id)
        if project is None or project.status == "archived":
            raise NotFoundError("project not found", {"project_id": project_id})
        return project

    async def update(self, project_id: str, payload: ProjectUpdate) -> NovelProject:
        project = await self.get(project_id)
        apply_updates(project, payload.model_dump(exclude_unset=True))
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def archive(self, project_id: str) -> NovelProject:
        project = await self.get(project_id)
        project.status = "archived"
        await self.session.commit()
        await self.session.refresh(project)
        return project
