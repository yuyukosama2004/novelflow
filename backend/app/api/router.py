from __future__ import annotations

from fastapi import APIRouter

from app.api import (
    bible,
    characters,
    context,
    exports,
    health,
    interview,
    memory,
    model_profiles,
    outline,
    projects,
    quick_creation,
    review,
    scenes,
    workflows,
    world_entries,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(quick_creation.router, tags=["quick-creation"])
api_router.include_router(characters.router, tags=["characters"])
api_router.include_router(world_entries.router, tags=["world"])
api_router.include_router(scenes.router, tags=["manuscript"])
api_router.include_router(exports.router, tags=["exports"])
api_router.include_router(model_profiles.router, tags=["models"])
api_router.include_router(workflows.router, tags=["workflows"])
api_router.include_router(context.router, tags=["context"])
api_router.include_router(review.router, tags=["review"])
api_router.include_router(memory.router, tags=["memory"])
api_router.include_router(interview.router, tags=["interview"])
api_router.include_router(bible.router, tags=["bible"])
api_router.include_router(outline.router, tags=["outline"])
