"""
Vanilla item data loader and analyzer
Scans Project Zomboid vanilla scripts and extracts item definitions
"""
import os
import re
from .helpers import sanitize_path, get_stat, has_property, parse_categories, count_recipes


def get_opening_maps(vanilla_path, silent=False):
    """
    Maps UnopenedID -> OpenedID using recipe itemMappers
    
    Args:
        vanilla_path: Path to vanilla scripts directory
        silent: Suppress print output
    
    Returns:
        dict: Mapping of unopened -> opened item IDs
    """
    mapping = {}
    
    if not silent:
        print("[*] Building Opening Map from Recipes...")
    
    recipe_dir = os.path.join(vanilla_path, "generated/recipes/")
    if not os.path.exists(recipe_dir):
        recipe_dir = os.path.join(os.path.dirname(vanilla_path), "generated/recipes/")
    
    if not os.path.exists(recipe_dir):
        return mapping
    
    for file in sorted(os.listdir(recipe_dir)):
        if not file.endswith(".txt"):
            continue
            
        with open(os.path.join(recipe_dir, file), "r", errors="ignore") as f:
            content = f.read()
            mappers = re.findall(r"itemMapper\s+\w+\s*\{([^}]*)\}", content, re.DOTALL)
            
            for mapper_content in mappers:
                pairs = re.findall(r"(?:Base\.)?(\w+)\s*=\s*(?:Base\.)?(\w+)", mapper_content)
                for opened, unopened in pairs:
                    mapping[unopened] = opened
    
    return mapping


def get_vanilla_data(vanilla_path, silent=False):
    """
    Scan vanilla scripts and extract item/fluid definitions
    
    Args:
        vanilla_path: Path to vanilla scripts directory
        silent: Suppress print output
    
    Returns:
        tuple: (item_data, fluid_data) dictionaries
    """
    item_data = {}
    fluid_data = {}
    opening_map = get_opening_maps(vanilla_path, silent=silent)
    
    if not silent:
        print(f"[*] Scanning Vanilla Scripts: {vanilla_path}")
    
    for root, dirs, files in os.walk(vanilla_path):
        for file in sorted(files):
            if not file.endswith(".txt"):
                continue
            
            file_path = os.path.join(root, file)
            file_rel = os.path.relpath(file_path, vanilla_path)
            
            with open(file_path, "r", errors="ignore") as f:
                content = f.read()
                
                # Parse items
                item_blocks = re.findall(r"item\s+([a-zA-Z_]\w*)\s*\{([^}]*)\}", content, re.DOTALL)
                for item_id, props in item_blocks:
                    categories = parse_categories(props)
                    
                    item_data[item_id] = {
                        'origin': file_rel,
                        'category': categories['category'],
                        'subcat': categories['subcat'],
                        'tags': categories['tags'],
                        'eat_type': categories['eat_type'],
                        'props': props,
                        'opened_variant': opening_map.get(item_id)
                    }
                
                # Parse fluids
                fluid_blocks = re.findall(r"fluid\s+([a-zA-Z_]\w*)\s*\{([^}]*)\}", content, re.DOTALL)
                for fluid_id, props in fluid_blocks:
                    fluid_data[fluid_id] = {
                        'origin': file_rel,
                        'category': 'Fluids',
                        'subcat': 'General',
                        'tags': 'N/A',
                        'eat_type': 'N/A',
                        'props': props,
                        'weight': 0.0
                    }
    
    return item_data, fluid_data


def combine_item_and_fluid_data(item_data, fluid_data):
    """
    Combine item and fluid data into single dictionary
    
    Args:
        item_data: Dictionary of items
        fluid_data: Dictionary of fluids
    
    Returns:
        dict: Combined item/fluid data
    """
    return {**item_data, **fluid_data}


def get_inherited_properties(item_id, item_data):
    """
    Get combined properties including inherited from opened variant
    
    Args:
        item_id: Item ID
        item_data: Item data dictionary
    
    Returns:
        str: Combined properties string
    """
    if item_id not in item_data:
        return ""
    
    item = item_data[item_id]
    props = item.get('props', '')
    
    # Add inherited properties from opened variant if exists
    opened_id = item.get('opened_variant')
    if opened_id and opened_id in item_data:
        inherited_props = item_data[opened_id].get('props', '')
        props = props + "\n" + inherited_props
    
    return props


def get_item_metadata(item_id, combined_data):
    """
    Get all metadata for an item including computed fields
    
    Args:
        item_id: Item ID
        combined_data: Combined item/fluid data
    
    Returns:
        dict: Complete item metadata
    """
    if item_id not in combined_data:
        return None
    
    meta = combined_data[item_id].copy()
    props = meta.get('props', '')
    
    # Compute additional fields
    meta['weight'] = get_stat('Weight', 0.1, props)
    meta['capacity'] = get_stat('Capacity', 0.0, props)
    meta['condition_max'] = get_stat('ConditionMax', 0.0, props)
    
    # Food properties
    meta['hunger_change'] = get_stat('HungerChange', 0.0, props)
    meta['thirst_change'] = get_stat('ThirstChange', 0.0, props)
    meta['calories'] = get_stat('Calories', 0.0, props)
    meta['days_fresh'] = get_stat('DaysFresh', 0.0, props)
    meta['days_rotten'] = get_stat('DaysTotallyRotten', 0.0, props)
    
    # Combat properties
    meta['min_damage'] = get_stat('MinDamage', 0.0, props)
    meta['max_damage'] = get_stat('MaxDamage', 0.0, props)
    meta['max_range'] = get_stat('MaxRange', 0.0, props)
    meta['max_hitcount'] = get_stat('MaxHitcount', 0.0, props)
    meta['critical_chance'] = get_stat('CriticalChance', 0.0, props)
    
    # Clothing properties
    meta['bite_defense'] = get_stat('BiteDefense', 0.0, props)
    meta['scratch_defense'] = get_stat('ScratchDefense', 0.0, props)
    meta['bullet_defense'] = get_stat('BulletDefense', 0.0, props)
    meta['insulation'] = get_stat('Insulation', 0.0, props)
    meta['wind_resistance'] = get_stat('WindResistance', 0.0, props)
    
    # Utility properties
    meta['weight_reduction'] = get_stat('WeightReduction', 0.0, props)
    meta['recipes_count'] = count_recipes(props)
    meta['use_delta'] = get_stat('UseDelta', 0.0, props)
    meta['total_uses'] = int(round(1.0 / meta['use_delta'])) if meta['use_delta'] > 0 else 1
    
    # Boolean flags
    meta['is_opened'] = has_property(props, 'opened') or has_property(props, 'open') or 'opened' in item_id.lower()
    meta['is_survival_gear'] = has_property(props, 'SurvivalGear')
    meta['is_sterile'] = has_property(props, 'Sterile')
    meta['is_high_tier'] = has_property(props, 'IsHighTier')
    
    return meta
