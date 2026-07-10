"""创作访谈 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.database.session import get_session
from app.services.interview_service import InterviewService

router = APIRouter()


class StartSessionRequest(BaseModel):
    entry_type: str  # idea | world | character | outline | direct
    title: str = ""
    model_profile_id: str | None = None


class SendMessageRequest(BaseModel):
    content: str


class UpdateCandidateRequest(BaseModel):
    status: str | None = None  # pending | approved | rejected
    content_json: dict | None = None


@router.post("/projects/{project_id}/interview/start")
async def start_interview(
    project_id: str,
    payload: StartSessionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """开始创作访谈会话。"""
    result = await InterviewService(session).start_session(
        project_id,
        payload.entry_type,
        payload.title,
        payload.model_profile_id,
    )
    return success(result, request)


@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: str,
    payload: SendMessageRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """发送消息到访谈会话，获取 LLM 回复。"""
    result = await InterviewService(session).send_message(
        session_id,
        payload.content,
    )
    return success(result, request)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """获取访谈会话详情。"""
    result = await InterviewService(session).get_session(session_id)
    return success(result, request)


@router.post("/sessions/{session_id}/extract-candidates")
async def extract_candidates(
    session_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """从访谈对话中提取结构化候选。"""
    candidates = await InterviewService(session).extract_candidates(session_id)
    return success(candidates, request)


@router.get("/sessions/{session_id}/candidates")
async def list_candidates(
    session_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """列出会话的所有候选。"""
    candidates = await InterviewService(session).list_candidates(session_id)
    return success(candidates, request)


@router.patch("/story-candidates/{candidate_id}")
async def update_candidate(
    candidate_id: str,
    payload: UpdateCandidateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """更新候选状态或内容。"""
    result = await InterviewService(session).update_candidate(
        candidate_id,
        status=payload.status,
        content_json=payload.content_json,
    )
    return success(result, request)


@router.post("/story-candidates/{candidate_id}/apply")
async def apply_candidate(
    candidate_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """将已批准的候选应用到实际实体。"""
    result = await InterviewService(session).apply_candidate(candidate_id)
    return success(result, request)
