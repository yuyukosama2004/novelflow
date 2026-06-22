# Database

The MVP database uses SQLite through SQLAlchemy async sessions. All core tables use string UUID primary keys and UTC timestamps.

Implemented tables:

- `novel_projects`
- `characters`
- `character_states`
- `character_knowledge`
- `world_entries`
- `volumes`
- `chapters`
- `scenes`
- `scene_versions`

Run migrations:

```powershell
cd backend
alembic upgrade head
```

Validate downgrade/upgrade:

```powershell
alembic downgrade -1
alembic upgrade head
```
