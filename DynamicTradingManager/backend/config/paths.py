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
    
    # Fallback to legacy structure if not found in discovery
    settings = get_server_settings()
    if mod_id in ["DynamicTradingCommon", "DynamicTradingV1", "DynamicTradingV2"]:
        return settings.dynamic_trading_path / "Contents/mods" / mod_id
    return Path()

def get_mod_common_path(mod_id: str) -> Path:
    """Returns the path to the 'common' directory for a mod."""
    return get_mod_root(mod_id) / "common"

def get_mod_version_path(mod_id: str, version: str = ACTIVE_VERSION) -> Path:
    """Returns the path to a specific version directory for a mod."""
    return get_mod_root(mod_id) / version

def get_manuals_root(mod_id: str, use_common: bool = True) -> Path:
    """Returns the path to the manuals Lua directory for a mod."""
    # Attempt dynamic discovery first, preferring lua/shared
    all_subs = get_all_sub_mods()
    candidate_roots = [Path(m["path"]) for m in all_subs if m["id"] == mod_id]
    
    for root in candidate_roots:
        # Search directly in mod root (e.g. 42.16/media)
        media_root = root / "media"
        if media_root.exists():
            for candidate in media_root.rglob("Manuals"):
                if candidate.is_dir() and "lua" in candidate.parts:
                    return candidate
        
        # Search in parent directory (e.g. DynamicTradingCommon/) to find
        # sibling folders like 'common/media/lua/.../Manuals'
        parent = root.parent
        if parent != root:
            for candidate in parent.rglob("Manuals"):
                if candidate.is_dir() and "media" in candidate.parts and "lua" in candidate.parts:
                    return candidate
        
    # Standard fallback
    root = get_mod_common_path(mod_id) if use_common else get_mod_version_path(mod_id)
    return root / "media/lua/shared/DT/Common/Manuals"

def get_manual_assets_root(mod_id: str) -> Path:
    """Returns the path to the manuals UI assets directory for a mod."""
    all_subs = get_all_sub_mods()
    candidate_roots = [Path(m["path"]) for m in all_subs if m["id"] == mod_id]
    
    for root in candidate_roots:
        # Search directly in mod root
        media_root = root / "media"
        if media_root.exists():
            for candidate in media_root.rglob("Manuals"):
                if candidate.is_dir() and "ui" in candidate.parts:
                    return candidate

        # Search in parent directory for sibling folders like 'common/media/ui/Manuals'
        parent = root.parent
        if parent != root:
            for candidate in parent.rglob("Manuals"):
                if candidate.is_dir() and "media" in candidate.parts and "ui" in candidate.parts:
                    return candidate

    return get_mod_common_path(mod_id) / "media/ui/Manuals"


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
