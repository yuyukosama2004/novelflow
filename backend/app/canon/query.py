from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canon import CanonCommit
from app.models.manuscript import SceneVersion


@dataclass(frozen=True)
class CanonSceneVersion:
    commit: CanonCommit
    version: SceneVersion


class CanonQueryService:
    """Read the current official manuscript from the Canon ledger."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_scene_version(self, scene_id: str) -> CanonSceneVersion | None:
        latest_sequence = (
            select(func.max(CanonCommit.sequence_no))
            .where(CanonCommit.scene_id == scene_id)
            .scalar_subquery()
        )
        result = await self.session.execute(
            select(CanonCommit, SceneVersion)
            .join(SceneVersion, SceneVersion.id == CanonCommit.scene_version_id)
            .where(
                CanonCommit.scene_id == scene_id,
                CanonCommit.sequence_no == latest_sequence,
            )
        )
        row = result.one_or_none()
        if row is None:
            return None
        return CanonSceneVersion(commit=row[0], version=row[1])

    async def latest_versions_for_scenes(
        self,
        scene_ids: list[str],
    ) -> dict[str, CanonSceneVersion]:
        if not scene_ids:
            return {}
        latest = (
            select(
                CanonCommit.scene_id.label("scene_id"),
                func.max(CanonCommit.sequence_no).label("sequence_no"),
            )
            .where(CanonCommit.scene_id.in_(scene_ids))
            .group_by(CanonCommit.scene_id)
            .subquery()
        )
        result = await self.session.execute(
            select(CanonCommit, SceneVersion)
            .join(
                latest,
                and_(
                    latest.c.scene_id == CanonCommit.scene_id,
                    latest.c.sequence_no == CanonCommit.sequence_no,
                ),
            )
            .join(SceneVersion, SceneVersion.id == CanonCommit.scene_version_id)
        )
        return {
            commit.scene_id: CanonSceneVersion(commit=commit, version=version)
            for commit, version in result.all()
        }
