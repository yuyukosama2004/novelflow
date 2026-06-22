# API

Base URL: `http://localhost:8000/api`

## Health

- `GET /health`

## Projects

- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`
- `PATCH /projects/{project_id}`
- `DELETE /projects/{project_id}`

## Characters

- `POST /projects/{project_id}/characters`
- `GET /projects/{project_id}/characters`
- `GET /characters/{character_id}`
- `PATCH /characters/{character_id}`
- `DELETE /characters/{character_id}`
- `POST /characters/{character_id}/states`
- `GET /characters/{character_id}/states`
- `GET /characters/{character_id}/current-state`
- `POST /characters/{character_id}/knowledge`
- `GET /characters/{character_id}/knowledge`

## World Entries

- `POST /projects/{project_id}/world-entries`
- `GET /projects/{project_id}/world-entries`
- `GET /world-entries/{entry_id}`
- `PATCH /world-entries/{entry_id}`
- `DELETE /world-entries/{entry_id}`
- `POST /world-entries/{entry_id}/approve`
- `POST /world-entries/{entry_id}/deprecate`

## Manuscript

- `POST /projects/{project_id}/volumes`
- `GET /projects/{project_id}/volumes`
- `POST /volumes/{volume_id}/chapters`
- `GET /volumes/{volume_id}/chapters`
- `POST /chapters/{chapter_id}/scenes`
- `GET /chapters/{chapter_id}/scenes`
- `GET /scenes/{scene_id}`
- `PATCH /scenes/{scene_id}`
- `DELETE /scenes/{scene_id}`
- `POST /scenes/reorder`

## Scene Versions

- `GET /scenes/{scene_id}/versions`
- `POST /scenes/{scene_id}/versions`
- `GET /scene-versions/{version_id}`
- `POST /scenes/{scene_id}/approve-version`
- `GET /scenes/{scene_id}/compare?left={id}&right={id}`

## Model Configuration

- `GET /model/providers` - list configured model providers and their status
- `POST /model/test` - test model connection and generate a test message
- `POST /model/generate` - generate text via configured model provider

## Context

- GET /scenes/{scene_id}/context - get assembled generation context (characters, world facts, previous scene, token estimate)

## Workflows

- `POST /scenes/{scene_id}/generate` - SSE scene generation; successful output is saved as an unapproved SceneVersion with workflow status `waiting_review`

## Workflow Runs

- `GET /workflows/runs/{run_id}` - query workflow run status

## Review

- `POST /scene-versions/{version_id}/review` - run continuity review
- `GET /scene-versions/{version_id}/issues` - list review issues
- `PATCH /issues/{issue_id}` - update issue status (`accepted`, `ignored`, `false_positive`)

## Memory

- `POST /scene-versions/{version_id}/extract-memories` - extract memory candidates
- `GET /scene-versions/{version_id}/candidates` - list memory candidates
- `PATCH /candidates/{candidate_id}` - approve/reject a pending candidate; repeated identical terminal requests are idempotent

## Exports

- `GET /projects/{project_id}/exports/markdown`
- `GET /projects/{project_id}/exports/json`
