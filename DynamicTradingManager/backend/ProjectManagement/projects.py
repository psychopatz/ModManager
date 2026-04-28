import os
import json
import logging
from pathlib import Path
from functools import lru_cache

from config.server_settings import get_server_settings
from WorkshopManagement.workshop import resolve_workshop_id

logger = logging.getLogger(__name__)


def _default_mod_root() -> Path:
    return get_server_settings().dynamic_trading_path


def _normalize_key(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _parse_workshop_title(repo_path: Path) -> str:
    workshop_txt = repo_path / "workshop.txt"
    if not workshop_txt.exists():
        return repo_path.name

    try:
        with open(workshop_txt, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if line.startswith("title="):
                    title = line.split("=", 1)[1].strip()
                    if title:
                        return title
    except Exception as exc:
        logger.debug("Unable to parse workshop title from %s: %s", workshop_txt, exc)

    return repo_path.name


def _discover_sub_mods(repo_path: Path) -> list[dict]:
    """
    Returns a list of sub-mods found in the repo by scanning for mod.info files.
    """
    mods_dir = repo_path / "Contents" / "mods"
    if not mods_dir.exists():
        return []

    sub_mods = []
    # Find all mod.info files under Contents/mods
    for mod_info_path in mods_dir.glob("**/mod.info"):
        try:
            mod_data = {}
            with open(mod_info_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.split("=", 1)
                        mod_data[k.strip()] = v.strip()
            
            if "name" in mod_data:
                sub_mods.append({
                    "id": mod_data.get("id", mod_info_path.parent.name),
                    "name": mod_data["name"],
                    "description": mod_data.get("description", ""),
                    "path": str(mod_info_path.parent)
                })
        except Exception as e:
            logger.debug(f"Error parsing mod.info at {mod_info_path}: {e}")
            
    # Sort for consistency
    sub_mods.sort(key=lambda m: m["name"].lower())
    return sub_mods


def _iter_workspace_paths(default_root: Path):
    workspace_file = Path(os.getenv("MOD_WORKSPACE_FILE", str(default_root / "DynamicTrading.code-workspace")))
    if not workspace_file.exists():
        return

    try:
        payload = json.loads(workspace_file.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Unable to parse workspace file %s: %s", workspace_file, exc)
        return

    for folder in payload.get("folders", []):
        folder_path = folder.get("path")
        if not folder_path:
            continue
        yield (workspace_file.parent / folder_path).resolve()


def _iter_candidate_paths():
    default_root = _default_mod_root()
    seen = set()

    def add(path: Path):
        resolved = path.resolve()
        key = str(resolved)
        if key in seen:
            return
        seen.add(key)
        yield resolved

    yield from add(default_root)

    colonies_root = get_server_settings().dynamic_colonies_path
    yield from add(colonies_root)

    for path in _iter_workspace_paths(default_root) or []:
        yield from add(path)

    parent = default_root.parent
    if parent.exists():
        for child in sorted(parent.iterdir(), key=lambda item: item.name.lower()):
            if child.is_dir():
                yield from add(child)


def list_workshop_projects():
    default_root = _default_mod_root()
    projects = []

    for repo_path in _iter_candidate_paths():
        if not repo_path.exists() or not (repo_path / "Contents").exists():
            continue

        workshop_id = resolve_workshop_id(repo_path)
        repo_name = repo_path.name
        project_key = _normalize_key(repo_name)
        title = _parse_workshop_title(repo_path)

        projects.append(
            {
                "key": project_key,
                "name": repo_name,
                "title": title,
                "path": str(repo_path),
                "has_preview": (repo_path / "preview.png").exists(),
                "workshop_id": workshop_id,
                "has_workshop_id": bool(workshop_id),
                "is_default": repo_path == default_root,
                "has_git": (repo_path / ".git").exists(),
                "sub_mods": _discover_sub_mods(repo_path),
            }
        )

    projects.sort(key=lambda item: (not item["is_default"], item["name"].lower()))
    return projects


def resolve_project_target(target: str | None) -> dict:
    projects = list_workshop_projects()
    if not target:
        for p in projects:
            if p["is_default"]:
                return p
        return projects[0]

    normalized = _normalize_key(target)
    for p in projects:
        if p["key"] == normalized:
            return p

    raise FileNotFoundError(f"Workshop project '{target}' not found (normalized: '{normalized}')")


@lru_cache(maxsize=1)
def get_all_sub_mods() -> list[dict]:
    """Returns a flattened list of all discovered sub-mods with their metadata."""
    sub_mods = []
    for project in list_workshop_projects():
        for mod in project.get("sub_mods", []):
            sub_mods.append(mod)
    return sub_mods


def get_mod_path_by_id(mod_id: str) -> Path | None:
    """Resolves a Mod ID to its absolute directory path (case-insensitive)."""
    target = mod_id.lower()
    for mod in get_all_sub_mods():
        if mod["id"].lower() == target:
            return Path(mod["path"])
    return None


@lru_cache(maxsize=32)
def find_media_subfolder(mod_id: str, subpath: str) -> Path | None:
    """
    Search for a subfolder (e.g. 'Manuals', 'ArchetypeDefinitions') 
    inside any of the mod's version folders (media/lua/shared/...).
    """
    all_subs = get_all_sub_mods()
    target = mod_id.lower()
    candidate_roots = [Path(m["path"]) for m in all_subs if m["id"].lower() == target]
    
    if not candidate_roots:
        return None
        
    for root in candidate_roots:
        # Search directly in mod root
        media_root = root / "media"
        if media_root.exists():
            for candidate in media_root.rglob(subpath):
                if candidate.is_dir():
                    return candidate
        
        # Search in sibling folders (e.g. if root is '42.16' and media is in 'common')
        # We check the parent directory for ANY 'media' folder
        parent = root.parent
        if parent != root:
            for candidate in parent.rglob(subpath):
                # Ensure we are still within the same mod's reach and it's a media path
                if candidate.is_dir() and "media" in candidate.parts:
                    return candidate
            
    return None


def get_flattened_modules():
    """Returns a list of modules derived from all sub-mods across all projects."""
    modules = []
    for project in list_workshop_projects():
        for mod in project.get("sub_mods", []):
            modules.append({
                "id": mod["id"],
                "name": mod["name"],
                "project_key": project["key"],
                "is_default": project["is_default"] and mod["id"] == "DynamicTradingCommon"
            })
    return modules
