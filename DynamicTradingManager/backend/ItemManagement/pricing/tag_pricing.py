from __future__ import annotations

import copy
import threading
from collections import Counter
from typing import Any, Dict

from ..commons.vanilla_loader import get_translated_name
from ..parse.overrides import OVERRIDES_FILE, apply_override, load_overrides
from ..tag.tagging import generate_tags
from .config_store import CONFIG_PATH, get_pricing_config
from .pricing import calculate_price_details
from .stock import calculate_stock_range
from .tag_utils import expand_hierarchy


_DESCRIPTOR_PREFIXES = ("Rarity.", "Quality.", "Origin.", "Theme.")
_TAG_INDEX_CACHE: dict[str, Any] | None = None
_CURRENT_STATE_CACHE: dict[str, Any] | None = None
_CACHE_LOCK = threading.RLock()


def _file_mtime(path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


def _items_signature(items: Dict[str, str]) -> tuple[int, int]:
    return id(items), len(items)


def _cache_signature(items: Dict[str, str]) -> tuple[tuple[int, int], float]:
    return _items_signature(items), _file_mtime(OVERRIDES_FILE)


def _pricing_signature() -> float:
    return _file_mtime(CONFIG_PATH)


def _primary_tag_for(tags: list[str]) -> str:
    return next(
        (
            tag for tag in tags
            if isinstance(tag, str) and not tag.startswith(_DESCRIPTOR_PREFIXES)
        ),
        "Misc.General",
    )


def _load_overrides_by_item() -> dict[str, dict[str, Any]]:
    return {
        override.get("item"): override
        for override in load_overrides()
        if override.get("item")
    }


def _entry_name(entry: dict[str, Any]) -> str:
    if entry.get("name") is None:
        entry["name"] = get_translated_name(entry["item_id"], entry["props"])
    return entry["name"]


def _build_tag_index(items: Dict[str, str]) -> dict[str, Any]:
    overrides_by_item = _load_overrides_by_item()
    catalog: dict[str, dict[str, Any]] = {}
    by_tag: dict[str, list[dict[str, Any]]] = {}
    item_entries: list[dict[str, Any]] = []

    for item_id, props in items.items():
        if not props:
            continue

        override = overrides_by_item.get(item_id)
        base_tags = generate_tags(item_id, props)
        tags = override.get("tags", base_tags) if override else base_tags
        tags = [str(tag) for tag in tags if isinstance(tag, str) and tag]
        expanded_tags = expand_hierarchy(tags)
        primary_tag = _primary_tag_for(tags)

        entry = {
            "item_id": item_id,
            "name": None,
            "props": props,
            "tags": tags,
            "override": override,
            "has_override": bool(override),
        }
        item_entries.append(entry)

        for tag in expanded_tags:
            by_tag.setdefault(tag, []).append(entry)
            bucket = catalog.setdefault(
                tag,
                {
                    "tag": tag,
                    "item_count": 0,
                    "domains": Counter(),
                    "samples": [],
                },
            )
            bucket["item_count"] += 1
            bucket["domains"][primary_tag] += 1
            if len(bucket["samples"]) < 3:
                bucket["samples"].append(
                    {
                        "item_id": item_id,
                        "name": _entry_name(entry),
                    }
                )

    rows = []
    for tag, bucket in catalog.items():
        row = {
            "tag": tag,
            "item_count": bucket["item_count"],
            "domains": [
                {"tag": domain, "count": count}
                for domain, count in bucket["domains"].most_common(10)
            ],
            "samples": bucket["samples"],
        }
        rows.append(row)

    rows.sort(key=lambda row: (-row["item_count"], row["tag"]))
    return {
        "signature": _cache_signature(items),
        "items": item_entries,
        "rows": rows,
        "by_tag": by_tag,
    }


def _get_tag_index(items: Dict[str, str]) -> dict[str, Any]:
    global _TAG_INDEX_CACHE

    signature = _cache_signature(items)
    with _CACHE_LOCK:
        if _TAG_INDEX_CACHE and _TAG_INDEX_CACHE["signature"] == signature:
            return _TAG_INDEX_CACHE

    built = _build_tag_index(items)
    with _CACHE_LOCK:
        if _TAG_INDEX_CACHE and _TAG_INDEX_CACHE["signature"] == signature:
            return _TAG_INDEX_CACHE
        _TAG_INDEX_CACHE = built
        return built


def _build_current_state(index: dict[str, Any], pricing_config: Dict[str, Any]) -> dict[str, Any]:
    states: dict[str, Any] = {}

    for entry in index["items"]:
        has_price_override = bool(entry["override"] and entry["override"].get("basePrice") is not None)
        stock_range = calculate_stock_range(
            entry["item_id"],
            entry["props"],
            entry["tags"],
            pricing_config=pricing_config,
        )
        current_details = calculate_price_details(
            entry["item_id"],
            entry["props"],
            entry["tags"],
            pricing_config=pricing_config,
        )
        current_price, current_tags, stock_min, stock_max, _ = apply_override(
            entry["item_id"],
            current_details["price"],
            entry["tags"],
            stock_range["min"],
            stock_range["max"],
            [entry["override"]] if entry["override"] else [],
        )
        states[entry["item_id"]] = {
            "current_price": int(current_price),
            "current_tags": list(current_tags),
            "stock_min": int(stock_min),
            "stock_max": int(stock_max),
            "primary_tag": current_details["primary_tag"],
            "current_pre_clamp_price": float(current_details.get("pre_global_clamp_price", current_details["price"])),
            "current_global_price_clamped": bool(current_details.get("global_price_clamped")) and not has_price_override,
            "current_global_price_clamp": current_details.get("global_price_clamp"),
            "current_global_max_price": current_details.get("global_max_price"),
            "has_price_override": has_price_override,
        }

    return states


def _get_current_state(index: dict[str, Any], pricing_config: Dict[str, Any] | None = None) -> dict[str, Any]:
    global _CURRENT_STATE_CACHE

    if pricing_config is not None:
        return _build_current_state(index, pricing_config)

    config = get_pricing_config()
    signature = (index["signature"], _pricing_signature())
    with _CACHE_LOCK:
        if _CURRENT_STATE_CACHE and _CURRENT_STATE_CACHE["signature"] == signature:
            return _CURRENT_STATE_CACHE["states"]

    built = _build_current_state(index, config)
    with _CACHE_LOCK:
        if _CURRENT_STATE_CACHE and _CURRENT_STATE_CACHE["signature"] == signature:
            return _CURRENT_STATE_CACHE["states"]
        _CURRENT_STATE_CACHE = {
            "signature": signature,
            "states": built,
        }
        return built


def build_pricing_tag_catalog(items: Dict[str, str], pricing_config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    config = pricing_config or get_pricing_config()
    current_additions = config.get("tag_price_additions", {})
    index = _get_tag_index(items)

    return {
        "tags": [
            {
                **row,
                "current_addition": float(current_additions.get(row["tag"], 0.0)),
            }
            for row in index["rows"]
        ]
    }


def preview_pricing_tag(
    items: Dict[str, str],
    tag: str,
    addition: float = 0.0,
    limit: int = 40,
    pricing_config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    base_config = pricing_config or get_pricing_config()
    preview_config = copy.deepcopy(base_config)
    preview_config.setdefault("tag_price_additions", {})

    if abs(float(addition)) < 1e-9:
        preview_config["tag_price_additions"].pop(tag, None)
    else:
        preview_config["tag_price_additions"][tag] = float(addition)

    index = _get_tag_index(items)
    current_states = _get_current_state(index, pricing_config if pricing_config is not None else None)
    matches = []
    domains: Counter[str] = Counter()
    current_total = 0.0
    preview_total = 0.0
    tag_entries = index["by_tag"].get(tag, [])

    for entry in tag_entries:
        state = current_states[entry["item_id"]]
        has_price_override = bool(entry["override"] and entry["override"].get("basePrice") is not None)
        preview_details = calculate_price_details(
            entry["item_id"],
            entry["props"],
            entry["tags"],
            pricing_config=preview_config,
        )
        preview_price, _, _, _, _ = apply_override(
            entry["item_id"],
            preview_details["price"],
            entry["tags"],
            state["stock_min"],
            state["stock_max"],
            [entry["override"]] if entry["override"] else [],
        )
        domains[state["primary_tag"]] += 1
        current_total += state["current_price"]
        preview_total += preview_price
        current_pre_clamp_price = state["current_pre_clamp_price"]
        preview_pre_clamp_price = float(preview_details.get("pre_global_clamp_price", preview_details["price"]))
        raw_delta = int(round(preview_pre_clamp_price - current_pre_clamp_price))
        final_delta = int(preview_price) - state["current_price"]
        current_global_price_clamped = state["current_global_price_clamped"]
        preview_global_price_clamped = bool(preview_details.get("global_price_clamped")) and not has_price_override

        matches.append(
            {
                "item_id": entry["item_id"],
                "name": _entry_name(entry),
                "primary_tag": state["primary_tag"],
                "current_price": state["current_price"],
                "preview_price": int(preview_price),
                "delta": final_delta,
                "raw_delta": raw_delta,
                "tags": state["current_tags"],
                "stock_min": state["stock_min"],
                "stock_max": state["stock_max"],
                "preview_stock_min": state["stock_min"],
                "preview_stock_max": state["stock_max"],
                "has_override": entry["has_override"],
                "has_price_override": has_price_override,
                "current_pre_clamp_price": round(current_pre_clamp_price, 2),
                "preview_pre_clamp_price": round(preview_pre_clamp_price, 2),
                "current_global_price_clamped": current_global_price_clamped,
                "preview_global_price_clamped": preview_global_price_clamped,
                "current_global_price_clamp": state["current_global_price_clamp"],
                "preview_global_price_clamp": preview_details.get("global_price_clamp"),
                "global_max_price": preview_details.get("global_max_price", state["current_global_max_price"]),
            }
        )

    matches.sort(
        key=lambda row: (
            -max(abs(row["delta"]), abs(row["raw_delta"])),
            -abs(row["raw_delta"]),
            -row["preview_price"],
            row["name"],
        )
    )
    total_items = len(matches)

    return {
        "tag": tag,
        "addition": float(addition),
        "saved_addition": float(base_config.get("tag_price_additions", {}).get(tag, 0.0)),
        "item_count": total_items,
        "domains": [{"tag": domain, "count": count} for domain, count in domains.most_common(10)],
        "stats": {
            "avg_current_price": round(current_total / total_items, 2) if total_items else 0.0,
            "avg_preview_price": round(preview_total / total_items, 2) if total_items else 0.0,
        },
        "items": matches[: max(1, limit)],
    }


def warm_pricing_tag_cache(items: Dict[str, str]) -> Dict[str, int]:
    index = _get_tag_index(items)
    states = _get_current_state(index)
    return {
        "items": len(states),
        "tags": len(index["rows"]),
    }
