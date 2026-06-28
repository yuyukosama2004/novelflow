"""大纲生成服务：LLM 根据项目圣经信息生成卷/章/场景结构。

生成结果以候选项形式返回，不直接写入数据库。用户确认后通过 apply 写入。
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.llm.base import LLMMessage, LLMRequest
from app.llm.router import LLMRouter
from app.models.character import Character
from app.models.manuscript import Chapter, Scene, Volume
from app.models.project import NovelProject
from app.models.world import WorldEntry
from app.services.project_service import ProjectService
from app.services.structured_output import generate_json_array

OUTLINE_SYSTEM_PROMPT = (
    "你是一位小说结构设计师，负责根据已有的故事设定生成大纲结构。\n\n"
    "规则：\n"
    "1. 根据项目设定（类型/基调/主题/人物/世界观）设计卷-章-场景三层结构。\n"
    "2. 每卷有明确的目标和主题。\n"
    "3. 每章推进一条关键情节线。\n"
    "4. 每个场景有具体的目标、冲突和转折点。\n"
    "5. 场景之间要有因果链。\n"
    "6. 卷数控制在 1-3 卷（可后续扩展），每卷 2-4 章，每章 2-4 个场景。\n"
    "7. 输出纯 JSON 数组，不要 Markdown 代码块。"
)


class OutlineScene(BaseModel):
    sequence_no: int
    title: str = ""
    goal: str = ""
    conflict: str = ""
    turning_point: str = ""
    ending_hook: str = ""


class OutlineChapter(BaseModel):
    sequence_no: int
    title: str = ""
    summary: str = ""
    goal: str = ""
    scenes: list[OutlineScene] = Field(default_factory=list)


class OutlineVolume(BaseModel):
    sequence_no: int
    title: str = ""
    summary: str = ""
    goal: str = ""
    chapters: list[OutlineChapter] = Field(default_factory=list)


class OutlineService:
    """大纲生成服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.llm = LLMRouter()
        self.settings = get_settings()

    async def generate_outline(self, project_id: str) -> list[dict]:
        """根据项目圣经信息生成大纲候选。"""
        await ProjectService(self.session).get(project_id)

        # 收集项目信息
        project = await self.session.get(NovelProject, project_id)

        characters = (await self.session.execute(
            select(Character).where(Character.project_id == project_id, Character.status == "active")
        )).scalars().all()

        world_entries = (await self.session.execute(
            select(WorldEntry).where(
                WorldEntry.project_id == project_id,
                WorldEntry.canon_status == "approved",
            )
        )).scalars().all()

        # 构建 prompt
        info_parts = ["## 项目设定"]
        if project:
            info_parts.append(f"书名：{project.title or '未设定'}")
            info_parts.append(f"类型：{project.genre or '未设定'}")
            info_parts.append(f"基调：{project.tone or '未设定'}")
            info_parts.append(f"视角：{project.pov_type or '未设定'}")
            info_parts.append(f"梗概：{project.summary or '暂无'}")

        if characters:
            info_parts.append("\n## 人物")
            for ch in characters:
                info_parts.append(
                    f"- {ch.name}（{ch.role}）：欲望={ch.core_desire or '?'}，"
                    f"恐惧={ch.core_fear or '?'}，背景={ch.background[:80] if ch.background else '?'}"
                )

        if world_entries:
            info_parts.append("\n## 世界观")
            for we in world_entries:
                info_parts.append(f"- [{we.entry_type}] {we.name}：{we.summary}")

        info_parts.append("\n请根据以上设定生成大纲结构。")

        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=OUTLINE_SYSTEM_PROMPT),
                LLMMessage(role="user", content="\n".join(info_parts)),
            ],
            max_tokens=4096,
            temperature=0.7,
        )

        volumes = await generate_json_array(
            self.llm, self.settings.default_model_provider, request, OutlineVolume,
        )

        return [
            {
                "sequence_no": v.sequence_no,
                "title": v.title,
                "summary": v.summary,
                "goal": v.goal,
                "chapters": [
                    {
                        "sequence_no": c.sequence_no,
                        "title": c.title,
                        "summary": c.summary,
                        "goal": c.goal,
                        "scenes": [
                            {
                                "sequence_no": s.sequence_no,
                                "title": s.title,
                                "goal": s.goal,
                                "conflict": s.conflict,
                                "turning_point": s.turning_point,
                                "ending_hook": s.ending_hook,
                            }
                            for s in c.scenes
                        ],
                    }
                    for c in v.chapters
                ],
            }
            for v in volumes
        ]

    async def apply_outline(self, project_id: str, outline: list[dict]) -> dict:
        """将确认的大纲批量写入数据库。"""
        await ProjectService(self.session).get(project_id)

        created = {"volumes": 0, "chapters": 0, "scenes": 0}

        for vol_data in outline:
            volume = Volume(
                project_id=project_id,
                sequence_no=vol_data["sequence_no"],
                title=vol_data.get("title", f"第{vol_data['sequence_no']}卷"),
                summary=vol_data.get("summary", ""),
                goal=vol_data.get("goal", ""),
            )
            self.session.add(volume)
            await self.session.flush()
            created["volumes"] += 1

            for ch_data in vol_data.get("chapters", []):
                chapter = Chapter(
                    volume_id=volume.id,
                    sequence_no=ch_data["sequence_no"],
                    title=ch_data.get("title", f"第{ch_data['sequence_no']}章"),
                    summary=ch_data.get("summary", ""),
                    goal=ch_data.get("goal", ""),
                )
                self.session.add(chapter)
                await self.session.flush()
                created["chapters"] += 1

                for sc_data in ch_data.get("scenes", []):
                    scene = Scene(
                        chapter_id=chapter.id,
                        sequence_no=sc_data["sequence_no"],
                        title=sc_data.get("title", f"场景{sc_data['sequence_no']}"),
                        goal=sc_data.get("goal", ""),
                        conflict=sc_data.get("conflict", ""),
                        turning_point=sc_data.get("turning_point", ""),
                        ending_hook=sc_data.get("ending_hook", ""),
                        status="planned",
                        timeline_order=sc_data["sequence_no"],
                    )
                    self.session.add(scene)
                    created["scenes"] += 1

        await self.session.commit()
        return created
