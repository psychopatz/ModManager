from __future__ import annotations

from ManualManagement.parser import _read_editor_payload
from ManualManagement.paths import _find_existing_manual_file_in_module, _get_manual_asset_base_url
from ManualManagement.render import _write_manual_file

from .constants import MANUAL_ID, MODULE
from .payload import build_donators_response, build_manual_payload


def get_donators_definition() -> dict:
    file_path = _find_existing_manual_file_in_module(MANUAL_ID, MODULE)
    payload = _read_editor_payload(file_path) if file_path.exists() else None
    response = build_donators_response(payload)
    response["asset_base_url"] = _get_manual_asset_base_url(MODULE, MANUAL_ID)
    response["source_file"] = str(file_path)
    return response


def save_donators_definition(data: dict) -> dict:
    manual_payload = build_manual_payload(data)
    file_path = _find_existing_manual_file_in_module(MANUAL_ID, MODULE)
    _write_manual_file(file_path, manual_payload)
    response = build_donators_response(manual_payload)
    response["asset_base_url"] = _get_manual_asset_base_url(MODULE, MANUAL_ID)
    response["source_file"] = str(file_path)
    return response
