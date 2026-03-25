import re

def calculate_worth(item_id, props, category, subcat):
    """Calculates a numerical multiplier based on item stats."""
    p_lower = props.lower()
    
    def get_stat(key, default=0.0):
        # Case-insensitive search for the key
        m = re.search(fr"{key}\s*=\s*(-?\d+\.?\d*)", props, re.IGNORECASE)
        return float(m.group(1)) if m else default

    weight = get_stat("Weight", 0.1)
    worth = 1.0
    
    cap = get_stat("Capacity", 0.0)
    wr = get_stat("WeightReduction", 0.0)
    res_val = get_stat("MetalValue") + get_stat("FuelValue")
    fuel_ratio = get_stat("FireFuelRatio", 0.0)
    
    # Calculate Total Uses from UseDelta
    use_delta = get_stat("UseDelta", 0.0)
    total_uses = int(round(1.0 / use_delta)) if use_delta > 0 else 1
    
    # Extract LearnedRecipes count
    recipes = len(re.findall(r"LearnedRecipes\s*=\s*([^,\n\s;]+)", props))

    if cap > 0:
        # Boosted base multiplier for containers/storage items
        worth = (cap * (wr / 10 + 1)) / (weight + 0.1) * 2.5
    elif category == "Food":
        hunger = abs(get_stat("HungerChange"))
        thirst = abs(get_stat("ThirstChange"))
        calories = get_stat("Calories") / 100.0
        # Penalties: positive Unhappy/Boredom/Stress are BAD stats in PZ
        penalties = (max(0, get_stat("UnhappyChange")) + max(0, get_stat("BoredomChange")) + max(0, get_stat("StressChange"))) * 2
        
        # Shelf-life factor
        fresh = get_stat("DaysFresh")
        rotten = get_stat("DaysTotallyRotten")
        shelf_life = (fresh + rotten) / 2.0
        
        stability = 0
        if "cannedfood = true" in p_lower: stability += 50
        elif "packaged = true" in p_lower: stability += 10
        
        worth = (hunger + (thirst/2) + calories - penalties + stability + shelf_life) / (weight * 1.5 + 0.1)
    elif "Weapon" in category:
        avg_dmg = (get_stat("MinDamage") + get_stat("MaxDamage")) / 2
        max_range = get_stat("MaxRange", 1.0)
        max_hit = get_stat("MaxHitcount", 1.0)
        condition = get_stat("ConditionMax", 5)
        reliability = get_stat("ConditionLowerChanceOneIn", 5)
        swing_time = get_stat("MinimumSwingtime", 1.0)
        worth = ((avg_dmg * max_range * max_hit) + (condition * reliability / 5)) / (weight * 2 + swing_time * 10 + 0.1)
    elif category in ["Clothing", "ProtectiveGear"]:
        bite = get_stat("BiteDefense")
        scratch = get_stat("ScratchDefense")
        bullet = get_stat("BulletDefense")
        insulation = get_stat("Insulation")
        wind_res = get_stat("WindResistance")
        run_mod = get_stat("RunSpeedModifier", 1.0)
        combat_mod = get_stat("CombatSpeedModifier", 1.0)
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
        worth *= (total_uses * 0.8) # Slight diminishing returns per use
        
    # 30% Discount for already opened items
    id_lower = item_id.lower()
    is_opened = "opened = true" in p_lower or "open = true" in p_lower or "open" in id_lower or "opened" in id_lower
    if is_opened:
        worth *= 0.7
        
    return round(max(0.1, worth), 2)
