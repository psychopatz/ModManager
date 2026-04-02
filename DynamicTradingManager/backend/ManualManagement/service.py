from __future__ import annotations

from .constants import DEFAULT_MODULE, DEFAULT_SCOPE
from .normalize import (
    _module_matches_payload,
    _normalize_manual_payload,
    _normalize_module,
    _normalize_scope,
    _payload_matches_scope,
)
from .parser import _read_editor_payload
from .paths import (
    _file_matches_scope,
    _find_existing_manual_file_in_module,
    _get_manual_asset_base_url,
    _get_manual_assets_root,
    _get_manual_assets_root_url,
    _get_manual_file_path,
    _get_manuals_roots,
)
from .render import _write_manual_file


def load_manual_editor_data(scope: str = DEFAULT_SCOPE, module: str = DEFAULT_MODULE) -> dict:
    scope = _normalize_scope(scope)
    module = _normalize_module(module)
    manuals_roots = _get_manuals_roots(module)
    assets_root = _get_manual_assets_root(module)
    manuals = []

    for manuals_root in manuals_roots:
        if not manuals_root.exists():
            continue
        for file_path in sorted(manuals_root.rglob("*.lua")):
            payload = _read_editor_payload(file_path)
            if payload is None:
                continue
            if not _payload_matches_scope(payload, scope):
                continue
            if not _module_matches_payload(payload, module):
                continue
            payload["source_file"] = str(file_path)
            payload["asset_base_url"] = _get_manual_asset_base_url(payload.get("module"), payload["manual_id"])
            manuals.append(payload)

    manuals.sort(key=lambda row: (
        int(row.get("sort_order") or 0),
        str(row.get("title", row.get("manual_id", ""))).lower(),
        str(row.get("manual_id", "")),
    ))

    return {
        "meta": {
            "scope": scope,
            "module": module,
            "manual_count": len(manuals),
        },
        "manuals": manuals,
        "definitions_root": str(manuals_roots[0]) if manuals_roots else "",
        "assets_root": str(assets_root),
        "assets_base_url": _get_manual_assets_root_url(module),
    }


def create_manual_definition(payload: dict, scope: str = DEFAULT_SCOPE, module: str = DEFAULT_MODULE) -> dict:
    scope = _normalize_scope(scope)
    module = _normalize_module(module)
    normalized = _normalize_manual_payload(payload, scope=scope, module=module)
    existing_file = _find_existing_manual_file_in_module(normalized["manual_id"], normalized.get("module") or module)
    if existing_file.exists():
        raise ValueError(f'Manual "{normalized["manual_id"]}" already exists.')
    file_path = _get_manual_file_path(
        normalized["manual_id"],
        normalized.get("source_folder"),
        scope=scope,
        module=normalized.get("module") or module,
    )
    _write_manual_file(file_path, normalized)
    return normalized


def save_manual_definition(manual_id: str, payload: dict, scope: str = DEFAULT_SCOPE, module: str = DEFAULT_MODULE) -> dict:
    scope = _normalize_scope(scope)
    module = _normalize_module(module)
    normalized = _normalize_manual_payload(payload, manual_id=manual_id, scope=scope, module=module)
    existing_file = _find_existing_manual_file_in_module(manual_id, normalized.get("module") or module)
    if existing_file.exists() and not _file_matches_scope(existing_file, scope):
        raise ValueError(f'Manual "{manual_id}" belongs to a different editor scope.')
    file_path = _get_manual_file_path(
        manual_id,
        normalized.get("source_folder"),
        scope=scope,
        module=normalized.get("module") or module,
    )
    _write_manual_file(file_path, normalized)
    if existing_file and existing_file != file_path and existing_file.exists():
        existing_file.unlink()
    return normalized


def delete_manual_definition(manual_id: str, scope: str = DEFAULT_SCOPE, module: str = DEFAULT_MODULE) -> None:
    scope = _normalize_scope(scope)
    file_path = _find_existing_manual_file_in_module(manual_id, module)
    if not file_path.exists():
        raise ValueError(f'Unknown manual "{manual_id}".')
    if not _file_matches_scope(file_path, scope):
        raise ValueError(f'Manual "{manual_id}" belongs to a different editor scope.')
    file_path.unlink()
