from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models import Base
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
from app.models.project import NovelProject
from app.services.context_builder import ContextBuilder


@pytest.fixture()
async def session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'scene-ordering.db'}",
        future=True,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as active_session:
        yield active_session
    await engine.dispose()


def response_data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


def test_scene_story_time_defaults_follow_narrative_position(
    client: TestClient,
) -> None:
    project = response_data(client.post("/api/projects", json={"title": "Order story"}))
    volume = response_data(
        client.post(
            f"/api/projects/{project['id']}/volumes",
            json={"sequence_no": 1, "title": "Volume"},
        )
    )
    chapter = response_data(
        client.post(
            f"/api/volumes/{volume['id']}/chapters",
            json={"sequence_no": 1, "title": "Chapter"},
        )
    )

    first = response_data(
        client.post(
            f"/api/chapters/{chapter['id']}/scenes",
            json={"sequence_no": 1, "title": "First"},
        )
    )
    second = response_data(
        client.post(
            f"/api/chapters/{chapter['id']}/scenes",
            json={"sequence_no": 2, "title": "Second"},
        )
    )
    flashback = response_data(
        client.post(
            f"/api/chapters/{chapter['id']}/scenes",
            json={
                "sequence_no": 3,
                "title": "Flashback",
                "story_time_order": 1,
            },
        )
    )

    assert first["story_time_order"] == 1
    assert second["story_time_order"] == 2
    assert flashback["story_time_order"] == 1
    assert "timeline_order" not in first


@pytest.mark.asyncio
async def test_previous_scene_uses_narrative_order_across_chapters_and_volumes(
    session: AsyncSession,
) -> None:
    project = NovelProject(title="Cross-volume story")
    session.add(project)
    await session.flush()
    first_volume = Volume(project_id=project.id, sequence_no=1, title="Volume 1")
    second_volume = Volume(project_id=project.id, sequence_no=2, title="Volume 2")
    session.add_all([first_volume, second_volume])
    await session.flush()
    first_chapter = Chapter(
        volume_id=first_volume.id,
        sequence_no=1,
        title="Chapter 1",
    )
    last_chapter = Chapter(
        volume_id=first_volume.id,
        sequence_no=2,
        title="Chapter 2",
    )
    current_chapter = Chapter(
        volume_id=second_volume.id,
        sequence_no=1,
        title="Chapter 3",
    )
    session.add_all([first_chapter, last_chapter, current_chapter])
    await session.flush()
    earlier = Scene(
        chapter_id=first_chapter.id,
        sequence_no=1,
        title="Earlier",
        story_time_order=5,
    )
    previous = Scene(
        chapter_id=last_chapter.id,
        sequence_no=1,
        title="Narrative predecessor",
        story_time_order=5,
    )
    current = Scene(
        chapter_id=current_chapter.id,
        sequence_no=1,
        title="Current",
        story_time_order=2,
    )
    session.add_all([earlier, previous, current])
    await session.flush()
    earlier_version = SceneVersion(
        scene_id=earlier.id,
        version_no=1,
        content_markdown="Earlier content",
    )
    previous_version = SceneVersion(
        scene_id=previous.id,
        version_no=1,
        content_markdown="Previous content",
    )
    session.add_all([earlier_version, previous_version])
    await session.flush()
    earlier.approved_version_id = earlier_version.id
    previous.approved_version_id = previous_version.id
    await session.commit()

    context = await ContextBuilder(session).build_for_scene(current.id)

    assert context.previous_scene is not None
    assert context.previous_scene.scene_id == previous.id
    assert context.previous_scene.content_preview == "Previous content"
