import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.routers.common import normalize_manual_module
from api.schemas import DonatorsSaveRequest
from ManualManagement import get_donators_definition, save_donators_definition
from ManualManagement.donators.constants import MANUAL_ID
from ManualManagement.paths import _get_manual_assets_root, _get_manual_assets_root_url

logger = logging.getLogger(__name__)
router = APIRouter(tags=["donators"])


@router.get("/api/donators")
async def get_donators():
    try:
        return get_donators_definition()
    except Exception as exc:
        logger.error("Error loading donators definition: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/api/donators")
async def save_donators(request: DonatorsSaveRequest):
    try:
        return {
            "success": True,
            "manual": save_donators_definition(request.model_dump()),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error saving donators definition: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/donators/images")
async def upload_donator_image(
    file: UploadFile = File(...),
    module: str = Form("common"),
):
    try:
        normalized_module = normalize_manual_module(module)
        assets_root = _get_manual_assets_root(normalized_module) / MANUAL_ID
        assets_root.mkdir(parents=True, exist_ok=True)

        original_name = Path(file.filename or "donator-image").name
        stem = Path(original_name).stem or "donator-image"
        suffix = Path(original_name).suffix.lower() or ".png"
        safe_stem = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in stem).strip("-").lower() or "donator-image"
        filename = f"{safe_stem}_{uuid4().hex[:10]}{suffix}"
        file_path = assets_root / filename

        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                buffer.write(chunk)

        base_url = _get_manual_assets_root_url(normalized_module)
        return {
            "success": True,
            "path": f"media/ui/Manuals/{MANUAL_ID}/{filename}",
            "url": f"{base_url}/{MANUAL_ID}/{filename}",
        }
    except Exception as exc:
        logger.error("Error uploading donator image: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
