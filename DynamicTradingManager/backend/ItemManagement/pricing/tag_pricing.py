from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
from typing import Any, Dict

from config.server_settings import get_server_settings

from .config_store import get_pricing_config

_RUNTIME_INDEX_CACHE: dict[str, Any] | None = None


def _dt_items_dir() -> Path:
    return Path(get_server_settings().dt_items_dir)


def _file_mtime(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


def _split_tags(value: str) -> list[str]:
    if not value:
        return []
    return [tag.strip() for tag in re.split(r"[;,]", value) if tag.strip()]


def _to_int(value: str | int | float | None, default: int = 0) -> int:
    try:
        if value is None: return default
        return int(float(value))
    except Exception:
        return default


def _to_float(value: str | int | float | None, default: float = 0.0) -> float:
    try:
        if value is None: return default
        return float(value)
    except Exception:
        return default


def _parse_v2_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []

    entries: list[dict[str, Any]] = []
    current_origin = "Unknown"
    current_tags = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith("#"):
            continue
            
        if line.startswith("@origin="):
            current_origin = line.split("=", 1)[1].strip()
            continue
            
        if line.startswith("@tags="):
            tag_str = line.split("=", 1)[1].strip()
            current_tags = [t.strip() for t in tag_str.split("|") if t.strip()]
            continue
            
        # Data row: FullType | Price | StockMin | StockMax
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            full_type = parts[0]
            current_price = _to_int(parts[1])
            stock_min = _to_int(parts[2]) if len(parts) >= 3 else 0
            stock_max = _to_int(parts[3]) if len(parts) >= 4 else 0
            
            module_name = "Base"
            display_name = full_type
            if "." in full_type:
                module_parts = full_type.split(".", 1)
                module_name = module_parts[0]
                display_name = module_parts[1]
                
            primary_tag = current_tags[0] if current_tags else "Misc.General"
            
            entries.append({
                "item_id": full_type,
                "module_name": module_name,
                "legacy_item_id": display_name,
                "name": display_name,
                "expanded_tags": list(current_tags),
                "primary_tag": primary_tag,
                "current_price": current_price,
                "stock_min": stock_min,
                "stock_max": stock_max,
                "lookup_source": f"origin:{current_origin}",
                "has_price_override": False,
                "has_override": False,
                "confidence": 1.0,
            })
            
    return entries

def parse_dt_items(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    
    if path.is_file():
        # Fallback for old single-file dump if it still exists
        return _parse_v2_file(path)
        
    # Recursive directory scan for V2
    all_entries = []
    for txt_file in path.rglob("*.txt"):
        all_entries.extend(_parse_v2_file(txt_file))
        
    return all_entries


def _build_runtime_index() -> dict[str, Any]:
    path = _dt_items_dir()
    signature = (str(path), _file_mtime(path))
    entries = parse_dt_items(path)
    if not entries:
        return {
            "signature": signature,
            "rows": [],
            "by_tag": {},
            "states": {},
            "item_count": 0,
        }

    by_tag: dict[str, list[dict[str, Any]]] = {}
    states: dict[str, dict[str, Any]] = {}
    catalog: dict[str, dict[str, Any]] = {}

    for entry in entries:
        item_id = entry["item_id"]
        states[item_id] = {
            "current_price": entry["current_price"],
            "current_tags": list(entry["expanded_tags"]),
            "stock_min": entry["stock_min"],
            "stock_max": entry["stock_max"],
            "primary_tag": entry["primary_tag"],
            "current_pre_clamp_price": float(entry["current_price"]),
            "current_global_price_clamped": False,
            "current_global_price_clamp": None,
            "current_global_max_price": None,
            "has_price_override": bool(entry.get("has_price_override")),
        }

        for tag in entry["expanded_tags"]:
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
            bucket["domains"][entry["primary_tag"]] += 1
            if len(bucket["samples"]) < 3:
                bucket["samples"].append(
                    {
                        "item_id": item_id,
                        "name": entry.get("name") or item_id,
                    }
                )

    rows = []
    for tag, bucket in catalog.items():
        rows.append(
            {
                "tag": tag,
                "item_count": bucket["item_count"],
                "domains": [
                    {"tag": domain, "count": count}
                    for domain, count in bucket["domains"].most_common(10)
                ],
                "samples": bucket["samples"],
            }
        )

    rows.sort(key=lambda row: (-row["item_count"], row["tag"]))

    return {
        "signature": signature,
        "rows": rows,
        "by_tag": by_tag,
        "states": states,
        "item_count": len(states),
    }


def _get_runtime_index() -> dict[str, Any]:
    global _RUNTIME_INDEX_CACHE
    path = _dt_items_dir()
    signature = (str(path), _file_mtime(path))
    if _RUNTIME_INDEX_CACHE and _RUNTIME_INDEX_CACHE.get("signature") == signature:
        return _RUNTIME_INDEX_CACHE

    _RUNTIME_INDEX_CACHE = _build_runtime_index()
    return _RUNTIME_INDEX_CACHE


def build_pricing_tag_catalog(items: Dict[str, str] | None = None, pricing_config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    config = pricing_config or get_pricing_config()
    current_additions = config.get("tag_price_additions", {})
    index = _get_runtime_index()

    return {
        "source": "lua-runtime-dump",
        "item_count": index.get("item_count", 0),
        "tags": [
            {
                **row,
                "current_addition": float(current_additions.get(row["tag"], 0.0)),
            }
            for row in index["rows"]
        ],
    }


def preview_pricing_tag(
    items: Dict[str, str] | None,
    tag: str,
    addition: float = 0.0,
    limit: int = 40,
    pricing_config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    base_config = pricing_config or get_pricing_config()
    index = _get_runtime_index()
    states = index.get("states", {})
    tag_entries = index.get("by_tag", {}).get(tag, [])

    matches = []
    domains: Counter[str] = Counter()
    current_total = 0.0
    preview_total = 0.0

    for entry in tag_entries:
        item_id = entry["item_id"]
        state = states.get(item_id)
        if not state:
            continue

        current_price = int(state["current_price"])
        preview_price = int(round(current_price + float(addition)))
        delta = preview_price - current_price

        domains[state["primary_tag"]] += 1
        current_total += current_price
        preview_total += preview_price

        matches.append(
            {
                "item_id": item_id,
                "name": entry.get("name") or item_id,
                "primary_tag": state["primary_tag"],
                "current_price": current_price,
                "preview_price": preview_price,
                "delta": delta,
                "raw_delta": delta,
                "tags": list(state["current_tags"]),
                "stock_min": int(state["stock_min"]),
                "stock_max": int(state["stock_max"]),
                "preview_stock_min": int(state["stock_min"]),
                "preview_stock_max": int(state["stock_max"]),
                "has_override": bool(entry.get("has_override")),
                "has_price_override": bool(entry.get("has_price_override")),
                "current_pre_clamp_price": float(state["current_pre_clamp_price"]),
                "preview_pre_clamp_price": float(state["current_pre_clamp_price"] + float(addition)),
                "current_global_price_clamped": False,
                "preview_global_price_clamped": False,
                "current_global_price_clamp": None,
                "preview_global_price_clamp": None,
                "global_max_price": None,
            }
        )

    matches.sort(
        key=lambda row: (
            -abs(row["delta"]),
            -row["preview_price"],
            row["name"],
        )
    )

    total_items = len(matches)
    return {
        "source": "lua-runtime-dump",
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


def warm_pricing_tag_cache(items: Dict[str, str] | None = None) -> Dict[str, int]:
    index = _get_runtime_index()
    return {
        "items": int(index.get("item_count", 0)),
        "tags": len(index.get("rows", [])),
    }
