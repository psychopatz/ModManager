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


@router.get("/api/runtime/dump")
async def get_runtime_dump():
    settings = get_server_settings()
    dump_path = Path(settings.runtime_dump_file)
    text = _read_text_file(dump_path)
    return {
        "path": str(dump_path),
        "text": text,
        "line_count": len(text.splitlines()),
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
    heuristics_path = Path(settings.dynamic_trading_path) / "Contents/mods/DynamicTradingCommon/42.16/media/lua/shared/DynamicTrading/DT_HeuristicsDB.lua"
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
