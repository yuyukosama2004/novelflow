from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.character import Character, CharacterKnowledge, CharacterState
from app.repositories.base import apply_updates
from app.repositories.character_repository import (
    CharacterKnowledgeRepository,
    CharacterRepository,
    CharacterStateRepository,
)
from app.schemas.character import (
    CharacterCreate,
    CharacterKnowledgeCreate,
    CharacterStateCreate,
    CharacterUpdate,
)
from app.services.project_service import ProjectService


class CharacterService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.characters = CharacterRepository(session)
        self.states = CharacterStateRepository(session)
        self.knowledge = CharacterKnowledgeRepository(session)

    async def create(self, project_id: str, payload: CharacterCreate) -> Character:
        await ProjectService(self.session).get(project_id)
        character = Character(project_id=project_id, **payload.model_dump())
        await self.characters.add(character)
        await self.session.commit()
        return character

    async def list_by_project(self, project_id: str) -> list[Character]:
        await ProjectService(self.session).get(project_id)
        return await self.characters.list_by_project(project_id)

    async def get(self, character_id: str) -> Character:
        character = await self.characters.get(character_id)
        if character is None:
            raise NotFoundError("character not found", {"character_id": character_id})
        return character

    async def update(self, character_id: str, payload: CharacterUpdate) -> Character:
        character = await self.get(character_id)
        apply_updates(character, payload.model_dump(exclude_unset=True))
        character.version += 1
        await self.session.commit()
        await self.session.refresh(character)
        return character

    async def delete(self, character_id: str) -> None:
        await self.get(character_id)
        await self.characters.delete(character_id)
        await self.session.commit()

    async def create_state(
        self,
        character_id: str,
        payload: CharacterStateCreate,
    ) -> CharacterState:
        await self.get(character_id)
        state = CharacterState(character_id=character_id, **payload.model_dump())
        await self.states.add(state)
        await self.session.commit()
        return state

    async def list_states(self, character_id: str) -> list[CharacterState]:
        await self.get(character_id)
        return await self.states.list_by_character(character_id)

    async def current_state(
        self,
        character_id: str,
        timeline_order: int | None = None,
    ) -> CharacterState | None:
        """获取人物当前最新已确认状态，可选限制时间线位置。

        与 ContextBuilder._current_state() 使用相同的过滤逻辑：
        只返回 status=confirmed 的状态，按 timeline_order DESC 取最新。
        """
        await self.get(character_id)

        conditions = [
            CharacterState.character_id == character_id,
            CharacterState.status == "confirmed",
        ]
        if timeline_order is not None:
            conditions.append(CharacterState.timeline_order <= timeline_order)

        result = await self.session.execute(
            select(CharacterState)
            .where(*conditions)
            .order_by(
                CharacterState.timeline_order.desc(),
                CharacterState.created_at.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_knowledge(
        self,
        character_id: str,
        payload: CharacterKnowledgeCreate,
    ) -> CharacterKnowledge:
        await self.get(character_id)
        item = CharacterKnowledge(character_id=character_id, **payload.model_dump())
        await self.knowledge.add(item)
        await self.session.commit()
        return item

    async def list_knowledge(self, character_id: str) -> list[CharacterKnowledge]:
        await self.get(character_id)
        return await self.knowledge.list_by_character(character_id)
