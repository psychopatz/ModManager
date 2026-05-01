from __future__ import annotations

from .constants import (
    AUTOPLAY_MS,
    BLOCK_TITLE,
    CHAPTER_ID,
    CURRENCY_SYMBOL,
    MANUAL_DESCRIPTION,
    MANUAL_ID,
    MANUAL_TITLE,
    MANUAL_TYPE,
    MODULE,
    PAGE_ID,
    PAGE_TITLE,
    SOURCE_FOLDER,
    THANK_YOU_TEXT,
)


def _slugify(value: str | None) -> str:
    text = str(value or "").strip().lower()
    parts = []
    last_was_sep = False
    for char in text:
        if char.isalnum() or char in {"_", "-"}:
            parts.append(char)
            last_was_sep = False
        elif not last_was_sep:
            parts.append("_")
            last_was_sep = True
    return "".join(parts).strip("_")


def _normalize_supporter(entry: dict) -> dict:
    total = float(entry.get("total_donation", 0) or 0)
    return {
        "id": _slugify(entry.get("id") or entry.get("name")),
        "name": str(entry.get("name", "")).strip(),
        "total_donation": total,
        "image_path": str(entry.get("image_path", "")).strip(),
        "support_message": str(
            entry.get("support_message")
            or entry.get("supportMessage")
            or entry.get("message")
            or ""
        ).strip(),
        "active": bool(entry.get("active", True)),
    }


def sort_supporters(entries: list[dict] | None) -> list[dict]:
    normalized = [
        _normalize_supporter(entry)
        for entry in (entries or [])
        if str(entry.get("name", "")).strip()
    ]
    normalized.sort(
        key=lambda row: (
            -(float(row.get("total_donation", 0) or 0)),
            str(row.get("name", "")).lower(),
            str(row.get("id", "")),
        )
    )
    return normalized


def build_donators_response(payload: dict | None = None) -> dict:
    manual = payload or {}
    page = (manual.get("pages") or [{}])[0]
    block = (page.get("blocks") or [{}])[0]

    # Support both the flat API request payload and the normalized manual payload
    # that comes back from the editor file.
    top_level_supporters = manual.get("supporters")
    supporters = sort_supporters(top_level_supporters if top_level_supporters is not None else block.get("supporters") or [])

    top_level_title = manual.get("title")
    top_level_page_title = manual.get("page_title")
    top_level_block_title = manual.get("block_title")
    top_level_autoplay = manual.get("autoplay_ms")
    top_level_currency = manual.get("currency_symbol")
    top_level_thank_you = manual.get("thank_you_text")

    return {
        "manual_id": MANUAL_ID,
        "manual_type": MANUAL_TYPE,
        "title": str(top_level_title or block.get("title") or MANUAL_TITLE),
        "page_title": str(top_level_page_title or page.get("title") or PAGE_TITLE),
        "block_title": str(top_level_block_title or block.get("title") or BLOCK_TITLE),
        "autoplay_ms": int(top_level_autoplay or block.get("autoplay_ms", AUTOPLAY_MS) or AUTOPLAY_MS),
        "currency_symbol": str(top_level_currency or block.get("currency_symbol") or CURRENCY_SYMBOL),
        "thank_you_text": str(top_level_thank_you or block.get("thank_you_text") or block.get("thankYouText") or THANK_YOU_TEXT),
        "supporters": supporters,
    }


def build_manual_payload(data: dict | None = None) -> dict:
    donor_data = build_donators_response(data)
    return {
        "manual_id": MANUAL_ID,
        "module": MODULE,
        "title": MANUAL_TITLE,
        "description": MANUAL_DESCRIPTION,
        "start_page_id": PAGE_ID,
        "audiences": [MODULE],
        "sort_order": 9999998,
        "release_version": "",
        "popup_version": "",
        "auto_open_on_update": False,
        "is_whats_new": False,
        "manual_type": MANUAL_TYPE,
        "show_in_library": False,
        "support_url": "",
        "banner_title": "",
        "banner_text": "",
        "banner_action_label": "",
        "source_folder": SOURCE_FOLDER,
        "chapters": [
            {
                "id": CHAPTER_ID,
                "title": "Supporters",
                "description": "Recognizes the supporters helping keep the project moving.",
            }
        ],
        "pages": [
            {
                "id": PAGE_ID,
                "chapter_id": CHAPTER_ID,
                "title": donor_data["page_title"],
                "keywords": ["support", "donators", "supporters", "donation", "thank you"],
                "blocks": [
                    {
                        "type": "supporter_carousel",
                        "title": donor_data["block_title"],
                        "autoplay_ms": donor_data["autoplay_ms"],
                        "currency_symbol": donor_data["currency_symbol"],
                        "thank_you_text": donor_data["thank_you_text"],
                        "supporters": donor_data["supporters"],
                    }
                ],
            }
        ],
    }
