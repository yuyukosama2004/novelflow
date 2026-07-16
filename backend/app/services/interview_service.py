"""访谈服务：会话管理、LLM 访谈、候选提取与应用。

LLM 作为访谈者，提问帮助作者打磨故事设定，而不是替作者直接定稿。
所有 LLM 产出以 StoryCandidate 形式保存，需作者确认后才写入正式实体。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.llm.base import LLMMessage, LLMRequest
from app.models.character import Character
from app.models.interview import InterviewSession, StoryCandidate
from app.models.manuscript import Chapter, Scene, Volume
from app.models.project import NovelProject
from app.models.world import WorldEntry
from app.services.model_runtime import ModelRuntime, ModelRuntimeResolver
from app.services.project_service import ProjectService
from app.services.structured_output import generate_json_array

# ── 访谈入口 Prompt ──

ENTRY_SYSTEM_PROMPTS: dict[str, str] = {
    "idea": (
        "你是一位经验丰富的小说编辑，正在帮助一位作者把一个故事创意发展成完整的故事概念。\n\n"
        "你的职责是提问和整理，不是替作者写故事。\n\n"
        "规则：\n"
        "1. 每次回复最多问 2-3 个有具体指向的问题。\n"
        "2. 聚焦于：核心冲突、主角动机、世界观规则、故事钩子、情感核心。\n"
        "3. 当作者的创意有漏洞或矛盾时，温和地指出并询问。\n"
        "4. 不要替作者做决定，给出选项让作者选择。\n"
        "5. 在对话末尾偶尔用一两句话总结你目前理解的故事轮廓。\n"
        "6. 用中文对话。"
    ),
    "world": (
        "你是一位世界观设定顾问，正在帮助一位作者从世界观出发构建故事。\n\n"
        "你的职责是提问和指出设定中的潜在冲突，不是替作者写世界观。\n\n"
        "规则：\n"
        "1. 每次回复最多问 2-3 个有具体指向的问题。\n"
        "2. 聚焦于：世界规则的代价和例外、不同群体/角色的利益冲突、历史事件的遗留影响、禁忌的边界。\n"
        "3. 追问「这个规则对谁最不公平」「打破规则会发生什么」等具体问题。\n"
        "4. 帮助作者从世界观中挖掘故事冲突。\n"
        "5. 在对话末尾偶尔总结目前已讨论的世界规则和潜在冲突。\n"
        "6. 用中文对话。"
    ),
    "character": (
        "你是一位人物塑造顾问，正在帮助一位作者从人物出发构建故事。\n\n"
        "你的职责是深入挖掘人物，不是替作者写人设。\n\n"
        "规则：\n"
        "1. 每次回复最多问 2-3 个有具体指向的问题。\n"
        "2. 聚焦于：欲望与恐惧的冲突、核心谎言与真相、关系网中的张力、成长弧线的关键节点。\n"
        "3. 追问「这个角色为什么想要这个」「他/她害怕失去什么」「谁是他的对立面」\n"
        "4. 帮助作者从人物欲望和恐惧中引出故事冲突。\n"
        "5. 在对话末尾偶尔总结目前已讨论的人物轮廓和潜在故事线。\n"
        "6. 用中文对话。"
    ),
    "outline": (
        "你是一位故事结构顾问，正在帮助一位作者完善已有的大纲。\n\n"
        "你的职责是检查结构完整性，不是替作者重写大纲。\n\n"
        "规则：\n"
        "1. 每次回复最多问 2-3 个有具体指向的问题。\n"
        "2. 聚焦于：因果链是否合理、信息释放节奏、高潮设计、各条线的收束、人物动机是否成立。\n"
        "3. 追问「这个转折的铺垫在哪里」「读者到这一章应该知道什么」\n"
        "4. 帮助作者发现大纲中的薄弱环节和逻辑漏洞。\n"
        "5. 在对话末尾偶尔总结目前讨论的结构问题和建议。\n"
        "6. 用中文对话。"
    ),
    "direct": (
        "作者选择直接开始写正文。\n"
        "你的职责是快速确认基本信息后结束访谈，引导作者进入写作工作台。\n\n"
        "规则：\n"
        "1. 只问最关键的信息：书名、类型、视角、基调。\n"
        "2. 如果作者已提供，简短确认后引导进入工作台。\n"
        "3. 不超过 3 轮对话。\n"
        "4. 用中文对话。"
    ),
}

ENTRY_TITLES: dict[str, str] = {
    "idea": "点子创作访谈",
    "world": "世界观创作访谈",
    "character": "人物创作访谈",
    "outline": "大纲创作访谈",
    "direct": "快速开始",
}

WORKSPACE_DISCUSSION_PROMPT = (
    "你是小说创作讨论伙伴，不是自动写稿工具。你正在帮助作者打磨一本正在创作的中文小说。\n\n"
    "规则：\n"
    "1. 用中文讨论，先分析作者的问题，再给可选择的建议；不要擅自把建议写入项目。\n"
    "2. 优先尊重全书既有的人称、文风、人物限制和场景卡；发现冲突时明确指出。\n"
    "3. 可以提出书名、场景卡和重写方向，但须说明它们只是候选，等待作者确认。\n"
    "4. 每次回复尽量包含可执行的下一步，避免空泛鼓励和长篇正文。\n"
    "5. 不要宣称建议已成为正史；只有作者点击“应用”才会写入项目。"
)

WORKSPACE_EXTRACT_PROMPT = (
    "从以下创作讨论中提取作者要求或明确认可的可应用候选。只输出 JSON 数组，不要 Markdown。\n"
    "每项包含 candidate_type、title、content_json、proposal、confidence。candidate_type 只能是：\n"
    "- project_setting：content_json 可含 title、summary、genre、tone；\n"
    "- scene_card：content_json 必含 scene_id，可含 title、goal、conflict、turning_point、ending_hook；\n"
    "- rewrite_instruction：content_json 必含 instruction，用于填入一次重写要求，绝不直接改正文。\n"
    "只提取有依据的建议；不要把助手未经作者确认的猜测伪装成事实。"
)

EXTRACT_SYSTEM_PROMPT = (
    "你是一位小说编辑，现在需要从一段创作访谈对话中提取作者已确认的设定，"
    "整理成结构化的候选条目。\n\n"
    "规则：\n"
    "1. 只提取作者在对话中明确同意或自己提出的内容，不要提取你作为访谈者的建议。\n"
    "2. 每个候选必须能在对话中找到依据。\n"
    "3. 输出一个 JSON 数组，每个元素包含：\n"
    '  - candidate_type: "project_setting" | "character" | "world_entry"\n'
    "  - title: 简短标题\n"
    "  - content_json: 具体内容（取决于 candidate_type）\n"
    "  - proposal: 从对话中提取的依据和理由\n"
    "  - confidence: 0.0-1.0 的置信度\n"
    "4. project_setting 的 content_json 包含：title(书名), summary(简介), genre(类型), tone(基调), theme(主题)\n"
    "5. character 的 content_json 包含：name(姓名), role(身份), core_desire(核心欲望), core_fear(核心恐惧), background(背景)\n"
    "6. world_entry 的 content_json 包含：name(名称), entry_type(类型), summary(摘要), content(详细内容)\n"
    "7. 如果没有足够的信息提取某个类型的候选，就不要凭空编造。\n"
    "8. 不要使用 Markdown 代码块，直接输出纯 JSON 数组。"
)


class InterviewService:
    """创作访谈服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── 会话管理 ──

    async def start_session(
        self,
        project_id: str,
        entry_type: str,
        title: str = "",
        model_profile_id: str | None = None,
    ) -> dict:
        """创建访谈会话并返回初始 LLM 消息。"""
        # 验证项目存在
        await ProjectService(self.session).get(project_id)

        if entry_type not in ENTRY_SYSTEM_PROMPTS:
            raise ValidationAppError(
                "invalid entry type",
                {"entry_type": entry_type, "valid": list(ENTRY_SYSTEM_PROMPTS)},
            )

        system_prompt = ENTRY_SYSTEM_PROMPTS[entry_type]
        session_title = title or ENTRY_TITLES.get(entry_type, "创作访谈")
        runtime = await ModelRuntimeResolver(self.session).resolve(
            project_id,
            model_profile_id,
        )

        # 构建初始 LLM 消息
        initial_message = await self._llm_first_message(
            entry_type,
            system_prompt,
            project_id,
            runtime,
        )

        session = InterviewSession(
            project_id=project_id,
            model_profile_id=runtime.profile_id,
            provider=runtime.provider,
            model=runtime.model,
            entry_type=entry_type,
            title=session_title,
            status="active",
            messages_json=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "assistant",
                    "content": initial_message,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            ],
        )
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)

        return {
            "id": session.id,
            "project_id": session.project_id,
            "model_profile_id": session.model_profile_id,
            "provider": session.provider,
            "model": session.model,
            "entry_type": session.entry_type,
            "title": session.title,
            "status": session.status,
            "messages": session.messages_json,
        }

    async def start_workspace_discussion(
        self,
        project_id: str,
        scene_id: str | None,
        model_profile_id: str | None = None,
    ) -> dict:
        """Create a persisted, project/scene-aware discussion without canonical writes."""
        project = await ProjectService(self.session).get(project_id)
        scene: Scene | None = None
        if scene_id:
            scene = await self._scene_in_project(project_id, scene_id)
        runtime = await ModelRuntimeResolver(self.session).resolve(
            project_id,
            model_profile_id,
        )
        scope = (
            f"当前场景：{scene.title}\n场景目标：{scene.goal or '未填写'}\n"
            f"场景冲突：{scene.conflict or '未填写'}\n场景转折：{scene.turning_point or '未填写'}\n"
            if scene
            else "当前范围：全书讨论。\n"
        )
        project_profile = (
            f"项目：{project.title}\n人称：{project.pov_type}\n"
            f"文风：{project.writing_style_preset}\n基调：{project.tone or '未填写'}\n"
        )
        system_prompt = f"{WORKSPACE_DISCUSSION_PROMPT}\n\n{project_profile}{scope}"
        greeting = (
            f"我会围绕{'当前场景' if scene else '全书'}和既有写作设置与你讨论。"
            "我给出的内容都只是候选；你可以在下方提取建议，再明确决定是否应用。"
        )
        discussion = InterviewSession(
            project_id=project_id,
            model_profile_id=runtime.profile_id,
            provider=runtime.provider,
            model=runtime.model,
            entry_type=self._workspace_entry_type(scene_id),
            title=f"{'场景' if scene else '全书'}讨论：{scene.title if scene else project.title}",
            status="active",
            messages_json=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "assistant",
                    "content": greeting,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            ],
        )
        self.session.add(discussion)
        await self.session.commit()
        await self.session.refresh(discussion)
        return self._session_out(discussion)

    async def list_workspace_discussions(self, project_id: str, scene_id: str | None) -> list[dict]:
        await ProjectService(self.session).get(project_id)
        result = await self.session.execute(
            select(InterviewSession)
            .where(
                InterviewSession.project_id == project_id,
                InterviewSession.entry_type == self._workspace_entry_type(scene_id),
            )
            .order_by(InterviewSession.updated_at.desc())
        )
        return [self._session_out(item) for item in result.scalars().all()]

    async def send_message(self, session_id: str, content: str) -> dict:
        """发送用户消息，获取 LLM 回复。"""
        session_obj = await self._get_session(session_id)
        runtime = await ModelRuntimeResolver(self.session).resolve(
            session_obj.project_id,
            session_obj.model_profile_id,
        )

        if session_obj.status != "active":
            raise ConflictError(
                "session is not active",
                {"session_id": session_id, "status": session_obj.status},
            )

        # 添加用户消息
        session_obj.messages_json.append(
            {
                "role": "user",
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # 调用 LLM
        llm_messages = [LLMMessage(role=m["role"], content=m["content"]) for m in session_obj.messages_json]
        response = await runtime.router.generate(
            LLMRequest(
                messages=llm_messages,
                model=runtime.model,
                max_tokens=1024,
                temperature=0.8,
            ),
            provider=runtime.provider,
        )

        # 添加 LLM 回复
        session_obj.messages_json.append(
            {
                "role": "assistant",
                "content": response.content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        await self.session.commit()
        await self.session.refresh(session_obj)

        return {
            "id": session_obj.id,
            "model_profile_id": session_obj.model_profile_id,
            "provider": session_obj.provider,
            "model": session_obj.model,
            "messages": session_obj.messages_json,
        }

    async def get_session(self, session_id: str) -> dict:
        """获取会话详情。"""
        session_obj = await self._get_session(session_id)
        return {
            "id": session_obj.id,
            "project_id": session_obj.project_id,
            "model_profile_id": session_obj.model_profile_id,
            "provider": session_obj.provider,
            "model": session_obj.model,
            "entry_type": session_obj.entry_type,
            "title": session_obj.title,
            "status": session_obj.status,
            "messages": session_obj.messages_json,
        }

    # ── 候选提取 ──

    async def extract_candidates(self, session_id: str) -> list[dict]:
        """从访谈对话中提取结构化候选。"""
        session_obj = await self._get_session(session_id)
        runtime = await ModelRuntimeResolver(self.session).resolve(
            session_obj.project_id,
            session_obj.model_profile_id,
        )

        if session_obj.entry_type.startswith("workspace:"):
            return await self._extract_workspace_candidates(session_obj, runtime)

        # 构建提取请求
        conversation_text = "\n".join(f"{m['role']}: {m['content']}" for m in session_obj.messages_json)

        llm_messages = [
            LLMMessage(role="system", content=EXTRACT_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=f"请从以下创作访谈中提取候选设定：\n\n{conversation_text}",
            ),
        ]

        from pydantic import BaseModel, Field

        class CandidateItem(BaseModel):
            candidate_type: str
            title: str
            content_json: dict
            proposal: str = ""
            confidence: float = Field(ge=0.0, le=1.0)

        items = await generate_json_array(
            runtime.router,
            runtime.provider,
            LLMRequest(
                messages=llm_messages,
                model=runtime.model,
                max_tokens=2048,
                temperature=0.4,
            ),
            CandidateItem,
        )

        # 保存候选
        candidates = []
        for item in items:
            candidate = StoryCandidate(
                project_id=session_obj.project_id,
                session_id=session_id,
                candidate_type=item.candidate_type,
                title=item.title,
                content_json=item.content_json,
                proposal=item.proposal,
                confidence=item.confidence,
                status="pending",
            )
            self.session.add(candidate)
            candidates.append(candidate)

        await self.session.commit()
        for c in candidates:
            await self.session.refresh(c)

        return [self._candidate_out(c) for c in candidates]

    async def list_candidates(self, session_id: str) -> list[dict]:
        """列出会话的所有候选。"""
        await self._get_session(session_id)
        result = await self.session.execute(
            select(StoryCandidate)
            .where(StoryCandidate.session_id == session_id)
            .order_by(StoryCandidate.created_at.desc())
        )
        return [self._candidate_out(c) for c in result.scalars().all()]

    async def update_candidate(
        self,
        candidate_id: str,
        status: str | None = None,
        content_json: dict | None = None,
    ) -> dict:
        """更新候选状态或内容。"""
        candidate = await self._get_candidate(candidate_id)

        if status:
            if status not in ("pending", "approved", "rejected"):
                raise ValidationAppError(
                    "invalid candidate status",
                    {"status": status},
                )
            candidate.status = status

        if content_json is not None:
            candidate.content_json = content_json

        await self.session.commit()
        await self.session.refresh(candidate)
        return self._candidate_out(candidate)

    async def apply_candidate(self, candidate_id: str) -> dict:
        """将批准的候选应用到实际实体。"""
        candidate = await self._get_candidate(candidate_id)

        if candidate.status != "approved":
            raise ConflictError(
                "only approved candidates can be applied",
                {"candidate_id": candidate_id, "status": candidate.status},
            )

        if candidate.applied_entity_id:
            raise ConflictError(
                "candidate already applied",
                {"candidate_id": candidate_id, "applied_entity_id": candidate.applied_entity_id},
            )

        entity_type, entity_id = await self._apply(candidate)

        candidate.applied_entity_type = entity_type
        candidate.applied_entity_id = entity_id
        await self.session.commit()
        await self.session.refresh(candidate)

        return self._candidate_out(candidate)

    # ── 内部方法 ──

    async def _get_session(self, session_id: str) -> InterviewSession:
        session_obj = await self.session.get(InterviewSession, session_id)
        if session_obj is None:
            raise NotFoundError("interview session not found", {"session_id": session_id})
        return session_obj

    @staticmethod
    def _workspace_entry_type(scene_id: str | None) -> str:
        return f"workspace:{scene_id or 'project'}"

    async def _scene_in_project(self, project_id: str, scene_id: str) -> Scene:
        result = await self.session.execute(
            select(Scene)
            .join(Chapter, Scene.chapter_id == Chapter.id)
            .join(Volume, Chapter.volume_id == Volume.id)
            .where(Scene.id == scene_id, Volume.project_id == project_id)
        )
        scene = result.scalar_one_or_none()
        if scene is None:
            raise NotFoundError("scene not found in project", {"scene_id": scene_id})
        return scene

    async def _extract_workspace_candidates(
        self, session_obj: InterviewSession, runtime: ModelRuntime
    ) -> list[dict]:
        from pydantic import BaseModel, Field

        class WorkspaceCandidate(BaseModel):
            candidate_type: str
            title: str
            content_json: dict
            proposal: str = ""
            confidence: float = Field(ge=0.0, le=1.0)

        scene_id = session_obj.entry_type.removeprefix("workspace:")
        if scene_id == "project":
            scene_id = ""
        conversation = "\n".join(
            f"{message['role']}: {message['content']}"
            for message in session_obj.messages_json
            if message["role"] != "system"
        )
        items = await generate_json_array(
            runtime.router,
            runtime.provider,
            LLMRequest(
                messages=[
                    LLMMessage(role="system", content=WORKSPACE_EXTRACT_PROMPT),
                    LLMMessage(
                        role="user",
                        content=f"当前 scene_id：{scene_id or '无（全书讨论）'}\n\n讨论记录：\n{conversation}",
                    ),
                ],
                model=runtime.model,
                max_tokens=1600,
                temperature=0.3,
            ),
            WorkspaceCandidate,
        )
        allowed_types = {"project_setting", "scene_card", "rewrite_instruction"}
        candidates: list[StoryCandidate] = []
        for item in items:
            if item.candidate_type not in allowed_types:
                continue
            content = dict(item.content_json)
            if item.candidate_type == "scene_card":
                if not scene_id:
                    continue
                content["scene_id"] = scene_id
            if item.candidate_type == "rewrite_instruction" and not content.get("instruction"):
                continue
            candidate = StoryCandidate(
                project_id=session_obj.project_id,
                session_id=session_obj.id,
                candidate_type=item.candidate_type,
                title=item.title,
                content_json=content,
                proposal=item.proposal,
                confidence=item.confidence,
                status="pending",
            )
            self.session.add(candidate)
            candidates.append(candidate)
        await self.session.commit()
        for candidate in candidates:
            await self.session.refresh(candidate)
        return [self._candidate_out(candidate) for candidate in candidates]

    async def _get_candidate(self, candidate_id: str) -> StoryCandidate:
        candidate = await self.session.get(StoryCandidate, candidate_id)
        if candidate is None:
            raise NotFoundError("candidate not found", {"candidate_id": candidate_id})
        return candidate

    async def _llm_first_message(
        self,
        entry_type: str,
        system_prompt: str,
        project_id: str,
        runtime: ModelRuntime,
    ) -> str:
        """生成访谈的第一条消息（LLM 发起对话）。"""
        # 获取项目基本信息
        project = await self.session.get(NovelProject, project_id)
        project_info = ""
        if project:
            project_info = (
                f"当前项目：{project.title}，类型：{project.genre or '未设定'}，"
                f"视角：{project.pov_type or '未设定'}，基调：{project.tone or '未设定'}。"
            )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(
                role="user",
                content=(
                    f"你好！我要开始创作了。{project_info}请根据我选择的创作入口，"
                    f"先问我第一个问题来了解我的故事。不要一次问太多，保持对话节奏。"
                ),
            ),
        ]

        response = await runtime.router.generate(
            LLMRequest(
                messages=messages,
                model=runtime.model,
                max_tokens=512,
                temperature=0.8,
            ),
            provider=runtime.provider,
        )
        return response.content

    async def _apply(self, candidate: StoryCandidate) -> tuple[str, str]:
        """将候选写入实际实体。"""
        content = candidate.content_json

        if candidate.candidate_type == "project_setting":
            project = await self.session.get(NovelProject, candidate.project_id)
            if project is None:
                raise NotFoundError("project not found", {"project_id": candidate.project_id})

            updates: dict[str, Any] = {}
            if "title" in content and content["title"]:
                updates["title"] = content["title"]
            if "summary" in content and content["summary"]:
                updates["summary"] = content["summary"]
            if "genre" in content and content["genre"]:
                updates["genre"] = content["genre"]
            if "tone" in content and content["tone"]:
                updates["tone"] = content["tone"]

            for key, value in updates.items():
                setattr(project, key, value)

            self.session.add(project)
            await self.session.flush()
            return "project", project.id

        if candidate.candidate_type == "character":
            character = Character(
                project_id=candidate.project_id,
                name=content.get("name", candidate.title),
                role=content.get("role", ""),
                core_desire=content.get("core_desire", ""),
                core_fear=content.get("core_fear", ""),
                background=content.get("background", ""),
                status="active",
            )
            self.session.add(character)
            await self.session.flush()
            return "character", character.id

        if candidate.candidate_type == "world_entry":
            entry = WorldEntry(
                project_id=candidate.project_id,
                name=content.get("name", candidate.title),
                entry_type=content.get("entry_type", "custom"),
                summary=content.get("summary", ""),
                content=content.get("content", ""),
                canon_status="draft",
            )
            self.session.add(entry)
            await self.session.flush()
            return "world_entry", entry.id

        if candidate.candidate_type == "scene_card":
            scene_id = str(content.get("scene_id", ""))
            scene = await self._scene_in_project(candidate.project_id, scene_id)
            for field in ("title", "goal", "conflict", "turning_point", "ending_hook"):
                value = content.get(field)
                if isinstance(value, str) and value.strip():
                    setattr(scene, field, value.strip())
            self.session.add(scene)
            await self.session.flush()
            return "scene", scene.id

        raise ValidationAppError(
            "unsupported candidate type for apply",
            {"candidate_type": candidate.candidate_type},
        )

    @staticmethod
    def _session_out(session_obj: InterviewSession) -> dict:
        return {
            "id": session_obj.id,
            "project_id": session_obj.project_id,
            "model_profile_id": session_obj.model_profile_id,
            "provider": session_obj.provider,
            "model": session_obj.model,
            "entry_type": session_obj.entry_type,
            "title": session_obj.title,
            "status": session_obj.status,
            "messages": session_obj.messages_json,
        }

    @staticmethod
    def _candidate_out(candidate: StoryCandidate) -> dict:
        return {
            "id": candidate.id,
            "project_id": candidate.project_id,
            "session_id": candidate.session_id,
            "candidate_type": candidate.candidate_type,
            "title": candidate.title,
            "content_json": candidate.content_json,
            "proposal": candidate.proposal,
            "confidence": candidate.confidence,
            "status": candidate.status,
            "applied_entity_type": candidate.applied_entity_type,
            "applied_entity_id": candidate.applied_entity_id,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            "updated_at": candidate.updated_at.isoformat() if candidate.updated_at else None,
        }
