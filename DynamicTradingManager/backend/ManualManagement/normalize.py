from __future__ import annotations

import re
from pathlib import Path

from .constants import DEFAULT_AUDIENCE, DEFAULT_MODULE, DEFAULT_SCOPE, VALID_SOURCE_FOLDERS


DESCRIPTION_MAX_LENGTH = 69


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
    if text in {"currency", "ce", "currencyexpanded", "currency_expanded"}:
        return "currency"
    return text


def _normalize_module(value: str | None) -> str:
    normalized = _normalize_audience(value)
    if normalized in {"v1", "v2", "colony", "currency", "common"}:
        return normalized
    return DEFAULT_MODULE


def _infer_module(module: str | None, payload: dict | None = None, file_path: Path | None = None) -> str:
    normalized = _normalize_module(module)
    if normalized != DEFAULT_MODULE:
        return normalized

    if file_path is not None:
        lowered = str(file_path).replace("\\", "/").lower()
        if "/dynamiccolonies/" in lowered:
            return "colony"
        if "/currencyexpanded/" in lowered:
            return "currency"
        if "/dt/v1/manuals/" in lowered:
            return "v1"
        if "/dt/v2/manuals/" in lowered:
            return "v2"
        if "/manuals/v1/" in lowered:
            return "v1"
        if "/manuals/v2/" in lowered:
            return "v2"

    if payload:
        audiences = _normalize_audiences(payload.get("audiences"), _slugify(payload.get("manual_id")))
        return _normalize_module((audiences or [DEFAULT_AUDIENCE])[0])

    return DEFAULT_MODULE


def _module_matches_payload(payload: dict, module: str) -> bool:
    return _normalize_module(payload.get("module")) == _normalize_module(module)


def _normalize_audiences(raw_audiences, manual_id: str, fallback_module: str = DEFAULT_MODULE) -> list[str]:
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
    if _normalize_module(fallback_module) == "currency":
        return ["currency"]
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


def _normalize_source_folder(
    raw_folder: str | None,
    audiences: list[str] | None,
    scope: str = DEFAULT_SCOPE,
    is_whats_new: bool = False,
    module: str = DEFAULT_MODULE,
    file_path: Path | None = None,
) -> str:
    if _normalize_scope(scope) == "updates" or is_whats_new:
        return "WhatsNew"

    normalized_module = _normalize_module(module)
    if normalized_module == "colony":
        return "Colony"
    if normalized_module == "currency":
        return "Universal"

    if file_path is not None:
        parent_name = file_path.parent.name
        if parent_name in VALID_SOURCE_FOLDERS:
            if parent_name == "WhatsNew":
                return "Universal"
            return parent_name

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
    if primary == "colony":
        return "Colony"
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


def _normalize_description(value: str | None, field_label: str, enforce_max_length: bool = True) -> str:
    text = str(value or "").strip()
    if len(text) > DESCRIPTION_MAX_LENGTH and enforce_max_length:
        raise ValueError(f"{field_label} must be {DESCRIPTION_MAX_LENGTH} characters or fewer.")
    if len(text) > DESCRIPTION_MAX_LENGTH:
        return text[:DESCRIPTION_MAX_LENGTH]
    return text


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
        width = int(block.get("width", 220))
        height = int(block.get("height", 140))
        keep_aspect_ratio = block.get("keep_aspect_ratio")
        if keep_aspect_ratio is None:
            keep_aspect_ratio = True
        aspect_ratio = block.get("aspect_ratio")
        if aspect_ratio in (None, ""):
            aspect_ratio = (width / height) if height else 1
        return {
            "type": "image",
            "path": str(block.get("path", "")).strip(),
            "caption": str(block.get("caption", "")).strip(),
            "width": width,
            "height": height,
            "keep_aspect_ratio": bool(keep_aspect_ratio),
            "aspect_ratio": float(aspect_ratio),
        }

    if block_type == "callout":
        return {
            "type": "callout",
            "tone": str(block.get("tone", "info")).strip() or "info",
            "title": str(block.get("title", "")).strip(),
            "text": str(block.get("text", "")).strip(),
        }

    raise ValueError(f'Unsupported block type "{block_type}" on page "{page_id}".')


def _normalize_manual_payload(
    payload: dict,
    manual_id: str | None = None,
    scope: str = DEFAULT_SCOPE,
    module: str = DEFAULT_MODULE,
    file_path: Path | None = None,
    enforce_description_limit: bool = True,
) -> dict:
    scope = _normalize_scope(scope)
    module = _normalize_module(_infer_module(module, payload, file_path))
    manual_id = _slugify(manual_id or payload.get("manual_id"))
    if not manual_id:
        raise ValueError("Manual id is required.")

    audiences = _normalize_audiences(payload.get("audiences"), manual_id, fallback_module=module)
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
    source_folder = _normalize_source_folder(
        payload.get("source_folder"),
        audiences,
        scope=scope,
        is_whats_new=is_whats_new,
        module=module,
        file_path=file_path,
    )

    manual_type = str(payload.get("manual_type") or payload.get("manualType") or payload.get("type") or "").strip().lower()
    if not manual_type:
        if is_whats_new:
            manual_type = "whats_new"
        elif source_folder == "Support" or manual_id.startswith("dt_support"):
            manual_type = "support"
        else:
            manual_type = "manual"

    popup_version = str(
        payload.get("popup_version")
        or payload.get("popupVersion")
        or payload.get("release_version")
        or payload.get("releaseVersion")
        or (manual_id if manual_type == "support" else "")
        or ""
    ).strip()

    support_url = str(payload.get("support_url") or payload.get("supportUrl") or "").strip()
    banner_title = str(payload.get("banner_title") or payload.get("bannerTitle") or "").strip()
    banner_text = str(payload.get("banner_text") or payload.get("bannerText") or "").strip()
    banner_action_label = str(payload.get("banner_action_label") or payload.get("bannerActionLabel") or "").strip()

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
            "description": _normalize_description(
                chapter.get("description", ""),
                f'Chapter "{chapter_id}" description',
                enforce_max_length=enforce_description_limit,
            ),
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
        "module": module,
        "title": str(payload.get("title", manual_id)).strip(),
        "description": _normalize_description(
            payload.get("description", ""),
            "Manual description",
            enforce_max_length=enforce_description_limit,
        ),
        "start_page_id": start_page_id,
        "audiences": audiences,
        "sort_order": sort_order,
        "release_version": release_version,
        "popup_version": popup_version,
        "auto_open_on_update": auto_open_on_update,
        "is_whats_new": is_whats_new,
        "manual_type": manual_type,
        "show_in_library": show_in_library,
        "support_url": support_url,
        "banner_title": banner_title,
        "banner_text": banner_text,
        "banner_action_label": banner_action_label,
        "source_folder": source_folder,
        "chapters": chapters,
        "pages": pages,
    }
