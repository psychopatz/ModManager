from pathlib import Path
from .server_settings import get_server_settings

# The current active version folder name for versioned assets
# This is where we look for things that aren't in 'common' yet
ACTIVE_VERSION = "42.16"

from ProjectManagement.projects import get_mod_path_by_id, find_media_subfolder, get_all_sub_mods


def _resolve_submod_root(path: Path) -> Path:
    """Normalize a discovered sub-mod path to the folder directly under Contents/mods."""
    path = Path(path)
    if path.parent.name == "mods":
        return path
    if path.parent.parent.name == "mods":
        return path.parent
    return path


def _collect_manual_dirs_in_priority(mod_root: Path) -> list[Path]:
    """Collect manual lua directories with preference: common first, then active version."""
    candidates = []

    # 1) Preferred convention: sibling common folder
    common_manuals = mod_root / "common" / "media" / "lua"
    if common_manuals.exists():
        candidates.extend(p for p in common_manuals.rglob("Manuals") if p.is_dir())

    # 2) Active version fallback (e.g. 42.16)
    version_manuals = mod_root / ACTIVE_VERSION / "media" / "lua"
    if version_manuals.exists():
        candidates.extend(p for p in version_manuals.rglob("Manuals") if p.is_dir())

    # 3) Any other nested manuals within this sub-mod only
    candidates.extend(p for p in mod_root.rglob("Manuals") if p.is_dir() and "media" in p.parts and "lua" in p.parts)

    deduped = []
    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)

    deduped.sort(key=lambda p: (
        "common" in p.parts,
        ACTIVE_VERSION in p.parts,
    ), reverse=True)
    return deduped

def get_mod_root(mod_id: str) -> Path:
    """Returns the absolute path to a mod's directory within its workshop item."""
    path = get_mod_path_by_id(mod_id)
    if path:
        return path
    
    return Path()

def get_mod_common_path(mod_id: str) -> Path:
    """Returns the path to the 'common' directory for a mod."""
    return get_mod_root(mod_id) / "common"

def get_mod_version_path(mod_id: str, version: str = ACTIVE_VERSION) -> Path:
    """Returns the path to a specific version directory for a mod."""
    return get_mod_root(mod_id) / version

def get_manuals_roots(mod_id: str) -> list[Path]:
    """Returns a list of all valid manuals Lua directories for a mod (e.g. common and versioned)."""
    all_subs = get_all_sub_mods()
    target_id = mod_id.lower()
    candidate_roots = [_resolve_submod_root(Path(m["path"])) for m in all_subs if m["id"].lower() == target_id]
    
    found_roots = []
    seen = set()

    def add_if_unique(path: Path):
        resolved = path.resolve()
        if resolved not in seen:
            found_roots.append(resolved)
            seen.add(resolved)

    for root in candidate_roots:
        for candidate in _collect_manual_dirs_in_priority(root):
            add_if_unique(candidate)
    
    if found_roots:
        # Keep preference for common first, then active version.
        found_roots.sort(key=lambda p: (
            "common" in p.parts,
            ACTIVE_VERSION in p.parts,
        ), reverse=True)
        return found_roots

    # Standard fallback - use mod initials for correct path structure
    root = get_mod_common_path(mod_id)
    initials = "".join(c for c in mod_id if c.isupper())
    safe_initials = initials or "DT"
    fallback = root / "media" / "lua" / "shared" / safe_initials / "Common" / "Manuals"
    return [fallback]

def get_manuals_root(mod_id: str, use_common: bool = True) -> Path:
    """Returns the primary manuals Lua directory for a mod."""
    roots = get_manuals_roots(mod_id)
    # If using versioned, try to find a root that contains ACTIVE_VERSION or isn't 'common'
    if not use_common:
        v_roots = [r for r in roots if ACTIVE_VERSION in str(r)]
        if v_roots:
            return v_roots[0]
    
    return roots[0]

def get_manual_assets_root(mod_id: str) -> Path:
    """Returns the path to the manuals UI assets directory for a mod."""
    all_subs = get_all_sub_mods()
    target_id = mod_id.lower()
    candidate_roots = [_resolve_submod_root(Path(m["path"])) for m in all_subs if m["id"].lower() == target_id]
    
    for root in candidate_roots:
        common_ui = root / "common" / "media" / "ui" / "Manuals"
        if common_ui.is_dir():
            return common_ui.resolve()

        version_ui = root / ACTIVE_VERSION / "media" / "ui" / "Manuals"
        if version_ui.is_dir():
            return version_ui.resolve()

        for candidate in root.rglob("Manuals"):
            if candidate.is_dir() and "media" in candidate.parts and "ui" in candidate.parts:
                return candidate.resolve()

    return get_mod_common_path(mod_id) / "media" / "ui" / "Manuals"


def get_archetypes_root(mod_id: str) -> Path | None:
    """Returns the path to the archetype definitions directory."""
    return find_media_subfolder(mod_id, "ArchetypeDefinitions")

def get_portraits_root(mod_id: str = "DynamicTradingCommon") -> Path:
    """Returns the path to the portrait textures directory."""
    found = find_media_subfolder(mod_id, "Portraits")
    if found:
        return found
    return get_mod_common_path(mod_id) / "media/ui/Portraits"

def get_items_root(mod_id: str = "DynamicTradingCommon") -> Path:
    """Returns the path to the common items directory."""
    found = find_media_subfolder(mod_id, "Items")
    if found:
        return found
    return get_mod_common_path(mod_id) / "media/lua/shared/DT/Common/Items"

def get_fluids_lua_path() -> Path:
    """Returns the path to the fluids Lua registry file."""
    return get_items_root() / "DT_Fluids.lua"
