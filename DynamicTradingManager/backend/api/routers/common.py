import os
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from config.server_settings import get_server_settings
from DebugManagement import LogParser
from ItemManagement import load_vanilla_items
from ProjectManagement import list_workshop_projects, resolve_project_target, get_flattened_modules

_settings = get_server_settings()
CONSOLE_PATH = str(_settings.console_path)
MOD_ROOT = _settings.dynamic_trading_path
COLONIES_ROOT = _settings.dynamic_colonies_path
CURRENCY_ROOT = _settings.dynamic_currency_path

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
    return str(module or "DynamicTradingCommon").strip()


def get_workshop_project_or_404(target: Optional[str] = None):
    try:
        project = resolve_project_target(target)
        resolved = dict(project)
        project_path = resolved.get("path")
        if isinstance(project_path, Path):
            return resolved
        if not project_path:
            raise FileNotFoundError(f"Workshop project '{target or '(default)'}' has no configured path")
        resolved["path"] = Path(project_path)
        return resolved
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception(f"Unexpected error resolving workshop project: {exc}")
        raise HTTPException(status_code=500, detail=f"Internal server error resolving project: {exc}")


def serialize_workshop_projects():
    projects = list_workshop_projects()
    modules = get_flattened_modules()
    default_target = next((project["key"] for project in projects if project["is_default"]), None)
    default_module = next((m["id"] for m in modules if m["is_default"]), "DynamicTradingCommon")
    return {
        "targets": projects, 
        "modules": modules,
        "default_target": default_target,
        "default_module": default_module
    }
