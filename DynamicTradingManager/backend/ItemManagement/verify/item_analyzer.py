"""
Item analysis and valuation system
Calculates worth, stock levels, and extracts detailed item statistics
"""
import re
from .helpers import get_stat, has_property, count_recipes


def calculate_worth(item_id, props, category, subcat):
    """
    Calculate item worth multiplier based on properties and category
    
    Args:
        item_id: Item identifier
        props: Properties string
        category: Item category
        subcat: Item subcategory
    
    Returns:
        float: Worth multiplier value
    """
    p_lower = props.lower()
    
    weight = get_stat("Weight", 0.1, props)
    worth = 1.0
    
    capacity = get_stat("Capacity", 0.0, props)
    weight_reduction = get_stat("WeightReduction", 0.0, props)
    metal_value = get_stat("MetalValue", 0.0, props)
    fuel_value = get_stat("FuelValue", 0.0, props)
    res_val = metal_value + fuel_value
    
    fuel_ratio = get_stat("FireFuelRatio", 0.0, props)
    use_delta = get_stat("UseDelta", 0.0, props)
    total_uses = int(round(1.0 / use_delta)) if use_delta > 0 else 1
    
    # Extract LearnedRecipes count
    recipes = count_recipes(props)
    
    # --- Category-specific valuation ---
    
    if capacity > 0:
        # Boosted base multiplier for containers/storage items
        worth = (capacity * (weight_reduction / 10 + 1)) / (weight + 0.1) * 2.5
    
    elif category == "Food":
        hunger = abs(get_stat("HungerChange", 0.0, props))
        thirst = abs(get_stat("ThirstChange", 0.0, props))
        calories = get_stat("Calories", 0.0, props) / 100.0
        
        # Penalties: positive Unhappy/Boredom/Stress are BAD stats in PZ
        penalties = (
            max(0, get_stat("UnhappyChange", 0.0, props)) +
            max(0, get_stat("BoredomChange", 0.0, props)) +
            max(0, get_stat("StressChange", 0.0, props))
        ) * 2
        
        # Shelf-life factor (Capped to prevent price inflation)
        fresh = get_stat("DaysFresh", 0.0, props)
        rotten = get_stat("DaysTotallyRotten", 0.0, props)
        shelf_life = min(50, (fresh + rotten) / 5.0)
        
        # Preservation bonus
        stability = 0
        if "cannedfood = true" in p_lower:
            stability += 50
        elif "packaged = true" in p_lower:
            stability += 10
        
        worth = (hunger + (thirst / 2) + calories - penalties + stability + shelf_life) / (weight * 1.5 + 0.1)
    
    elif "Weapon" in category:
        min_dmg = get_stat("MinDamage", 0.0, props)
        max_dmg = get_stat("MaxDamage", 0.0, props)
        avg_dmg = (min_dmg + max_dmg) / 2
        max_range = get_stat("MaxRange", 1.0, props)
        max_hitcount = get_stat("MaxHitcount", 1.0, props)
        condition = get_stat("ConditionMax", 5.0, props)
        reliability = get_stat("ConditionLowerChanceOneIn", 5.0, props)
        swing_time = get_stat("MinimumSwingtime", 1.0, props)
        
        worth = ((avg_dmg * max_range * max_hitcount) + (condition * reliability / 5)) / (weight * 2 + swing_time * 10 + 0.1)
    
    elif category in ["Clothing", "ProtectiveGear"]:
        bite = get_stat("BiteDefense", 0.0, props)
        scratch = get_stat("ScratchDefense", 0.0, props)
        bullet = get_stat("BulletDefense", 0.0, props)
        insulation = get_stat("Insulation", 0.0, props)
        wind_res = get_stat("WindResistance", 0.0, props)
        run_mod = get_stat("RunSpeedModifier", 1.0, props)
        combat_mod = get_stat("CombatSpeedModifier", 1.0, props)
        
        penalty = (1.0 - run_mod) * 100 + (1.0 - combat_mod) * 50
        
        worth = ((bite * 3) + scratch + (bullet * 2) + (insulation * 20) + (wind_res * 10)) / (weight * 3 + penalty + 1)
    
    elif recipes > 0 or category == "Literature":
        worth = (recipes * 25 + 5) / (weight + 0.1)
    
    elif fuel_ratio > 0:
        worth = (fuel_ratio * 15) / (weight + 0.1)
    
    else:
        worth = (res_val / 10 + 1) / (weight + 0.1)
    
    # Scale worth by total uses for drainables
    if total_uses > 1:
        worth *= (total_uses * 0.8)  # Slight diminishing returns per use
    
    # 30% discount for already opened items
    id_lower = item_id.lower()
    is_opened = ("opened = true" in p_lower or 
                 "open = true" in p_lower or 
                 "open" in id_lower or 
                 "opened" in id_lower)
    
    if is_opened:
        worth *= 0.7
    
    return round(max(0.1, worth), 2)


def calculate_stock_level(weight, category, props):
    """
    Calculate minimum and maximum stock levels based on item properties
    
    Args:
        weight: Item weight
        category: Item category
        props: Properties string
    
    Returns:
        dict: {'min': min_stock, 'max': max_stock}
    """
    # Base multiplier by weight
    if weight <= 0.05:
        bms = 50
    elif weight <= 0.2:
        bms = 25
    elif weight <= 0.5:
        bms = 15
    elif weight <= 1.5:
        bms = 10
    elif weight <= 5.0:
        bms = 5
    else:
        bms = 2
    
    # Category-specific multipliers
    mult = 1.0
    p_lower = props.lower()
    
    if category == "Food" and ("fresh = true" in p_lower or "perishable = true" in p_lower):
        mult *= 0.5  # Perishables sell faster
    
    if category in ["Weapon", "Resource"] and ("ammo" in props.lower() or "nail" in props.lower()):
        mult *= 2.0  # Ammunition is always in demand
    
    max_stock = max(1, int(bms * mult))
    min_stock = int(max_stock * 0.2)
    
    return {"min": min_stock, "max": max_stock}


def analyze_item_stats(item_id, props, category):
    """
    Extract detailed statistics about an item for analysis
    
    Args:
        item_id: Item ID
        props: Properties string
        category: Item category
    
    Returns:
        dict: Comprehensive statistics
    """
    stats = {
        'item_id': item_id,
        'category': category,
        'weight': get_stat('Weight', 0.1, props),
        'capacity': get_stat('Capacity', 0.0, props),
        'weight_reduction': get_stat('WeightReduction', 0.0, props),
        
        # Combat
        'min_damage': get_stat('MinDamage', 0.0, props),
        'max_damage': get_stat('MaxDamage', 0.0, props),
        'max_range': get_stat('MaxRange', 0.0, props),
        'critical_chance': get_stat('CriticalChance', 0.0, props),
        'condition_max': get_stat('ConditionMax', 0.0, props),
        
        # Food
        'hunger_change': get_stat('HungerChange', 0.0, props),
        'thirst_change': get_stat('ThirstChange', 0.0, props),
        'calories': get_stat('Calories', 0.0, props),
        'carbs': get_stat('Carbohydrates', 0.0, props),
        'proteins': get_stat('Proteins', 0.0, props),
        'lipids': get_stat('Lipids', 0.0, props),
        'days_fresh': get_stat('DaysFresh', 0.0, props),
        'days_rotten': get_stat('DaysTotallyRotten', 0.0, props),
        
        # Clothing
        'bite_defense': get_stat('BiteDefense', 0.0, props),
        'scratch_defense': get_stat('ScratchDefense', 0.0, props),
        'bullet_defense': get_stat('BulletDefense', 0.0, props),
        'insulation': get_stat('Insulation', 0.0, props),
        'wind_resistance': get_stat('WindResistance', 0.0, props),
        
        # Utility
        'use_delta': get_stat('UseDelta', 0.0, props),
        'fire_fuel_ratio': get_stat('FireFuelRatio', 0.0, props),
        'metal_value': get_stat('MetalValue', 0.0, props),
        'recipes_count': count_recipes(props),
        
        # Boolean flags
        'is_canned': has_property(props, 'CannedFood'),
        'is_packaged': has_property(props, 'Packaged'),
        'is_sterile': has_property(props, 'Sterile'),
        'is_survival_gear': has_property(props, 'SurvivalGear'),
        'is_high_tier': has_property(props, 'IsHighTier'),
        'two_hand_weapon': has_property(props, 'TwoHandWeapon'),
    }
    
    # Computed fields
    stats['total_uses'] = int(round(1.0 / stats['use_delta'])) if stats['use_delta'] > 0 else 1
    stats['avg_damage'] = (stats['min_damage'] + stats['max_damage']) / 2
    
    return stats


def generate_lua_snippet(item_id, tags, worth, stock):
    """
    Generate Lua snippet for item registration
    
    Args:
        item_id: Item ID
        tags: List of tags
        worth: Base worth value
        stock: Stock range dictionary
    
    Returns:
        str: Lua snippet
    """
    tag_str = ', '.join([f'"{t}"' for t in tags])
    price = max(1, int(round(worth)))
    
    return f'{{ item="Base.{item_id}", tags={{{tag_str}}}, basePrice={price}, stockRange={{min={stock["min"]}, max={stock["max"]}}} }},'
