"""AI summaries used to identify scene versions without exposing their opening text."""

from __future__ import annotations

import re

from app.llm.base import LLMMessage, LLMRequest
from app.services.model_runtime import ModelRuntime

MAX_SUMMARY_LENGTH = 16


def build_version_summary_request(content: str, model: str) -> LLMRequest:
    return LLMRequest(
        messages=[
            LLMMessage(
                role="system",
                content=(
                    "你是中文小说编辑。请只输出这版正文的内容梗概，"
                    "控制在 12 到 16 个汉字，不使用引号、前缀、标点、评价或解释。"
                ),
            ),
            LLMMessage(role="user", content=content),
        ],
        model=model,
        max_tokens=80,
        temperature=0.2,
    )


def normalize_version_summary(value: str) -> str:
    summary = re.sub(r"\s+", "", value).strip("“”\"'。；;：:")
    summary = re.sub(r"^(?:内容)?(?:梗概|摘要)[:：]", "", summary)
    return summary[:MAX_SUMMARY_LENGTH]


async def generate_version_summary(runtime: ModelRuntime, content: str) -> str:
    """Generate a compact Chinese synopsis from the final version body."""
    if not content.strip():
        return ""
    response = await runtime.router.generate(
        build_version_summary_request(content, runtime.model),
        provider=runtime.provider,
    )
    return normalize_version_summary(response.content)
