# NovelFlow 项目开发执行文档（Agent 实施版）

> 文档用途：直接交给 Claude Code、Codex、Cursor Agent、OpenCode 或其他代码 Agent，指导其按阶段完成 NovelFlow 项目开发。  
> 项目名称：NovelFlow  
> 项目定位：基于 LangGraph、结构化故事记忆和多模型路由的 AI 长篇小说创作平台  
> 默认开发环境：Windows 11 / PowerShell / VS Code  
> 默认技术栈：React + TypeScript + Vite + TailwindCSS + Tiptap + FastAPI + SQLAlchemy + Alembic + LangGraph + SQLite/PostgreSQL  
> 文档版本：v1.0  
> 日期：2026-06-13

---

# 0. 给开发 Agent 的总指令

你正在开发一个真实可运行的 AI 小说创作系统，不是在生成概念 Demo。

请严格遵守以下原则：

1. 按阶段完成，不得一次性创建大量不可运行的空壳代码。
2. 每完成一个阶段，必须运行测试、启动服务并验证核心功能。
3. 不得跳过数据库迁移、异常处理、日志、类型定义和验收。
4. 不得将复杂业务逻辑写在 API Controller 中。
5. 不得把所有 Agent 写进一个文件。
6. 不得让多个 Agent 自由对话或无限循环。
7. 所有 LLM 工作流都必须有明确节点、状态、输出结构和重试上限。
8. 所有 AI 生成内容先保存为草稿，不得直接覆盖正式正文。
9. 所有故事事实更新先保存为候选变更，必须由用户确认后写入正式状态。
10. 结构化事实以数据库为准，向量检索只能用于召回相关内容。
11. 每个 AI 结果必须保存所使用的模型、Prompt 版本和上下文清单。
12. 禁止在代码中写死 API Key、数据库密码和模型密钥。
13. 所有敏感配置写入 `.env`，并提供 `.env.example`。
14. 所有公开 API 都必须进行 Pydantic 参数校验。
15. 所有时间字段统一保存 UTC，前端负责本地化显示。
16. 所有数据库表必须有主键、创建时间和更新时间。
17. 所有核心业务必须有测试。
18. 在不确定业务含义时，优先实现本文档规定的保守行为。
19. 不得擅自删除已有可用功能。
20. 每次修改前先阅读现有代码、README、测试和迁移文件。

开发 Agent 每次执行一个阶段时，应按以下格式工作：

```text
1. 阅读当前仓库状态
2. 列出本次要修改的文件
3. 实现最小完整功能
4. 运行格式检查和测试
5. 启动服务进行冒烟测试
6. 修复失败
7. 更新 README / docs / CHANGELOG
8. 输出本阶段完成情况、测试结果和遗留问题
```

---

# 1. 项目目标

NovelFlow 是一个以作者为核心的 AI 长篇小说创作工作台。

系统不是简单的聊天页面，也不是一键自动生成整本小说的工具。

系统核心能力：

- 小说项目管理；
- 世界观管理；
- 人物和人物状态管理；
- 卷、章、场景三级结构；
- 场景卡；
- AI 场景规划；
- AI 场景正文生成；
- 上下文可视化；
- 人物、时间线、事实和视角一致性检查；
- 用户确认后的故事状态更新；
- 场景版本管理；
- DeepSeek、OpenAI 兼容接口和 Ollama 多模型支持；
- SSE 流式输出；
- Markdown、TXT、JSON 项目备份导出。

第一阶段目标是完成一个可用的 MVP：

```text
建立小说资料
→ 创建人物与场景
→ 构建场景上下文
→ 生成场景正文
→ 检查一致性
→ 用户确认正文
→ 提取并确认状态变化
→ 下一场景读取最新状态
```

---

# 2. 不在 MVP 范围内的功能

以下功能禁止在 MVP 阶段优先开发：

- 一键生成整本小说；
- 多 Agent 无限制讨论；
- 自动生成几十章；
- 自动发布小说平台；
- 多人实时协作；
- 复杂知识图谱数据库；
- 自训练大模型；
- 封面、插图和有声书；
- EPUB 和复杂排版；
- 移动端 App；
- 自动联网研究；
- 自动模仿具体在世作家风格；
- 全书自动评分后无限重写；
- 微服务拆分；
- Kubernetes；
- 消息队列集群。

如果已有代码中包含这些功能，不得影响 MVP 主线稳定性。

---

# 3. 技术栈与版本策略

## 3.1 后端

推荐：

```text
Python 3.12
FastAPI
Uvicorn
Pydantic v2
SQLAlchemy 2.x
Alembic
LangGraph
httpx
sse-starlette 或 FastAPI StreamingResponse
python-dotenv / pydantic-settings
structlog 或标准 logging
pytest
pytest-asyncio
ruff
mypy
```

数据库：

```text
MVP：SQLite
生产准备：PostgreSQL
向量检索：MVP 可暂不启用，后续使用 pgvector 或 Qdrant
```

## 3.2 前端

推荐：

```text
Node.js 22 LTS
React
TypeScript
Vite
TailwindCSS
Tiptap
Zustand
TanStack Query
Axios
React Router
Zod
Vitest
React Testing Library
ESLint
Prettier
```

## 3.3 模型

MVP 支持：

- DeepSeek API；
- 任意 OpenAI 兼容接口；
- Ollama。

模型能力通过统一适配器调用。

禁止业务代码直接调用某个厂商 SDK。

---

# 4. 目标目录结构

开发 Agent 应按照以下结构组织代码。允许根据实际框架略作调整，但不得把核心模块混在一起。

```text
novelflow/
├── README.md
├── CHANGELOG.md
├── LICENSE
├── .gitignore
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── architecture.md
│   ├── database.md
│   ├── api.md
│   ├── workflows.md
│   ├── prompts.md
│   └── development.md
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   ├── exceptions.py
│   │   │   ├── responses.py
│   │   │   └── security.py
│   │   ├── api/
│   │   │   ├── router.py
│   │   │   ├── health.py
│   │   │   ├── projects.py
│   │   │   ├── characters.py
│   │   │   ├── world_entries.py
│   │   │   ├── volumes.py
│   │   │   ├── chapters.py
│   │   │   ├── scenes.py
│   │   │   ├── workflows.py
│   │   │   ├── model_profiles.py
│   │   │   └── exports.py
│   │   ├── schemas/
│   │   │   ├── common.py
│   │   │   ├── project.py
│   │   │   ├── character.py
│   │   │   ├── manuscript.py
│   │   │   ├── workflow.py
│   │   │   ├── review.py
│   │   │   └── model.py
│   │   ├── models/
│   │   │   ├── base.py
│   │   │   ├── project.py
│   │   │   ├── character.py
│   │   │   ├── manuscript.py
│   │   │   ├── world.py
│   │   │   ├── workflow.py
│   │   │   └── model_profile.py
│   │   ├── repositories/
│   │   │   ├── project_repository.py
│   │   │   ├── character_repository.py
│   │   │   ├── manuscript_repository.py
│   │   │   ├── workflow_repository.py
│   │   │   └── model_profile_repository.py
│   │   ├── services/
│   │   │   ├── project_service.py
│   │   │   ├── character_service.py
│   │   │   ├── manuscript_service.py
│   │   │   ├── context_service.py
│   │   │   ├── workflow_service.py
│   │   │   ├── export_service.py
│   │   │   └── version_service.py
│   │   ├── llm/
│   │   │   ├── base.py
│   │   │   ├── schemas.py
│   │   │   ├── openai_compatible.py
│   │   │   ├── deepseek.py
│   │   │   ├── ollama.py
│   │   │   ├── router.py
│   │   │   └── usage.py
│   │   ├── agents/
│   │   │   ├── scene_planner.py
│   │   │   ├── context_researcher.py
│   │   │   ├── scene_writer.py
│   │   │   ├── continuity_reviewer.py
│   │   │   ├── memory_curator.py
│   │   │   └── style_editor.py
│   │   ├── workflows/
│   │   │   ├── state.py
│   │   │   ├── nodes.py
│   │   │   ├── routing.py
│   │   │   └── scene_writing_graph.py
│   │   ├── prompts/
│   │   │   ├── scene_planner/
│   │   │   ├── scene_writer/
│   │   │   ├── continuity_reviewer/
│   │   │   └── memory_curator/
│   │   ├── retrieval/
│   │   │   ├── context_builder.py
│   │   │   ├── token_budget.py
│   │   │   └── source_manifest.py
│   │   └── database/
│   │       ├── session.py
│   │       └── migrations.py
│   └── tests/
│       ├── unit/
│       ├── integration/
│       ├── workflow/
│       └── fixtures/
│
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── src/
    │   ├── main.tsx
    │   ├── app/
    │   ├── api/
    │   ├── types/
    │   ├── stores/
    │   ├── hooks/
    │   ├── components/
    │   ├── editor/
    │   ├── features/
    │   │   ├── projects/
    │   │   ├── characters/
    │   │   ├── world/
    │   │   ├── outline/
    │   │   ├── manuscript/
    │   │   ├── workflows/
    │   │   ├── context-inspector/
    │   │   ├── reviews/
    │   │   ├── memory-changes/
    │   │   └── settings/
    │   └── pages/
    └── tests/
```

---

# 5. 环境初始化

## 5.1 根目录

创建：

```text
README.md
CHANGELOG.md
.env.example
.gitignore
docker-compose.yml
docs/
backend/
frontend/
```

`.gitignore` 至少包含：

```gitignore
.env
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
node_modules/
dist/
coverage/
*.db
*.sqlite
data/
uploads/
exports/
.idea/
.vscode/settings.json
```

不得忽略 `.env.example`。

## 5.2 后端初始化

推荐使用 `uv`。

PowerShell：

```powershell
cd backend
uv init
uv add fastapi uvicorn[standard] sqlalchemy alembic pydantic-settings httpx langgraph
uv add --dev pytest pytest-asyncio ruff mypy
```

如果用户机器没有 `uv`，README 必须说明安装方式，也允许使用标准 `venv + pip`。

启动命令：

```powershell
uv run uvicorn app.main:app --reload --port 8000
```

测试：

```powershell
uv run pytest
uv run ruff check .
uv run mypy app
```

## 5.3 前端初始化

```powershell
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom axios zustand @tanstack/react-query zod
npm install @tiptap/react @tiptap/pm @tiptap/starter-kit
npm install -D tailwindcss postcss autoprefixer vitest @testing-library/react @testing-library/jest-dom
```

启动：

```powershell
npm run dev
```

构建：

```powershell
npm run build
npm run test
npm run lint
```

---

# 6. 配置设计

## 6.1 `.env.example`

至少包含：

```dotenv
APP_NAME=NovelFlow
APP_ENV=development
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000

DATABASE_URL=sqlite+aiosqlite:///./novelflow.db

CORS_ORIGINS=http://localhost:5173

DEFAULT_MODEL_PROVIDER=deepseek
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com

OLLAMA_BASE_URL=http://localhost:11434

LOG_LEVEL=INFO

WORKFLOW_MAX_REVISIONS=2
WORKFLOW_MAX_JSON_REPAIRS=2
SSE_HEARTBEAT_SECONDS=15
```

## 6.2 配置要求

- 使用 `pydantic-settings`；
- 启动时校验配置；
- 缺少非必要模型 Key 时，应用仍可启动；
- 调用对应模型时再返回明确错误；
- 不得把完整 Key 打印到日志；
- 前端只接收“是否已配置”，不得接收原始 Key。

---

# 7. 数据库模型

## 7.1 通用字段

所有核心表：

```text
id: UUID 或字符串 UUID
created_at: datetime UTC
updated_at: datetime UTC
```

推荐使用 UUID。

## 7.2 NovelProject

字段：

```text
id
title
summary
genre
theme_json
target_word_count
pov_type
tone
status
language
current_timeline_position
created_at
updated_at
```

状态：

```text
draft
active
archived
completed
```

## 7.3 Character

字段：

```text
id
project_id
name
aliases_json
role
age_text
appearance
background
public_identity
secret_identity
core_desire
core_fear
values_json
decision_pattern
stress_response
speech_style
moral_boundaries_json
ability_limits_json
forbidden_behaviors_json
arc_plan
status
version
created_at
updated_at
```

## 7.4 CharacterState

字段：

```text
id
character_id
timeline_order
location_id
physical_state_json
emotional_state
current_goal
current_pressure
resources_json
injuries_json
active_secrets_json
notes
source_scene_version_id
status
created_at
updated_at
```

不得直接覆盖历史状态。

新状态应创建新记录或事件记录。

## 7.5 CharacterKnowledge

字段：

```text
id
character_id
fact_key
fact_value_json
knowledge_status
learned_at_scene_version_id
confidence
created_at
updated_at
```

`knowledge_status`：

```text
unknown
suspected
believed
confirmed
misunderstood
forgotten
```

## 7.6 WorldEntry

字段：

```text
id
project_id
entry_type
name
summary
content
tags_json
canon_status
version
created_at
updated_at
```

`entry_type`：

```text
rule
location
organization
item
ability
history
term
custom
```

`canon_status`：

```text
draft
candidate
approved
deprecated
conflicted
```

只有 `approved` 默认进入硬约束上下文。

## 7.7 Volume

```text
id
project_id
sequence_no
title
summary
goal
status
```

## 7.8 Chapter

```text
id
volume_id
sequence_no
title
summary
goal
status
approved_word_count
```

## 7.9 Scene

```text
id
chapter_id
sequence_no
title
pov_character_id
time_text
timeline_order
location_id
goal
conflict
turning_point
ending_hook
must_include_json
must_not_reveal_json
forbidden_actions_json
status
approved_version_id
created_at
updated_at
```

状态：

```text
unplanned
planned
ready
drafting
reviewing
approved
needs_revision
```

## 7.10 SceneVersion

```text
id
scene_id
version_no
parent_version_id
branch_name
content_markdown
summary
source_type
model_profile_id
prompt_snapshot_json
context_manifest_json
review_status
created_by
created_at
updated_at
```

`source_type`：

```text
human
ai_generated
ai_revised
human_revised
merged
```

任何 AI 生成操作必须创建新版本，不得覆盖旧版本。

## 7.11 TimelineEvent

```text
id
project_id
scene_version_id
timeline_order
time_text
location_id
event_type
title
description
participants_json
causes_json
effects_json
canon_status
created_at
updated_at
```

## 7.12 ReviewIssue

```text
id
scene_version_id
review_type
severity
location_hint
evidence
conflicting_rule
message
suggestion
confidence
status
created_at
updated_at
```

## 7.13 MemoryCandidate

```text
id
workflow_run_id
scene_version_id
entity_type
entity_id
field_name
operation
old_value_json
new_value_json
evidence
confidence
status
created_at
updated_at
```

状态：

```text
pending
approved
edited
rejected
conflicted
```

## 7.14 ModelProfile

```text
id
name
provider
base_url
model_name
api_key_encrypted
temperature
max_output_tokens
timeout_seconds
supports_json
supports_streaming
supports_tools
is_default
enabled
created_at
updated_at
```

MVP 可先从 `.env` 读取 Key，后续再实现数据库加密存储。

## 7.15 WorkflowRun

```text
id
project_id
scene_id
workflow_type
current_node
status
input_json
state_json
error_json
started_at
completed_at
created_at
updated_at
```

---

# 8. 数据库迁移与种子数据

Agent 必须：

1. 初始化 Alembic；
2. 生成第一版迁移；
3. 检查升级和降级；
4. 提供测试种子数据脚本。

命令示例：

```powershell
uv run alembic revision --autogenerate -m "initial schema"
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```

种子数据必须创建：

- 1 个小说项目；
- 3 个人物；
- 3 条世界观；
- 1 卷；
- 1 章；
- 2 个场景；
- 至少 1 个已确认人物状态；
- 至少 1 条人物知识边界。

种子数据用于演示和测试。

---

# 9. API 规范

## 9.1 通用响应

成功：

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "request_id": "req_xxx"
}
```

失败：

```json
{
  "code": 40001,
  "message": "scene not found",
  "details": {},
  "request_id": "req_xxx"
}
```

HTTP 状态码必须正确，不能所有错误都返回 200。

## 9.2 健康检查

```text
GET /api/health
```

返回：

```json
{
  "status": "ok",
  "database": "ok",
  "version": "0.1.0"
}
```

## 9.3 项目 API

```text
POST   /api/projects
GET    /api/projects
GET    /api/projects/{project_id}
PATCH  /api/projects/{project_id}
DELETE /api/projects/{project_id}
```

删除建议采用软删除或要求显式确认。

## 9.4 人物 API

```text
POST   /api/projects/{project_id}/characters
GET    /api/projects/{project_id}/characters
GET    /api/characters/{character_id}
PATCH  /api/characters/{character_id}
DELETE /api/characters/{character_id}

POST   /api/characters/{character_id}/states
GET    /api/characters/{character_id}/states
GET    /api/characters/{character_id}/current-state

POST   /api/characters/{character_id}/knowledge
GET    /api/characters/{character_id}/knowledge
```

## 9.5 世界观 API

```text
POST   /api/projects/{project_id}/world-entries
GET    /api/projects/{project_id}/world-entries
GET    /api/world-entries/{entry_id}
PATCH  /api/world-entries/{entry_id}
DELETE /api/world-entries/{entry_id}
POST   /api/world-entries/{entry_id}/approve
POST   /api/world-entries/{entry_id}/deprecate
```

## 9.6 卷章场景 API

```text
POST   /api/projects/{project_id}/volumes
GET    /api/projects/{project_id}/volumes

POST   /api/volumes/{volume_id}/chapters
GET    /api/volumes/{volume_id}/chapters

POST   /api/chapters/{chapter_id}/scenes
GET    /api/chapters/{chapter_id}/scenes

GET    /api/scenes/{scene_id}
PATCH  /api/scenes/{scene_id}
DELETE /api/scenes/{scene_id}
POST   /api/scenes/reorder
```

## 9.7 场景版本 API

```text
GET  /api/scenes/{scene_id}/versions
POST /api/scenes/{scene_id}/versions
GET  /api/scene-versions/{version_id}
POST /api/scenes/{scene_id}/approve-version
GET  /api/scenes/{scene_id}/compare?left={id}&right={id}
```

批准版本时：

- 更新 `scene.approved_version_id`；
- 更新场景状态；
- 不自动更新人物状态；
- 状态更新必须通过记忆候选确认流程。

## 9.8 模型配置 API

```text
GET  /api/model-profiles
POST /api/model-profiles
PATCH /api/model-profiles/{id}
POST /api/model-profiles/{id}/test
GET  /api/model-providers/ollama/models
```

测试模型时不得把 Key 返回前端。

## 9.9 工作流 API

```text
POST /api/workflows/scene-plan
POST /api/workflows/scene-write
POST /api/workflows/{run_id}/resume
POST /api/workflows/{run_id}/cancel
GET  /api/workflows/{run_id}
GET  /api/workflows/{run_id}/events
GET  /api/workflows/{run_id}/context
```

---

# 10. LLM 统一适配层

## 10.1 抽象接口

必须定义类似接口：

```python
from typing import AsyncIterator, Protocol

class LLMClient(Protocol):
    async def complete(
        self,
        messages: list[dict],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_schema: type | None = None,
    ) -> str | dict:
        ...

    async def stream(
        self,
        messages: list[dict],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        ...

    async def test_connection(self) -> dict:
        ...
```

## 10.2 OpenAI Compatible

支持：

- base_url；
- api_key；
- model；
- 流式输出；
- JSON 输出；
- 超时；
- 错误统一转换。

## 10.3 DeepSeek

DeepSeek 适配器可以复用 OpenAI Compatible，但必须：

- 独立类或配置；
- 明确默认 base URL；
- 正确处理模型名；
- 保存 usage；
- 错误信息脱敏。

## 10.4 Ollama

支持：

- 模型列表；
- 普通生成；
- 流式生成；
- 连接检测；
- 超时；
- 本地服务未启动时返回清晰错误。

## 10.5 模型路由

至少定义任务类型：

```text
scene_planning
scene_writing
continuity_review
memory_extraction
style_editing
summarization
json_repair
```

路由规则：

- 每种任务可配置一个模型；
- 未配置时使用默认模型；
- 正文模型失败时不得静默切到低质量本地模型；
- 摘要和 JSON 修复可以自动回退；
- 每次运行记录实际使用模型。

---

# 11. Prompt 管理

## 11.1 文件化

每个 Agent 的 Prompt 至少拆成：

```text
system.md
task.md
constraints.md
output_schema.md
```

禁止将几千字 Prompt 写死在 Python 文件中。

## 11.2 场景规划 Agent

输入：

- 场景所属章节目标；
- 前一场景；
- 相关人物状态；
- 当前时间线；
- 必须包含；
- 禁止泄露；
- 用户要求。

输出 Pydantic：

```python
class SceneBeat(BaseModel):
    order: int
    action: str
    purpose: str
    emotion_shift: str | None = None

class ScenePlanOutput(BaseModel):
    status: Literal["ready", "blocked"]
    scene_goal: str
    character_goals: list[str]
    conflict: str
    beats: list[SceneBeat]
    turning_point: str
    ending_hook: str
    must_include: list[str]
    must_not_reveal: list[str]
    forbidden_actions: list[str]
    risks: list[str]
    alternatives: list[str]
```

## 11.3 场景写作 Agent

只能写当前场景。

不得：

- 自动写下一场景；
- 自动改变大纲；
- 自动新增关键设定；
- 自动修改人物卡；
- 让角色知道不该知道的信息；
- 使用未批准的候选设定。

## 11.4 一致性审查 Agent

输出：

```python
class ReviewIssueOutput(BaseModel):
    type: Literal[
        "canon",
        "character_consistency",
        "knowledge_boundary",
        "timeline",
        "causality",
        "pov",
        "style"
    ]
    severity: Literal["info", "low", "medium", "high", "blocking"]
    location: str
    evidence: str
    conflicting_rule: str | None = None
    suggestion: str
    confidence: float

class ReviewOutput(BaseModel):
    overall_status: Literal["pass", "warning", "fail"]
    issues: list[ReviewIssueOutput]
    strengths: list[str]
```

审查问题必须有证据，不得只给空泛评价。

## 11.5 记忆提取 Agent

输出：

```python
class MemoryChangeOutput(BaseModel):
    entity_type: str
    entity_id: str | None
    field_name: str
    operation: Literal["add", "update", "remove", "create"]
    old_value: object | None
    new_value: object
    evidence: str
    confidence: float
```

结果只写入 `MemoryCandidate`。

---

# 12. 上下文构建器

## 12.1 上下文来源优先级

```text
P0 系统规则
P1 已确认硬事实
P2 场景卡
P3 人物当前状态
P4 人物知识边界
P5 上一场景结尾
P6 相关历史事件
P7 世界观
P8 文风资料
```

## 12.2 MVP 上下文来源

第一版无需向量库。

使用确定性查询：

- 当前场景；
- 当前章节；
- 场景 POV 人物；
- 场景涉及人物；
- 人物当前状态；
- 人物知识；
- 场景地点；
- 项目所有 `approved` 且被场景引用的世界观；
- 前一场景已批准版本；
- 手动固定资料。

## 12.3 Context Manifest

每次生成保存：

```json
[
  {
    "source_type": "character",
    "source_id": "char_xxx",
    "title": "林默",
    "priority": 2,
    "reason": "当前场景视角人物",
    "token_estimate": 320
  }
]
```

前端必须能够查看。

## 12.4 Token 预算

实现简单 Token 估算器。

当内容过长时：

1. 保留硬事实；
2. 保留当前状态；
3. 保留前一场景结尾；
4. 截断次要历史；
5. 不得删除禁止泄露和知识边界。

---

# 13. LangGraph 场景写作工作流

## 13.1 State

```python
class SceneWritingState(TypedDict):
    run_id: str
    project_id: str
    chapter_id: str
    scene_id: str

    scene: dict
    scene_plan: dict | None
    context_pack: dict | None
    context_manifest: list[dict]

    draft_text: str | None
    draft_version_id: str | None

    review_result: dict | None
    revision_count: int

    memory_candidates: list[dict]

    status: str
    error: dict | None
    usage: list[dict]
```

## 13.2 节点

```text
load_scene
validate_scene
build_context
wait_for_context_confirmation
write_scene
save_draft_version
review_scene
wait_for_draft_confirmation
extract_memory_candidates
wait_for_memory_confirmation
commit_memory_changes
finish
```

MVP 可把 `wait_for_context_confirmation` 作为可选开关，但必须保留设计。

## 13.3 路由

```text
validate_scene
├── 缺少 POV/目标/地点 → blocked
└── 通过 → build_context

review_scene
├── blocking/high 问题 → waiting_user
└── 无高危问题 → waiting_user_final

memory
├── 用户拒绝全部 → finish
└── 用户批准部分 → commit_memory_changes
```

## 13.4 中断

用户确认点：

1. 正文确认；
2. 记忆候选确认。

可选：

3. 上下文确认；
4. 场景规划确认。

## 13.5 重试

- JSON 修复最多 2 次；
- 网络请求最多 3 次；
- 自动修订最多 2 次；
- 不允许无限循环；
- 每次重试记录原因。

## 13.6 幂等性

每个工作流创建 `run_id`。

启动请求支持 `idempotency_key`。

同一场景默认只允许一个活动中的 `scene-write` 工作流。

---

# 14. SSE

## 14.1 事件类型

```text
workflow.started
node.started
node.completed
context.ready
waiting.user
generation.delta
generation.completed
review.issue
memory.candidate
workflow.completed
workflow.failed
heartbeat
```

## 14.2 事件结构

```json
{
  "event": "generation.delta",
  "run_id": "run_xxx",
  "node": "write_scene",
  "data": {
    "delta": "林默没有立刻回答。"
  },
  "timestamp": "2026-06-13T12:00:00Z"
}
```

## 14.3 要求

- 每 15 秒发送 heartbeat；
- 客户端断线后可通过 `run_id` 查询最终状态；
- SSE 断开不得取消后端任务，除非用户显式取消；
- 流式文本同时写入临时缓冲；
- 完成后保存为场景版本；
- 失败时保留已生成文本为临时草稿。

---

# 15. 前端实现要求

## 15.1 页面

MVP 页面：

```text
/
├── 项目列表
├── /projects/:projectId/workspace
├── /settings/models
└── /settings/general
```

## 15.2 工作台布局

左侧：

- 小说结构；
- 世界观；
- 人物；
- 场景列表。

中间：

- 标题；
- Tiptap 编辑器；
- 自动保存；
- 字数；
- 版本切换。

右侧：

- 场景卡；
- AI 操作；
- 运行状态；
- 上下文；
- 审查问题；
- 记忆候选。

## 15.3 状态管理

建议：

- TanStack Query：服务端数据；
- Zustand：当前项目、当前场景、UI 面板状态；
- 编辑器内容独立管理。

不得把所有数据塞入一个全局 Store。

## 15.4 编辑器

MVP 支持：

- 段落；
- 标题；
- 加粗；
- 斜体；
- 引用；
- 分隔线；
- 撤销重做；
- 自动保存；
- 字数统计；
- Markdown 导出；
- AI 生成插入为新版本。

## 15.5 自动保存

- 用户输入后 800～1500ms debounce；
- 保存失败显示明确状态；
- 页面关闭前检查未保存内容；
- AI 生成版本和人工编辑版本分开；
- 不得在 AI 流式生成期间自动覆盖当前正式版本。

## 15.6 版本历史

显示：

- 版本号；
- 来源；
- 模型；
- 时间；
- 是否正式；
- 字数；
- 审查状态。

操作：

- 打开；
- 比较；
- 复制为新版本；
- 批准；
- 删除未批准草稿。

不得删除当前正式版本。

---

# 16. 前端与后端类型同步

建议使用 OpenAPI 生成前端类型，或至少维护统一 TypeScript 类型。

关键类型：

```text
NovelProject
Character
CharacterState
WorldEntry
Volume
Chapter
Scene
SceneVersion
ContextManifestItem
ReviewIssue
MemoryCandidate
WorkflowRun
SSEEvent
ModelProfile
```

禁止大量使用 `any`。

---

# 17. 项目开发阶段

---

# 阶段 0：仓库初始化与基础设施

## 目标

建立可启动、可测试的前后端项目。

## 任务

- 创建目录；
- 初始化 Git；
- 初始化 FastAPI；
- 初始化 React；
- 配置 CORS；
- 配置日志；
- 配置环境变量；
- 实现健康检查；
- 配置 Ruff、Mypy、Pytest；
- 配置 ESLint、Prettier、Vitest；
- 编写启动文档。

## 验收

```text
GET /api/health 返回 200
前端可访问
前端可请求健康检查
backend tests 通过
frontend build 通过
```

## 禁止进入下一阶段的条件

- 后端无法启动；
- 前端无法构建；
- 环境变量写死；
- 没有 README；
- 测试命令失败。

---

# 阶段 1：数据库和基础 CRUD

## 目标

完成小说项目、人物、世界观、卷章场景的基本管理。

## 任务

- 创建 SQLAlchemy 模型；
- 创建 Pydantic Schema；
- 初始化 Alembic；
- 创建 Repository；
- 创建 Service；
- 创建 API；
- 创建种子数据；
- 创建后端测试；
- 前端创建项目列表；
- 前端创建工作台基础布局；
- 完成项目、人物、世界观 CRUD。

## 验收

- 可以新建小说；
- 可以新建人物；
- 可以新建世界观；
- 可以创建卷、章、场景；
- 可以刷新页面后读取数据；
- 数据库迁移可升级和降级；
- API 测试通过。

---

# 阶段 2：正文编辑器与版本管理

## 目标

在没有 AI 的情况下，系统已经可以作为基础小说编辑器使用。

## 任务

- 集成 Tiptap；
- 场景正文编辑；
- 自动保存；
- SceneVersion；
- 版本历史；
- 批准版本；
- Markdown 导出；
- 项目 JSON 备份。

## 验收

- 输入正文后自动保存；
- 每次手动创建版本不会覆盖旧版本；
- 可以指定一个正式版本；
- 可以导出 Markdown；
- 重启后内容不丢失；
- 可以查看版本历史。

---

# 阶段 3：模型适配与流式生成

## 目标

接入 DeepSeek/OpenAI Compatible/Ollama。

## 任务

- 定义统一 LLMClient；
- 实现 OpenAI Compatible；
- 实现 DeepSeek；
- 实现 Ollama；
- 实现模型测试接口；
- 实现任务路由；
- 实现 SSE；
- 创建最简单场景生成接口；
- 保存生成结果为新版本；
- 记录模型、Token 和 Prompt。

## 验收

- DeepSeek 可生成；
- Ollama 可连接和列出模型；
- 正文可流式显示；
- 断线后可查询结果；
- 模型失败返回清晰错误；
- 生成不覆盖正式版本。

---

# 阶段 4：上下文构建器

## 目标

生成时不再只依赖一个简单 Prompt，而是从数据库装配正确资料。

## 任务

- 当前场景查询；
- 人物卡查询；
- 人物当前状态；
- 人物知识边界；
- 世界观 approved 过滤；
- 前一场景正式版本；
- Context Manifest；
- Token 估算；
- 前端上下文检查器。

## 验收

- 可以看到本次生成使用的所有资料；
- 废弃设定不会进入上下文；
- 未批准候选设定不会进入硬约束；
- 前一场景读取正式版本；
- 人物知识边界被包含；
- 上下文可在前端展开查看。

---

# 阶段 5：LangGraph 场景写作工作流

## 目标

将场景生成改为可恢复的工作流。

## 任务

- 定义 State；
- 定义节点；
- 定义路由；
- 保存 WorkflowRun；
- 接入 Checkpoint；
- SSE 发送节点状态；
- 用户确认正文；
- 取消工作流；
- 错误恢复。

## 验收

- 可以看到当前节点；
- 生成结束等待用户确认；
- 用户确认后版本成为正式；
- 用户拒绝时保留草稿但不批准；
- 进程重启后可读取工作流状态；
- 模型失败后可重试当前节点。

---

# 阶段 6：一致性审查

## 目标

发现人设、知识、时间和事实问题。

## 任务

- Continuity Reviewer；
- 审查 Prompt；
- Pydantic 输出；
- ReviewIssue 表；
- 前端审查面板；
- 接受、忽略、误报；
- 高危问题阻断批准的可选配置。

## 验收

至少通过以下测试：

1. 女主不知道男主真实身份，但草稿直接说出身份；
2. 男主左臂受伤，却用左臂完成高强度动作；
3. 男主设定不向陌生人倾诉，却第一次见面讲完整过去；
4. 场景时间比前一场景更早但无闪回标记；
5. 草稿引用已废弃世界观。

审查必须给出证据和修改建议。

---

# 阶段 7：记忆候选与状态更新

## 目标

正文确认后，系统能够提取并由用户确认状态变化。

## 任务

- Memory Curator；
- MemoryCandidate 表；
- 证据定位；
- 用户确认；
- 更新 CharacterState；
- 更新 CharacterKnowledge；
- 写入 TimelineEvent；
- 更新场景摘要；
- 审计日志。

## 验收

- 正文出现受伤后，生成伤势候选；
- 正文出现角色获知秘密后，生成知识候选；
- 候选未批准前不修改正式状态；
- 用户可编辑候选；
- 用户批准后下一场景能读取新状态；
- 拒绝候选不产生正式变化。

---

# 阶段 8：MVP 完整体验和测试

## 目标

完成可展示和可长期使用的第一版。

## 任务

- 异常处理；
- 加载状态；
- 空状态；
- 错误提示；
- Demo 数据；
- 完整端到端测试；
- Docker Compose；
- README；
- 截图；
- API 文档；
- 开发文档；
- 备份恢复。

## 验收

完整演示：

1. 创建小说；
2. 创建三个人物；
3. 设置秘密和知识边界；
4. 创建场景；
5. 查看上下文；
6. 流式生成；
7. 审查发现问题；
8. 用户修改；
9. 批准版本；
10. 确认记忆候选；
11. 下一场景读取最新状态；
12. 导出 Markdown；
13. 备份和恢复项目。

---

# 18. Agent 详细实现要求

## 18.1 Scene Planner

MVP 中可选，但建议实现。

职责：

- 将用户的简单场景目标转成结构化场景卡；
- 不写正文；
- 若任务违反人物约束，返回 blocked。

不得：

- 修改人物设定；
- 写入正式大纲；
- 自动批准输出。

## 18.2 Context Researcher

MVP 中主要由确定性代码实现。

职责：

- 决定需要哪些实体；
- 查询数据库；
- 构建上下文；
- 输出来源清单。

不要让 LLM 自由决定数据库 SQL。

## 18.3 Scene Writer

职责：

- 写当前场景；
- 遵循所有硬约束；
- 返回正文和自检。

输入必须包含：

- 场景卡；
- 人物行为规则；
- 当前状态；
- 知识边界；
- 前一场景；
- 世界观；
- 用户要求。

## 18.4 Continuity Reviewer

职责：

- 检查；
- 不直接自动重写正文。

问题必须包含：

- 类型；
- 严重程度；
- 原文证据；
- 冲突规则；
- 修改建议；
- 置信度。

## 18.5 Memory Curator

职责：

- 从批准或待批准正文提取状态变化；
- 只创建候选；
- 不直接更新正式状态。

## 18.6 Style Editor

放在 MVP 后半段。

职责：

- 删除明显 AI 套话；
- 保留含义；
- 提供修改前后差异；
- 不改变剧情事实。

---

# 19. 服务层业务规则

## 19.1 场景版本

- AI 生成创建新版本；
- 人工编辑可创建新版本；
- 批准只改变 `approved_version_id`；
- 正式版本不得直接删除；
- 旧正式版本保留；
- 修改旧场景后要标记后续场景可能受影响。

## 19.2 场景顺序

- 同一章节内 `sequence_no` 唯一；
- 重排必须事务执行；
- 前一场景按顺序和正式版本确定。

## 19.3 正式设定

- `approved` 才进入硬约束；
- `candidate` 可在用户明确选择时作为参考；
- `deprecated` 默认永远不进入上下文；
- `conflicted` 需要在上下文检查器中提示。

## 19.4 人物状态

- 查询当前状态时按 `timeline_order` 取最近有效状态；
- 不允许后来的场景读取未来状态；
- 未确认候选不算正式状态。

## 19.5 人物知识

场景上下文必须区分：

```text
作者知道
读者知道
当前角色知道
当前角色怀疑
当前角色误解
```

---

# 20. 错误处理

统一错误类型：

```text
ValidationError
NotFoundError
ConflictError
ModelConfigurationError
ModelConnectionError
ModelResponseError
WorkflowStateError
PermissionError
ExportError
```

API 返回：

- 明确错误码；
- 用户可读信息；
- request_id；
- 不返回堆栈；
- 服务器日志记录完整堆栈。

模型错误需要区分：

- API Key 错误；
- 模型不存在；
- Ollama 未启动；
- 超时；
- 限流；
- JSON 格式错误；
- 内容过长；
- 用户取消。

---

# 21. 日志与可观测性

日志至少包含：

```text
request_id
run_id
project_id
scene_id
node
model_provider
model_name
duration_ms
input_token_estimate
output_tokens
status
error_type
```

不得记录：

- API Key；
- 密码；
- 完整 Authorization Header；
- 默认情况下的完整小说正文。

开发环境可以记录正文摘要，生产环境默认关闭。

---

# 22. 测试要求

## 22.1 后端单元测试

必须覆盖：

- 项目 Service；
- 人物当前状态查询；
- 世界观 approved 过滤；
- 场景顺序；
- 版本批准；
- Token 预算；
- Context Manifest；
- LLM 路由；
- Review 输出校验；
- MemoryCandidate 状态流转。

## 22.2 集成测试

必须覆盖：

- 创建项目到创建场景；
- 生成场景版本；
- 批准版本；
- 创建和批准记忆候选；
- 下一场景读取状态；
- SSE 事件顺序；
- 数据库事务回滚；
- 工作流失败恢复。

## 22.3 Mock 模型

测试不能依赖真实付费 API。

实现 `FakeLLMClient`：

- 可返回固定正文；
- 可流式返回；
- 可返回固定 JSON；
- 可模拟超时；
- 可模拟格式错误；
- 可模拟限流。

## 22.4 前端测试

至少覆盖：

- 项目列表；
- 场景切换；
- 编辑器保存状态；
- SSE 消息处理；
- 审查问题展示；
- 候选记忆确认；
- 错误提示。

## 22.5 E2E

推荐 Playwright，MVP 后期加入。

核心 E2E：

```text
新建项目
→ 新建人物
→ 新建场景
→ 启动 Fake 工作流
→ 接收流式正文
→ 审查
→ 批准
→ 记忆候选确认
```

---

# 23. 代码质量要求

后端：

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
```

前端：

```powershell
npm run lint
npm run test
npm run build
```

合并前必须全部通过。

不得通过以下方式规避：

- 大量 `# type: ignore`；
- 全局关闭 lint；
- 使用 `any` 绕过类型；
- 删除失败测试；
- 捕获所有异常后静默忽略；
- 把失败测试标记 skip 而不解释。

---

# 24. Git 提交建议

每个阶段拆分为小提交。

示例：

```text
chore: initialize backend and frontend workspace
feat: add project and character persistence
feat: add manuscript hierarchy and scene versions
feat: integrate unified llm client
feat: stream scene generation over sse
feat: build deterministic scene context
feat: add langgraph scene writing workflow
feat: add continuity review pipeline
feat: add memory candidate approval flow
test: add end-to-end mvp workflow coverage
docs: add deployment and user guide
```

禁止一个提交包含整个项目。

---

# 25. 开发 Agent 每阶段输出模板

完成阶段后输出：

```markdown
## 本阶段完成内容

- ...

## 修改文件

- `path/file.py`
- ...

## 数据库迁移

- ...

## 新增 API

- ...

## 测试结果

- `pytest`: xx passed
- `ruff`: passed
- `mypy`: passed
- `npm test`: passed
- `npm run build`: passed

## 手动验证

1. ...
2. ...

## 已知问题

- ...

## 下一阶段建议

- ...
```

---

# 26. 第一轮开发任务清单

开发 Agent 第一次接手项目时，只执行以下内容，不要直接开发 AI 工作流：

## Task 1：初始化仓库

- 创建前后端；
- 配置环境变量；
- 健康检查；
- CORS；
- 日志；
- 测试工具；
- README。

## Task 2：数据库基础

- SQLAlchemy async session；
- Base；
- Alembic；
- NovelProject；
- Character；
- WorldEntry；
- Volume；
- Chapter；
- Scene；
- SceneVersion。

## Task 3：基础 API

- 项目 CRUD；
- 人物 CRUD；
- 世界观 CRUD；
- 卷章场景 CRUD；
- 场景版本 CRUD；
- API 测试。

## Task 4：前端骨架

- 路由；
- 项目列表；
- 工作台三栏布局；
- API Client；
- Query Client；
- 基础类型；
- 错误提示。

## Task 5：手动正文

- Tiptap；
- 自动保存；
- 版本创建；
- 版本批准；
- Markdown 导出。

完成以上内容后再进入 LLM 集成。

---

# 27. 可直接交给 Agent 的首轮执行提示词

下面这段可以直接复制给代码 Agent：

```text
你现在负责开发 NovelFlow 项目。

请先完整阅读仓库中的：
- README.md
- docs/
- NovelFlow 项目开发执行文档
- pyproject.toml
- package.json
- Alembic 迁移
- 现有测试

本轮只完成“阶段 0：仓库初始化与基础设施”。

必须完成：
1. 初始化 FastAPI 后端。
2. 初始化 React + TypeScript + Vite 前端。
3. 配置环境变量和 .env.example。
4. 配置 CORS。
5. 配置统一日志和 request_id。
6. 实现 GET /api/health。
7. 前端显示后端健康状态。
8. 配置 pytest、ruff、mypy。
9. 配置 ESLint、Prettier、Vitest。
10. 编写 Windows PowerShell 下的启动说明。
11. 运行全部检查并修复错误。
12. 更新 README 和 CHANGELOG。

限制：
- 不要开始数据库业务表。
- 不要接入模型。
- 不要实现 Agent。
- 不要创建无用空文件。
- 不要使用硬编码密钥。
- 不要跳过测试。

完成后按文档中的“开发 Agent 每阶段输出模板”汇报。
```

---

# 28. 阶段 1 执行提示词

```text
继续开发 NovelFlow。

本轮只完成“阶段 1：数据库和基础 CRUD”。

先阅读全部现有代码、测试和迁移，不得破坏阶段 0。

必须实现：
1. SQLAlchemy 2.x 异步数据库。
2. Alembic。
3. NovelProject。
4. Character。
5. CharacterState。
6. CharacterKnowledge。
7. WorldEntry。
8. Volume。
9. Chapter。
10. Scene。
11. SceneVersion。
12. 对应 Pydantic Schema。
13. Repository 和 Service 分层。
14. REST API。
15. 数据库迁移。
16. 种子数据。
17. 单元和集成测试。
18. 前端项目列表和基础工作台。
19. 前端人物、世界观和场景基础管理。
20. 更新 docs/database.md、docs/api.md 和 CHANGELOG。

业务限制：
- API 层不能直接写复杂数据库逻辑。
- 所有项目子资源必须验证 project_id 归属。
- SceneVersion 不得覆盖旧版本。
- WorldEntry 必须有 canon_status。
- CharacterState 必须支持历史状态。
- 所有删除需防止破坏正式版本关系。
- 本阶段不接入模型和 LangGraph。

完成后运行：
- alembic upgrade/downgrade/upgrade
- pytest
- ruff
- mypy
- npm test
- npm run build

按标准模板汇报。
```

---

# 29. 阶段 2 执行提示词

```text
继续开发 NovelFlow。

本轮只完成“阶段 2：正文编辑器与版本管理”。

必须实现：
1. Tiptap 编辑器。
2. 场景正文自动保存。
3. SceneVersion 创建。
4. 人工编辑版本。
5. 版本列表。
6. 版本详情。
7. 批准版本。
8. 版本比较的基础实现。
9. Markdown 导出。
10. JSON 项目备份。
11. 前后端测试。
12. 文档更新。

规则：
- 自动保存不得覆盖已有正式版本。
- 正式版本不得直接删除。
- AI 和人工版本必须保留 source_type。
- 页面刷新后正文不得丢失。
- 自动保存必须有 loading/saved/error 状态。
- 本阶段仍不接入 LLM。

完成后运行全部检查并按标准模板汇报。
```

---

# 30. 阶段 3 执行提示词

```text
继续开发 NovelFlow。

本轮完成“阶段 3：模型适配与流式生成”。

必须实现：
1. LLMClient 抽象接口。
2. OpenAI Compatible 适配器。
3. DeepSeek 配置。
4. Ollama 适配器。
5. 模型连接测试。
6. Ollama 模型列表。
7. 模型任务路由。
8. SSE 基础设施。
9. 流式场景生成。
10. 生成完成后创建 SceneVersion。
11. 保存实际模型、Prompt 快照、上下文清单和 usage。
12. FakeLLMClient。
13. 模型错误测试。
14. SSE 测试。
15. 前端模型设置和流式显示。
16. 文档更新。

重要规则：
- 不得把 API Key 返回给前端。
- 正文模型失败不得静默降级到本地小模型。
- 生成不得覆盖正式版本。
- 断线后可通过 run_id 查询结果。
- 所有模型异常统一转换。
- 测试不得调用真实付费模型。

完成后运行全部检查并汇报。
```

---

# 31. 阶段 4 至阶段 7 执行顺序

后续 Agent 必须严格按顺序：

```text
阶段 4：上下文构建器
阶段 5：LangGraph 场景写作工作流
阶段 6：一致性审查
阶段 7：记忆候选与状态更新
阶段 8：MVP 完整体验
```

不得先做多 Agent、高级 RAG、知识图谱、自动出版。

---

# 32. MVP 最终验收脚本

开发完成后，Agent 应执行以下人工或自动化验收。

## 32.1 创建项目

```text
书名：雨夜档案
类型：悬疑
视角：第三人称限知
基调：克制、现实
```

## 32.2 创建人物

### 林默

```text
身份：调查记者
秘密：曾出现在三年前案发现场
行为规则：对陌生人戒备，不主动长篇倾诉
伤势：左臂轻伤
```

### 苏岚

```text
身份：刑警
已知：林默与案件有关
未知：林默曾在案发现场
```

### 周启

```text
身份：医院医生
已知：林默左臂伤势
```

## 32.3 创建场景

```text
地点：医院走廊
时间：第三天晚上
POV：苏岚
目标：苏岚试探林默
禁止泄露：林默曾在案发现场
```

## 32.4 生成故意错误的草稿

Fake 模型返回：

- 苏岚直接说出林默案发现场经历；
- 林默主动讲述完整童年；
- 林默使用受伤左臂搬重物。

## 32.5 预期审查

系统应生成：

1. 知识边界 high/blocking；
2. 人设一致性 high；
3. 伤势事实 medium/high。

## 32.6 修改并批准

用户修改正文并批准。

## 32.7 状态提取

系统生成候选：

- 苏岚对林默怀疑加深；
- 林默左臂伤势加重；
- 时间推进；
- 两人信任下降。

## 32.8 下一场景

下一场景上下文必须读取这些批准后的状态。

## 32.9 导出

导出 Markdown 和 JSON 备份。

---

# 33. Definition of Done

一个阶段只有同时满足以下条件才算完成：

- 功能已实现；
- API 可用；
- 前端可操作；
- 数据能持久化；
- 有测试；
- 测试通过；
- Lint 通过；
- 类型检查通过；
- 构建通过；
- 文档已更新；
- 没有把密钥提交仓库；
- 没有未说明的重大 TODO；
- 有明确的人工验证步骤；
- 不破坏之前阶段功能。

---

# 34. 最终产品约束

NovelFlow 的核心不是“生成得更多”，而是“生成过程可控”。

任何后续功能都必须遵守：

```text
可查看
可修改
可确认
可拒绝
可回滚
可解释
可恢复
```

AI 不得绕过作者成为故事事实的最终决定者。

---

# 35. 项目完成后的推荐扩展顺序

MVP 稳定后再按以下顺序扩展：

1. BM25 + 向量混合检索；
2. 文风样本与文风编辑；
3. 伏笔管理；
4. 时间线图；
5. 人物关系图；
6. 旧场景修改影响分析；
7. 章节级审稿；
8. 全书级审稿；
9. DOCX 和 EPUB；
10. PostgreSQL + pgvector；
11. Redis 缓存；
12. 多用户和权限；
13. Docker 部署；
14. 插件和 MCP；
15. 自动研究、插图和有声书。

每次只增加一个可验证的能力，避免系统重新变成不可控的自动化黑箱。
