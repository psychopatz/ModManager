"""
Signature module exports.
Makes all property-based signatures available.
"""
from .weapons import matches_weapon_signature, get_weapon_tags
from .fishing import matches_fishing_signature, get_fishing_tags
from .clothing import matches_clothing_signature, get_clothing_tags
from .food import matches_food_signature, get_food_tags
from .tools import matches_tool_signature, get_tool_tags
from .electronics import matches_electronics_signature, get_electronics_tags
from .medical import matches_medical_signature, get_medical_tags
from .containers import matches_container_signature, get_container_tags
from .resources import matches_resource_signature, get_resource_tags
from .building import matches_building_signature, get_building_tags

__all__ = [
    'matches_weapon_signature', 'get_weapon_tags',
    'matches_fishing_signature', 'get_fishing_tags',
    'matches_clothing_signature', 'get_clothing_tags',
    'matches_food_signature', 'get_food_tags',
    'matches_tool_signature', 'get_tool_tags',
    'matches_electronics_signature', 'get_electronics_tags',
    'matches_medical_signature', 'get_medical_tags',
    'matches_container_signature', 'get_container_tags',
    'matches_resource_signature', 'get_resource_tags',
    'matches_building_signature', 'get_building_tags',
]
