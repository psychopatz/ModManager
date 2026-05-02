"""Whitelist helpers backed by the shared blacklist.json file."""

from __future__ import annotations

import json
import os

_whitelist_cache = None


def _get_blacklist_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "blacklist.json")


def _get_legacy_whitelist_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "whitelist.json")


def _load_blacklist_payload() -> dict:
    path = _get_blacklist_path()
    if not os.path.exists(path):
        return {
            "itemIds": [],
            "whitelistItemIds": [],
            "properties": {"names": [], "values": {}},
        }

    try:
        with open(path, "r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
            if not isinstance(payload, dict):
                payload = {}
            payload.setdefault("itemIds", [])
            payload.setdefault("whitelistItemIds", [])
            payload.setdefault("properties", {"names": [], "values": {}})
            return payload
    except Exception:
        return {
            "itemIds": [],
            "whitelistItemIds": [],
            "properties": {"names": [], "values": {}},
        }


def _save_blacklist_payload(payload: dict):
    payload.setdefault("itemIds", [])
    payload.setdefault("whitelistItemIds", [])
    payload.setdefault("properties", {"names": [], "values": {}})
    with open(_get_blacklist_path(), "w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2)


def _load_legacy_ids() -> list[str]:
    path = _get_legacy_whitelist_path()
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
            if isinstance(payload, dict):
                ids = payload.get("itemIds", [])
                if isinstance(ids, list):
                    return [str(item_id) for item_id in ids if isinstance(item_id, str) and item_id]
    except Exception:
        return []

    return []


def load_whitelist():
    """Load whitelist IDs from blacklist.json (shared rules file)."""
    global _whitelist_cache
    if _whitelist_cache is not None:
        return _whitelist_cache

    payload = _load_blacklist_payload()
    item_ids = payload.get("whitelistItemIds", [])
    if not isinstance(item_ids, list):
        item_ids = []

    # Compatibility migration for older installations that still have whitelist.json.
    if not item_ids:
        legacy_ids = _load_legacy_ids()
        if legacy_ids:
            item_ids = sorted(set(legacy_ids))
            payload["whitelistItemIds"] = item_ids
            _save_blacklist_payload(payload)

    _whitelist_cache = {"itemIds": sorted(set(str(item_id) for item_id in item_ids if isinstance(item_id, str) and item_id))}
    return _whitelist_cache


def reload_whitelist():
    """Force reload of whitelist configuration."""
    global _whitelist_cache
    _whitelist_cache = None
    return load_whitelist()


def is_item_whitelisted(item_id: str) -> bool:
    whitelist = load_whitelist()
    return item_id in whitelist.get("itemIds", [])


def add_item_to_whitelist(item_id: str):
    if not item_id or not isinstance(item_id, str):
        raise ValueError("item_id must be a non-empty string")

    payload = _load_blacklist_payload()
    item_ids = list(payload.get("whitelistItemIds", []))

    if item_id not in item_ids:
        item_ids.append(item_id)
        item_ids.sort()

    payload["whitelistItemIds"] = item_ids
    _save_blacklist_payload(payload)

    next_whitelist = {"itemIds": item_ids}

    reload_whitelist()
    return next_whitelist


def remove_item_from_whitelist(item_id: str):
    if not item_id or not isinstance(item_id, str):
        raise ValueError("item_id must be a non-empty string")

    payload = _load_blacklist_payload()
    item_ids = [entry for entry in payload.get("whitelistItemIds", []) if entry != item_id]

    next_whitelist = {"itemIds": item_ids}
    payload["whitelistItemIds"] = item_ids
    _save_blacklist_payload(payload)

    reload_whitelist()
    return next_whitelist
