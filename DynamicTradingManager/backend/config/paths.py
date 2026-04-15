from pathlib import Path
from .server_settings import get_server_settings

# The current active version folder name for versioned assets
# This is where we look for things that aren't in 'common' yet
ACTIVE_VERSION = "42.16"

def get_mod_root(mod_id: str) -> Path:
    """Returns the absolute path to a mod's directory within its workshop item."""
    settings = get_server_settings()
    if mod_id in ["DynamicTradingCommon", "DynamicTradingV1", "DynamicTradingV2"]:
        return settings.dynamic_trading_path / "Contents/mods" / mod_id
    if mod_id == "DynamicColonies":
        return settings.dynamic_colonies_path / "Contents/mods" / mod_id
    if mod_id == "CurrencyExpanded":
        return settings.dynamic_currency_path / "Contents/mods/CurrencyExpanded"
    return Path()

def get_mod_common_path(mod_id: str) -> Path:
    """Returns the path to the 'common' directory for a mod."""
    return get_mod_root(mod_id) / "common"

def get_mod_version_path(mod_id: str, version: str = ACTIVE_VERSION) -> Path:
    """Returns the path to a specific version directory for a mod."""
    return get_mod_root(mod_id) / version

def get_manuals_root(mod_id: str, use_common: bool = True) -> Path:
    """Returns the path to the manuals Lua directory for a mod."""
    root = get_mod_common_path(mod_id) if use_common else get_mod_version_path(mod_id)
    
    mapping = {
        "DynamicTradingCommon": "media/lua/shared/DT/Common/Manuals",
        "DynamicTradingV1": "media/lua/shared/DT/V1/Manuals",
        "DynamicTradingV2": "media/lua/shared/DT/V2/Manuals",
        "DynamicColonies": "media/lua/shared/DC/Common/Manuals",
        "CurrencyExpanded": "media/lua/shared/CE/Common/Manuals",
    }
    
    return root / mapping.get(mod_id, "")

def get_manual_assets_root(mod_id: str, use_common: bool = True) -> Path:
    """Returns the path to the manuals UI assets directory for a mod."""
    root = get_mod_common_path(mod_id) if use_common else get_mod_version_path(mod_id)
    return root / "media/ui/Manuals"

def get_portraits_root() -> Path:
    """Returns the path to the portrait textures directory."""
    return get_mod_common_path("DynamicTradingCommon") / "media/ui/Portraits"

def get_items_root() -> Path:
    """Returns the path to the common items directory."""
    return get_mod_common_path("DynamicTradingCommon") / "media/lua/shared/DT/Common/Items"

def get_fluids_lua_path() -> Path:
    """Returns the path to the fluids Lua registry file."""
    return get_items_root() / "DT_Fluids.lua"
