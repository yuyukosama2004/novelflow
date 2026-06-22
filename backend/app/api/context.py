from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.database.session import get_session
from app.services.context_builder import ContextBuilder

router = APIRouter()


class PreviousSceneOut(BaseModel):
    scene_id: str
    title: str
    version_no: int
    content_preview: str

    model_config = {"from_attributes": True}


class CharacterCardOut(BaseModel):
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

    model_config = {"from_attributes": True}


class WorldFactOut(BaseModel):
    id: str
    name: str
    entry_type: str
    summary: str
    content: str

    model_config = {"from_attributes": True}


class SceneContextOut(BaseModel):
    previous_scene: PreviousSceneOut | None
    characters: list[CharacterCardOut]
    world_facts: list[WorldFactOut]
    manifest: dict

    model_config = {"from_attributes": True}


@router.get("/scenes/{scene_id}/context")
async def get_scene_context(
    scene_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    builder = ContextBuilder(session)
    ctx = await builder.build_for_scene(scene_id)
    return success(
        SceneContextOut(
            previous_scene=(
                PreviousSceneOut(
                    scene_id=ctx.previous_scene.scene_id,
                    title=ctx.previous_scene.title,
                    version_no=ctx.previous_scene.version_no,
                    content_preview=ctx.previous_scene.content_preview,
                )
                if ctx.previous_scene
                else None
            ),
            characters=[
                CharacterCardOut(
                    id=c.id,
                    name=c.name,
                    role=c.role,
                    public_identity=c.public_identity,
                    speech_style=c.speech_style,
                    decision_pattern=c.decision_pattern,
                    core_desire=c.core_desire,
                    core_fear=c.core_fear,
                    forbidden_behaviors=c.forbidden_behaviors,
                    current_state=c.current_state,
                    knowledge_known=c.knowledge_known,
                    knowledge_unknown=c.knowledge_unknown,
                )
                for c in ctx.characters
            ],
            world_facts=[
                WorldFactOut(
                    id=w.id,
                    name=w.name,
                    entry_type=w.entry_type,
                    summary=w.summary,
                    content=w.content,
                )
                for w in ctx.world_facts
            ],
            manifest=ctx.manifest,
        ),
        request,
    )
