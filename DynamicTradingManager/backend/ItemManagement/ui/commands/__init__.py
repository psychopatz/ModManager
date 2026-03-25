"""
CLI Commands Package
Organized command modules for ItemGenerator
"""

from .properties import (
    find_property,
    list_properties,
    dump_property,
    analyze_properties,
)

from .spawns import (
    find_rarity,
    rarity_stats,
    analyze_spawns,
)

from .items import (
    update,
    add,
    show_stats,
    delete_all_items,
    get_registered_items,
)

from .blacklist import (
    show_blacklist_stats,
    show_blacklist,
    add_to_blacklist,
    remove_from_blacklist,
)

from .cleanup import (
    cleanup_blacklist,
)

from .overrides import (
    show_override_stats,
    show_overrides,
    add_override_command,
    remove_override_command,
)

__all__ = [
    # Property commands
    'find_property',
    'list_properties',
    'dump_property',
    'analyze_properties',
    
    # Spawn commands
    'find_rarity',
    'rarity_stats',
    'analyze_spawns',
    
    # Item commands
    'update',
    'add',
    'show_stats',
    'delete_all_items',
    'get_registered_items',
    
    # Blacklist commands
    'show_blacklist_stats',
    'show_blacklist',
    'add_to_blacklist',
    'remove_from_blacklist',
    
    # Cleanup commands
    'cleanup_blacklist',
    
    # Override commands
    'show_override_stats',
    'show_overrides',
    'add_override_command',
    'remove_override_command',
]
