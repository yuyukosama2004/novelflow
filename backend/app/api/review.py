from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ReviewExecutionError
from app.core.responses import success
from app.database.session import get_session
from app.llm.router import LLMRouter
from app.models.base import utc_now
from app.models.manuscript import SceneVersion
from app.models.review import ReviewIssue, ReviewRun
from app.schemas.review import (
    ReviewIssueOut,
    ReviewResultOut,
    ReviewRunOut,
    UpdateIssueStatusRequest,
)
from app.services.context_builder import ContextBuilder
from app.services.continuity_reviewer import ContinuityReviewer
from app.services.manuscript_service import ManuscriptService

router = APIRouter()


def review_result(run: ReviewRun, issues: list[ReviewIssue]) -> ReviewResultOut:
    return ReviewResultOut(
        run=ReviewRunOut.model_validate(run),
        issues=[ReviewIssueOut.model_validate(issue) for issue in issues],
    )


@router.post("/scene-versions/{version_id}/review")
async def review_version(
    version_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Run continuity review on a scene version."""
    settings = get_settings()
    manuscript = ManuscriptService(session)
    version = await manuscript.get_version(version_id)

    run = ReviewRun(
        scene_version_id=version.id,
        model_profile_id=version.model_profile_id,
        status="pending",
        prompt_snapshot_json={},
        summary="",
    )
    session.add(run)
    await session.commit()
    run_id = run.id

    try:
        run.status = "running"
        run.started_at = utc_now()
        version.review_status = "running"
        await session.commit()

        builder = ContextBuilder(session)
        ctx = await builder.build_for_scene(version.scene_id)
        reviewer = ContinuityReviewer(LLMRouter(), settings.default_model_provider)
        run.prompt_snapshot_json = {
            "provider": settings.default_model_provider,
            "prompt": reviewer.build_prompt(version, ctx),
        }
        issues = await reviewer.review(version, ctx)

        for issue in issues:
            issue.review_run_id = run.id
            session.add(issue)
        run.status = "completed"
        run.completed_at = utc_now()
        run.summary = f"发现 {len(issues)} 个问题" if issues else "未发现问题"
        version.review_status = "completed"
        await session.commit()
    except Exception:
        await session.rollback()
        failed_run = await session.get(ReviewRun, run_id)
        failed_version = await session.get(SceneVersion, version_id)
        if failed_run is not None:
            failed_run.status = "failed"
            failed_run.completed_at = utc_now()
            failed_run.summary = "审查执行失败"
        if failed_version is not None:
            failed_version.review_status = "failed"
        await session.commit()
        raise ReviewExecutionError("review execution failed", {"review_run_id": run_id}) from None

    return success(review_result(run, issues), request)


@router.get("/scene-versions/{version_id}/review-runs")
async def list_review_runs(
    version_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await ManuscriptService(session).get_version(version_id)
    result = await session.execute(
        select(ReviewRun)
        .where(ReviewRun.scene_version_id == version_id)
        .order_by(ReviewRun.created_at.desc(), ReviewRun.id.desc())
    )
    return success(
        [ReviewRunOut.model_validate(run) for run in result.scalars().all()],
        request,
    )


@router.get("/review-runs/{run_id}")
async def get_review_run(
    run_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    run = await session.get(ReviewRun, run_id)
    if run is None:
        raise NotFoundError("review run not found", {"review_run_id": run_id})
    result = await session.execute(
        select(ReviewIssue)
        .where(ReviewIssue.review_run_id == run_id)
        .order_by(ReviewIssue.severity.desc(), ReviewIssue.confidence.desc())
    )
    return success(review_result(run, list(result.scalars().all())), request)


@router.get("/scene-versions/{version_id}/issues")
async def list_issues(
    version_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List issues from the latest review run for compatibility."""
    await ManuscriptService(session).get_version(version_id)
    run_result = await session.execute(
        select(ReviewRun)
        .where(ReviewRun.scene_version_id == version_id)
        .order_by(ReviewRun.created_at.desc(), ReviewRun.id.desc())
        .limit(1)
    )
    run = run_result.scalar_one_or_none()
    if run is None:
        return success([], request)
    issue_result = await session.execute(
        select(ReviewIssue)
        .where(ReviewIssue.review_run_id == run.id)
        .order_by(ReviewIssue.severity.desc(), ReviewIssue.confidence.desc())
    )
    issues = issue_result.scalars().all()
    return success([ReviewIssueOut.model_validate(i) for i in issues], request)


@router.patch("/issues/{issue_id}")
async def update_issue_status(
    issue_id: str,
    payload: UpdateIssueStatusRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Update an issue status (accept/ignore/false_positive)."""
    issue = await session.get(ReviewIssue, issue_id)
    if issue is None:
        raise NotFoundError("review issue not found", {"issue_id": issue_id})
    if payload.status not in ("accepted", "ignored", "false_positive"):
        from app.core.exceptions import ValidationAppError

        raise ValidationAppError("invalid status", {"status": payload.status})
    issue.status = payload.status
    await session.commit()
    return success(ReviewIssueOut.model_validate(issue), request)
