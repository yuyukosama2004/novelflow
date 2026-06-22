from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import NovelProject
from app.repositories.base import Repository


class ProjectRepository(Repository[NovelProject]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, NovelProject)

    async def list_active(self) -> list[NovelProject]:
        return await self.list(
            select(NovelProject)
            .where(NovelProject.status != "archived")
            .order_by(NovelProject.updated_at.desc())
        )
