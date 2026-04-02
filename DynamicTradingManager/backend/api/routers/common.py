import os
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from DebugManagement import LogParser
from ItemManagement import load_vanilla_items
from ProjectManagement import list_workshop_projects, resolve_project_target

CONSOLE_PATH = os.getenv("CONSOLE_PATH", "/home/psychopatz/Zomboid/console.txt")
MOD_ROOT = Path(os.getenv("DYNAMIC_TRADING_PATH", "/home/psychopatz/Zomboid/Workshop/DynamicTrading/"))
COLONIES_ROOT = Path(os.getenv("DYNAMIC_COLONIES_PATH", str(MOD_ROOT.parent / "DynamicColonies")))
CURRENCY_ROOT = Path(os.getenv("DYNAMIC_CURRENCY_PATH", str(MOD_ROOT.parent / "CurrencyExpanded")))

debug_parser = LogParser(CONSOLE_PATH)
cached_vanilla_items = None


def configure_environment(
    *,
    console_path: Optional[str] = None,
    mod_root: Optional[Path] = None,
    colonies_root: Optional[Path] = None,
    currency_root: Optional[Path] = None,
):
    global CONSOLE_PATH, MOD_ROOT, COLONIES_ROOT, CURRENCY_ROOT, debug_parser

    if console_path:
        CONSOLE_PATH = console_path
    if mod_root is not None:
        MOD_ROOT = mod_root
    if colonies_root is not None:
        COLONIES_ROOT = colonies_root
    if currency_root is not None:
        CURRENCY_ROOT = currency_root

    debug_parser = LogParser(CONSOLE_PATH)


def get_items():
    global cached_vanilla_items
    if cached_vanilla_items is None:
        cached_vanilla_items = load_vanilla_items()
    return cached_vanilla_items


def clear_items_cache():
    global cached_vanilla_items
    cached_vanilla_items = None


def get_debug_parser() -> LogParser:
    return debug_parser


def get_mod_roots():
    return MOD_ROOT, COLONIES_ROOT, CURRENCY_ROOT


def normalize_manual_module(module: Optional[str]) -> str:
    normalized = str(module or "common").strip().lower()
    if normalized in {"v1", "v2", "colony", "currency", "common"}:
        return normalized
    return "common"


def get_workshop_project_or_404(target: Optional[str] = None):
    try:
        return resolve_project_target(target)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def serialize_workshop_projects():
    projects = list_workshop_projects()
    default_target = next((project["key"] for project in projects if project["is_default"]), None)
    return {"targets": projects, "default_target": default_target}
