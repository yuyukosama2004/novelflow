from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.session import get_session
from app.main import app
from app.models import Base


@pytest.fixture()
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture()
def client(database_path: Path) -> Iterator[TestClient]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}", future=True)

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session() -> AsyncIterator[Any]:
        async with maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

    async def dispose() -> None:
        await engine.dispose()

    asyncio.run(dispose())
