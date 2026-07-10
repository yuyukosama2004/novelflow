from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import ValidationAppError
from app.models import Base
from app.models.bible import CharacterRelationship
from app.models.character import Character, CharacterKnowledge, CharacterState
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
from app.models.memory import MemoryCandidate, TimelineEvent
from app.models.project import NovelProject
from app.models.world import WorldEntry
from app.services.memory_application import MemoryApplicationService


@pytest.fixture()
async def session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'memory-handlers.db'}",
        future=True,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as active_session:
        yield active_session
    await engine.dispose()


async def create_graph(session: AsyncSession) -> dict[str, object]:
    project = NovelProject(title="Handler story", status="active")
    other_project = NovelProject(title="Other story", status="active")
    session.add_all([project, other_project])
    await session.flush()

    first = Character(project_id=project.id, name="Lin", status="active")
    second = Character(project_id=project.id, name="Mei", status="active")
    outsider = Character(project_id=other_project.id, name="Outsider", status="active")
    world = WorldEntry(
        project_id=project.id,
        entry_type="rule",
        name="Old rule",
        canon_status="approved",
    )
    other_world = WorldEntry(
        project_id=other_project.id,
        entry_type="rule",
        name="Other rule",
        canon_status="approved",
    )
    volume = Volume(project_id=project.id, sequence_no=1, title="Volume")
    session.add_all([first, second, outsider, world, other_world, volume])
    await session.flush()

    chapter = Chapter(volume_id=volume.id, sequence_no=1, title="Chapter")
    session.add(chapter)
    await session.flush()
    scene = Scene(
        chapter_id=chapter.id,
        sequence_no=1,
        title="Scene",
        timeline_order=7,
    )
    session.add(scene)
    await session.flush()
    version = SceneVersion(
        scene_id=scene.id,
        version_no=1,
        content_markdown="The story changed.",
    )
    session.add(version)
    await session.flush()
    scene.approved_version_id = version.id
    await session.commit()
    return {
        "project": project,
        "first": first,
        "second": second,
        "outsider": outsider,
        "world": world,
        "other_world": other_world,
        "version": version,
    }


def candidate(
    version: SceneVersion,
    candidate_type: str,
    target_entity_type: str,
    target_entity_id: str | None,
    content_json: dict[str, object],
) -> MemoryCandidate:
    return MemoryCandidate(
        scene_version_id=version.id,
        candidate_type=candidate_type,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        content_json=content_json,
        evidence="Evidence",
        confidence=0.9,
        status="pending",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        "character_state",
        "character_knowledge",
        "timeline_event",
        "relationship_change",
        "world_fact_update",
    ],
)
async def test_memory_handler_applies_idempotently(
    session: AsyncSession,
    case: str,
) -> None:
    graph = await create_graph(session)
    version = graph["version"]
    first = graph["first"]
    second = graph["second"]
    world = graph["world"]
    assert isinstance(version, SceneVersion)
    assert isinstance(first, Character)
    assert isinstance(second, Character)
    assert isinstance(world, WorldEntry)

    if case == "character_state":
        item = candidate(
            version,
            case,
            "character",
            first.id,
            {"emotional_state": "alert", "injuries": {"arm": "bruised"}},
        )
    elif case == "character_knowledge":
        item = candidate(
            version,
            case,
            "character",
            first.id,
            {
                "fact_key": "knows_secret",
                "fact_value_json": {"value": True},
                "knowledge_status": "confirmed",
            },
        )
    elif case == "timeline_event":
        item = candidate(
            version,
            case,
            "scene",
            None,
            {"event_text": "The bell rang.", "affected_character_ids": [first.id]},
        )
    elif case == "relationship_change":
        item = candidate(
            version,
            case,
            "relationship",
            None,
            {
                "character_a_id": first.id,
                "character_b_id": second.id,
                "relation_type": "ally",
                "description": "They agreed to cooperate.",
            },
        )
    else:
        item = candidate(
            version,
            case,
            "world_entry",
            world.id,
            {"name": "New rule", "summary": "Magic now has a cost."},
        )

    service = MemoryApplicationService(session)
    await service.apply(item)
    await session.flush()
    await service.apply(item)
    await session.flush()

    if case == "character_state":
        count = await session.scalar(select(func.count(CharacterState.id)))
        state = (await session.execute(select(CharacterState))).scalar_one()
        assert count == 1
        assert state.emotional_state == "alert"
    elif case == "character_knowledge":
        count = await session.scalar(select(func.count(CharacterKnowledge.id)))
        knowledge = (await session.execute(select(CharacterKnowledge))).scalar_one()
        assert count == 1
        assert knowledge.fact_key == "knows_secret"
    elif case == "timeline_event":
        count = await session.scalar(select(func.count(TimelineEvent.id)))
        event = (await session.execute(select(TimelineEvent))).scalar_one()
        assert count == 1
        assert event.event_text == "The bell rang."
    elif case == "relationship_change":
        count = await session.scalar(select(func.count(CharacterRelationship.id)))
        relationship = (await session.execute(select(CharacterRelationship))).scalar_one()
        assert count == 1
        assert relationship.description == "They agreed to cooperate."
    else:
        refreshed_world = await session.get(WorldEntry, world.id)
        assert refreshed_world is not None
        assert refreshed_world.name == "New rule"
        assert refreshed_world.summary == "Magic now has a cost."
        assert refreshed_world.version == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        "character_state",
        "character_knowledge",
        "timeline_event",
        "relationship_change",
        "world_fact_update",
    ],
)
async def test_memory_handler_rejects_cross_project_targets(
    session: AsyncSession,
    case: str,
) -> None:
    graph = await create_graph(session)
    version = graph["version"]
    first = graph["first"]
    outsider = graph["outsider"]
    other_world = graph["other_world"]
    assert isinstance(version, SceneVersion)
    assert isinstance(first, Character)
    assert isinstance(outsider, Character)
    assert isinstance(other_world, WorldEntry)

    if case == "character_state":
        item = candidate(
            version,
            case,
            "character",
            outsider.id,
            {"emotional_state": "alert"},
        )
    elif case == "character_knowledge":
        item = candidate(
            version,
            case,
            "character",
            outsider.id,
            {"fact_key": "foreign_fact"},
        )
    elif case == "timeline_event":
        item = candidate(
            version,
            case,
            "scene",
            None,
            {"event_text": "Foreign event", "affected_character_ids": [outsider.id]},
        )
    elif case == "relationship_change":
        item = candidate(
            version,
            case,
            "relationship",
            None,
            {
                "character_a_id": first.id,
                "character_b_id": outsider.id,
                "relation_type": "rival",
            },
        )
    else:
        item = candidate(
            version,
            case,
            "world_entry",
            other_world.id,
            {"summary": "Wrong project"},
        )

    with pytest.raises(ValidationAppError):
        await MemoryApplicationService(session).apply(item)
