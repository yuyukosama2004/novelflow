from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.character import Character, CharacterKnowledge, CharacterState
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
from app.models.world import WorldEntry


@dataclass
class CharacterCard:
    id: str
    name: str
    role: str
    public_identity: str
    speech_style: str
    decision_pattern: str
    core_desire: str
    core_fear: str
    forbidden_behaviors: list[str]
    current_state: dict | None
    knowledge_known: list[str]
    knowledge_unknown: list[str]


@dataclass
class WorldFact:
    id: str
    name: str
    entry_type: str
    summary: str
    content: str


@dataclass
class PreviousScene:
    scene_id: str
    title: str
    version_no: int
    content_preview: str


@dataclass
class SceneContext:
    current_scene: Scene
    previous_scene: PreviousScene | None
    characters: list[CharacterCard] = field(default_factory=list)
    world_facts: list[WorldFact] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)


class ContextBuilder:
    """Assembles deterministic scene context from database.

    Never uses LLM to decide SQL or what to include.
    Always filters: approved world entries, confirmed character states.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def build_for_scene(self, scene_id: str) -> SceneContext:
        # Eager-load scene with chapter -> volume to avoid async lazy-load
        result = await self.session.execute(
            select(Scene)
            .options(selectinload(Scene.chapter).selectinload(Chapter.volume))
            .where(Scene.id == scene_id)
        )
        scene = result.scalar_one_or_none()
        if scene is None:
            raise ValueError(f"Scene {scene_id} not found")

        project_id = scene.chapter.volume.project_id

        # Previous scene follows narrative order across chapters and volumes.
        prev = await self._prev_scene(scene)

        # Characters in this project
        characters = await self._character_cards(
            project_id,
            scene,
        )

        # Approved world entries
        world_facts = await self._approved_world(project_id)

        manifest = {
            "scene_id": scene_id,
            "scene_title": scene.title,
            "scene_goal": scene.goal,
            "scene_conflict": scene.conflict,
            "pov_character_id": scene.pov_character_id,
            "time_text": scene.time_text,
            "must_include": scene.must_include_json,
            "must_not_reveal": scene.must_not_reveal_json,
            "forbidden_actions": scene.forbidden_actions_json,
            "character_count": len(characters),
            "world_fact_count": len(world_facts),
            "has_previous_scene": prev is not None,
        }

        token_estimate = await self._estimate_tokens(scene, prev, characters, world_facts)
        manifest["token_estimate"] = token_estimate

        return SceneContext(
            current_scene=scene,
            previous_scene=prev,
            characters=characters,
            world_facts=world_facts,
            manifest=manifest,
        )

    async def _prev_scene(self, current_scene: Scene) -> PreviousScene | None:
        current_chapter = current_scene.chapter
        current_volume = current_chapter.volume
        result = await self.session.execute(
            select(Scene)
            .join(Chapter, Scene.chapter_id == Chapter.id)
            .join(Volume, Chapter.volume_id == Volume.id)
            .where(
                Volume.project_id == current_volume.project_id,
                Scene.approved_version_id.isnot(None),
                or_(
                    Volume.sequence_no < current_volume.sequence_no,
                    and_(
                        Volume.sequence_no == current_volume.sequence_no,
                        Chapter.sequence_no < current_chapter.sequence_no,
                    ),
                    and_(
                        Volume.sequence_no == current_volume.sequence_no,
                        Chapter.sequence_no == current_chapter.sequence_no,
                        Scene.sequence_no < current_scene.sequence_no,
                    ),
                ),
            )
            .order_by(
                Volume.sequence_no.desc(),
                Chapter.sequence_no.desc(),
                Scene.sequence_no.desc(),
            )
            .limit(1)
        )
        prev_scene = result.scalar_one_or_none()
        if prev_scene is None or prev_scene.approved_version_id is None:
            return None

        prev_version = await self.session.get(SceneVersion, prev_scene.approved_version_id)
        if prev_version is None:
            return None

        return PreviousScene(
            scene_id=prev_scene.id,
            title=prev_scene.title,
            version_no=prev_version.version_no,
            content_preview=(prev_version.content_markdown[:500] + "...")
            if len(prev_version.content_markdown) > 500
            else prev_version.content_markdown,
        )

    async def _character_cards(
        self,
        project_id: str,
        current_scene: Scene,
    ) -> list[CharacterCard]:
        result = await self.session.execute(
            select(Character).where(
                Character.project_id == project_id,
                Character.status == "active",
            )
        )
        characters = result.scalars().all()

        cards: list[CharacterCard] = []
        for ch in characters:
            state = await self._current_state(ch.id, current_scene.story_time_order)
            known, unknown = await self._knowledge_boundaries(
                ch.id,
                current_scene,
            )
            cards.append(
                CharacterCard(
                    id=ch.id,
                    name=ch.name,
                    role=ch.role,
                    public_identity=ch.public_identity,
                    speech_style=ch.speech_style,
                    decision_pattern=ch.decision_pattern,
                    core_desire=ch.core_desire,
                    core_fear=ch.core_fear,
                    forbidden_behaviors=ch.forbidden_behaviors_json,
                    current_state=state,
                    knowledge_known=known,
                    knowledge_unknown=unknown,
                )
            )
        return cards

    async def _current_state(
        self,
        character_id: str,
        timeline_order: int,
    ) -> dict | None:
        result = await self.session.execute(
            select(CharacterState)
            .where(
                CharacterState.character_id == character_id,
                CharacterState.status == "confirmed",
                CharacterState.timeline_order <= timeline_order,
            )
            .order_by(
                CharacterState.timeline_order.desc(),
                CharacterState.created_at.desc(),
            )
            .limit(1)
        )
        state = result.scalar_one_or_none()
        if state is None:
            return None
        return {
            "emotional_state": state.emotional_state,
            "current_goal": state.current_goal,
            "current_pressure": state.current_pressure,
            "injuries": state.injuries_json,
            "physical_state": state.physical_state_json,
        }

    async def _knowledge_boundaries(
        self,
        character_id: str,
        current_scene: Scene,
    ) -> tuple[list[str], list[str]]:
        current_chapter = current_scene.chapter
        current_volume = current_chapter.volume
        result = await self.session.execute(
            select(CharacterKnowledge)
            .outerjoin(
                SceneVersion,
                CharacterKnowledge.learned_at_scene_version_id == SceneVersion.id,
            )
            .outerjoin(Scene, SceneVersion.scene_id == Scene.id)
            .outerjoin(Chapter, Scene.chapter_id == Chapter.id)
            .outerjoin(Volume, Chapter.volume_id == Volume.id)
            .where(
                CharacterKnowledge.character_id == character_id,
                or_(
                    CharacterKnowledge.learned_at_scene_version_id.is_(None),
                    Scene.story_time_order < current_scene.story_time_order,
                    and_(
                        Scene.story_time_order == current_scene.story_time_order,
                        or_(
                            Volume.sequence_no < current_volume.sequence_no,
                            and_(
                                Volume.sequence_no == current_volume.sequence_no,
                                Chapter.sequence_no < current_chapter.sequence_no,
                            ),
                            and_(
                                Volume.sequence_no == current_volume.sequence_no,
                                Chapter.sequence_no == current_chapter.sequence_no,
                                Scene.sequence_no <= current_scene.sequence_no,
                            ),
                        ),
                    ),
                ),
            )
        )
        items = result.scalars().all()
        known: list[str] = []
        unknown: list[str] = []
        for item in items:
            if item.knowledge_status in (
                "suspected",
                "believed",
                "confirmed",
                "misunderstood",
            ):
                known.append(item.fact_key)
            else:
                unknown.append(item.fact_key)
        return known, unknown

    async def _approved_world(self, project_id: str) -> list[WorldFact]:
        result = await self.session.execute(
            select(WorldEntry).where(
                WorldEntry.project_id == project_id,
                WorldEntry.canon_status == "approved",
            )
        )
        entries = result.scalars().all()
        return [
            WorldFact(
                id=e.id,
                name=e.name,
                entry_type=e.entry_type,
                summary=e.summary,
                content=e.content,
            )
            for e in entries
        ]

    async def _estimate_tokens(
        self,
        scene: Scene,
        prev: PreviousScene | None,
        characters: list[CharacterCard],
        world_facts: list[WorldFact],
    ) -> int:
        chars = 0
        chars += len(scene.goal or "")
        chars += len(scene.conflict or "")
        chars += sum(len(s) for s in scene.must_include_json)
        chars += sum(len(s) for s in scene.must_not_reveal_json)
        chars += sum(len(s) for s in scene.forbidden_actions_json)

        if prev:
            chars += len(prev.content_preview)

        for ch in characters:
            chars += len(ch.public_identity or "")
            chars += len(ch.speech_style or "")
            chars += len(ch.core_desire or "")
            chars += len(ch.core_fear or "")
            chars += sum(len(s) for s in ch.forbidden_behaviors)
            chars += sum(len(s) for s in ch.knowledge_known)
            chars += sum(len(s) for s in ch.knowledge_unknown)

        for wf in world_facts:
            chars += len(wf.summary or "")
            chars += len(wf.content or "")

        return int(chars / 2.5)
