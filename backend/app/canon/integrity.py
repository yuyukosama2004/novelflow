from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.canon.hashing import scene_version_content_hash
from app.models.base import utc_now
from app.models.canon import CanonCommit
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume


@dataclass(frozen=True)
class CanonIntegrityIssue:
    code: str
    scene_id: str
    commit_id: str | None
    details: dict[str, Any]


@dataclass(frozen=True)
class CanonIntegrityReport:
    project_id: str
    status: str
    checked_scenes: int
    checked_commits: int
    issues: list[CanonIntegrityIssue]
    audited_at: datetime


class CanonIntegrityService:
    """Compare the compatibility projection with the immutable canon ledger."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def audit_project(self, project_id: str) -> CanonIntegrityReport:
        scene_result = await self.session.execute(
            select(Scene)
            .join(Chapter, Scene.chapter_id == Chapter.id)
            .join(Volume, Chapter.volume_id == Volume.id)
            .where(Volume.project_id == project_id)
            .order_by(Scene.id)
        )
        scenes = list(scene_result.scalars().all())
        scene_by_id = {scene.id: scene for scene in scenes}
        scene_ids = set(scene_by_id)

        commit_scope = CanonCommit.project_id == project_id
        if scene_ids:
            commit_scope = or_(commit_scope, CanonCommit.scene_id.in_(scene_ids))
        commit_result = await self.session.execute(
            select(CanonCommit).where(commit_scope).order_by(CanonCommit.scene_id, CanonCommit.sequence_no)
        )
        commits = list(commit_result.scalars().all())

        version_ids = {
            version_id
            for version_id in (
                [commit.scene_version_id for commit in commits]
                + [scene.approved_version_id for scene in scenes]
            )
            if version_id is not None
        }
        if version_ids:
            version_result = await self.session.execute(
                select(SceneVersion).where(SceneVersion.id.in_(version_ids))
            )
            version_by_id = {version.id: version for version in version_result.scalars().all()}
        else:
            version_by_id = {}

        commits_by_scene: dict[str, list[CanonCommit]] = defaultdict(list)
        for commit in commits:
            commits_by_scene[commit.scene_id].append(commit)

        issues: list[CanonIntegrityIssue] = []
        for scene in scenes:
            history = commits_by_scene.get(scene.id, [])
            issues.extend(
                self._audit_scene(
                    project_id=project_id,
                    scene=scene,
                    commits=history,
                    version_by_id=version_by_id,
                )
            )

        for scene_id, history in commits_by_scene.items():
            if scene_id not in scene_by_id:
                issues.append(
                    CanonIntegrityIssue(
                        code="COMMIT_SCENE_MISSING",
                        scene_id=scene_id,
                        commit_id=history[-1].id,
                        details={"commit_count": len(history)},
                    )
                )

        return CanonIntegrityReport(
            project_id=project_id,
            status="ok" if not issues else "drift",
            checked_scenes=len(scenes),
            checked_commits=len(commits),
            issues=issues,
            audited_at=utc_now(),
        )

    @staticmethod
    def _audit_scene(
        *,
        project_id: str,
        scene: Scene,
        commits: list[CanonCommit],
        version_by_id: dict[str, SceneVersion],
    ) -> list[CanonIntegrityIssue]:
        issues: list[CanonIntegrityIssue] = []
        if scene.approved_version_id is None:
            if commits:
                issues.append(
                    CanonIntegrityIssue(
                        code="ORPHAN_CANON_HISTORY",
                        scene_id=scene.id,
                        commit_id=commits[-1].id,
                        details={"commit_count": len(commits)},
                    )
                )
        elif not commits:
            issues.append(
                CanonIntegrityIssue(
                    code="SCENE_COMMIT_MISSING",
                    scene_id=scene.id,
                    commit_id=None,
                    details={"approved_version_id": scene.approved_version_id},
                )
            )
        elif commits[-1].scene_version_id != scene.approved_version_id:
            issues.append(
                CanonIntegrityIssue(
                    code="PROJECTION_VERSION_MISMATCH",
                    scene_id=scene.id,
                    commit_id=commits[-1].id,
                    details={
                        "approved_version_id": scene.approved_version_id,
                        "latest_commit_version_id": commits[-1].scene_version_id,
                    },
                )
            )

        previous: CanonCommit | None = None
        for expected_sequence, commit in enumerate(commits, start=1):
            expected_previous_id = previous.id if previous is not None else None
            if commit.sequence_no != expected_sequence:
                issues.append(
                    CanonIntegrityIssue(
                        code="COMMIT_SEQUENCE_GAP",
                        scene_id=scene.id,
                        commit_id=commit.id,
                        details={
                            "expected_sequence_no": expected_sequence,
                            "actual_sequence_no": commit.sequence_no,
                        },
                    )
                )
            if commit.previous_commit_id != expected_previous_id:
                issues.append(
                    CanonIntegrityIssue(
                        code="COMMIT_PREVIOUS_MISMATCH",
                        scene_id=scene.id,
                        commit_id=commit.id,
                        details={
                            "expected_previous_commit_id": expected_previous_id,
                            "actual_previous_commit_id": commit.previous_commit_id,
                        },
                    )
                )
            if commit.project_id != project_id:
                issues.append(
                    CanonIntegrityIssue(
                        code="COMMIT_PROJECT_MISMATCH",
                        scene_id=scene.id,
                        commit_id=commit.id,
                        details={
                            "expected_project_id": project_id,
                            "actual_project_id": commit.project_id,
                        },
                    )
                )

            version = version_by_id.get(commit.scene_version_id)
            if version is None:
                issues.append(
                    CanonIntegrityIssue(
                        code="COMMIT_VERSION_MISSING",
                        scene_id=scene.id,
                        commit_id=commit.id,
                        details={"scene_version_id": commit.scene_version_id},
                    )
                )
            else:
                if version.scene_id != scene.id:
                    issues.append(
                        CanonIntegrityIssue(
                            code="COMMIT_VERSION_SCENE_MISMATCH",
                            scene_id=scene.id,
                            commit_id=commit.id,
                            details={
                                "expected_scene_id": scene.id,
                                "actual_scene_id": version.scene_id,
                            },
                        )
                    )
                actual_hash = scene_version_content_hash(
                    version.content_json,
                    version.content_markdown,
                )
                if actual_hash != version.document_hash:
                    issues.append(
                        CanonIntegrityIssue(
                            code="DOCUMENT_HASH_MISMATCH",
                            scene_id=scene.id,
                            commit_id=commit.id,
                            details={
                                "stored_hash": version.document_hash,
                                "actual_hash": actual_hash,
                                "scene_version_id": version.id,
                            },
                        )
                    )
                if actual_hash != commit.content_hash:
                    issues.append(
                        CanonIntegrityIssue(
                            code="COMMIT_HASH_MISMATCH",
                            scene_id=scene.id,
                            commit_id=commit.id,
                            details={
                                "expected_hash": commit.content_hash,
                                "actual_hash": actual_hash,
                                "stored_document_hash": version.document_hash,
                            },
                        )
                    )
            previous = commit

        return issues
