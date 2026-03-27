from __future__ import annotations

import json
import re
from pathlib import Path

from .config import default_paths

EDITOR_BEGIN = "-- DT_MANUAL_EDITOR_BEGIN"
EDITOR_END = "-- DT_MANUAL_EDITOR_END"


def load_manual_editor_data() -> dict:
    manuals_root = _get_manuals_root()
    assets_root = _get_manual_assets_root()
    manuals = []

    if manuals_root.exists():
        for file_path in sorted(manuals_root.rglob("*.lua")):
            payload = _read_editor_payload(file_path)
            if payload is None:
                continue
            payload["source_file"] = str(file_path)
            payload["asset_base_url"] = f'/static/manuals/{payload["manual_id"]}'
            manuals.append(payload)

    manuals.sort(key=lambda row: str(row.get("title", row.get("manual_id", ""))).lower())

    return {
        "meta": {
            "manual_count": len(manuals),
        },
        "manuals": manuals,
        "definitions_root": str(manuals_root),
        "assets_root": str(assets_root),
        "assets_base_url": "/static/manuals",
    }


def create_manual_definition(payload: dict) -> dict:
    normalized = _normalize_manual_payload(payload)
    file_path = _get_manual_file_path(normalized["manual_id"])
    if file_path.exists():
        raise ValueError(f'Manual "{normalized["manual_id"]}" already exists.')
    _write_manual_file(file_path, normalized)
    return normalized


def save_manual_definition(manual_id: str, payload: dict) -> dict:
    normalized = _normalize_manual_payload(payload, manual_id=manual_id)
    file_path = _get_manual_file_path(manual_id)
    _write_manual_file(file_path, normalized)
    return normalized


def delete_manual_definition(manual_id: str) -> None:
    file_path = _get_manual_file_path(manual_id)
    if not file_path.exists():
        raise ValueError(f'Unknown manual "{manual_id}".')
    file_path.unlink()


def _get_manuals_root() -> Path:
    return default_paths().root / "Contents/mods/DynamicTradingCommon/42.13/media/lua/shared/DT/Common/Manuals/Definitions"


def _get_manual_assets_root() -> Path:
    return default_paths().root / "Contents/mods/DynamicTradingCommon/42.13/media/ui/Manuals"


def _get_manual_file_path(manual_id: str) -> Path:
    return _get_manuals_root() / f"DT_Manual_{manual_id}.lua"


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


def _normalize_manual_payload(payload: dict, manual_id: str | None = None) -> dict:
    manual_id = _slugify(manual_id or payload.get("manual_id"))
    if not manual_id:
        raise ValueError("Manual id is required.")

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

    lines = [
        EDITOR_BEGIN,
        json_comment,
        EDITOR_END,
        'if DynamicTrading and DynamicTrading.RegisterManual then',
        f'    DynamicTrading.RegisterManual("{_escape(payload["manual_id"])}", {{',
        f'        title = "{_escape(payload["title"])}",',
        f'        description = "{_escape(payload["description"])}",',
        f'        startPageId = "{_escape(payload["start_page_id"])}",',
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


def _slugify(value: str | None) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_\\-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")
