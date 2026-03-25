from __future__ import annotations

from typing import Any, Dict, Iterable, List


DEFAULT_TAGS_DICT = {
    "primary": "Misc.General",
    "rarity": "Common",
    "quality": None,
    "origin": "Vanilla",
    "theme": [],
    "all_tags": [],
}


def normalize_tags_dict(tags_dict: Any) -> Dict[str, Any]:
    if isinstance(tags_dict, list):
        normalized = dict(DEFAULT_TAGS_DICT)
        normalized["all_tags"] = [str(tag) for tag in tags_dict if isinstance(tag, str) and tag]
        normalized["primary"] = next(
            (
                tag for tag in tags_dict
                if isinstance(tag, str)
                and not tag.startswith(("Rarity.", "Quality.", "Origin.", "Theme."))
            ),
            "Misc.General",
        )
        for tag in tags_dict:
            if not isinstance(tag, str):
                continue
            if tag.startswith("Rarity."):
                normalized["rarity"] = tag.split(".", 1)[1] or "Common"
            elif tag.startswith("Quality."):
                normalized["quality"] = tag.split(".", 1)[1] or None
            elif tag.startswith("Origin."):
                normalized["origin"] = tag.split(".", 1)[1] or None
            elif tag.startswith("Theme."):
                normalized["theme"].append(tag.split(".", 1)[1] or "General")
        return normalized

    if not isinstance(tags_dict, dict):
        return dict(DEFAULT_TAGS_DICT)

    normalized = dict(DEFAULT_TAGS_DICT)
    normalized["primary"] = str(tags_dict.get("primary") or "Misc.General")
    normalized["rarity"] = str(tags_dict.get("rarity") or "Common")

    quality = tags_dict.get("quality")
    normalized["quality"] = str(quality) if quality else None

    origin = tags_dict.get("origin")
    normalized["origin"] = str(origin) if origin else "Vanilla"

    theme = tags_dict.get("theme") or []
    if isinstance(theme, list):
        normalized["theme"] = [str(value) for value in theme if value]
    elif theme:
        normalized["theme"] = [str(theme)]

    all_tags = tags_dict.get("all_tags") or []
    if isinstance(all_tags, list) and all_tags:
        normalized["all_tags"] = [str(tag) for tag in all_tags if tag]
    else:
        rebuilt = [normalized["primary"]]
        if normalized["rarity"]:
            rebuilt.append(f"Rarity.{normalized['rarity']}")
        if normalized["quality"]:
            rebuilt.append(f"Quality.{normalized['quality']}")
        if normalized["origin"]:
            rebuilt.append(f"Origin.{normalized['origin']}")
        for theme_tag in normalized["theme"]:
            rebuilt.append(theme_tag if theme_tag.startswith("Theme.") else f"Theme.{theme_tag}")
        normalized["all_tags"] = rebuilt

    return normalized


def category_parts(primary_tag: str) -> tuple[str, List[str]]:
    primary = primary_tag or "Misc.General"
    parts = [part for part in primary.split(".") if part]
    if not parts:
        return "Misc", []
    return parts[0], parts[1:]


def infer_category(tags_dict: Dict[str, Any]) -> str:
    category, _ = category_parts(str(tags_dict.get("primary") or "Misc.General"))
    return category


def has_tag_path(primary_tag: str, path: Iterable[str]) -> bool:
    probe = primary_tag or ""
    prefixes = set(expand_hierarchy([probe]))
    return any(candidate in prefixes for candidate in path)


def expand_hierarchy(tags: Iterable[str]) -> List[str]:
    out: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        probe = str(tag or "")
        while probe:
            if probe not in seen:
                out.append(probe)
                seen.add(probe)
            if "." not in probe:
                break
            probe = probe.rsplit(".", 1)[0]
    return out
