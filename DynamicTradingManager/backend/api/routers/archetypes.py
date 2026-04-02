import logging

from fastapi import APIRouter, HTTPException

from api.schemas import ArchetypeSaveRequest
from Simulation.archetype_editor import load_archetype_editor_data, save_archetype_definition

logger = logging.getLogger(__name__)
router = APIRouter(tags=["archetypes"])


@router.get("/api/archetypes/editor")
async def get_archetype_editor_data():
    try:
        return load_archetype_editor_data()
    except Exception as exc:
        logger.error("Error loading archetype editor data: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/api/archetypes/{archetype_id}/allocations")
async def update_archetype_allocations(archetype_id: str, request: ArchetypeSaveRequest):
    try:
        payload = save_archetype_definition(
            archetype_id,
            request.model_dump(),
        )
        return {
            "success": True,
            "archetype_id": archetype_id,
            "archetype": payload,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error saving allocations for %s: %s", archetype_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))
