from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.responses import success
from app.database.session import get_session
from app.llm.router import LLMRouter
from app.models.review import ReviewIssue
from app.services.context_builder import ContextBuilder
from app.services.continuity_reviewer import ContinuityReviewer
from app.services.manuscript_service import ManuscriptService

router = APIRouter()


class ReviewIssueOut(BaseModel):
    id: str
    scene_version_id: str
    issue_type: str
    severity: str
    evidence_json: str
    conflict_rule: str
    suggestion: str
    confidence: float
    status: str

    model_config = {"from_attributes": True}


class UpdateIssueStatusRequest(BaseModel):
    status: str  # accepted | ignored | false_positive


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

    builder = ContextBuilder(session)
    ctx = await builder.build_for_scene(version.scene_id)

    reviewer = ContinuityReviewer(LLMRouter(), settings.default_model_provider)
    issues = await reviewer.review(version, ctx)

    for issue in issues:
        session.add(issue)
    await session.commit()

    return success([ReviewIssueOut.model_validate(i) for i in issues], request)


@router.get("/scene-versions/{version_id}/issues")
async def list_issues(
    version_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List review issues for a scene version."""
    from sqlalchemy import select

    result = await session.execute(
        select(ReviewIssue)
        .where(ReviewIssue.scene_version_id == version_id)
        .order_by(ReviewIssue.severity.desc(), ReviewIssue.confidence.desc())
    )
    issues = result.scalars().all()
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
