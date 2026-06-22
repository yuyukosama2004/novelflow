# Changelog

## 0.7.1 - 2026-06-21

**Security and correctness hardening**

- Removed the local agent handoff file from Git tracking and added it to `.gitignore`.
- Removed the exposed API key from the local handoff. Any previously committed key must be revoked.
- Fixed workflow failures being overwritten as `done`.
- Prevented partial failed generations from being saved as successful scene versions.
- Kept successful generated drafts in `waiting_review` until explicit version approval.
- Limited character state and learned knowledge context to the current scene timeline.
- Fixed confirmed/believed character knowledge classification.
- Made memory candidate approval idempotent and validated terminal state transitions.
- Derived memory project and timeline metadata from canonical database relations.
- Added confirmed character-knowledge candidate application.
- Added structured JSON validation and bounded repair retries for review and memory extraction.
- Added regression tests for workflow errors, context time boundaries, candidate idempotency, and structured output repair.
- Corrected README and handoff claims: the current workflow is an explicit async state machine, not LangGraph.

## 0.7.0 - 2026-06-18

**Backend workflow prototype**

- Added documentation for the model, context, review, and memory APIs.
- Added a persisted async scene-writing state machine.
- Added backend continuity-review and memory-candidate prototypes.
- This release did not complete LangGraph checkpoint/resume, frontend review/memory panels, or E2E coverage.

## 0.6.0 - 2026-06-18

**Memory Candidates and State Updates**

- Added MemoryCandidate and TimelineEvent models with migration.
- Added MemoryCurator service for LLM-based state extraction.
- Added candidate approval endpoints.

## 0.5.0 - 2026-06-18

**Continuity Review**

- Added ReviewIssue model with Alembic migration.
- Added ContinuityReviewer service for character/world constraint checks.
- Added review creation, listing, and status APIs.

## 0.4.0 - 2026-06-18

**Persisted Scene-Writing State Machine**

- Added planning and drafting workflow nodes with SSE events.
- Added WorkflowRun persistence.
- Added workflow-run query API.
- Generated output is stored as a new SceneVersion.

## 0.3.0 - 2026-06-18

**Context Builder**

- Added deterministic context assembly from the database.
- Added approved-world filtering, previous approved scene, character state, and knowledge boundaries.
- Added token estimation and the frontend ContextChecker.

## 0.2.0 - 2026-06-18

**Model Adapters and Streaming Generation**

- Added unified LLMClient abstraction.
- Added OpenAI-compatible, DeepSeek, Ollama, and FakeLLM adapters.
- Added model configuration and test APIs.
- Added SSE scene generation and the frontend SceneGenerationPanel.

## 0.1.0 - 2026-06-13

- Initialized NovelFlow monorepo structure.
- Added FastAPI infrastructure, async SQLAlchemy, Alembic, and core CRUD APIs.
- Added scene version creation, approval, Markdown export, and JSON backup.
- Added the React workspace, Tiptap editor, and initial tests.
