from __future__ import annotations

import json
import re
from pathlib import Path

from .config import default_paths

EDITOR_BEGIN = "-- DT_MANUAL_EDITOR_BEGIN"
EDITOR_END = "-- DT_MANUAL_EDITOR_END"
VALID_SOURCE_FOLDERS = {"Universal", "V1", "V2", "Definitions", "WhatsNew"}
DEFAULT_AUDIENCE = "common"
DEFAULT_SCOPE = "manuals"


def load_manual_editor_data(scope: str = DEFAULT_SCOPE) -> dict:
    scope = _normalize_scope(scope)
    manuals_root = _get_manuals_root()
    assets_root = _get_manual_assets_root()
    manuals = []

    if manuals_root.exists():
        for file_path in sorted(manuals_root.rglob("*.lua")):
            payload = _read_editor_payload(file_path)
            if payload is None:
                continue
            if not _payload_matches_scope(payload, scope):
                continue
            payload["source_file"] = str(file_path)
            payload["asset_base_url"] = f'/static/manuals/{payload["manual_id"]}'
            manuals.append(payload)

    manuals.sort(key=lambda row: (
        int(row.get("sort_order") or 0),
        str(row.get("title", row.get("manual_id", ""))).lower(),
        str(row.get("manual_id", "")),
    ))

    return {
        "meta": {
            "scope": scope,
            "manual_count": len(manuals),
        },
        "manuals": manuals,
        "definitions_root": str(manuals_root),
        "assets_root": str(assets_root),
        "assets_base_url": "/static/manuals",
}


def create_manual_definition(payload: dict, scope: str = DEFAULT_SCOPE) -> dict:
    scope = _normalize_scope(scope)
    normalized = _normalize_manual_payload(payload, scope=scope)
    existing_file = _find_existing_manual_file(normalized["manual_id"])
    if existing_file.exists():
        raise ValueError(f'Manual "{normalized["manual_id"]}" already exists.')
    file_path = _get_manual_file_path(normalized["manual_id"], normalized.get("source_folder"), scope=scope)
    _write_manual_file(file_path, normalized)
    return normalized


def save_manual_definition(manual_id: str, payload: dict, scope: str = DEFAULT_SCOPE) -> dict:
    scope = _normalize_scope(scope)
    normalized = _normalize_manual_payload(payload, manual_id=manual_id, scope=scope)
    existing_file = _find_existing_manual_file(manual_id)
    if existing_file.exists() and not _file_matches_scope(existing_file, scope):
        raise ValueError(f'Manual "{manual_id}" belongs to a different editor scope.')
    file_path = _get_manual_file_path(manual_id, normalized.get("source_folder"), scope=scope)
    _write_manual_file(file_path, normalized)
    if existing_file and existing_file != file_path and existing_file.exists():
        existing_file.unlink()
    return normalized


def delete_manual_definition(manual_id: str, scope: str = DEFAULT_SCOPE) -> None:
    scope = _normalize_scope(scope)
    file_path = _find_existing_manual_file(manual_id)
    if not file_path.exists():
        raise ValueError(f'Unknown manual "{manual_id}".')
    if not _file_matches_scope(file_path, scope):
        raise ValueError(f'Manual "{manual_id}" belongs to a different editor scope.')
    file_path.unlink()


def _get_manuals_root() -> Path:
    return default_paths().root / "Contents/mods/DynamicTradingCommon/42.13/media/lua/shared/DT/Common/Manuals"


def _get_manual_assets_root() -> Path:
    return default_paths().root / "Contents/mods/DynamicTradingCommon/42.13/media/ui/Manuals"


def _get_manual_file_path(manual_id: str, source_folder: str | None = None, scope: str = DEFAULT_SCOPE) -> Path:
    folder = _normalize_source_folder(source_folder, None, scope=scope)
    return _get_manuals_root() / folder / f"DT_Manual_{manual_id}.lua"


def _find_existing_manual_file(manual_id: str) -> Path:
    manuals_root = _get_manuals_root()
    matches = sorted(manuals_root.rglob(f"DT_Manual_{manual_id}.lua"))
    if matches:
        return matches[0]
    return _get_manual_file_path(manual_id)


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
    return _normalize_manual_payload(payload, manual_id=payload.get("manual_id"))


def _normalize_manual_payload(payload: dict, manual_id: str | None = None, scope: str = DEFAULT_SCOPE) -> dict:
    scope = _normalize_scope(scope)
    manual_id = _slugify(manual_id or payload.get("manual_id"))
    if not manual_id:
        raise ValueError("Manual id is required.")

    audiences = _normalize_audiences(payload.get("audiences"), manual_id)
    is_whats_new = _normalize_bool(payload.get("is_whats_new"))
    if scope == "updates":
        is_whats_new = True
    sort_order = payload.get("sort_order")
    if sort_order in (None, ""):
        sort_order = _default_sort_order(manual_id, audiences, is_whats_new)
    else:
        sort_order = int(sort_order)

    release_version = str(payload.get("release_version", "") or "").strip()
    auto_open_on_update = _normalize_bool(payload.get("auto_open_on_update"))
    show_in_library = _normalize_bool(payload.get("show_in_library")) if "show_in_library" in payload else not is_whats_new
    if scope == "updates":
        show_in_library = False
    source_folder = _normalize_source_folder(payload.get("source_folder"), audiences, scope=scope, is_whats_new=is_whats_new)

    chapters = []
    seen_chapters: set[str] = set()
    for index, chapter in enumerate(payload.get("chapters") or []):
        chapter_id = _slugify(chapter.get("id"))
        if not chapter_id:
            raise ValueError(f"Chapter #{index + 1} is missing an id.")
        if chapter_id in seen_chapters:
            raise ValueError(f'Duplicate chapter id "{chapter_id}".')
        seen_chapters.add(chapter_id)
        chapters.append({
            "id": chapter_id,
            "title": str(chapter.get("title", chapter_id)).strip(),
            "description": str(chapter.get("description", "")).strip(),
        })

    pages = []
    seen_pages: set[str] = set()
    section_ids_by_page: dict[str, set[str]] = {}
    valid_chapters = {row["id"] for row in chapters}

    for index, page in enumerate(payload.get("pages") or []):
        page_id = _slugify(page.get("id"))
        if not page_id:
            raise ValueError(f"Page #{index + 1} is missing an id.")
        if page_id in seen_pages:
            raise ValueError(f'Duplicate page id "{page_id}".')
        seen_pages.add(page_id)

        chapter_id = _slugify(page.get("chapter_id") or page.get("chapterId"))
        if chapter_id and chapter_id not in valid_chapters:
            raise ValueError(f'Page "{page_id}" references unknown chapter "{chapter_id}".')

        blocks = []
        section_ids_by_page[page_id] = set()
        for block_index, block in enumerate(page.get("blocks") or []):
            normalized_block = _normalize_block(block, page_id, block_index + 1, section_ids_by_page[page_id])
            blocks.append(normalized_block)

        pages.append({
            "id": page_id,
            "chapter_id": chapter_id,
            "title": str(page.get("title", page_id)).strip(),
            "keywords": [str(keyword).strip() for keyword in (page.get("keywords") or []) if str(keyword).strip()],
            "blocks": blocks,
        })

    start_page_id = _slugify(payload.get("start_page_id") or payload.get("startPageId"))
    if start_page_id and start_page_id not in seen_pages:
        raise ValueError(f'Start page "{start_page_id}" does not exist.')

    return {
        "manual_id": manual_id,
        "title": str(payload.get("title", manual_id)).strip(),
        "description": str(payload.get("description", "")).strip(),
        "start_page_id": start_page_id,
        "audiences": audiences,
        "sort_order": sort_order,
        "release_version": release_version,
        "auto_open_on_update": auto_open_on_update,
        "is_whats_new": is_whats_new,
        "show_in_library": show_in_library,
        "source_folder": source_folder,
        "chapters": chapters,
        "pages": pages,
    }


def _normalize_block(block: dict, page_id: str, position: int, used_section_ids: set[str]) -> dict:
    block_type = str(block.get("type", "")).strip()
    if not block_type:
        raise ValueError(f'Page "{page_id}" block #{position} is missing a type.')

    if block_type == "heading":
        section_id = _slugify(block.get("id"))
        if not section_id:
            raise ValueError(f'Page "{page_id}" heading block #{position} is missing an id.')
        if section_id in used_section_ids:
            raise ValueError(f'Page "{page_id}" has a duplicate heading id "{section_id}".')
        used_section_ids.add(section_id)
        return {
            "type": "heading",
            "id": section_id,
            "level": int(block.get("level", 1)),
            "text": str(block.get("text", "")).strip(),
        }

    if block_type == "paragraph":
        return {
            "type": "paragraph",
            "text": str(block.get("text", "")).strip(),
        }

    if block_type == "bullet_list":
        items = [str(item).strip() for item in (block.get("items") or []) if str(item).strip()]
        return {
            "type": "bullet_list",
            "items": items,
        }

    if block_type == "image":
        return {
            "type": "image",
            "path": str(block.get("path", "")).strip(),
            "caption": str(block.get("caption", "")).strip(),
            "width": int(block.get("width", 220)),
            "height": int(block.get("height", 140)),
        }

    if block_type == "callout":
        return {
            "type": "callout",
            "tone": str(block.get("tone", "info")).strip() or "info",
            "title": str(block.get("title", "")).strip(),
            "text": str(block.get("text", "")).strip(),
        }

    raise ValueError(f'Unsupported block type "{block_type}" on page "{page_id}".')


def _write_manual_file(file_path: Path, payload: dict) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(_render_manual_file(payload), encoding="utf-8")


def _render_manual_file(payload: dict) -> str:
    json_text = json.dumps(payload, indent=2, ensure_ascii=False)
    json_comment = "\n".join(f"-- {line}" for line in json_text.splitlines())
    audience_values = ", ".join(f'"{_escape(audience)}"' for audience in payload["audiences"])

    lines = [
        EDITOR_BEGIN,
        json_comment,
        EDITOR_END,
        'if DynamicTrading and DynamicTrading.RegisterManual then',
        f'    DynamicTrading.RegisterManual("{_escape(payload["manual_id"])}", {{',
        f'        title = "{_escape(payload["title"])}",',
        f'        description = "{_escape(payload["description"])}",',
        f'        startPageId = "{_escape(payload["start_page_id"])}",',
        f"        audiences = {{ {audience_values} }},",
        f'        sortOrder = {int(payload["sort_order"])},',
        f'        releaseVersion = "{_escape(payload["release_version"])}",',
        f'        autoOpenOnUpdate = {"true" if payload["auto_open_on_update"] else "false"},',
        f'        isWhatsNew = {"true" if payload["is_whats_new"] else "false"},',
        f'        showInLibrary = {"true" if payload["show_in_library"] else "false"},',
        '        chapters = {',
    ]

    for chapter in payload["chapters"]:
        lines.extend([
            "            {",
            f'                id = "{_escape(chapter["id"])}",',
            f'                title = "{_escape(chapter["title"])}",',
            f'                description = "{_escape(chapter["description"])}",',
            "            },",
        ])

    lines.extend([
        "        },",
        "        pages = {",
    ])

    for page in payload["pages"]:
        lines.append("            {")
        lines.append(f'                id = "{_escape(page["id"])}",')
        lines.append(f'                chapterId = "{_escape(page["chapter_id"])}",')
        lines.append(f'                title = "{_escape(page["title"])}",')
        lines.append("                keywords = { " + ", ".join(f'"{_escape(keyword)}"' for keyword in page["keywords"]) + " },")
        lines.append("                blocks = {")
        for block in page["blocks"]:
            lines.append("                    " + _render_block(block) + ",")
        lines.extend([
            "                },",
            "            },",
        ])

    lines.extend([
        "        },",
        "    })",
        "end",
        "",
    ])
    return "\n".join(lines)


def _render_block(block: dict) -> str:
    if block["type"] == "heading":
        return f'{{ type = "heading", id = "{_escape(block["id"])}", level = {int(block["level"])}, text = "{_escape(block["text"])}" }}'
    if block["type"] == "paragraph":
        return f'{{ type = "paragraph", text = "{_escape(block["text"])}" }}'
    if block["type"] == "bullet_list":
        items = ", ".join(f'"{_escape(item)}"' for item in block["items"])
        return f'{{ type = "bullet_list", items = {{ {items} }} }}'
    if block["type"] == "image":
        return (
            f'{{ type = "image", path = "{_escape(block["path"])}", caption = "{_escape(block["caption"])}", '
            f'width = {int(block["width"])}, height = {int(block["height"])} }}'
        )
    return (
        f'{{ type = "callout", tone = "{_escape(block["tone"])}", title = "{_escape(block["title"])}", '
        f'text = "{_escape(block["text"])}" }}'
    )


def _escape(value: str) -> str:
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"')


def _normalize_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_audience(value: str | None) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text in {"all", "shared", "universal"}:
        return "common"
    if text in {"dtv1", "dynamictrading"}:
        return "v1"
    if text in {"dtv2", "dynamictradingv2"}:
        return "v2"
    if text == "dynamiccolonies":
        return "colony"
    return text


def _normalize_audiences(raw_audiences, manual_id: str) -> list[str]:
    values = raw_audiences if isinstance(raw_audiences, list) else [raw_audiences]
    audiences: list[str] = []

    for raw in values:
        audience = _normalize_audience(raw)
        if audience and audience not in audiences:
            audiences.append(audience)

    if audiences:
        return audiences

    if manual_id.startswith("dc_"):
        return ["colony"]
    if "v1" in manual_id:
        return ["v1"]
    if "v2" in manual_id:
        return ["v2"]
    return [DEFAULT_AUDIENCE]


def _normalize_scope(scope: str | None) -> str:
    normalized = str(scope or DEFAULT_SCOPE).strip().lower()
    if normalized in {"updates", "update", "whatsnew", "what_s_new", "whats_new"}:
        return "updates"
    return "manuals"


def _payload_matches_scope(payload: dict, scope: str) -> bool:
    scope = _normalize_scope(scope)
    source_folder = str(payload.get("source_folder") or "")
    is_update = source_folder == "WhatsNew" or payload.get("is_whats_new") is True
    return is_update if scope == "updates" else not is_update


def _file_matches_scope(file_path: Path, scope: str) -> bool:
    folder = file_path.parent.name
    is_update = folder == "WhatsNew"
    return is_update if _normalize_scope(scope) == "updates" else not is_update


def _normalize_source_folder(raw_folder: str | None, audiences: list[str] | None, scope: str = DEFAULT_SCOPE, is_whats_new: bool = False) -> str:
    if _normalize_scope(scope) == "updates" or is_whats_new:
        return "WhatsNew"

    folder = str(raw_folder or "").strip().replace("\\", "/")
    if folder in VALID_SOURCE_FOLDERS:
        if folder == "WhatsNew":
            return "Universal"
        return folder

    lowered = folder.lower()
    for candidate in VALID_SOURCE_FOLDERS:
        if lowered == candidate.lower():
            if candidate == "WhatsNew":
                return "Universal"
            return candidate

    primary = (audiences or [DEFAULT_AUDIENCE])[0]
    if primary == "v1":
        return "V1"
    if primary == "v2":
        return "V2"
    return "Universal"


def _default_sort_order(manual_id: str, audiences: list[str], is_whats_new: bool) -> int:
    primary = (audiences or [DEFAULT_AUDIENCE])[0]
    base = 300000

    if primary in {"v1", "v2"}:
        base = 100000
    elif primary == "colony":
        base = 200000

    if is_whats_new or manual_id == "dt_whats_new":
        base = 0

    return base


def _slugify(value: str | None) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_\\-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")
