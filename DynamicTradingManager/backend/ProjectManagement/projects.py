import json
import logging
import os
from pathlib import Path

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
                    "description": mod_data.get("description", "")
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


def resolve_project_target(target: str | None = None):
    projects = list_workshop_projects()
    if not projects:
        raise FileNotFoundError("No workshop projects were discovered.")

    if not target:
        project = projects[0]
        return {**project, "path": Path(project["path"])}

    normalized = _normalize_key(target)
    target_path = Path(target).expanduser().resolve()

    for project in projects:
        if normalized and normalized in {
            project["key"],
            _normalize_key(project["name"]),
            _normalize_key(project["title"]),
        }:
            return {**project, "path": Path(project["path"])}

        if target_path == Path(project["path"]):
            return {**project, "path": Path(project["path"])}

    if target_path.exists() and (target_path / "Contents").exists():
        repo_name = target_path.name
        return {
            "key": _normalize_key(repo_name),
            "name": repo_name,
            "title": _parse_workshop_title(target_path),
            "path": target_path,
            "has_preview": (target_path / "preview.png").exists(),
            "workshop_id": resolve_workshop_id(target_path),
            "has_workshop_id": bool(resolve_workshop_id(target_path)),
            "is_default": target_path == _default_mod_root(),
            "has_git": (target_path / ".git").exists(),
            "sub_mods": _discover_sub_mods(target_path),
        }

    raise FileNotFoundError(f'Unable to resolve workshop project "{target}".')
