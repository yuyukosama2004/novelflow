from app.api.workflows import (
    _build_system_prompt,
    _perspective_warning,
    _summary_from_plan,
)
from app.models.project import NovelProject
from app.services.writing_style import (
    PERSPECTIVE_INSTRUCTIONS,
    WRITING_STYLE_PRESETS,
    writing_style_instruction,
)


def test_writing_style_presets_are_complete_and_customizable() -> None:
    expected = {
        "general_web",
        "light_novel",
        "male_web",
        "female_web",
        "suspense",
        "literary",
        "historical",
        "scifi",
        "custom",
    }

    assert expected == set(WRITING_STYLE_PRESETS)
    instruction = writing_style_instruction("suspense", "避免暴力描写")
    assert "信息差" in instruction
    assert "避免暴力描写" in instruction


def test_generation_prompt_applies_perspective_style_length_and_rewrite_request() -> None:
    project = NovelProject(
        title="Prompt controls",
        pov_type="first_person",
        writing_style_preset="light_novel",
        writing_style_custom="对话简洁，不使用网络热梗。",
    )

    prompt = _build_system_prompt(
        project,
        target_word_count=2000,
        generation_mode="rewrite",
        instruction="加强主角的戒备感。",
    )

    assert PERSPECTIVE_INSTRUCTIONS["first_person"] in prompt
    assert "轻小说" in prompt
    assert "约 2000 个汉字" in prompt
    assert "重写完整场景" in prompt
    assert "加强主角的戒备感" in prompt
    assert "约束优先级" in prompt
    assert "不得覆盖全书人称、文风" in prompt


def test_generated_version_summary_uses_plan_instead_of_manuscript_opening() -> None:
    summary = _summary_from_plan(
        "摘要：沈砚在旧档案室发现被篡改的照片，决定隐瞒线索继续追查。\n节拍：翻档、发现、犹豫、决定。",
        "旧档案室",
        "rewrite",
    )

    assert summary == "沈砚在旧档案室发现被篡改的照片，决定隐瞒线索继续追查"
    assert "AI 重写" in _summary_from_plan("", "旧档案室", "rewrite")


def test_perspective_warning_only_flags_clear_third_person_mismatch() -> None:
    assert not _perspective_warning("我说。" * 3, "third_person_omniscient")
    assert "第一人称" in _perspective_warning(
        "我推开门，我看见桌上的照片，我想起昨夜的雨，我不敢出声，我转身离开。" * 10,
        "third_person_limited",
    )
