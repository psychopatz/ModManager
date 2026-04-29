import logging
import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from api.routers.common import get_mod_roots, normalize_manual_module
from api.schemas import ManualSaveRequest
from ManualManagement import (
    create_manual_definition,
    delete_manual_definition,
    load_manual_editor_data,
    save_manual_definition,
)
from GitManagement.diff_handler import get_batched_git_log

logger = logging.getLogger(__name__)
router = APIRouter(tags=["manuals"])


@router.get("/api/manuals/editor")
async def get_manual_editor_data(scope: str = "manuals", module: str = "DynamicTradingCommon"):
    try:
        return load_manual_editor_data(scope=scope, module=normalize_manual_module(module))
    except Exception as exc:
        logger.error("Error loading manual editor data: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/manuals")
async def create_manual(request: ManualSaveRequest, scope: str = "manuals", module: str = "common"):
    try:
        payload = create_manual_definition(request.model_dump(), scope=scope, module=normalize_manual_module(module))
        return {
            "success": True,
            "manual": payload,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error creating manual: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/api/manuals/{manual_id}")
async def update_manual(manual_id: str, request: ManualSaveRequest, scope: str = "manuals", module: str = "common"):
    try:
        payload = save_manual_definition(manual_id, request.model_dump(), scope=scope, module=normalize_manual_module(module))
        return {
            "success": True,
            "manual": payload,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error saving manual %s: %s", manual_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/api/manuals/{manual_id}")
async def remove_manual(manual_id: str, scope: str = "manuals", module: str = "common"):
    try:
        delete_manual_definition(manual_id, scope=scope, module=normalize_manual_module(module))
        return {
            "success": True,
            "manual_id": manual_id,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Error deleting manual %s: %s", manual_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/manuals/images")
async def upload_manual_image(
    manual_id: str = Form(...),
    module: str = Form("DynamicTradingCommon"),
    file: UploadFile = File(...),
):
    def _resolve_extension(upload: UploadFile, original_name: str) -> str:
        suffix = Path(original_name).suffix.lower()
        if suffix:
            return suffix

        content_type = (upload.content_type or "").lower()
        if content_type in {"image/jpeg", "image/jpg"}:
            return ".jpg"
        if content_type == "image/png":
            return ".png"
        if content_type == "image/webp":
            return ".webp"
        if content_type == "image/gif":
            return ".gif"
        return ".png"

    def _build_unique_name(assets_dir: Path, upload: UploadFile) -> str:
        original_name = Path(upload.filename or "manual-image").name
        stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(original_name).stem).strip("-").lower() or "manual-image"
        extension = _resolve_extension(upload, original_name)

        while True:
            candidate = f"{stem}_{uuid4().hex[:10]}{extension}"
            if not (assets_dir / candidate).exists():
                return candidate

    mod_root, colonies_root, currency_root = get_mod_roots()

    normalized_module = normalize_manual_module(module)
    from config.paths import get_manual_assets_root
    
    # We resolve the actual Mod ID and base URL dynamically
    mod_id = normalized_module # We assume normalized_module is the Mod ID (lowercased)
    
    # Resolve the proper-cased Mod ID for path finding
    from ProjectManagement.projects import get_flattened_modules
    actual_mod_id = next((m["id"] for m in get_flattened_modules() if m["id"].lower() == normalized_module.lower()), "DynamicTradingCommon")
    
    base_url = "/static/manuals"
    if normalized_module.lower() == "dynamiccolonies":
        base_url = "/static/manuals-colony"
    elif normalized_module.lower() == "currencyexpanded":
        base_url = "/static/manuals-currency"

    assets_root = get_manual_assets_root(actual_mod_id) / manual_id
    assets_root.mkdir(parents=True, exist_ok=True)
    filename = _build_unique_name(assets_root, file)
    file_path = assets_root / filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {
            "success": True,
            "path": f"media/ui/Manuals/{manual_id}/{filename}",
            "url": f"{base_url}/{manual_id}/{filename}",
        }
    except Exception as exc:
        logger.error("Error uploading manual image for %s: %s", manual_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/manuals/batch/git-history")
async def get_batch_git_history(
    since: str = "2026-03-27",
    until: str | None = None,
    branch: str = "develop",
    module: str | None = None,
):
    try:
        data = get_batched_git_log(since, branch, until, module)
        return {
            "success": True,
            "history": data
        }
    except Exception as exc:
        logger.error("Error fetching batched git history: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
@router.get("/assets/{module}/{manual_id}/{filename:path}")
def proxy_manual_asset(module: str, manual_id: str, filename: str):
    """Dynamically resolves and serves manual assets from the correct mod root."""
    from ManualManagement.paths import _get_manual_assets_root
    
    root = _get_manual_assets_root(module)
    asset_path = root / manual_id / filename
    
    if not asset_path.exists() or not asset_path.is_file():
        # Fallback: check if it's directly in the root (legacy or non-namespaced)
        asset_path = root / filename
        if not asset_path.exists() or not asset_path.is_file():
             raise HTTPException(status_code=404, detail=f"Asset {filename} not found for module {module}")
    
    return FileResponse(asset_path)
