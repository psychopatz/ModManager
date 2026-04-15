from __future__ import annotations

from pathlib import Path

from config.server_settings import get_server_settings
from Simulation.config import default_paths

from .constants import ALL_MODULES, DEFAULT_MODULE, DEFAULT_SCOPE
from .normalize import (
    _module_matches_payload,
    _normalize_module,
    _normalize_scope,
    _normalize_source_folder,
    _payload_matches_scope,
    _slugify,
)
from .parser import _read_editor_payload


from config.paths import get_manuals_root, get_manual_assets_root

def _get_dynamic_trading_root() -> Path:
    return get_manuals_root("DynamicTradingCommon")


def _get_dynamic_trading_v1_root() -> Path:
    return get_manuals_root("DynamicTradingV1")


def _get_dynamic_trading_v2_root() -> Path:
    return get_manuals_root("DynamicTradingV2")


def _get_dynamic_colonies_mod_root() -> Path:
    return get_server_settings().dynamic_colonies_path


def _get_dynamic_colonies_root() -> Path:
    return get_manuals_root("DynamicColonies")


def _get_currency_expanded_mod_root() -> Path:
    return get_server_settings().dynamic_currency_path


def _get_currency_expanded_root() -> Path:
    return get_manuals_root("CurrencyExpanded")


def _get_manuals_roots(module: str = DEFAULT_MODULE) -> list[Path]:
    normalized = _normalize_module(module)
    if normalized == "v1":
        return [_get_dynamic_trading_v1_root()]
    if normalized == "v2":
        return [_get_dynamic_trading_v2_root()]
    if normalized == "colony":
        return [_get_dynamic_colonies_root()]
    if normalized == "currency":
        return [_get_currency_expanded_root()]
    return [_get_dynamic_trading_root()]


def _get_manual_assets_root(module: str = DEFAULT_MODULE) -> Path:
    normalized = _normalize_module(module)
    if normalized == "colony":
        return get_manual_assets_root("DynamicColonies")
    if normalized == "currency":
        return get_manual_assets_root("CurrencyExpanded")
    return get_manual_assets_root("DynamicTradingCommon")


def _get_manual_assets_root_url(module: str = DEFAULT_MODULE) -> str:
    normalized = _normalize_module(module)
    if normalized == "colony":
        return "/static/manuals-colony"
    if normalized == "currency":
        return "/static/manuals-currency"
    return "/static/manuals"


def _get_manual_asset_base_url(module: str | None, manual_id: str) -> str:
    return f'{_get_manual_assets_root_url(module or DEFAULT_MODULE)}/{manual_id}'


def _get_manual_file_path(
    manual_id: str,
    source_folder: str | None = None,
    scope: str = DEFAULT_SCOPE,
    module: str = DEFAULT_MODULE,
) -> Path:
    normalized_module = _normalize_module(module)
    folder = _normalize_source_folder(source_folder, None, scope=scope, module=normalized_module)
    if normalized_module == "v1":
        return _get_dynamic_trading_v1_root() / folder / f"DT_Manual_{manual_id}.lua"
    if normalized_module == "v2":
        return _get_dynamic_trading_v2_root() / folder / f"DT_Manual_{manual_id}.lua"
    if normalized_module == "colony":
        return _get_dynamic_colonies_root() / f"DC_Manual_{manual_id}.lua"
    if normalized_module == "currency":
        return _get_currency_expanded_root() / folder / f"CE_Manual_{manual_id}.lua"
    return _get_dynamic_trading_root() / folder / f"DT_Manual_{manual_id}.lua"


def _find_existing_manual_file(manual_id: str, module: str | None = None) -> Path:
    normalized_id = _slugify(manual_id)
    module_candidates = [_normalize_module(module)] if module else list(ALL_MODULES)
    for candidate_module in module_candidates:
        for root in _get_manuals_roots(candidate_module):
            if not root.exists():
                continue
            for file_path in sorted(root.rglob("*.lua")):
                payload = _read_editor_payload(file_path)
                if payload and payload.get("manual_id") == normalized_id and _module_matches_payload(payload, candidate_module):
                    return file_path
    if module:
        return _get_manual_file_path(normalized_id, module=_normalize_module(module))
    return _get_manual_file_path(normalized_id)


def _find_existing_manual_file_in_module(manual_id: str, module: str) -> Path:
    return _find_existing_manual_file(manual_id, module=module)


def _file_matches_scope(file_path: Path, scope: str) -> bool:
    payload = _read_editor_payload(file_path)
    if payload is None:
        return False
    return _payload_matches_scope(payload, _normalize_scope(scope))
