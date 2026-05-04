import logging
import re
from collections import Counter
from typing import Optional

from fastapi import APIRouter

from api.routers.common import get_items
from api.schemas import StatsResponse
from ItemManagement import calculate_price, generate_tags, get_stat
from ItemManagement.commons.vanilla_loader import get_translated_name, get_vanilla_script_count, _load_vanilla_scripts
from ItemManagement.parse import is_item_blacklisted, is_item_whitelisted
from ItemManagement.ui.stats import find_invalid_blacklist_ids

logger = logging.getLogger(__name__)
router = APIRouter(tags=["catalog"])


@router.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    items = get_items()
    total_runtime = len(items)
    
    dt_items = items
    vanilla_scripts = _load_vanilla_scripts(apply_blacklist=False)
    
    total_vanilla = 0
    total_modded = 0
    registered_vanilla = 0
    
    # Items in DT_Items that are modded
    mod_origin_counts = Counter()
    
    vanilla_keys = set(vanilla_scripts.keys())
    for item_id, props in dt_items.items():
        base_id = item_id.split(".")[-1]
        props_str = str(props)
        is_vanilla = "origin:Vanilla" in props_str
        
        if is_vanilla:
            total_vanilla += 1
            if base_id in vanilla_keys:
                registered_vanilla += 1
        else:
            total_modded += 1
            # Try to grab mod name from origin:ModName
            origin_match = re.search(r"origin:([A-Za-z0-9_\-\s&]+)", props_str)
            if origin_match:
                origin = origin_match.group(1).strip()
                if origin and origin != "Vanilla":
                    mod_origin_counts[origin] += 1

    total_unregistered = max(0, len(vanilla_scripts) - registered_vanilla)
    notifications = []
    invalid_blacklist = find_invalid_blacklist_ids()
    if invalid_blacklist:
        notifications.append(f"{len(invalid_blacklist)} invalid item ID(s) in blacklist")

    from ItemManagement.parse import load_blacklist, load_whitelist
    from ItemManagement.parse.overrides import load_overrides
    
    total_blacklisted = len(load_blacklist().get("itemIds", []))
    total_whitelisted = len(load_whitelist().get("itemIds", []))
    total_overrides = len(load_overrides())

    return {
        "total_runtime": total_runtime,
        "total_vanilla": total_vanilla,
        "total_modded": total_modded,
        "registered_vanilla": registered_vanilla,
        "unregistered_vanilla": total_unregistered,
        "mod_breakdown": dict(mod_origin_counts),
        "source": "dt_items",
        "total_scripts": len(vanilla_scripts),
        "notifications": notifications,
        "blacklisted": total_blacklisted,
        "whitelisted": total_whitelisted,
        "overrides": total_overrides,
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
        items = get_items()

        filtered_results = []
        item_keys = list(items.keys())

        for item_id in item_keys:
            props = items[item_id]
            is_bl, _ = is_item_blacklisted(item_id, {})
            is_wl = is_item_whitelisted(item_id)

            tags_list = generate_tags(item_id, props)
            tags_dict = {t: True for t in tags_list}
            price = calculate_price(item_id, props, tags_dict)
            weight = get_stat(props, "Weight", 0.5)

            item_name = get_translated_name(item_id, props)

            if search and search.lower() not in item_name.lower() and search.lower() not in item_id.lower():
                continue

            if status:
                if status == "blacklisted" and not is_bl:
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
                    "is_blacklisted": bool(is_bl),
                    "is_whitelisted": bool(is_wl),
                    "price": int(price),
                    "tags": tags_list,
                    "weight": float(weight),
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
        items = get_items()
        unique_tags = set()

        for item_id, props in items.items():
            tags_list = generate_tags(item_id, props)
            for tag in tags_list:
                unique_tags.add(tag)

        return {"tags": sorted(list(unique_tags))}
    except Exception as exc:
        logger.error("Error fetching tags: %s", exc)
        return {"tags": [], "error": str(exc)}
