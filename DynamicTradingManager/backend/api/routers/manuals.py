import logging
import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.routers.common import get_mod_roots, normalize_manual_module
from api.schemas import ManualSaveRequest
from ManualManagement import (
    create_manual_definition,
    delete_manual_definition,
    load_manual_editor_data,
    save_manual_definition,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["manuals"])


@router.get("/api/manuals/editor")
async def get_manual_editor_data(scope: str = "manuals", module: str = "common"):
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
    module: str = Form("common"),
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
    
    if normalized_module == "colony":
        base_url = "/static/manuals-colony"
        mod_id = "DynamicColonies"
    elif normalized_module == "currency":
        base_url = "/static/manuals-currency"
        mod_id = "CurrencyExpanded"
    else:
        base_url = "/static/manuals"
        mod_id = "DynamicTradingCommon"

    assets_root = get_manual_assets_root(mod_id) / manual_id
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
