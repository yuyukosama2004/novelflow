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
- Review and memory-candidate confirmation are currently backend APIs, not complete frontend workflows.

## Planned Upgrade

1. Introduce LangGraph only when checkpoint/resume behavior is implemented and tested.
2. Add explicit resume, cancel, approve, and reject workflow commands.
3. Add SSE reconnection using persisted `run_id`.
4. Add FakeLLM integration tests for event order and failure recovery.
5. Add frontend review and memory-candidate panels.
