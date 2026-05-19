import logging
from typing import Optional

from fastapi import APIRouter

from api.routers.common import get_items, get_processed_items
from api.schemas import StatsResponse
from ItemManagement.ui.commands import get_registered_items
from ItemManagement.ui.stats import count_registered_items, find_invalid_blacklist_ids

logger = logging.getLogger(__name__)
router = APIRouter(tags=["catalog"])


@router.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    items = get_items()
    total_vanilla = len(items)
    registered = count_registered_items()
    unregistered = total_vanilla - registered
    coverage = (registered / total_vanilla * 100) if total_vanilla > 0 else 0

    notifications = []
    invalid_blacklist = find_invalid_blacklist_ids()
    if invalid_blacklist:
        notifications.append(f"{len(invalid_blacklist)} invalid item ID(s) in blacklist")

    return {
        "total_vanilla": total_vanilla,
        "registered": registered,
        "unregistered": unregistered,
        "coverage": round(coverage, 2),
        "notifications": notifications,
    }


@router.get("/api/items")
async def list_items(
    search: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    min_weight: Optional[float] = None,
    max_weight: Optional[float] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
):
    try:
        processed_items = get_processed_items()
        registered_ids = get_registered_items()

        filtered_results = []

        for item in processed_items:
            item_id = item["id"]
            is_bl = item["is_blacklisted"]
            is_wl = item["is_whitelisted"]
            price = item["price"]
            weight = item["weight"]
            tags_list = item["tags"]
            item_name = item["name"]

            if search and search.lower() not in item_name.lower() and search.lower() not in item_id.lower():
                continue

            if status:
                if status == "registered" and item_id not in registered_ids:
                    continue
                elif status == "unregistered" and (item_id in registered_ids or is_bl):
                    continue
                elif status == "blacklisted" and not is_bl:
                    continue
                elif status == "whitelisted" and not is_wl:
                    continue

            if tag and not any(tag.lower() in t.lower() for t in tags_list):
                continue

            if min_weight is not None and weight < min_weight:
                continue
            if max_weight is not None and weight > max_weight:
                continue
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue

            filtered_results.append(
                {
                    "id": item_id,
                    "name": item_name,
                    "is_blacklisted": is_bl,
                    "is_whitelisted": is_wl,
                    "is_registered": item_id in registered_ids,
                    "price": price,
                    "tags": tags_list,
                    "weight": weight,
                }
            )

        total = len(filtered_results)
        paginated_results = filtered_results[offset : offset + limit]

        return {"total": total, "items": paginated_results}
    except Exception as exc:
        logger.error("Error in list_items: %s", exc)
        return {"total": 0, "items": [], "error": str(exc)}


@router.get("/api/tags")
async def list_unique_tags():
    try:
        processed_items = get_processed_items()
        unique_tags = set()

        for item in processed_items:
            for tag in item["tags"]:
                unique_tags.add(tag)

        return {"tags": sorted(list(unique_tags))}
    except Exception as exc:
        logger.error("Error fetching tags: %s", exc)
        return {"tags": [], "error": str(exc)}
