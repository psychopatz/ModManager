from __future__ import annotations

from pathlib import Path

from config.server_settings import get_server_settings
from Simulation.config import default_paths

from .constants import DEFAULT_MODULE, DEFAULT_SCOPE
from .normalize import (
    _module_matches_payload,
    _normalize_module,
    _normalize_scope,
    _normalize_source_folder,
    _payload_matches_scope,
    _slugify,
)
from .parser import _read_editor_payload


from config.paths import get_manuals_root, get_manual_assets_root, get_manuals_roots
from ProjectManagement.projects import list_workshop_projects

def _get_manual_root_for_mod(mod_id: str) -> Path:
    from config.paths import get_manuals_root
    return get_manuals_root(mod_id)

def _get_manuals_roots(module: str = DEFAULT_MODULE) -> list[Path]:
    normalized = _normalize_module(module)
    from config.paths import get_manuals_roots
    return get_manuals_roots(normalized)


def _get_manual_assets_root(module: str = DEFAULT_MODULE) -> Path:
    normalized = _normalize_module(module)
    return get_manual_assets_root(normalized)


def _get_manual_assets_root_url(module: str = DEFAULT_MODULE) -> str:
    normalized = _normalize_module(module)
    # Use the dynamic proxy endpoint instead of hardcoded static mounts
    return f"/api/manuals/assets/{normalized}"


def _get_manual_asset_base_url(module: str | None, manual_id: str) -> str:
    # Avoid double slashes and ensure clean path joining for the frontend
    module_id = _normalize_module(module or DEFAULT_MODULE)
    return f"/api/manuals/assets/{module_id}/{manual_id}"


def _get_manual_prefix(mod_id: str) -> str:
    """Extracts a prefix like DTC_ based on the Mod ID."""
    # Try to find an existing manual file to steal the prefix from
    root = _get_manual_root_for_mod(mod_id)
    if root.exists():
        for f in root.glob("*Manual_*.lua"):
            if "_" in f.name:
                return f.name.split("Manual_")[0] + "Manual_"
        for f in root.glob("*_*.lua"):
             if "_" in f.name:
                 return f.name.split("_")[0] + "_"
    
    # Fallback: Generate from Mod ID (Capitals)
    capitals = "".join(c for c in mod_id if c.isupper())
    if capitals:
         return f"{capitals}_"
    return "Manual_"

def _get_manual_file_path(
    manual_id: str,
    source_folder: str | None = None,
    scope: str = DEFAULT_SCOPE,
    module: str = DEFAULT_MODULE,
) -> Path:
    normalized_module = _normalize_module(module)
    folder = _normalize_source_folder(source_folder, None, scope=scope, module=normalized_module)
    
    root = _get_manual_root_for_mod(normalized_module)
    prefix = _get_manual_prefix(normalized_module)
    
    # Avoid duplicate prefixing (e.g., DTC_DTC_Upd -> DTC_Upd)
    filename = manual_id
    if not filename.lower().startswith(prefix.lower()):
        filename = f"{prefix}{manual_id}"
        
    return root / folder / f"{filename}.lua"


def _find_existing_manual_file(manual_id: str, module: str | None = None) -> Path:
    normalized_id = _slugify(manual_id)
    if module:
        module_candidates = [_normalize_module(module)]
    else:
        # Dynamically discover all unique mod IDs for broad search
        from ProjectManagement.projects import get_flattened_modules
        module_candidates = list(set(m["id"].lower() for m in get_flattened_modules()))

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
