"""故事圣经 API：人物关系管理。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.responses import success
from app.database.session import get_session
from app.models.bible import CharacterRelationship
from app.models.character import Character
from app.services.project_service import ProjectService

router = APIRouter()


class RelationshipCreate(BaseModel):
    character_a_id: str
    character_b_id: str
    relation_type: str = "other"
    description: str = ""
    timeline_info: str = ""


class RelationshipUpdate(BaseModel):
    relation_type: str | None = None
    description: str | None = None
    timeline_info: str | None = None
    status: str | None = None


class RelationshipOut(BaseModel):
    id: str
    project_id: str
    character_a_id: str
    character_b_id: str
    relation_type: str
    description: str
    timeline_info: str
    status: str
    created_at: str | None = None
    updated_at: str | None = None

    model_config = {"from_attributes": True}


@router.post("/projects/{project_id}/relationships")
async def create_relationship(
    project_id: str,
    payload: RelationshipCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """创建人物关系。"""
    await ProjectService(session).get(project_id)

    if payload.character_a_id == payload.character_b_id:
        raise ValidationAppError("cannot create self-relationship")

    # 验证两个人物都属于该项目
    char_a = await session.get(Character, payload.character_a_id)
    char_b = await session.get(Character, payload.character_b_id)
    if not char_a or char_a.project_id != project_id:
        raise ValidationAppError("character_a not found in project")
    if not char_b or char_b.project_id != project_id:
        raise ValidationAppError("character_b not found in project")

    rel = CharacterRelationship(
        project_id=project_id,
        character_a_id=payload.character_a_id,
        character_b_id=payload.character_b_id,
        relation_type=payload.relation_type,
        description=payload.description,
        timeline_info=payload.timeline_info,
    )
    session.add(rel)
    await session.commit()
    await session.refresh(rel)

    return success(_out(rel), request)


@router.get("/projects/{project_id}/relationships")
async def list_relationships(
    project_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """列出项目的所有人物关系。"""
    await ProjectService(session).get(project_id)
    result = await session.execute(
        select(CharacterRelationship)
        .where(CharacterRelationship.project_id == project_id)
        .order_by(CharacterRelationship.created_at.desc())
    )
    rels = result.scalars().all()
    return success([_out(r) for r in rels], request)


@router.patch("/relationships/{relationship_id}")
async def update_relationship(
    relationship_id: str,
    payload: RelationshipUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """更新人物关系。"""
    rel = await session.get(CharacterRelationship, relationship_id)
    if rel is None:
        raise NotFoundError("relationship not found", {"relationship_id": relationship_id})

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(rel, key, value)

    await session.commit()
    await session.refresh(rel)
    return success(_out(rel), request)


@router.delete("/relationships/{relationship_id}")
async def delete_relationship(
    relationship_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """删除人物关系。"""
    rel = await session.get(CharacterRelationship, relationship_id)
    if rel is None:
        raise NotFoundError("relationship not found", {"relationship_id": relationship_id})

    await session.delete(rel)
    await session.commit()
    return success({"deleted": True}, request)


def _out(rel: CharacterRelationship) -> dict:
    return {
        "id": rel.id,
        "project_id": rel.project_id,
        "character_a_id": rel.character_a_id,
        "character_b_id": rel.character_b_id,
        "relation_type": rel.relation_type,
        "description": rel.description,
        "timeline_info": rel.timeline_info,
        "status": rel.status,
        "created_at": rel.created_at.isoformat() if rel.created_at else None,
        "updated_at": rel.updated_at.isoformat() if rel.updated_at else None,
    }
