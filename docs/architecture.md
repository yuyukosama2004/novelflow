# Architecture

NovelFlow is a two-part application:

- FastAPI backend owns persistence, business rules, exports, and future model workflows.
- React frontend provides the author workspace and never receives raw model keys.

The backend is intentionally layered:

- API routers validate HTTP shape and delegate work.
- Services enforce business rules.
- Repositories isolate persistence details.
- SQLAlchemy models represent canonical story state.

The first MVP slice keeps all AI operations out of the code path. Scene text is manual, versioned, approvable, and exportable so the application is useful before model integration.
