from __future__ import annotations

import json
from pathlib import Path

from .constants import EDITOR_BEGIN, EDITOR_END
from .normalize import _normalize_module


def _escape(value: str) -> str:
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"')


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


def _render_manual_file(payload: dict) -> str:
    json_text = json.dumps(payload, indent=2, ensure_ascii=False)
    json_comment = "\n".join(f"-- {line}" for line in json_text.splitlines())
    audience_values = ", ".join(f'"{_escape(audience)}"' for audience in payload["audiences"])

    module_name = _normalize_module(payload.get("module"))
    if module_name == "currency":
        register_guard = "if CurrencyExpanded and CurrencyExpanded.RegisterManual then"
        register_call = "CurrencyExpanded.RegisterManual"
    else:
        register_guard = "if DynamicTrading and DynamicTrading.RegisterManual then"
        register_call = "DynamicTrading.RegisterManual"

    lines = [
        EDITOR_BEGIN,
        json_comment,
        EDITOR_END,
        register_guard,
        f'    {register_call}("{_escape(payload["manual_id"])}", {{',
        f'        title = "{_escape(payload["title"])}",',
        f'        description = "{_escape(payload["description"])}",',
        f'        startPageId = "{_escape(payload["start_page_id"])}",',
        f"        audiences = {{ {audience_values} }},",
        f'        sortOrder = {int(payload["sort_order"])},',
        f'        releaseVersion = "{_escape(payload["release_version"])}",',
        f'        popupVersion = "{_escape(payload.get("popup_version", ""))}",',
        f'        autoOpenOnUpdate = {"true" if payload["auto_open_on_update"] else "false"},',
        f'        isWhatsNew = {"true" if payload["is_whats_new"] else "false"},',
        f'        manualType = "{_escape(payload.get("manual_type", "manual"))}",',
        f'        showInLibrary = {"true" if payload["show_in_library"] else "false"},',
        f'        supportUrl = "{_escape(payload.get("support_url", ""))}",',
        f'        bannerTitle = "{_escape(payload.get("banner_title", ""))}",',
        f'        bannerText = "{_escape(payload.get("banner_text", ""))}",',
        f'        bannerActionLabel = "{_escape(payload.get("banner_action_label", ""))}",',
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
        lines.append("                keywords = { " + ", ".join(f'\"{_escape(keyword)}\"' for keyword in page["keywords"]) + " },")
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


def _write_manual_file(file_path: Path, payload: dict) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(_render_manual_file(payload), encoding="utf-8")
