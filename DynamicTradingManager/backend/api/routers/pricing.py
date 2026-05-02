import logging
import threading

from fastapi import APIRouter, HTTPException

from api.routers.common import get_items
from api.schemas import PricingConfigRequest, PricingPreviewRequest, PricingTagPreviewRequest
from ItemManagement import (
    build_pricing_audit,
    build_pricing_tag_catalog,
    calculate_price_details,
    generate_tags,
    load_pricing_config,
    preview_pricing_tag,
    save_pricing_config,
    warm_pricing_tag_cache,
)
from ItemManagement.commons.lua_handler.records import tags_list_to_dict
from ItemManagement.commons.vanilla_loader import get_translated_name

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pricing"])


def _finish_pricing_page_warm():
    try:
        warmed = warm_pricing_tag_cache()
        logger.info(
            "Warmed tag pricing cache for %s items across %s tags",
            warmed["items"],
            warmed["tags"],
        )
    except Exception as exc:
        logger.warning("Unable to warm tag pricing cache on startup: %s", exc)


@router.on_event("startup")
async def warm_pricing_page_cache():
    try:
        catalog = build_pricing_tag_catalog()
        logger.info("Warmed tag pricing catalog for %s tags", len(catalog.get("tags", [])))
    except Exception as exc:
        logger.warning("Unable to warm tag pricing catalog on startup: %s", exc)
        return

    threading.Thread(target=_finish_pricing_page_warm, daemon=True).start()


@router.get("/api/pricing/config")
async def get_pricing_config():
    try:
        return load_pricing_config()
    except Exception as exc:
        logger.error("Error loading pricing config: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/api/pricing/config")
async def update_pricing_config(request: PricingConfigRequest):
    try:
        return save_pricing_config(request.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error saving pricing config: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/pricing/preview")
async def preview_pricing(request: PricingPreviewRequest):
    try:
        items = get_items()
        props = request.props or items.get(request.item_id)
        if not props:
            raise HTTPException(status_code=404, detail=f"Unknown item: {request.item_id}")

        tags_list = request.tags or generate_tags(request.item_id, props)
        tags_dict = tags_list_to_dict(tags_list)
        details = calculate_price_details(request.item_id, props, tags_dict)

        return {
            "item_id": request.item_id,
            "name": get_translated_name(request.item_id, props),
            "tags": tags_list,
            "price": details["price"],
            "details": details,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error previewing pricing for %s: %s", request.item_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/pricing/audit")
async def get_pricing_audit(limit: int = 20):
    try:
        return build_pricing_audit(get_items(), outlier_limit=limit)
    except Exception as exc:
        logger.error("Error building pricing audit: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/pricing/tags")
async def get_pricing_tags():
    try:
        return build_pricing_tag_catalog()
    except Exception as exc:
        logger.error("Error building pricing tag catalog: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/pricing/tags/preview")
async def preview_pricing_tags(request: PricingTagPreviewRequest):
    try:
        return preview_pricing_tag(
            None,
            request.tag,
            addition=request.addition,
            limit=request.limit,
        )
    except Exception as exc:
        logger.error("Error previewing pricing tag %s: %s", request.tag, exc)
        raise HTTPException(status_code=500, detail=str(exc))
