from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.world import WorldEntry
from app.repositories.base import apply_updates
from app.repositories.world_repository import WorldEntryRepository
from app.schemas.world import WorldEntryCreate, WorldEntryUpdate
from app.services.project_service import ProjectService


class WorldService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.world_entries = WorldEntryRepository(session)

    async def create(self, project_id: str, payload: WorldEntryCreate) -> WorldEntry:
        await ProjectService(self.session).get(project_id)
        entry = WorldEntry(project_id=project_id, **payload.model_dump())
        await self.world_entries.add(entry)
        await self.session.commit()
        return entry

    async def list_by_project(self, project_id: str) -> list[WorldEntry]:
        await ProjectService(self.session).get(project_id)
        return await self.world_entries.list_by_project(project_id)

    async def get(self, entry_id: str) -> WorldEntry:
        entry = await self.world_entries.get(entry_id)
        if entry is None:
            raise NotFoundError("world entry not found", {"entry_id": entry_id})
        return entry

    async def update(self, entry_id: str, payload: WorldEntryUpdate) -> WorldEntry:
        entry = await self.get(entry_id)
        apply_updates(entry, payload.model_dump(exclude_unset=True))
        entry.version += 1
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def delete(self, entry_id: str) -> None:
        await self.get(entry_id)
        await self.world_entries.delete(entry_id)
        await self.session.commit()

    _valid_statuses = {"draft", "candidate", "approved", "deprecated", "conflicted"}

    async def set_status(self, entry_id: str, status: str) -> WorldEntry:
        if status not in self._valid_statuses:
            raise ValidationAppError(
                "invalid canon status",
                {"status": status, "valid": list(self._valid_statuses)},
            )
        entry = await self.get(entry_id)
        entry.canon_status = status
        entry.version += 1
        await self.session.commit()
        await self.session.refresh(entry)
        return entry
