import logging

from fastapi import APIRouter, HTTPException

from api.routers.common import serialize_workshop_projects
from api.schemas import (
    GeolocatorGenerateRequest,
    GeolocatorInspectRequest,
    GeolocatorVanillaGenerateRequest,
)
from GeolocatorManagement.service import (
    generate_registry_files,
    inspect_source_path,
    list_workshop_sources,
)
from GeolocatorManagement.Vanilla.service import build_vanilla_map_definitions, generate_vanilla_registry
from ItemManagement.task_manager import manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["geolocator"])


@router.get("/api/geolocator/targets")
async def get_geolocator_targets():
    return serialize_workshop_projects()


@router.get("/api/geolocator/vanilla-maps")
async def get_vanilla_maps(target: str | None = None, module: str = "DynamicTradingCommon"):
    try:
        return build_vanilla_map_definitions(target=target, module=module)
    except Exception as exc:
        logger.exception("Failed to build vanilla map definitions")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/geolocator/vanilla-generate")
async def generate_vanilla_registry_endpoint(request: GeolocatorVanillaGenerateRequest):
    try:
        task_id = manager.create_task(
            "Generate Vanilla Geolocator Registry",
            generate_vanilla_registry,
            request.target,
            request.module,
            request.map_ids,
        )
        return {"task_id": task_id}
    except Exception as exc:
        logger.exception("Failed to start vanilla generation")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/geolocator/workshop-sources")
async def get_geolocator_workshop_sources(
    root: str | None = None,
    target: str | None = None,
    module: str = "DynamicTradingCommon",
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    llm_thinking: bool = False,
    llm_reasoning_effort: str | None = None,
):
    try:
        llm_config = None
        if llm_base_url and llm_model:
            llm_config = {
                "base_url": llm_base_url,
                "api_key": llm_api_key or "",
                "model": llm_model,
                "thinking": llm_thinking,
                "reasoning_effort": llm_reasoning_effort or "medium",
            }
        return list_workshop_sources(root, target=target, module=module, llm_config=llm_config)
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
        return inspect_source_path(request.source_path, target=request.target, module=request.module, llm_config=request.llm_config)
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
        inspect_source_path(request.source_path, target=request.target, module=request.module, llm_config=request.llm_config)
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
        request.llm_config,
    )
    return {"task_id": task_id}
