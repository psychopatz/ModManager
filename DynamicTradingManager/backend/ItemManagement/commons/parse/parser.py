import os
import re
from ..helpers import sanitize_path
from ...pricing.economy import calculate_worth

def get_opening_maps(vanilla_path):
    """Maps UnopenedID -> OpenedID using recipe itemMappers."""
    mapping = {}
    print("[*] Building Opening Map from Recipes...")
    recipe_dir = os.path.join(vanilla_path, "generated/recipes/")
    if not os.path.exists(recipe_dir):
        recipe_dir = os.path.join(os.path.dirname(vanilla_path), "generated/recipes/")
    
    if not os.path.exists(recipe_dir): return mapping
    
    for file in sorted(os.listdir(recipe_dir)):
        if not file.endswith(".txt"): continue
        with open(os.path.join(recipe_dir, file), "r", errors="ignore") as f:
            content = f.read()
            mappers = re.findall(r"itemMapper\s+\w+\s*\{([^}]*)\}", content, re.DOTALL)
            for mapper_content in mappers:
                pairs = re.findall(r"(?:Base\.)?(\w+)\s*=\s*(?:Base\.)?(\w+)", mapper_content)
                for opened, unopened in pairs:
                    mapping[unopened] = opened
    return mapping

def get_vanilla_data(vanilla_path):
    item_data, fluid_data = {}, {}
    opening_map = get_opening_maps(vanilla_path)
    
    print(f"[*] Scanning Vanilla Scripts: {vanilla_path}")
    for root, dirs, files in os.walk(vanilla_path):
        for file in sorted(files):
            if not file.endswith(".txt"): continue
            file_rel = os.path.relpath(os.path.join(root, file), vanilla_path)
            with open(os.path.join(root, file), "r", errors="ignore") as f:
                content = f.read()
                
                # Items
                item_blocks = re.findall(r"item\s+([a-zA-Z_]\w*)\s*\{([^}]*)\}", content, re.DOTALL)
                for item_id, props in item_blocks:
                    cat_match = re.search(r"DisplayCategory\s*=\s*([^,\n\s;]+)", props)
                    eat_match = re.search(r"EatType\s*=\s*([^,\n\s;]+)", props)
                    tag_match = re.search(r"Tags\s*=\s*([^,\n\s;]+)", props)
                    
                    raw_tags = tag_match.group(1).strip() if tag_match else "None"
                    raw_eat = eat_match.group(1).strip() if eat_match else "None"
                    category = sanitize_path(cat_match.group(1).strip() if cat_match else "Uncategorized")
                    
                    subcat = "General"
                    if eat_match: subcat = sanitize_path(raw_eat)
                    elif tag_match:
                        first_tag = raw_tags.split(';')[0].split(',')[0].strip()
                        subcat = sanitize_path(first_tag)
                    
                    item_data[item_id] = {
                        "origin": file_rel, "category": category, "subcat": subcat,
                        "tags": raw_tags, "eat_type": raw_eat, "props": props,
                        "opened_variant": opening_map.get(item_id)
                    }
                
                # Fluids
                fluid_blocks = re.findall(r"fluid\s+([a-zA-Z_]\w*)\s*\{([^}]*)\}", content, re.DOTALL)
                for fluid_id, props in fluid_blocks:
                    fluid_data[fluid_id] = {
                        "origin": file_rel, "category": "Fluids", "subcat": "General",
                        "tags": "N/A", "eat_type": "N/A", "props": props, "worth": 1.0
                    }
    
    # Process item stats and worth
    for item_id, data in item_data.items():
        oprops = data["props"]
        inherited = ""
        oid = data.get("opened_variant")
        if oid and oid in item_data: inherited = item_data[oid]["props"]
        combined_props = oprops + "\n" + inherited
        
        def gsl(key, default=0.0, p=combined_props):
            m = re.search(fr"{key}\s*=\s*(-?\d+\.?\d*)", p, re.IGNORECASE)
            return float(m.group(1)) if m else default

        data["worth"] = calculate_worth(item_id, combined_props, data["category"], data["subcat"])
        data["weight"] = gsl("Weight", 0.1)
        data["capacity"] = gsl("Capacity", 0.0)
        data["weight_reduction"] = gsl("WeightReduction", 0.0)
        use_delta = gsl("UseDelta", 0.0)
        data["total_uses"] = int(round(1.0 / use_delta)) if use_delta > 0 else 1
        data["fire_fuel"] = gsl("FireFuelRatio", 0.0)
        data["unhappy"] = gsl("UnhappyChange", 0.0)
        data["recipes"] = len(re.findall(r"LearnedRecipes\s*=\s*([^,\n\s;]+)", combined_props))
        data["fresh"] = gsl("DaysFresh", 0.0)
        data["rotten"] = gsl("DaysTotallyRotten", 0.0)
        data["hunger"] = abs(gsl("HungerChange", 0.0))
        data["insulation"] = gsl("Insulation", 0.0)
        data["wind_res"] = gsl("WindResistance", 0.0)
        data["bite_def"] = gsl("BiteDefense", 0.0)
        data["scratch_def"] = gsl("ScratchDefense", 0.0)
        data["bullet_def"] = gsl("BulletDefense", 0.0)
        data["condition_max"] = gsl("ConditionMax", 0.0)
                    
    return item_data, fluid_data

def get_mod_data(mod_path):
    mod_data, mod_duplicates = {}, {}
    print(f"[*] Scanning Mod Registries: {mod_path}")
    if not os.path.exists(mod_path): return mod_data, mod_duplicates
    
    for root, dirs, files in os.walk(mod_path):
        for file in sorted(files):
            if not file.endswith(".lua"): continue
            file_rel = os.path.relpath(os.path.join(root, file), mod_path)
            with open(os.path.join(root, file), "r", errors="ignore") as f:
                content = f.read()
                found = re.findall(r'(?:item\s*=\s*|\[)"Base\.(\w+)"', content)
                for m in found:
                    if m in mod_data:
                        if m not in mod_duplicates:
                            mod_duplicates[m] = [mod_data[m]["origin"]]
                        mod_duplicates[m].append(file_rel)
                    mod_data[m] = {"origin": file_rel}
    return mod_data, mod_duplicates
