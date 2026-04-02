import logging

from fastapi import APIRouter, HTTPException

from api.routers.common import clear_items_cache
from api.schemas import BlacklistItemRequest, ItemOverrideRequest
from ItemManagement import add_item_to_blacklist, reload_blacklist
from ItemManagement.parse import load_blacklist
from ItemManagement.parse.overrides import load_overrides, save_overrides, validate_override

logger = logging.getLogger(__name__)
router = APIRouter(tags=["blacklist-overrides"])


@router.get("/api/blacklist")
async def get_blacklist():
    return load_blacklist()


@router.post("/api/blacklist/item")
async def add_blacklist_item(request: BlacklistItemRequest):
    try:
        blacklist = add_item_to_blacklist(request.item_id)
        reload_blacklist()
        clear_items_cache()
        return {
            "success": True,
            "item_id": request.item_id,
            "blacklist": blacklist,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error adding %s to blacklist: %s", request.item_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/overrides")
async def get_overrides():
    try:
        overrides = load_overrides()
        return {
            "overrides": overrides,
            "by_item": {override.get("item"): override for override in overrides if override.get("item")},
        }
    except Exception as exc:
        logger.error("Error loading overrides: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/api/overrides/item")
async def save_item_override(request: ItemOverrideRequest):
    try:
        override = {"item": request.item_id}
        if request.base_price is not None:
            override["basePrice"] = request.base_price
        if request.tags:
            override["tags"] = request.tags
        if request.stock_min is not None or request.stock_max is not None:
            override["stockRange"] = {}
            if request.stock_min is not None:
                override["stockRange"]["min"] = request.stock_min
            if request.stock_max is not None:
                override["stockRange"]["max"] = request.stock_max
        if request.description:
            override["description"] = request.description

        if len(override) == 1:
            raise HTTPException(status_code=400, detail="Override must include at least one field to save.")

        is_valid, error = validate_override(override)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error or "Invalid override")

        overrides = [entry for entry in load_overrides() if entry.get("item") != request.item_id]
        overrides.append(override)
        save_overrides(overrides)
        return {
            "success": True,
            "override": override,
            "overrides": overrides,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error saving override for %s: %s", request.item_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/api/overrides/item/{item_id}")
async def delete_item_override(item_id: str):
    try:
        overrides = load_overrides()
        next_overrides = [entry for entry in overrides if entry.get("item") != item_id]
        if len(next_overrides) == len(overrides):
            raise HTTPException(status_code=404, detail="Override not found")

        save_overrides(next_overrides)
        return {
            "success": True,
            "item_id": item_id,
            "overrides": next_overrides,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error deleting override for %s: %s", item_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))
