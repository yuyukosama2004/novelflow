from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import Character, CharacterKnowledge, CharacterState
from app.repositories.base import Repository


class CharacterRepository(Repository[Character]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Character)

    async def list_by_project(self, project_id: str) -> list[Character]:
        return await self.list(
            select(Character).where(Character.project_id == project_id).order_by(Character.name)
        )


class CharacterStateRepository(Repository[CharacterState]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CharacterState)

    async def list_by_character(self, character_id: str) -> list[CharacterState]:
        return await self.list(
            select(CharacterState)
            .where(CharacterState.character_id == character_id)
            .order_by(CharacterState.timeline_order.desc(), CharacterState.created_at.desc())
        )


class CharacterKnowledgeRepository(Repository[CharacterKnowledge]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CharacterKnowledge)

    async def list_by_character(self, character_id: str) -> list[CharacterKnowledge]:
        return await self.list(
            select(CharacterKnowledge)
            .where(CharacterKnowledge.character_id == character_id)
            .order_by(CharacterKnowledge.fact_key)
        )
