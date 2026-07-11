from __future__ import annotations

WRITING_STYLE_PRESETS: dict[str, dict[str, str]] = {
    "general_web": {
        "label": "通用网络小说",
        "instruction": (
            "节奏清晰，优先用具体动作、对话和感官细节推动情节。"
            "每一段都服务于冲突、信息推进或人物关系变化；避免空泛抒情、"
            "重复解释和套路化总结。"
        ),
    },
    "light_novel": {
        "label": "轻小说",
        "instruction": (
            "语言轻快自然，对话占比适中，以角色即时反应和日常细节塑造氛围。"
            "允许适度幽默与节奏停顿，但不使用网络梗堆砌；情绪转折必须由事件触发。"
        ),
    },
    "male_web": {
        "label": "男频成长冒险",
        "instruction": (
            "突出目标、代价、行动结果与能力成长。冲突必须可感知、可推进，"
            "信息揭示服务于下一步选择；避免无代价获胜和无意义升级。"
        ),
    },
    "female_web": {
        "label": "女频情感成长",
        "instruction": (
            "重视人物关系、情绪动机与选择后的余波。通过行动、对话与细节呈现情感，"
            "不替读者直接下结论；人物要保有主动性和边界。"
        ),
    },
    "suspense": {
        "label": "悬疑推理",
        "instruction": (
            "维持信息差与因果链。线索必须可回溯、可解释，误导必须公平；"
            "用场景细节制造压迫和疑问，但不得提前泄露受限事实或用巧合解决核心问题。"
        ),
    },
    "literary": {
        "label": "文学现实主义",
        "instruction": (
            "语言克制准确，关注人物处境、感官细节和潜台词。意象必须服务于人物与主题，"
            "避免华丽辞藻堆砌、说教和为追求文艺感而牺牲叙事清晰度。"
        ),
    },
    "historical": {
        "label": "古风历史",
        "instruction": (
            "遵守既定时代语境、礼制与社会关系。用现代读者易懂的自然中文表达，"
            "不滥用生僻古语或伪文言；权力、礼法和行动代价要符合设定。"
        ),
    },
    "scifi": {
        "label": "科幻幻想",
        "instruction": (
            "让设定通过人物行动和后果自然显现。技术或超自然规则必须前后一致，"
            "每次能力使用都交代限制、成本或风险，避免用新设定临时解决冲突。"
        ),
    },
    "custom": {
        "label": "自定义文风",
        "instruction": (
            "以作者填写的自定义文风与约束为主，同时保持叙事清晰、人物行为一致，"
            "避免无关套话、重复说明和元评论。"
        ),
    },
}

PERSPECTIVE_INSTRUCTIONS = {
    "first_person": (
        "使用第一人称“我”叙述。只写叙述者亲眼所见、亲耳所闻、亲身感受或合理推断的信息，禁止全知视角。"
    ),
    "third_person_limited": (
        "使用第三人称限知视角。只进入当前 POV 人物的感受、判断和已知信息，禁止切入其他人物内心。"
    ),
    "third_person_omniscient": (
        "使用第三人称全知视角。可以在必要时展示多位人物的信息，但每次转换必须清晰、节制，并服务于情节。"
    ),
}


def writing_style_instruction(preset: str, custom: str) -> str:
    style = WRITING_STYLE_PRESETS.get(preset, WRITING_STYLE_PRESETS["general_web"])
    parts = [f"文风预设：{style['label']}。", style["instruction"]]
    if custom.strip():
        parts.append(f"作者自定义文风与约束（优先遵守）：{custom.strip()}")
    return "\n".join(parts)


def perspective_instruction(pov_type: str) -> str:
    return PERSPECTIVE_INSTRUCTIONS.get(
        pov_type,
        PERSPECTIVE_INSTRUCTIONS["third_person_limited"],
    )
