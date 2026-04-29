from __future__ import annotations

import json
import re
from pathlib import Path

from .constants import EDITOR_BEGIN, EDITOR_END
from .normalize import _normalize_manual_payload


def _read_editor_payload(file_path: Path) -> dict | None:
    text = file_path.read_text(encoding="utf-8")
    match = re.search(
        rf"{re.escape(EDITOR_BEGIN)}\n(.*?)\n{re.escape(EDITOR_END)}",
        text,
        re.DOTALL,
    )
    if not match:
        return None

    json_lines = []
    for line in match.group(1).splitlines():
        stripped = line
        if stripped.startswith("-- "):
            stripped = stripped[3:]
        elif stripped.startswith("--"):
            stripped = stripped[2:]
        json_lines.append(stripped)

    payload = json.loads("\n".join(json_lines))
    payload["raw_lua"] = text
    return _normalize_manual_payload(
        payload,
        manual_id=payload.get("manual_id"),
        file_path=file_path,
        enforce_description_limit=False,
    )
