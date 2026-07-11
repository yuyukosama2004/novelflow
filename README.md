# NovelFlow

NovelFlow 是一个强调作者控制的 AI 长篇小说创作工作台。AI 生成内容只会创建新草稿版本，故事事实和人物状态必须经过用户确认后才能写入正式状态。

## Current Status

当前版本已完成主要创作流程闭环：

- **全中文平台**：所有用户可见文案中文，后端枚举前端映射。
- **创作向导**：5 入口（点子/世界观/人物/大纲/直接正文）→ LLM 访谈对话 → 候选确认。
- **故事圣经**：核心概念/人物详情/人物关系/世界观/大纲/时间线 6 Tab 统一管理。
- **大纲生成**：LLM 从圣经信息生成卷-章-场景结构，确认后批量写入。
- **写作工作台**：Tiptap 编辑器、写作辅助面板（约束+可用信息）、自动保存、版本历史、版本批准。
- **场景卡编辑器**：完整场景字段编辑（目标/冲突/转折/钩子/约束）。
- **AI 场景生成**：SSE 流式生成 + 并发锁保护。
- **一致性审查 + 记忆候选**：LLM 审查 + 提取 → 用户确认 → 写入正式状态。
- Markdown/JSON 导出。

仍待后续：

- SSE 断线恢复和生成任务查询。
- 完整 E2E 测试。
- Docker Compose 部署验证。

## Stack

- Backend: Python 3.10+, FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic, SQLite
- Frontend: React 18, TypeScript, Vite, TailwindCSS, Tiptap, TanStack Query
- Models: DeepSeek, OpenAI-compatible, Ollama, FakeLLM
- Quality: pytest, Ruff, mypy, Vitest, React Testing Library, ESLint

## Secrets

不要把 API Key 写入项目文件、Markdown、日志或 Git。

推荐设置为 Windows 用户环境变量：

```powershell
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "your-key", "User")
```

新终端通常会继承用户环境变量。若当前终端尚未读取到，可临时注入：

```powershell
$env:DEEPSEEK_API_KEY = [Environment]::GetEnvironmentVariable("DEEPSEEK_API_KEY", "User")
```

如果 Key 曾被提交到 Git，即使后来删除文件，也必须在服务商后台撤销并重新生成。

模型设置页也可以保存不同 Provider 的连接配置。当前版本面向本地单用户，API Key
会以明文保存在本机 SQLite 数据库中；数据库文件已被 Git 忽略，但这不等同于加密。
不要把数据库复制到公开位置，也不要将当前存储方式直接用于多人或公网部署。更新配置时
将 Key 留空表示保留原值；如需删除，请使用设置页单独的“清除 API Key”操作。

## Quick Start

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

本机开发默认同时允许 `http://localhost:5173` 和 `http://127.0.0.1:5173` 访问后端。前端默认 API 地址是 `http://127.0.0.1:8000/api`，这样可以避开部分 Windows 环境里 `localhost` 优先解析到 IPv6 而后端只监听 IPv4 的问题。

如果你在本机维护启动脚本，建议放在被忽略的本地目录：

- `local-dev-docs\30-tools\windows\`

这些脚本不作为公开仓库文件推送。公开启动方式以上面的后端、前端命令为准。

## Quality Checks

Backend:

```powershell
cd backend
ruff check .
ruff format --check .
mypy app
pytest tests -v
python scripts/smoke.py
```

Frontend:

```powershell
cd frontend
npm run lint
npm run test
npm run build
node scripts/smoke.mjs
```

## Recommended Creation Workflow

NovelFlow 的目标流程不是直接从卷、章、场景开始写正文，而是先帮助作者建立可控的故事基础：

1. 新建小说项目。
2. 选择创作入口：点子、世界观、人物、大纲或直接写正文。
3. 通过 LLM 访谈式共创，补充主题、主冲突、世界规则、人物欲望和故事限制。
4. 将 LLM 输出保存为候选项，作者编辑、确认或拒绝。
5. 形成故事圣经：核心概念、世界观、人物、关系、时间线和伏笔。
6. 生成并调整全书大纲、卷纲、章节纲和场景卡。
7. 进入正文工作台，人工写作或生成场景草稿。
8. 编辑中的内容自动保存到每个场景唯一的 `SceneWorkingDraft`，使用 revision 防止过期覆盖；只有手动“保存版本”才创建不可变的 `SceneVersion`。
9. 作者审查并批准正式版本。
10. 运行一致性审查，提取记忆候选。
11. 作者确认人物状态、知识、世界观或时间线更新。
12. 下一场景只读取当前时间线之前的正式状态和知识。

当前代码已经覆盖后半段的场景、版本、审查和记忆基础能力；前半段的创作向导、故事圣经和大纲共创仍是后续重点。

场景的叙事位置由卷、章、场景的 `sequence_no` 决定；故事内时间使用 `story_time_order`。新场景未显式提供故事时间时，会根据上一叙事场景自动推导。

## Important API

- `GET /api/health`
- `GET /api/model/providers`
- `POST /api/model/test`
- `POST /api/model/generate`
- `GET /api/scenes/{scene_id}/context`
- `POST /api/scenes/{scene_id}/generate`
- `GET /api/scenes/{scene_id}/working-draft`
- `PUT /api/scenes/{scene_id}/working-draft`
- `POST /api/scenes/{scene_id}/versions`
- `GET /api/workflows/runs/{run_id}`
- `POST /api/scene-versions/{version_id}/review`
- `GET /api/scene-versions/{version_id}/issues`
- `POST /api/scene-versions/{version_id}/extract-memories`
- `GET /api/scene-versions/{version_id}/candidates`
- `PATCH /api/candidates/{candidate_id}`

## Document Policy

公开仓库只保留 `README.md` 作为 Markdown 文档入口。开发过程文档、交接文档、博客草稿、本机脚本和内部计划放在本地忽略目录 `local-dev-docs/`，不会随 Git 推送。
