from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.canon import CanonCommit
from app.models.manuscript import Scene, SceneVersion
from app.models.review import ReviewIssue, ReviewRun


class CanonService:
    """Single write path for authoritative scene-version commits."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_scene_commits(self, scene_id: str) -> list[CanonCommit]:
        result = await self.session.execute(
            select(CanonCommit)
            .where(CanonCommit.scene_id == scene_id)
            .order_by(CanonCommit.sequence_no.desc())
        )
        return list(result.scalars().all())

    async def record_scene_approval(
        self,
        *,
        project_id: str,
        scene: Scene,
        version: SceneVersion,
        review_run: ReviewRun,
        review_issues: list[ReviewIssue],
        override_reason: str | None,
        committed_by: str = "user",
    ) -> CanonCommit:
        existing_result = await self.session.execute(
            select(CanonCommit).where(CanonCommit.scene_version_id == version.id)
        )
        if existing_result.scalar_one_or_none() is not None:
            raise ConflictError(
                "scene version already has a canon commit",
                {
                    "reason": "VERSION_ALREADY_COMMITTED",
                    "scene_version_id": version.id,
                },
            )

        previous_result = await self.session.execute(
            select(CanonCommit)
            .where(CanonCommit.scene_id == scene.id)
            .order_by(CanonCommit.sequence_no.desc())
            .limit(1)
        )
        previous = previous_result.scalar_one_or_none()
        commit = CanonCommit(
            project_id=project_id,
            scene_id=scene.id,
            scene_version_id=version.id,
            previous_commit_id=previous.id if previous else None,
            sequence_no=(previous.sequence_no + 1) if previous else 1,
            content_hash=version.document_hash,
            contract_snapshot_json=self._contract_snapshot(scene),
            review_snapshot_json=self._review_snapshot(review_run, review_issues),
            commit_reason="version_replacement" if previous else "initial_approval",
            override_reason=override_reason,
            committed_by=committed_by,
        )
        self.session.add(commit)
        await self.session.flush()
        return commit

    @staticmethod
    def _contract_snapshot(scene: Scene) -> dict[str, object]:
        return {
            "goal": scene.goal,
            "conflict": scene.conflict,
            "turning_point": scene.turning_point,
            "ending_hook": scene.ending_hook,
            "pov_character_id": scene.pov_character_id,
            "location_id": scene.location_id,
            "time_text": scene.time_text,
            "story_time_order": scene.story_time_order,
            "must_include": list(scene.must_include_json),
            "must_not_reveal": list(scene.must_not_reveal_json),
            "forbidden_actions": list(scene.forbidden_actions_json),
        }

    @staticmethod
    def _review_snapshot(
        review_run: ReviewRun,
        review_issues: list[ReviewIssue],
    ) -> dict[str, object]:
        return {
            "review_run_id": review_run.id,
            "status": review_run.status,
            "summary": review_run.summary,
            "completed_at": (
                review_run.completed_at.isoformat() if review_run.completed_at is not None else None
            ),
            "issues": [
                {
                    "id": issue.id,
                    "type": issue.issue_type,
                    "severity": issue.severity,
                    "status": issue.status,
                    "confidence": issue.confidence,
                }
                for issue in sorted(review_issues, key=lambda item: item.id)
            ],
        }
