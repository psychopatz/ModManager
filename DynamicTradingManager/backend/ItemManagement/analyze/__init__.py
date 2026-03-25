"""
Analysis module for item properties and spawn rates
Provides analysis tools for examining vanilla item data
"""

from .property_analyzer import (
    find_items_with_property,
    dump_items_by_property,
    list_all_properties,
    analyze_all_properties,
    find_items_by_multiple_properties
)

from .spawn_analyzer import (
    load_spawn_data,
    get_spawn_weight,
    get_spawn_locations,
    calculate_rarity_from_spawn,
    calculate_rarity_score,
    get_rarity_statistics,
    get_items_by_rarity,
    calculate_enhanced_rarity_score
)

__all__ = [
    # Property analysis
    'find_items_with_property',
    'dump_items_by_property',
    'list_all_properties',
    'analyze_all_properties',
    'find_items_by_multiple_properties',
    # Spawn analysis
    'load_spawn_data',
    'get_spawn_weight',
    'get_spawn_locations',
    'calculate_rarity_from_spawn',
    'calculate_rarity_score',
    'get_rarity_statistics',
    'get_items_by_rarity',
    'calculate_enhanced_rarity_score',
]
