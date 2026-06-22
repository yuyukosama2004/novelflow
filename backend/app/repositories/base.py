from __future__ import annotations

from typing import Any, Generic, TypeVar, cast

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    async def get(self, item_id: str) -> ModelT | None:
        return await self.session.get(self.model, item_id)

    async def list(self, statement: Select[tuple[ModelT]] | None = None) -> list[ModelT]:
        active_statement = select(self.model) if statement is None else statement
        result = await self.session.execute(active_statement)
        return list(result.scalars().all())

    async def add(self, item: ModelT) -> ModelT:
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def delete(self, item_id: str) -> None:
        id_column = cast(Any, self.model).id
        await self.session.execute(delete(self.model).where(id_column == item_id))


def apply_updates(model: Any, values: dict[str, Any]) -> None:
    for key, value in values.items():
        setattr(model, key, value)
