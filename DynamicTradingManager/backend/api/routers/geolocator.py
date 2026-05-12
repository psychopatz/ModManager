import logging

from fastapi import APIRouter, HTTPException

from api.routers.common import serialize_workshop_projects
from api.schemas import GeolocatorGenerateRequest, GeolocatorInspectRequest
from GeolocatorManagement.service import generate_registry_files, inspect_source_path, list_workshop_sources
from ItemManagement.task_manager import manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["geolocator"])


@router.get("/api/geolocator/targets")
async def get_geolocator_targets():
    return serialize_workshop_projects()


@router.get("/api/geolocator/workshop-sources")
async def get_geolocator_workshop_sources(root: str | None = None, target: str | None = None, module: str = "DynamicTradingCommon"):
    try:
        return list_workshop_sources(root, target=target, module=module)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to list workshop map sources for root: %s", root)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/geolocator/inspect")
async def inspect_geolocator_source(request: GeolocatorInspectRequest):
    try:
        return inspect_source_path(request.source_path, target=request.target, module=request.module)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to inspect geolocator source: %s", request.source_path)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/geolocator/generate")
async def generate_geolocator_registry(request: GeolocatorGenerateRequest):
    try:
        inspect_source_path(request.source_path, target=request.target, module=request.module)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to validate geolocator generation request: %s", request.source_path)
        raise HTTPException(status_code=500, detail=str(exc))

    task_id = manager.create_task(
        "Generate Geolocator Registry",
        generate_registry_files,
        request.source_path,
        request.target,
        request.module,
    )
    return {"task_id": task_id}
