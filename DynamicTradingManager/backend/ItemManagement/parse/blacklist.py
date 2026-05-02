"""
Blacklist module for filtering unwanted items
Supports blacklisting by:
- Item ID (exact match)
- Property name (any item with this property)
- Property value (specific property:value pairs)
"""

import os
import json

_blacklist_cache = None

def load_blacklist():
    """Load blacklist configuration from blacklist.json"""
    global _blacklist_cache
    if _blacklist_cache is not None:
        return _blacklist_cache
    
    blacklist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blacklist.json")
    
    if not os.path.exists(blacklist_path):
        print(f"[WARNING] Blacklist file not found at {blacklist_path}, using empty blacklist")
        _blacklist_cache = {
            "itemIds": [],
            "whitelistItemIds": [],
            "properties": {
                "names": [],
                "values": {}
            }
        }
        return _blacklist_cache
    
    try:
        with open(blacklist_path, 'r') as f:
            _blacklist_cache = json.load(f)
            if not isinstance(_blacklist_cache, dict):
                _blacklist_cache = {}
            _blacklist_cache.setdefault("itemIds", [])
            _blacklist_cache.setdefault("whitelistItemIds", [])
            _blacklist_cache.setdefault("properties", {"names": [], "values": {}})
            return _blacklist_cache
    except Exception as e:
        print(f"[ERROR] Failed to load blacklist: {e}")
        _blacklist_cache = {
            "itemIds": [],
            "whitelistItemIds": [],
            "properties": {
                "names": [],
                "values": {}
            }
        }
        return _blacklist_cache


def is_item_blacklisted(item_id, item_properties=None):
    """
    Check if an item is blacklisted
    
    Args:
        item_id: The item ID (e.g., "Base.Money")
        item_properties: Dict of item properties {property_name: value}
    
    Returns:
        tuple: (is_blacklisted, reason) where reason explains why it was blacklisted
    """
    blacklist = load_blacklist()
    
    # Check item ID blacklist
    if item_id in blacklist.get("itemIds", []):
        return (True, f"Item ID '{item_id}' is blacklisted")
    
    # If no properties provided, can only check ID
    if item_properties is None:
        return (False, None)
    
    # Check property name blacklist
    blacklisted_property_names = blacklist.get("properties", {}).get("names", [])
    for prop_name in blacklisted_property_names:
        if prop_name in item_properties:
            return (True, f"Has blacklisted property '{prop_name}'")
    
    # Check property:value blacklist
    property_values = blacklist.get("properties", {}).get("values", {})
    for prop_name, blacklisted_values in property_values.items():
        if prop_name in item_properties:
            item_value = item_properties[prop_name]
            
            # Handle different value types
            if isinstance(blacklisted_values, list):
                # Check if the item's value is in the blacklist
                if item_value in blacklisted_values:
                    return (True, f"Property '{prop_name}' has blacklisted value '{item_value}'")
                
                # Also check string comparison for numeric values
                try:
                    if str(item_value) in [str(v) for v in blacklisted_values]:
                        return (True, f"Property '{prop_name}' has blacklisted value '{item_value}'")
                except:
                    pass
    
    return (False, None)


def filter_items(items_dict, verbose=False):
    """
    Filter out blacklisted items from a dictionary
    
    Args:
        items_dict: Dict of {item_id: item_data} where item_data contains properties
        verbose: If True, print information about filtered items
    
    Returns:
        tuple: (filtered_dict, blacklisted_items) where blacklisted_items is {item_id: reason}
    """
    filtered = {}
    blacklisted = {}
    
    for item_id, item_data in items_dict.items():
        # Extract properties from item_data
        # Assuming item_data is a dict with properties directly or in a 'properties' key
        if isinstance(item_data, dict):
            properties = item_data.get('properties', item_data)
        else:
            properties = None
        
        is_blacklisted, reason = is_item_blacklisted(item_id, properties)
        
        if is_blacklisted:
            blacklisted[item_id] = reason
            if verbose:
                print(f"[BLACKLIST] Excluding {item_id}: {reason}")
        else:
            filtered[item_id] = item_data
    
    return filtered, blacklisted


def get_blacklist_stats():
    """Get statistics about the current blacklist configuration"""
    blacklist = load_blacklist()
    
    item_count = len(blacklist.get("itemIds", []))
    property_name_count = len(blacklist.get("properties", {}).get("names", []))
    
    property_value_count = 0
    for prop_name, values in blacklist.get("properties", {}).get("values", {}).items():
        if isinstance(values, list):
            property_value_count += len(values)
        else:
            property_value_count += 1
    
    return {
        "blacklisted_item_ids": item_count,
        "blacklisted_property_names": property_name_count,
        "blacklisted_property_values": property_value_count
    }


def find_invalid_blacklist_ids():
    """
    Find invalid item IDs in blacklist
    Note: This is a placeholder - we can't validate IDs without loading vanilla items
    Returns empty list for now
    """
    return []


def find_duplicate_blacklist_ids():
    """Find duplicate item IDs in blacklist"""
    blacklist = load_blacklist()
    item_ids = blacklist.get("itemIds", [])
    
    seen = set()
    duplicates = []
    
    for item_id in item_ids:
        if item_id in seen:
            if item_id not in duplicates:
                duplicates.append(item_id)
        seen.add(item_id)
    
    return duplicates



def reload_blacklist():
    """Force reload of blacklist configuration"""
    global _blacklist_cache
    _blacklist_cache = None
    return load_blacklist()


def add_item_to_blacklist(item_id):
    """Add an item ID to blacklist.json if it is not already present"""
    if not item_id or not isinstance(item_id, str):
        raise ValueError("item_id must be a non-empty string")

    blacklist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blacklist.json")
    blacklist = reload_blacklist()
    item_ids = list(blacklist.get("itemIds", []))

    if item_id not in item_ids:
        item_ids.append(item_id)
        item_ids.sort()

    next_blacklist = {
        "itemIds": item_ids,
        "whitelistItemIds": list(blacklist.get("whitelistItemIds", [])),
        "properties": blacklist.get("properties", {"names": [], "values": {}}),
    }

    with open(blacklist_path, "w") as file_handle:
        json.dump(next_blacklist, file_handle, indent=2)

    reload_blacklist()
    return next_blacklist
