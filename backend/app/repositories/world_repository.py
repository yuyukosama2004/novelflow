from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.world import WorldEntry
from app.repositories.base import Repository


class WorldEntryRepository(Repository[WorldEntry]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WorldEntry)

    async def list_by_project(self, project_id: str) -> list[WorldEntry]:
        return await self.list(
            select(WorldEntry).where(WorldEntry.project_id == project_id).order_by(WorldEntry.name)
        )
