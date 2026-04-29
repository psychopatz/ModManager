from pathlib import Path
from .server_settings import get_server_settings

# The current active version folder name for versioned assets
# This is where we look for things that aren't in 'common' yet
ACTIVE_VERSION = "42.16"

from ProjectManagement.projects import get_mod_path_by_id, find_media_subfolder, get_all_sub_mods

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
    candidate_roots = [Path(m["path"]) for m in all_subs if m["id"].lower() == target_id]
    
    initials = "".join(c for c in mod_id if c.isupper())
    found_roots = []
    seen = set()

    def add_if_unique(path: Path):
        resolved = path.resolve()
        if resolved not in seen:
            found_roots.append(resolved)
            seen.add(resolved)

    for root in candidate_roots:
        # 1. Prefer 'common' sibling if it exists (highly likely in B42 structure)
        parent = root.parent
        if parent != root:
            # Check for direct 'common/media/lua/shared/.../Manuals'
            for candidate in parent.glob("common/media/lua/*/Manuals"):
                 if candidate.is_dir():
                     add_if_unique(candidate)
            # Fallback sibling search
            for candidate in parent.rglob("Manuals"):
                if candidate.is_dir() and "media" in candidate.parts and "lua" in candidate.parts:
                    add_if_unique(candidate)

        # 2. Search directly in mod root (e.g. 42.16/media)
        media_root = root / "media"
        if media_root.exists():
            for candidate in media_root.rglob("Manuals"):
                if candidate.is_dir() and "lua" in candidate.parts:
                    add_if_unique(candidate)
    
    if found_roots:
        # Sort so that roots containing initials come first, and then prefer 'common' in the path
        found_roots.sort(key=lambda p: (
            (initials != "" and initials in p.parts),
            ("common" in p.parts)
        ), reverse=True)
        return found_roots

    # Standard fallback - use mod initials for correct path structure
    root = get_mod_common_path(mod_id)
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
    candidate_roots = [Path(m["path"]) for m in all_subs if m["id"].lower() == target_id]
    
    for root in candidate_roots:
        # Search directly in mod root
        media_root = root / "media"
        if media_root.exists():
            for candidate in media_root.rglob("Manuals"):
                if candidate.is_dir() and "ui" in candidate.parts:
                    return candidate

        # Search in parent directory for sibling folders
        parent = root.parent
        if parent != root:
            for candidate in parent.rglob("Manuals"):
                if candidate.is_dir() and "media" in candidate.parts and "ui" in candidate.parts:
                    return candidate

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
