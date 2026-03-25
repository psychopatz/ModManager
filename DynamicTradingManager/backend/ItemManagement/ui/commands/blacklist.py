"""
Blacklist management commands
"""
import json
import os
from ...parse.blacklist import load_blacklist, get_blacklist_stats, reload_blacklist


def show_blacklist_stats():
    """Display blacklist statistics"""
    stats = get_blacklist_stats()
    
    print("\n" + "="*60)
    print("📋 BLACKLIST STATISTICS")
    print("="*60)
    print(f"Blacklisted Item IDs:       {stats['blacklisted_item_ids']}")
    print(f"Blacklisted Property Names: {stats['blacklisted_property_names']}")
    print(f"Blacklisted Property Values: {stats['blacklisted_property_values']}")
    print(f"Total Blacklist Rules:      {sum(stats.values())}")
    print("="*60 + "\n")


def show_blacklist():
    """Display current blacklist configuration"""
    blacklist = load_blacklist()
    
    print("\n" + "="*60)
    print("📋 CURRENT BLACKLIST CONFIGURATION")
    print("="*60)
    
    # Show blacklisted item IDs
    print("\n🚫 Blacklisted Item IDs:")
    item_ids = blacklist.get("itemIds", [])
    if item_ids:
        for item_id in sorted(item_ids):
            print(f"  - {item_id}")
    else:
        print("  (none)")
    
    # Show blacklisted property names
    print("\n🚫 Blacklisted Properties (by name):")
    prop_names = blacklist.get("properties", {}).get("names", [])
    if prop_names:
        for prop_name in sorted(prop_names):
            print(f"  - {prop_name}")
    else:
        print("  (none)")
    
    # Show blacklisted property values
    print("\n🚫 Blacklisted Properties (by value):")
    prop_values = blacklist.get("properties", {}).get("values", {})
    if prop_values:
        for prop_name, values in sorted(prop_values.items()):
            if isinstance(values, list):
                values_str = ", ".join(str(v) for v in values)
            else:
                values_str = str(values)
            print(f"  - {prop_name}: {values_str}")
    else:
        print("  (none)")
    
    print("="*60 + "\n")


def add_to_blacklist(item_id=None, property_name=None, property_value=None):
    """
    Add an entry to the blacklist
    
    Args:
        item_id: Item ID to blacklist (e.g., "Base.Money")
        property_name: Property name to blacklist (e.g., "hidden")
        property_value: Tuple of (property_name, value) to blacklist (e.g., ("Weight", 10))
    """
    blacklist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blacklist.json")
    
    blacklist = load_blacklist()
    modified = False
    
    if item_id:
        if item_id not in blacklist.get("itemIds", []):
            blacklist.setdefault("itemIds", []).append(item_id)
            modified = True
            print(f"✅ Added item ID '{item_id}' to blacklist")
        else:
            print(f"ℹ️  Item ID '{item_id}' is already blacklisted")
    
    if property_name:
        if property_name not in blacklist.get("properties", {}).get("names", []):
            blacklist.setdefault("properties", {}).setdefault("names", []).append(property_name)
            modified = True
            print(f"✅ Added property name '{property_name}' to blacklist")
        else:
            print(f"ℹ️  Property name '{property_name}' is already blacklisted")
    
    if property_value:
        prop_name, value = property_value
        values_list = blacklist.setdefault("properties", {}).setdefault("values", {}).setdefault(prop_name, [])
        
        if not isinstance(values_list, list):
            values_list = [values_list]
            blacklist["properties"]["values"][prop_name] = values_list
        
        if value not in values_list:
            values_list.append(value)
            modified = True
            print(f"✅ Added property value '{prop_name}={value}' to blacklist")
        else:
            print(f"ℹ️  Property value '{prop_name}={value}' is already blacklisted")
    
    if modified:
        with open(blacklist_path, 'w') as f:
            json.dump(blacklist, f, indent=2)
        reload_blacklist()
        print(f"💾 Blacklist saved to {blacklist_path}")
    
    return modified


def remove_from_blacklist(item_id=None, property_name=None, property_value=None):
    """
    Remove an entry from the blacklist
    
    Args:
        item_id: Item ID to remove
        property_name: Property name to remove
        property_value: Tuple of (property_name, value) to remove
    """
    blacklist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blacklist.json")
    
    blacklist = load_blacklist()
    modified = False
    
    if item_id:
        if item_id in blacklist.get("itemIds", []):
            blacklist["itemIds"].remove(item_id)
            modified = True
            print(f"✅ Removed item ID '{item_id}' from blacklist")
        else:
            print(f"ℹ️  Item ID '{item_id}' was not in blacklist")
    
    if property_name:
        if property_name in blacklist.get("properties", {}).get("names", []):
            blacklist["properties"]["names"].remove(property_name)
            modified = True
            print(f"✅ Removed property name '{property_name}' from blacklist")
        else:
            print(f"ℹ️  Property name '{property_name}' was not in blacklist")
    
    if property_value:
        prop_name, value = property_value
        values_list = blacklist.get("properties", {}).get("values", {}).get(prop_name, [])
        
        if isinstance(values_list, list) and value in values_list:
            values_list.remove(value)
            if not values_list:
                del blacklist["properties"]["values"][prop_name]
            modified = True
            print(f"✅ Removed property value '{prop_name}={value}' from blacklist")
        else:
            print(f"ℹ️  Property value '{prop_name}={value}' was not in blacklist")
    
    if modified:
        with open(blacklist_path, 'w') as f:
            json.dump(blacklist, f, indent=2)
        reload_blacklist()
        print(f"💾 Blacklist saved to {blacklist_path}")
    
    return modified
