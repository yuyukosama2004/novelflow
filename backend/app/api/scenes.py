from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.database.session import get_session
from app.schemas.manuscript import (
    ApproveVersionRequest,
    ChapterCreate,
    ChapterRead,
    ChapterUpdate,
    ImpactReportRead,
    ImpactReportUpdate,
    SceneCreate,
    SceneRead,
    SceneReorderRequest,
    SceneUpdate,
    SceneVersionCreate,
    SceneVersionRead,
    SceneWorkingDraftRead,
    SceneWorkingDraftUpdate,
    VersionCompareRead,
    VolumeCreate,
    VolumeRead,
    VolumeUpdate,
)
from app.services.manuscript_service import ManuscriptService

router = APIRouter()


@router.post("/projects/{project_id}/volumes")
async def create_volume(
    project_id: str,
    payload: VolumeCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    volume = await ManuscriptService(session).create_volume(project_id, payload)
    return success(VolumeRead.model_validate(volume), request)


@router.get("/projects/{project_id}/volumes")
async def list_volumes(
    project_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    volumes = await ManuscriptService(session).list_volumes(project_id)
    return success([VolumeRead.model_validate(item) for item in volumes], request)


@router.patch("/volumes/{volume_id}")
async def update_volume(
    volume_id: str,
    payload: VolumeUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    volume = await ManuscriptService(session).update_volume(volume_id, payload)
    return success(VolumeRead.model_validate(volume), request)


@router.post("/volumes/{volume_id}/chapters")
async def create_chapter(
    volume_id: str,
    payload: ChapterCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    chapter = await ManuscriptService(session).create_chapter(volume_id, payload)
    return success(ChapterRead.model_validate(chapter), request)


@router.get("/volumes/{volume_id}/chapters")
async def list_chapters(
    volume_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    chapters = await ManuscriptService(session).list_chapters(volume_id)
    return success([ChapterRead.model_validate(item) for item in chapters], request)


@router.patch("/chapters/{chapter_id}")
async def update_chapter(
    chapter_id: str,
    payload: ChapterUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    chapter = await ManuscriptService(session).update_chapter(chapter_id, payload)
    return success(ChapterRead.model_validate(chapter), request)


@router.post("/chapters/{chapter_id}/scenes")
async def create_scene(
    chapter_id: str,
    payload: SceneCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    scene = await ManuscriptService(session).create_scene(chapter_id, payload)
    return success(SceneRead.model_validate(scene), request)


@router.get("/chapters/{chapter_id}/scenes")
async def list_scenes(
    chapter_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    scenes = await ManuscriptService(session).list_scenes(chapter_id)
    return success([SceneRead.model_validate(item) for item in scenes], request)


@router.get("/scenes/{scene_id}")
async def get_scene(
    scene_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    scene = await ManuscriptService(session).get_scene(scene_id)
    return success(SceneRead.model_validate(scene), request)


@router.patch("/scenes/{scene_id}")
async def update_scene(
    scene_id: str,
    payload: SceneUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    scene = await ManuscriptService(session).update_scene(scene_id, payload)
    return success(SceneRead.model_validate(scene), request)


@router.post("/scenes/{scene_id}/clear-stale")
async def clear_scene_stale(
    scene_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    scene = await ManuscriptService(session).clear_scene_stale(scene_id)
    return success(SceneRead.model_validate(scene), request)


@router.get("/projects/{project_id}/impact-reports")
async def list_impact_reports(
    project_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    reports = await ManuscriptService(session).list_impact_reports(project_id)
    return success([ImpactReportRead.model_validate(item) for item in reports], request)


@router.patch("/impact-reports/{report_id}")
async def update_impact_report(
    report_id: str,
    payload: ImpactReportUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    report = await ManuscriptService(session).update_impact_report(
        report_id,
        payload.status,
    )
    return success(ImpactReportRead.model_validate(report), request)


@router.delete("/scenes/{scene_id}")
async def delete_scene(
    scene_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await ManuscriptService(session).delete_scene(scene_id)
    return success({"deleted": True}, request)


@router.post("/scenes/reorder")
async def reorder_scenes(
    payload: SceneReorderRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    scenes = await ManuscriptService(session).reorder_scenes(payload)
    return success([SceneRead.model_validate(item) for item in scenes], request)


@router.get("/scenes/{scene_id}/versions")
async def list_scene_versions(
    scene_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    versions = await ManuscriptService(session).list_versions(scene_id)
    return success([SceneVersionRead.model_validate(item) for item in versions], request)


@router.get("/scenes/{scene_id}/working-draft")
async def get_scene_working_draft(
    scene_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    draft = await ManuscriptService(session).get_working_draft(scene_id)
    if draft is None:
        return success(
            SceneWorkingDraftRead(
                scene_id=scene_id,
                content_json={"type": "doc", "content": [{"type": "paragraph"}]},
                content_markdown="",
                revision=0,
                updated_at=None,
            ),
            request,
        )
    return success(SceneWorkingDraftRead.model_validate(draft), request)


@router.put("/scenes/{scene_id}/working-draft")
async def update_scene_working_draft(
    scene_id: str,
    payload: SceneWorkingDraftUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    draft = await ManuscriptService(session).update_working_draft(scene_id, payload)
    return success(SceneWorkingDraftRead.model_validate(draft), request)


@router.post("/scenes/{scene_id}/versions")
async def create_scene_version(
    scene_id: str,
    payload: SceneVersionCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    version = await ManuscriptService(session).create_version(scene_id, payload)
    return success(SceneVersionRead.model_validate(version), request)


@router.get("/scene-versions/{version_id}")
async def get_scene_version(
    version_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    version = await ManuscriptService(session).get_version(version_id)
    return success(SceneVersionRead.model_validate(version), request)


@router.post("/scenes/{scene_id}/approve-version")
async def approve_scene_version(
    scene_id: str,
    payload: ApproveVersionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    scene = await ManuscriptService(session).approve_version(scene_id, payload)
    return success(SceneRead.model_validate(scene), request)


@router.post("/scenes/{scene_id}/complete")
async def complete_scene(
    scene_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    scene = await ManuscriptService(session).complete_scene(scene_id)
    return success(SceneRead.model_validate(scene), request)


@router.get("/scenes/{scene_id}/compare")
async def compare_scene_versions(
    scene_id: str,
    request: Request,
    left: str = Query(),
    right: str = Query(),
    session: AsyncSession = Depends(get_session),
) -> dict:
    left_version, right_version, changed = await ManuscriptService(session).compare_versions(
        scene_id,
        left,
        right,
    )
    return success(
        VersionCompareRead(
            left=SceneVersionRead.model_validate(left_version),
            right=SceneVersionRead.model_validate(right_version),
            changed=changed,
        ),
        request,
    )
