from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


MAPS_SUFFIX = Path("media/maps")


@dataclass(frozen=True)
class DiscoveredMod:
    mod_root: Path
    mod_info_files: tuple[Path, ...]
    content_roots: tuple[Path, ...]
    map_folders: tuple[Path, ...]


def normalize_source_path(source_path: str) -> Path:
    resolved = Path(source_path).expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Source path does not exist: {resolved}")
    return resolved


def discover_mods_from_source(source_path: str | Path) -> list[DiscoveredMod]:
    source = normalize_source_path(str(source_path))
    mod_roots = _discover_mod_roots(source)
    discovered: list[DiscoveredMod] = []

    for mod_root in mod_roots:
        mod_info_files = tuple(sorted(_collect_mod_info_files(mod_root)))
        content_roots = tuple(sorted(_collect_content_roots(mod_root)))
        map_folders = tuple(sorted(_collect_map_folders(content_roots), key=lambda item: item.name.lower()))
        if not mod_info_files or not map_folders:
            continue
        discovered.append(
            DiscoveredMod(
                mod_root=mod_root,
                mod_info_files=mod_info_files,
                content_roots=content_roots,
                map_folders=map_folders,
            )
        )

    if not discovered:
        raise FileNotFoundError(f"No modded map content was found under: {source}")

    discovered.sort(key=lambda item: item.mod_root.name.lower())
    return discovered


def _discover_mod_roots(source: Path) -> list[Path]:
    candidates: list[Path] = []

    if _is_map_folder(source):
        mod_root = _ascend_to_mod_root_from_map_folder(source)
        if mod_root:
            candidates.append(mod_root)
    elif _is_content_root(source):
        mod_root = _ascend_to_mod_root_from_content_root(source)
        if mod_root:
            candidates.append(mod_root)
    elif _looks_like_workshop_content_root(source):
        candidates.extend(_discover_mod_roots_from_workshop_content_root(source))
    elif _looks_like_mod_root(source):
        candidates.append(source)
    else:
        mods_dir = source / "mods"
        if mods_dir.is_dir():
            for child in sorted(mods_dir.iterdir(), key=lambda item: item.name.lower()):
                if child.is_dir() and _looks_like_mod_root(child):
                    candidates.append(child)

    normalized: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(resolved)
    return normalized


def _collect_mod_info_files(mod_root: Path) -> list[Path]:
    candidates: list[Path] = []
    direct = mod_root / "mod.info"
    if direct.exists():
        candidates.append(direct)

    for child in sorted(mod_root.iterdir(), key=lambda item: item.name.lower()) if mod_root.exists() else []:
        if not child.is_dir():
            continue
        mod_info = child / "mod.info"
        if mod_info.exists():
            candidates.append(mod_info)

    return candidates


def _collect_content_roots(mod_root: Path) -> list[Path]:
    roots: list[Path] = []
    for child in sorted(mod_root.iterdir(), key=lambda item: item.name.lower()) if mod_root.exists() else []:
        if not child.is_dir():
            continue
        media_maps = child / MAPS_SUFFIX
        if media_maps.is_dir():
            roots.append(child)
    if (mod_root / MAPS_SUFFIX).is_dir():
        roots.append(mod_root)
    return roots


def _collect_map_folders(content_roots: tuple[Path, ...]) -> list[Path]:
    map_folders: list[Path] = []
    seen: set[str] = set()
    for content_root in content_roots:
        maps_root = content_root / MAPS_SUFFIX
        if not maps_root.is_dir():
            continue
        for child in maps_root.iterdir():
            if not child.is_dir():
                continue
            if not _is_valid_map_folder(child):
                continue
            key = str(child.resolve())
            if key in seen:
                continue
            seen.add(key)
            map_folders.append(child.resolve())
    return map_folders


def _is_map_folder(path: Path) -> bool:
    parts = path.parts
    return len(parts) >= 3 and tuple(parts[-3:-1]) == ("media", "maps")


def _is_content_root(path: Path) -> bool:
    return (path / MAPS_SUFFIX).is_dir()


def _looks_like_mod_root(path: Path) -> bool:
    if not path.is_dir():
        return False
    if (path / "mod.info").exists():
        return True
    return any((child / "mod.info").exists() for child in path.iterdir() if child.is_dir())


def _looks_like_workshop_content_root(path: Path) -> bool:
    if not path.is_dir():
        return False
    for child in path.iterdir():
        if not child.is_dir() or not child.name.isdigit():
            continue
        if (child / "mods").is_dir():
            return True
    return False


def _discover_mod_roots_from_workshop_content_root(path: Path) -> list[Path]:
    mod_roots: list[Path] = []
    for item_dir in sorted(path.iterdir(), key=lambda item: item.name.lower()):
        if not item_dir.is_dir() or not item_dir.name.isdigit():
            continue
        mods_dir = item_dir / "mods"
        if not mods_dir.is_dir():
            continue
        for mod_dir in sorted(mods_dir.iterdir(), key=lambda item: item.name.lower()):
            if mod_dir.is_dir() and _looks_like_mod_root(mod_dir):
                mod_roots.append(mod_dir)
    return mod_roots


def _ascend_to_mod_root_from_map_folder(path: Path) -> Path | None:
    maps_root = path.parent
    media_root = maps_root.parent
    content_root = media_root.parent
    return _ascend_to_mod_root_from_content_root(content_root)


def _ascend_to_mod_root_from_content_root(path: Path) -> Path | None:
    current = path.resolve()
    while current != current.parent:
        if _looks_like_mod_root(current):
            return current
        current = current.parent
    return None


def _is_valid_map_folder(path: Path) -> bool:
    if not path.is_dir():
        return False
    patterns = ("*.lotheader", "worldmap.xml", "worldmap.xml.bin", "worldmap-annotations.lua", "map.info", "spawnpoints.lua")
    for pattern in patterns:
        try:
            if any(path.glob(pattern)):
                return True
        except Exception:
            continue
    return False


def sanitize_pascal_case(value: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", str(value or ""))
    return "".join(token[:1].upper() + token[1:] for token in tokens if token)


def strip_version_tokens(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\bB\d+(?:\.\d+)?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bBuild\s*\d+(?:\.\d+)?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bv\d+(?:\.\d+)?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" ,-_")
    return text or str(value or "").strip()


def normalize_registry_key(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def get_workshop_item_id_for_mod_root(mod_root: Path) -> str | None:
    try:
        parent = mod_root.parent
        if parent.name != "mods":
            return None
        item_dir = parent.parent
        return item_dir.name if item_dir.name.isdigit() else None
    except Exception:
        return None
