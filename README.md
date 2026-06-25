# NovelFlow

NovelFlow 是一个强调作者控制的 AI 长篇小说创作工作台。AI 生成内容只会创建新草稿版本，故事事实和人物状态必须经过用户确认后才能写入正式状态。

## Current Status

当前版本包含：

- 可用的项目、人物、世界观、卷、章、场景和正文版本管理。
- Tiptap 编辑器、版本历史、版本批准、Markdown/JSON 导出。
- DeepSeek、OpenAI-compatible、Ollama 和 Fake LLM 统一适配层。
- SSE 场景生成、确定性上下文构建和持久化工作流运行记录。
- 后端一致性审查与记忆候选 API。
- 人物状态和人物知识候选的确认写入。

当前版本仍不是完整的 8 阶段成品：

- 场景生成使用显式异步状态机，不是 LangGraph，也没有 checkpoint/resume。
- 前端已有一致性审查和记忆候选确认面板（含工作流级别集成测试），但尚无完整 E2E。
- SSE 前端取消会断开请求，但完整的服务端恢复机制尚未实现。
- 自动测试已覆盖关键回归，但尚无完整 E2E。
- Docker Compose 仍需部署验证。

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

Open `http://localhost:5173`.

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

## Main Workflow

1. 创建小说项目和人物资料。
2. 创建世界观、卷、章和场景卡。
3. 查看生成上下文。
4. 流式生成场景草稿。
5. 草稿保存为新的 `SceneVersion`，状态停留在 `waiting_review`。
6. 作者编辑并批准正式版本。
7. 通过 API 运行一致性审查。
8. 通过 API 提取并确认人物状态、人物知识或时间线候选。
9. 下一场景只读取其时间线位置之前的正式状态和知识。

## Important API

- `GET /api/health`
- `GET /api/model/providers`
- `POST /api/model/test`
- `POST /api/model/generate`
- `GET /api/scenes/{scene_id}/context`
- `POST /api/scenes/{scene_id}/generate`
- `GET /api/workflows/runs/{run_id}`
- `POST /api/scene-versions/{version_id}/review`
- `GET /api/scene-versions/{version_id}/issues`
- `POST /api/scene-versions/{version_id}/extract-memories`
- `GET /api/scene-versions/{version_id}/candidates`
- `PATCH /api/candidates/{candidate_id}`

See [docs/api.md](docs/api.md) for the complete API list.
