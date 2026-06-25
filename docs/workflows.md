# Workflows

## Current Implementation

Scene generation currently uses a persisted explicit async state machine:

```text
planning -> drafting -> waiting_review
```

Errors terminate in `error`. Client cancellation records `cancelled` when the server observes the cancelled stream.

Successful generation creates a new `SceneVersion` with `source_type=ai_generated`. It does not approve the version. The existing version approval API remains the author-controlled canonicalization step.

Workflow runs persist:

- provider and model metadata
- prompt snapshot
- context manifest
- plan and draft
- emitted events
- error text
- created version id

## Current Limitations

- This is not a LangGraph implementation.
- There is no checkpoint-based resume endpoint.
- There is no server-side retry-current-node endpoint.
- The frontend has no workflow resume UI.
- Review and memory-candidate confirmation have compact frontend panels with workflow-level integration tests (run review, extract, approve, reject, refresh, context invalidation), but they are not full E2E-tested workflows yet.

## Scene Version Selection

The workspace includes a Scene Version selector in the right rail. It lets the author explicitly choose which `SceneVersion` is the active target for editing-adjacent AI workflows.

### Default Selection

When a scene is selected:

- The approved version is preferred when it matches `scene.approved_version_id`.
- If no version is approved, the newest version by `version_no` is selected.
- When switching scenes, the selection resets to the new scene's default.

### What the Selection Controls

The selected version drives:

- Continuity Review panel - runs review against the selected version and lists its issues.
- Memory Candidate panel - extracts candidates from and lists candidates for the selected version.

### Selector Display

Each option shows:

- Version number, such as `v1` or `v2`.
- Source type, such as `AI`, `Draft`, or `Approved`.
- Review status when present, such as `pending` or `completed`.
- `approved` marker when the version matches the scene's approved version.
- Short summary or content preview.

A detail card below the dropdown shows the currently selected version's metadata and preview.

### Version Refresh

When a new version is created via AI generation or manual save, the version list is invalidated. Once the refreshed list includes the new version, the selector switches to it so review and memory actions target the fresh draft.

## Planned Upgrade

1. Introduce LangGraph only when checkpoint/resume behavior is implemented and tested.
2. Add explicit resume, cancel, approve, and reject workflow commands.
3. Add SSE reconnection using persisted `run_id`.
4. Add FakeLLM integration tests for event order and failure recovery.
5. Add full E2E coverage for review and memory-candidate panels.
