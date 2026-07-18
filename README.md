# NovelFlow

NovelFlow 是面向本地单用户的 AI 长篇小说创作工作台。它把“生成草稿”和“写入正史”严格分开：AI 可以协助构思、生成和审查，但不能自动改写故事正史、人物状态或后续正文。

## 核心原则

- 作者始终拥有最终决定权；AI 输出默认是草稿或候选项。
- 只有作者明确批准，版本、记忆候选和故事事实才会进入正式状态。
- 替换正式稿会标记所有叙事后续场景为“需复查”，系统不会擅自改写它们。
- 写作上下文遵循故事时间与知识边界，避免角色提前获知后续事件。
- 前端用户文案使用中文；后端 API 枚举保持英文，并由前端映射显示。

## 已实现能力

### 创作与世界设定

- 创作向导：从点子、世界观、人物、大纲或直接正文进入访谈式共创。
- 故事圣经：统一维护核心概念、人物、人物关系、世界观、大纲和时间线。
- 大纲生成：根据故事圣经生成卷、章、场景结构，作者确认后再写入。
- 快速创作：输入一个点子，快速建立基础项目结构并进入普通工作台。

### 写作工作台

- Tiptap 正文编辑器、场景卡编辑、写作辅助和 AI 场景生成。
- 编辑内容自动保存为工作草稿；手动“保存版本”才会创建不可变的场景版本。
- 场景版本以规范化 Tiptap JSON 为权威文档，Markdown、纯文本、schema 版本和内容哈希由统一编解码契约生成；旧客户端只提交 Markdown 时仍会自动转换。
- 桌面端提供可调宽三栏工作台；中小屏幕将大纲和创作辅助切换为抽屉，专注模式只保留正文。
- 正文可在现代无衬线与书籍衬线之间切换，并支持 14/16/18/20px、三档行距和三档版心；偏好只保存在本机，不会写入正文或导出文件。
- 提供撤销、重做、加粗、斜体、二级标题、引用和列表等基础格式工具，现有 Markdown 版本格式保持兼容。
- 右侧中文分组为“创作”“检查”“资料”；版本历史集中展示 `vN / 来源 / 梗概 / 字数`，版本审批也在资料区完成。

### 正史、审查与上下文

- AI 生成场景后创建草稿版本；正史采用必须由作者手动确认。
- 每次正式批准都会创建不可变的 `CanonCommit`，记录前序提交、规范化内容哈希、场景契约和审查快照；替换历史形成可追溯的线性提交链。
- 数据库阻止修改已保存版本的正文与生成来源；完整性审计会同时核对实际正文、版本文档哈希、兼容投影和 Canon 提交链。
- 正式稿导出和“上一场景”写作上下文以最新 Canon 提交为准，即使兼容投影发生漂移也不会读取旧稿。
- 一致性审查发现问题后，可按条处理；阻塞问题允许填写原因后强制批准。
- 记忆提取产生候选项，作者可确认、修改或拒绝；AI 不会自动写入正史。
- 场景上下文可关联角色与世界观条目，并受 POV、故事时间、显式关系和项目规则限制。
- 长正文审查与记忆提取按完整段落分块，记录证据位置并去重。
- 替换既有正式稿会使相关旧记忆失效，生成影响报告并标记后续场景待复查。

### 生成可靠性

- 场景生成使用 SSE 流式输出。
- 生成任务持久化为 `WorkflowRun`，带数据库活动任务唯一锁和递增事件 ID。
- 页面刷新后可恢复任务状态与已有草稿；取消操作会同步写回后端。

## 技术栈

- 后端：Python 3.10+、FastAPI、Pydantic v2、SQLAlchemy 2（异步）、Alembic、SQLite
- 前端：React 18、TypeScript、Vite、Tailwind CSS、Tiptap、TanStack Query
- 模型：DeepSeek、兼容 OpenAI API 的服务、Ollama、FakeLLM
- 质量工具：pytest、Ruff、mypy、Vitest、React Testing Library、ESLint、Prettier

## 本地启动

后端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload --port 8000
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

打开 `http://127.0.0.1:5173`。前端默认使用 `http://127.0.0.1:8000/api`，后端同时允许 `http://localhost:5173` 与 `http://127.0.0.1:5173` 的本地开发请求。

## 模型与数据安全

不要把 API Key 写入项目文件、Markdown、日志或 Git。建议通过 Windows 用户环境变量设置：

```powershell
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "your-key", "User")
```

模型设置页可以保存不同 Provider 的连接配置。当前项目仅面向本地单用户，API Key 会以明文保存在本机 SQLite 数据库中；数据库文件已被 Git 忽略，但这不等同于加密。不要复制数据库到公开位置，也不要将当前存储方式直接用于多人或公网部署。

若密钥曾被提交到 Git，应立即在服务商后台撤销并重新生成；仅删除文件不足以使历史记录失效。

## 数据库备份与恢复

安装后端后，可以在数据库仍被 NovelFlow 使用时创建一致性 SQLite 备份。备份完成前会执行完整性检查，默认不会覆盖已有文件：

```powershell
cd backend
novelflow-db create --output .\backups\novelflow-2026-07-16.db
novelflow-db verify .\backups\novelflow-2026-07-16.db
```

恢复默认写入新的数据库路径，便于先验证恢复结果再替换现有数据：

```powershell
novelflow-db restore .\backups\novelflow-2026-07-16.db --output .\restored\novelflow.db
```

也可以使用 `python -m app.platform.backup` 调用相同命令。数据库迁移、批量导入或大规模正史变更前应先创建备份。

## 推荐创作流程

1. 新建项目，选择创作入口或使用“快速创作”。
2. 通过访谈式共创补充主题、冲突、世界规则和人物动机。
3. 编辑并确认候选内容，建立故事圣经与大纲。
4. 编写或生成场景草稿，按需保存不可变版本。
5. 在“资料 → 版本历史”查看版本，审查后再批准正式稿；阻塞问题如需通过，必须填写原因。
6. 提取记忆候选，由作者决定哪些人物状态、知识、世界观或时间线更新成为正史。
7. 遇到正式稿替换时，查看影响报告并复查所有被标记的后续场景。

场景的叙事顺序由卷、章、场景的 `sequence_no` 决定，故事内时间使用 `story_time_order`。后续场景获得的知识会被标记为不可提前泄露；写作上下文不会将这些信息交给较早的场景。

## 版本与发布

- 当前稳定版本：[v0.2.0](https://github.com/yuyukosama2004/novelflow/releases/tag/v0.2.0)（2026-07-16）。
- 发布标签只指向经过完整前端验证的 `main`；历史开发分支在合入后会清理，日常使用以 `main` 和 Release 为准。

## 质量检查

后端：

```powershell
cd backend
ruff check .
ruff format --check .
mypy app
pytest tests -v
python scripts/smoke.py
```

前端：

```powershell
cd frontend
npm run format
npm run lint
npm run test
npm run build
node scripts/smoke.mjs
```

当前主线已验证：从空 SQLite 数据库执行全部 Alembic 迁移、重复运行初始化数据、后端与前端测试、静态检查、构建，以及两端本地 smoke 启动。

## 常用 API

- `GET /api/health`
- `GET /api/model/providers`
- `POST /api/model/test`
- `POST /api/model/generate`
- `GET /api/scenes/{scene_id}/context`
- `POST /api/scenes/{scene_id}/generate`
- `GET` / `PUT /api/scenes/{scene_id}/working-draft`
- `GET` / `PUT /api/scenes/{scene_id}/context-links`
- `POST /api/scenes/{scene_id}/versions`
- `GET /api/scenes/{scene_id}/canon-commits`
- `GET /api/projects/{project_id}/canon-integrity`
- `GET /api/workflows/runs/{run_id}`
- `GET /api/projects/{project_id}/impact-reports`
- `POST /api/scenes/{scene_id}/clear-stale`
- `POST /api/scene-versions/{version_id}/review`
- `POST /api/scene-versions/{version_id}/extract-memories`
- `GET /api/scene-versions/{version_id}/issues`
- `GET /api/scene-versions/{version_id}/candidates`
- `PATCH /api/candidates/{candidate_id}`

## 文档与仓库规则

公开仓库只保留本文件 `README.md` 作为 Markdown 文档入口。开发计划、交接记录、本机脚本和内部资料放在被忽略的 `local-dev-docs/`；`docs/`、`local-dev-docs/` 与 `CLAUDE.md` 都不会随 Git 推送。

构建生成的 `*.egg-info/`、本地数据库、日志、`.env` 与依赖目录也已被忽略，不应提交。
