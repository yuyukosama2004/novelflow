# Development

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload --port 8000
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Checks

Backend:

```powershell
pytest
ruff check .
ruff format --check .
mypy app
python scripts/smoke.py
```

Frontend:

```powershell
npm run lint
npm run test
npm run build
node scripts/smoke.mjs
```
