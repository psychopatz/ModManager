import logging
import os
import shutil
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from api.routers.common import get_workshop_project_or_404, serialize_workshop_projects
from api.schemas import WorkshopPushRequest
from ItemManagement.task_manager import manager
from WorkshopManagement.workshop import (
    fetch_steam_metadata,
    parse_workshop_txt,
    prepare_staging,
    run_full_workshop_push,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["workshop"])


@router.post("/api/workshop/prepare")
async def trigger_workshop_prepare(target: Optional[str] = None):
    project = get_workshop_project_or_404(target)
    mod_root = project["path"]
    staging_dir = mod_root / "upload_staging"

    success = prepare_staging(mod_root, staging_dir)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to prepare staging directory")

    return {"success": True, "staging_dir": str(staging_dir)}


@router.get("/api/workshop/targets")
async def get_workshop_targets():
    return serialize_workshop_projects()


@router.get("/api/workshop/metadata")
async def get_workshop_metadata(target: Optional[str] = None):
    project = get_workshop_project_or_404(target)
    mod_root = project["path"]
    workshop_txt_path = mod_root / "workshop.txt"
    return {
        **parse_workshop_txt(workshop_txt_path),
        "target": project["key"],
        "project_name": project["name"],
        "project_title": project["title"],
    }


@router.get("/api/workshop/sync")
async def sync_workshop_metadata(target: Optional[str] = None, item_id: Optional[str] = None):
    project = get_workshop_project_or_404(target)
    mod_root = project["path"]
    local_meta = parse_workshop_txt(mod_root / "workshop.txt")
    resolved_item_id = item_id or local_meta.get("id", "")
    if not resolved_item_id:
        raise HTTPException(status_code=400, detail="This project has no workshop ID yet.")

    steam_meta = fetch_steam_metadata(resolved_item_id)
    if not steam_meta:
        raise HTTPException(status_code=500, detail="Failed to fetch data from Steam Web API")
    return {**steam_meta, "target": project["key"], "project_name": project["name"]}


@router.get("/api/workshop/preview")
async def get_workshop_preview(target: Optional[str] = None):
    project = get_workshop_project_or_404(target)
    preview_path = project["path"] / "preview.png"
    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="Preview image not found for this project.")
    return FileResponse(preview_path)


@router.post("/api/workshop/image")
async def upload_workshop_image(file: UploadFile = File(...), target: Optional[str] = None):
    project = get_workshop_project_or_404(target)
    mod_root = project["path"]
    preview_path = mod_root / "preview.png"

    try:
        with open(preview_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"success": True, "filename": "preview.png", "target": project["key"]}
    except Exception as exc:
        logger.error("Error uploading image: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/workshop/push")
async def trigger_workshop_push(request: WorkshopPushRequest):
    project = get_workshop_project_or_404(request.target)
    mod_root = project["path"]
    staging_dir = mod_root / "upload_staging"
    vdf_path = mod_root / "workshop_update.vdf"
    steamcmd_path = os.getenv("STEAM_CMD_PATH", os.getenv("STEAMCMD_PATH", "/home/psychopatz/Desktop/Apps/SteamCMD/steamcmd.sh"))

    task_id = manager.create_task(
        "Internal Workshop Sync & Push",
        run_full_workshop_push,
        mod_root,
        staging_dir,
        vdf_path,
        steamcmd_path,
        request.username,
        request.password,
        request.dict(),
    )

    return {"task_id": task_id, "target": project["key"], "project_name": project["name"]}
