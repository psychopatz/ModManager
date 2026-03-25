"""
Cleanup commands for managing Lua files
"""
from ...commons.lua_handler import cleanup_blacklisted_items


def cleanup_blacklist(vanilla_items, dry_run=False):
    """
    Remove all blacklisted items from existing Lua files
    
    Args:
        vanilla_items: Vanilla item data dictionary
        dry_run: If True, only show what would be removed
    """
    return cleanup_blacklisted_items(vanilla_items, dry_run=dry_run)
