from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from ItemManagement.parse import load_blacklist, load_whitelist
from ItemManagement.parse.overrides import load_overrides
from api.routers.blacklist_overrides import _write_runtime_rules_file
from api.routers.common import clear_items_cache
from config.server_settings import get_server_settings

router = APIRouter(tags=["runtime-sync"])


def _read_text_file(path: Path) -> str:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="replace")


@router.get("/api/runtime/dt_items")
async def get_runtime_dt_items():
    settings = get_server_settings()
    dt_items_path = Path(settings.dt_items_dir)
    
    if dt_items_path.is_file():
        text = _read_text_file(dt_items_path)
        return {
            "path": str(dt_items_path),
            "text": text,
            "line_count": len(text.splitlines()),
            "type": "file"
        }
    
    # Aggregated directory view
    aggregated_text = []
    file_count = 0
    for txt_file in sorted(dt_items_path.rglob("*.txt")):
        try:
            rel_path = txt_file.relative_to(dt_items_path)
            content = _read_text_file(txt_file)
            aggregated_text.append(f"--- FILE: {rel_path} ---\n{content}\n")
            file_count += 1
        except Exception:
            continue
            
    full_text = "\n".join(aggregated_text)
    return {
        "path": str(dt_items_path),
        "text": full_text,
        "line_count": len(full_text.splitlines()),
        "file_count": file_count,
        "type": "directory"
    }


@router.get("/api/runtime/rules")
async def get_runtime_rules():
    settings = get_server_settings()
    rules_path = Path(settings.runtime_rules_file)

    rules_text = ""
    if rules_path.exists():
        rules_text = _read_text_file(rules_path)

    return {
        "path": str(rules_path),
        "text": rules_text,
        "blacklist": load_blacklist().get("itemIds", []),
        "whitelist": load_whitelist().get("itemIds", []),
        "overrides": load_overrides(),
    }


@router.get("/api/runtime/heuristics")
async def get_runtime_heuristics_source():
    settings = get_server_settings()
    heuristics_path = Path(settings.market_sense_path) / "Contents/mods/MarketSense/common/media/lua/shared/MarketSense/DT_HeuristicsDB.lua"
    text = _read_text_file(heuristics_path)

    return {
        "path": str(heuristics_path),
        "text": text,
        "line_count": len(text.splitlines()),
    }


@router.post("/api/runtime/apply")
async def apply_runtime_rules_from_manager_json():
    """Force-write runtime rules data from manager JSON sources.

    Sources:
    - blacklist.json (itemIds + whitelistItemIds)
    - overrides.json
    """
    sync_info = _write_runtime_rules_file()
    clear_items_cache()

    blacklist = load_blacklist().get("itemIds", [])
    whitelist = load_whitelist().get("itemIds", [])
    overrides = load_overrides()

    return {
        "success": True,
        "runtime_rules_sync": sync_info,
        "blacklist_count": len(blacklist),
        "whitelist_count": len(whitelist),
        "override_count": len(overrides),
        "message": "Applied manager JSON data to runtime rules file.",
    }
