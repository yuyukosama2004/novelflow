from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.database.session import AsyncSessionLocal
from app.models.character import Character, CharacterKnowledge, CharacterState
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
from app.models.model_profile import ModelProfile
from app.models.project import NovelProject
from app.models.world import WorldEntry


async def main() -> None:
    async with AsyncSessionLocal() as session:
        # 从 .env 创建默认模型配置
        settings = get_settings()
        existing_profile = await session.execute(
            select(ModelProfile).where(ModelProfile.is_default.is_(True))
        )
        if existing_profile.scalar_one_or_none() is None:
            profile = ModelProfile(
                name="默认 DeepSeek",
                provider="deepseek",
                base_url=settings.deepseek_base_url,
                api_key=settings.deepseek_api_key,
                model_name="deepseek-chat",
                is_default=True,
                enabled=True,
            )
            session.add(profile)
            await session.commit()
            print(f"Created default profile: {profile.name}")

        existing = await session.execute(select(NovelProject).where(NovelProject.title == "雨夜档案"))
        if existing.scalar_one_or_none() is not None:
            print("Seed data already exists.")
            return

        project = NovelProject(
            title="雨夜档案",
            summary="一名调查记者与刑警在旧案阴影中追查真相。",
            genre="悬疑",
            theme_json={"themes": ["真相", "信任", "隐瞒"]},
            pov_type="第三人称限知",
            tone="克制、现实",
            status="active",
        )
        session.add(project)
        await session.flush()

        lin_mo = Character(
            project_id=project.id,
            name="林默",
            role="调查记者",
            secret_identity="曾出现在三年前案发现场",
            decision_pattern="对陌生人戒备，不主动长篇倾诉",
            forbidden_behaviors_json=["第一次见面就讲述完整过去"],
        )
        su_lan = Character(
            project_id=project.id,
            name="苏岚",
            role="刑警",
            public_identity="市局刑警",
            core_desire="查清三年前旧案",
        )
        zhou_qi = Character(project_id=project.id, name="周启", role="医院医生")
        session.add_all([lin_mo, su_lan, zhou_qi])
        await session.flush()

        session.add_all(
            [
                CharacterState(
                    character_id=lin_mo.id,
                    timeline_order=1,
                    emotional_state="戒备",
                    current_goal="隐藏三年前的行踪",
                    injuries_json={"left_arm": "轻伤"},
                    status="confirmed",
                ),
                CharacterKnowledge(
                    character_id=su_lan.id,
                    fact_key="lin_mo_case_relation",
                    fact_value_json={"known": "林默与案件有关", "unknown": "林默曾在案发现场"},
                    knowledge_status="believed",
                    confidence=0.7,
                ),
            ]
        )

        session.add_all(
            [
                WorldEntry(
                    project_id=project.id,
                    entry_type="location",
                    name="市立医院",
                    summary="旧案相关伤者曾被送往这里。",
                    content="夜间走廊灯光昏白，监控覆盖不完整。",
                    canon_status="approved",
                ),
                WorldEntry(
                    project_id=project.id,
                    entry_type="rule",
                    name="证据规则",
                    summary="警方不能无证公开指认。",
                    content="正式询问前，刑警只能试探，不能摊牌。",
                    canon_status="approved",
                ),
                WorldEntry(
                    project_id=project.id,
                    entry_type="history",
                    name="三年前旧案",
                    summary="一场未公开真相的雨夜命案。",
                    content="现场证据被人为污染，部分卷宗缺页。",
                    canon_status="candidate",
                ),
            ]
        )

        volume = Volume(project_id=project.id, sequence_no=1, title="第一卷 雨夜回声")
        session.add(volume)
        await session.flush()
        chapter = Chapter(volume_id=volume.id, sequence_no=1, title="医院走廊")
        session.add(chapter)
        await session.flush()

        scene_one = Scene(
            chapter_id=chapter.id,
            sequence_no=1,
            title="试探",
            pov_character_id=su_lan.id,
            time_text="第三天晚上",
            story_time_order=10,
            goal="苏岚试探林默",
            conflict="林默隐瞒三年前行踪",
            must_not_reveal_json=["林默曾在案发现场"],
            status="ready",
        )
        scene_two = Scene(
            chapter_id=chapter.id,
            sequence_no=2,
            title="病房外的录音",
            pov_character_id=lin_mo.id,
            time_text="第三天深夜",
            story_time_order=11,
            goal="林默确认有人监听",
            status="unplanned",
        )
        session.add_all([scene_one, scene_two])
        await session.flush()
        version = SceneVersion(
            scene_id=scene_one.id,
            version_no=1,
            content_markdown="苏岚在医院走廊拦住林默，没有直接说破她已经掌握的线索。",
            summary="苏岚与林默首次正面试探。",
            source_type="human",
        )
        session.add(version)
        await session.flush()
        scene_one.approved_version_id = version.id
        scene_one.status = "approved"

        await session.commit()
        print(f"Seeded project: {project.title} ({project.id})")


if __name__ == "__main__":
    asyncio.run(main())
