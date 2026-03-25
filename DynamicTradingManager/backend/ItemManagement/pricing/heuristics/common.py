from __future__ import annotations

import re
from typing import Any, Dict

from ...commons.vanilla_loader import count_learned_recipes, get_stat
from ..tag_utils import category_parts, infer_category


METAL_FAMILY_TOKENS = {
    "gold": ("gold",),
    "silver": ("silver",),
    "copper": ("copper",),
    "brass": ("brass",),
    "bronze": ("bronze",),
    "steel": ("steel",),
    "iron": ("iron",),
    "aluminum": ("aluminum", "aluminium"),
    "lead": ("lead",),
    "tin": ("tin",),
}

METAL_FORM_TOKENS = [
    ("mold", ("mold", "cast")),
    ("ore", ("ore",)),
    ("scrap", ("scrap",)),
    ("coin", ("coin",)),
    ("sheet", ("sheet",)),
    ("ingot", ("ingot",)),
    ("bloom", ("bloom",)),
    ("block", ("block",)),
    ("chunk", ("chunk",)),
    ("piece", ("piece",)),
    ("rod", ("rod",)),
    ("band", ("band",)),
    ("slug", ("slug",)),
    ("bar", ("bar",)),
    ("fragment", ("fragment",)),
]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_unit_stat(value: float) -> float:
    value = float(value or 0.0)
    if abs(value) >= 1.0:
        return value / 100.0
    return value


def make_component(label: str, value: float, detail: str | None = None) -> Dict[str, Any]:
    component = {
        "label": label,
        "value": round(float(value), 3),
    }
    if detail:
        component["detail"] = detail
    return component


def _item_tokens(item_id: str) -> list[str]:
    normalized = re.sub(r"([a-z])([A-Z])", r"\1 \2", item_id or "")
    normalized = normalized.replace("_", " ")
    return [token.lower() for token in re.findall(r"[A-Za-z]+", normalized)]


def _detect_metal_family(item_id: str, all_tags: list[str]) -> str:
    for tag in all_tags or []:
        if isinstance(tag, str) and tag.startswith("Resource.Material.MetalFamily."):
            return tag.rsplit(".", 1)[-1].lower()

    item_tokens = _item_tokens(item_id)
    for family, tokens in METAL_FAMILY_TOKENS.items():
        if any(token in item_tokens for token in tokens):
            return family
    return "generic"


def _detect_metal_form(item_id: str, all_tags: list[str]) -> str:
    for tag in all_tags or []:
        if isinstance(tag, str) and tag.startswith("Resource.Material.MetalForm."):
            return tag.rsplit(".", 1)[-1].lower()

    item_tokens = _item_tokens(item_id)
    for form, tokens in METAL_FORM_TOKENS:
        if any(token in item_tokens for token in tokens):
            return form
    return "raw"


def build_item_context(item_id: str, props: str, tags_dict: Dict[str, Any]) -> Dict[str, Any]:
    props = props or ""
    item_lower = (item_id or "").lower()
    props_lower = props.lower()
    primary = str(tags_dict.get("primary") or "Misc.General")
    primary_lower = primary.lower()
    category, subcategories = category_parts(primary)
    weight = get_stat(props, "Weight", 0.1)
    capacity_match = re.search(r"\bCapacity\s*=\s*(-?\d+\.?\d*)", props, re.IGNORECASE)
    capacity = float(capacity_match.group(1)) if capacity_match else 0.0
    vehicle_capacity_match = re.search(r"\bMaxCapacity\s*=\s*(-?\d+\.?\d*)", props, re.IGNORECASE)
    vehicle_max_capacity = float(vehicle_capacity_match.group(1)) if vehicle_capacity_match else 0.0
    weight_reduction = get_stat(props, "WeightReduction", 0.0)
    metal_value = get_stat(props, "MetalValue", 0.0)
    fuel_value = get_stat(props, "FuelValue", 0.0)
    fire_fuel_ratio = get_stat(props, "FireFuelRatio", 0.0)
    use_delta = get_stat(props, "UseDelta", 0.0)

    stress_change = normalize_unit_stat(get_stat(props, "StressChange", 0.0)) * 100.0
    unhappy_change = normalize_unit_stat(get_stat(props, "UnhappyChange", 0.0)) * 100.0
    boredom_change = normalize_unit_stat(get_stat(props, "BoredomChange", 0.0)) * 100.0
    run_mod = get_stat(props, "RunSpeedModifier", 1.0)
    combat_mod = get_stat(props, "CombatSpeedModifier", 1.0)
    display_category_match = re.search(r"DisplayCategory\s*=\s*([^,\n\s;]+)", props, re.IGNORECASE)
    display_category = (display_category_match.group(1).lower() if display_category_match else "")
    tags_match = re.search(r"Tags\s*=\s*([^\n]+)", props, re.IGNORECASE)
    raw_tags = (tags_match.group(1).lower() if tags_match else "")
    fluid_capacity = capacity
    if fluid_capacity <= 0:
        fluid_match = re.search(r"component\s+FluidContainer\s*\{.*?Capacity\s*=\s*(-?\d+\.?\d*)", props, re.IGNORECASE | re.DOTALL)
        fluid_capacity = float(fluid_match.group(1)) if fluid_match else 0.0
    ammo_like = (
        ".ammo" in primary.lower()
        or display_category == "ammo"
        or any(token in item_lower for token in ("bullet", "shell", "cartridge", "ammo", "clip"))
    )
    firearm_like = (
        not ammo_like
        and (
            "firearm" in primary.lower()
            or any(token in item_lower for token in ("pistol", "shotgun", "rifle", "revolver", "carbine"))
        )
    )
    has_survival_gear = "survivalgear = true" in props_lower
    all_tags = [tag for tag in (tags_dict.get("all_tags") or []) if isinstance(tag, str)]
    skill_level = get_stat(props, "LvlSkillTrained", 0.0)
    if skill_level <= 0:
        level_match = re.search(r"(\d+)$", item_id or "")
        if level_match:
            skill_level = float(level_match.group(1))

    is_metal_resource = category == "Resource" and ".metal" in primary_lower
    metal_family = _detect_metal_family(item_id, all_tags) if is_metal_resource else "generic"
    metal_form = _detect_metal_form(item_id, all_tags) if is_metal_resource else "raw"

    return {
        "item_id": item_id,
        "item_lower": item_lower,
        "props": props,
        "props_lower": props_lower,
        "display_category": display_category,
        "raw_tags": raw_tags,
        "tags_dict": tags_dict,
        "all_tags": all_tags,
        "primary_tag": primary,
        "category": infer_category(tags_dict) or category,
        "subcategories": subcategories,
        "weight": weight,
        "capacity": capacity,
        "vehicle_max_capacity": vehicle_max_capacity,
        "fluid_capacity": fluid_capacity,
        "weight_reduction": weight_reduction,
        "metal_value": metal_value,
        "fuel_value": fuel_value,
        "fire_fuel_ratio": fire_fuel_ratio,
        "use_delta": use_delta,
        "total_uses": int(round(1.0 / use_delta)) if use_delta > 0 else 1,
        "recipes": count_learned_recipes(props),
        "skill_level": skill_level,
        "hunger": abs(normalize_unit_stat(get_stat(props, "HungerChange", 0.0))),
        "thirst": abs(normalize_unit_stat(get_stat(props, "ThirstChange", 0.0))),
        "calories": get_stat(props, "Calories", 0.0),
        "days_fresh": get_stat(props, "DaysFresh", 0.0),
        "days_rotten": get_stat(props, "DaysTotallyRotten", 0.0),
        "unhappy": max(0.0, unhappy_change),
        "boredom": max(0.0, boredom_change),
        "stress": max(0.0, stress_change),
        "stress_relief": abs(min(0.0, stress_change)),
        "unhappy_relief": abs(min(0.0, unhappy_change)),
        "boredom_relief": abs(min(0.0, boredom_change)),
        "min_damage": get_stat(props, "MinDamage", 0.0),
        "max_damage": get_stat(props, "MaxDamage", 0.0),
        "max_range": get_stat(props, "MaxRange", 0.0),
        "max_hit": get_stat(props, "MaxHitcount", 1.0),
        "condition_max": get_stat(props, "ConditionMax", 0.0),
        "reliability": get_stat(props, "ConditionLowerChanceOneIn", 0.0),
        "swing_time": get_stat(props, "MinimumSwingtime", 0.0),
        "bite_defense": get_stat(props, "BiteDefense", 0.0),
        "scratch_defense": get_stat(props, "ScratchDefense", 0.0),
        "bullet_defense": get_stat(props, "BulletDefense", 0.0) or get_stat(props, "BluntDefense", 0.0),
        "insulation": get_stat(props, "Insulation", 0.0),
        "wind_resistance": get_stat(props, "WindResistance", 0.0),
        "run_modifier": run_mod,
        "combat_modifier": combat_mod,
        "is_opened": (
            any(flag in props_lower for flag in ("opened = true", "open = true"))
            or any(token in item_lower for token in ("_open", "_opened"))
            or item_lower.endswith("open")
            or item_lower.endswith("opened")
        ),
        "is_drainable": "itemtype = base:drainable" in props_lower or get_stat(props, "UseDelta", 0.0) > 0,
        "is_cant_eat": bool(re.search(r"\bCantEat\s*=\s*true", props, re.IGNORECASE)),
        "is_canned": "cannedfood = true" in props_lower or ".canned" in primary_lower,
        "is_packaged": "packaged = true" in props_lower,
        "is_sterile": bool(re.search(r"\bSterile\s*=\s*true", props, re.IGNORECASE)),
        "is_debug_item": any(token in item_lower for token in ("debug", "testdebug")),
        "is_carton": "carton" in item_lower or "opencarton" in props_lower,
        "is_box_bundle": "box" in item_lower or "openbox" in props_lower,
        "is_hygiene_item": "tissue" in item_lower,
        "is_firestarter_misc": (
            "base:startfire" in raw_tags
            or any(token in item_lower for token in ("match", "firestarter", "lighter", "candle"))
        ),
        "is_water_purifier_misc": "base:purifywater" in raw_tags or "purificationtablet" in item_lower,
        "is_filter_misc": "respiratorfilter" in raw_tags or "gasmaskfilter" in item_lower or "filter" in item_lower,
        "is_hygiene_misc": any(token in item_lower for token in ("soap", "towel", "napkin", "razor", "repellent", "spraypaint")),
        "is_cosmetic_misc": display_category == "appearance" or any(token in item_lower for token in ("lipstick", "makeup", "hairgel", "hairspray")),
        "is_morale_misc": (
            "base:ismemento" in raw_tags
            or any(token in item_lower for token in ("toy", "spiffo", "doll", "board", "camera", "basketball", "bell"))
        ),
        "is_crafting_misc": (
            display_category in ("tool", "cooking", "camping")
            or has_survival_gear
            or any(token in item_lower for token in ("handdrill", "bellows", "tongs", "jar", "yeast", "mix", "needle", "punch", "file"))
        ),
        "is_jar_box_misc": "boxofjars" in item_lower or "jarbox" in item_lower,
        "is_key_misc": "key" in item_lower,
        "is_camera_misc": "camera" in item_lower,
        "is_metal_trinket_misc": display_category == "junk" and get_stat(props, "MetalValue", 0.0) > 0 and not any(token in item_lower for token in ("tongs", "bellows", "handdrill", "camera")),
        "is_drink_item": ".drink." in primary_lower or display_category == "food" and any(token in item_lower for token in ("water", "cola", "pop", "beer", "wine", "vodka", "whiskey", "juice", "coffee", "tea")),
        "is_alcohol_drink": ".drink.alcohol" in primary_lower or any(token in item_lower for token in ("beer", "wine", "vodka", "whiskey", "rum", "gin", "brandy", "tequila", "cider", "port")),
        "is_prepared_food_required": "tooltip_item_mustaddrecipe" in props_lower or ("oncooked" in props_lower and "canteat = true" in props_lower),
        "is_dried_staple": "base:driedfood" in props_lower or any(token in item_lower for token in ("pasta", "macaroni", "bean", "lentil", "oat", "rice")),
        "is_preserved_ingredient": "base:preservedfood" in props_lower,
        "is_generator": "generator" in item_lower,
        "is_lantern": "lantern" in item_lower,
        "is_portable": any(token in item_lower for token in ("portable", "walkie", "radio", "torch", "flashlight", "lantern")),
        "is_radio": any(token in item_lower for token in ("walkie", "radio", "hamradio")),
        "is_light_source": any(token in item_lower for token in ("torch", "flashlight", "lantern", "candle")),
        "is_firearm": firearm_like,
        "is_ammo": ammo_like and not firearm_like,
        "is_explosive": any(token in item_lower for token in ("grenade", "explosive", "bomb", "molotov", "aerosol")),
        "is_two_handed": bool(re.search(r"\bTwoHandWeapon\s*=\s*true", props, re.IGNORECASE)),
        "is_skill_book": "skillbook" in item_lower or "skillbook" in primary_lower,
        "is_magazine": "magazine" in item_lower or "media" in primary_lower,
        "is_map": bool(re.search(r"\bMap\s*=", props, re.IGNORECASE)) or "map" in item_lower,
        "is_surgical": any(token in item_lower for token in ("scalpel", "suture", "tweezers", "forceps")),
        "is_bandaid": "bandaid" in item_lower,
        "is_bandage": any(token in item_lower for token in ("bandage", "bandaid", "cotton", "gauze")),
        "is_disinfectant": any(token in item_lower for token in ("disinfect", "alcohol")),
        "is_pills": "pills" in item_lower,
        "is_beta": "beta" in item_lower,
        "is_sleep_aid": any(token in item_lower for token in ("sleep", "sleepingtablet")),
        "is_antidepressant": any(token in item_lower for token in ("antidep", "depress")),
        "is_vitamin": "vitamin" in item_lower,
        "is_splint": "splint" in item_lower,
        "is_tobacco": any(token in item_lower for token in ("tobacco", "cigarette", "cigar", "smoke")),
        "is_powered_tool": any(token in item_lower for token in ("electric", "battery", "drill", "saw", "generator")),
        "is_medical_tool": "medical" in primary_lower or any(token in item_lower for token in ("scalpel", "tweezers", "forceps", "suture")),
        "is_farming_tool": "farming" in primary_lower or any(token in item_lower for token in ("shovel", "hoe", "rake", "trowel", "watering")),
        "is_fishing_tool": "fishing" in primary_lower or any(token in item_lower for token in ("rod", "hook", "net", "tackle")),
        "is_crafting_tool": "craft" in primary_lower or any(token in item_lower for token in ("hammer", "wrench", "screwdriver", "saw")),
        "is_tool_like": any(token in item_lower for token in ("hammer", "wrench", "screwdriver", "saw", "shovel", "trowel", "hoe", "rake", "crowbar")),
        "is_pry_tool": any(token in item_lower for token in ("crowbar", "tireiron", "spikepuller")),
        "is_small_battery": item_lower == "battery" or "lighter_battery" in item_lower,
        "is_car_battery": "carbattery" in item_lower,
        "is_propane_tank": "propanetank" in item_lower,
        "is_fuel_container": any(token in item_lower for token in ("gascan", "jerrycan", "fuelcan")),
        "is_spice_food": "spice" in primary_lower,
        "has_survival_gear": has_survival_gear,
        "is_garden_building": category == "Building" and ("garden" in primary_lower or display_category == "gardening"),
        "is_seed_building": category == "Building" and (".seed" in primary_lower or item_lower.endswith("seed") or "bagseed" in item_lower),
        "is_garden_supply_building": category == "Building"
        and (
            "garden" in primary_lower
            or display_category == "gardening"
        )
        and (
            any(token in item_lower for token in ("fertilizer", "compost", "spray", "repellent"))
            or any(tag in raw_tags for tag in ("base:fertilizer", "base:compost"))
        ),
        "is_crop_treatment_building": category == "Building"
        and (
            any(token in item_lower for token in ("fertilizer", "compost", "spray", "repellent"))
            or any(tag in raw_tags for tag in ("base:fertilizer", "base:compost"))
        ),
        "is_farm_bulk_building": category == "Building"
        and (
            any(token in item_lower for token in ("feed", "grass"))
            or "base:farmingloot" in raw_tags
        ),
        "is_survival_building": category == "Building" and "survival" in primary_lower,
        "is_trap_building": category == "Building" and ("trap" in primary_lower or "trap" in item_lower),
        "is_fixture_building": category == "Building" and "fixture" in primary_lower,
        "is_vehicle_building": category == "Building" and "vehicle" in primary_lower,
        "is_moveable_building": category == "Building" and "moveable" in primary_lower,
        "is_packed_building": category == "Building"
        and (
            "_packed" in item_lower
            or "packed" in item_lower
            or "tentkit" in item_lower
        ),
        "is_building_appliance": category == "Building"
        and (
            ".appliance" in primary_lower
            or any(token in item_lower for token in ("fridge", "freezer", "oven", "stove", "microwave", "toaster", "washer", "dryer", "dishwasher", "vending", "fryer", "airconditioner", "coffeemaker", "espresso", "bbq"))
        ),
        "is_building_plumbing": category == "Building"
        and (
            ".plumbing" in primary_lower
            or any(token in item_lower for token in ("sink", "toilet", "urinal", "shower", "waterdispenser", "bathtub"))
        ),
        "is_building_storage": category == "Building"
        and (
            ".storage" in primary_lower
            or capacity > 0
            or any(token in item_lower for token in ("cabinet", "locker", "shelf", "shelves", "crate", "drawers", "mailbox", "trunk", "glovebox"))
        ),
        "is_building_counter": category == "Building" and (".counter" in primary_lower or "counter" in item_lower),
        "is_building_table": category == "Building" and (".table" in primary_lower or "table" in item_lower),
        "is_building_chair": category == "Building" and (".chair" in primary_lower or "chair" in item_lower or "stool" in item_lower),
        "is_building_bench": category == "Building" and (".bench" in primary_lower or "bench" in item_lower),
        "is_building_bed": category == "Building"
        and (
            ".bed" in primary_lower
            or any(token in item_lower for token in ("mattress", "bed", "futon", "cot"))
        ),
        "is_survival_shelter_building": category == "Building"
        and (
            display_category == "camping"
            or any(token in item_lower for token in ("tent", "sleepingbag", "bedroll"))
        )
        and "trap" not in item_lower,
        "is_building_communication": category == "Building"
        and (
            ".communication" in primary_lower
            or any(token in item_lower for token in ("phone", "microphone"))
        ),
        "is_building_hardware": category == "Building"
        and (
            ".hardware" in primary_lower
            or any(token in item_lower for token in ("padlock", "lock", "pipe"))
        ),
        "is_building_utility_station": category == "Building"
        and (
            ".utility" in primary_lower
            or any(token in item_lower for token in ("concretemixer", "benchgrinder", "forge", "brazier", "keyduplicator", "turnstile", "construction", "hydrant"))
        ),
        "is_building_lighting": category == "Building"
        and any(token in item_lower for token in ("lamp", "light", "neon", "signoutofgas")),
        "is_building_decor": category == "Building"
        and (
            ".decor" in primary_lower
            or any(token in item_lower for token in ("painting", "poster", "curtain", "mirror", "flag", "clock", "skull", "trophy", "gnome", "flamingo", "flowers", "birdbath", "doily"))
        ),
        "is_vehicle_container_building": category == "Building"
        and "vehicle" in primary_lower
        and (
            any(token in item_lower for token in ("trunk", "glovebox"))
        ),
        "is_vehicle_maintenance_building": category == "Building"
        and "vehicle" in primary_lower
        and any(token in item_lower for token in ("engineparts", "brake", "suspension", "muffler", "tire", "jack", "lugwrench", "tirepump")),
        "is_vehicle_body_building": category == "Building"
        and "vehicle" in primary_lower
        and any(token in item_lower for token in ("door", "window", "windshield", "trunk", "hood", "seat")),
        "is_replaceable_bag_supply": "replaceondeplete = base.emptysandbag" in props_lower,
        "is_material_resource": category == "Resource" and display_category == "material",
        "is_fuel_resource": category == "Resource" and (".fuel" in primary_lower or "base:isfirefuel" in raw_tags),
        "is_gas_fuel_resource": category == "Resource"
        and (".fuel.gas" in primary_lower or "propanetank" in item_lower or "propane" in item_lower),
        "is_solid_fuel_resource": category == "Resource"
        and (".fuel.solid" in primary_lower or "base:isfirefuel" in raw_tags or "charcoal" in item_lower or item_lower == "log"),
        "is_hardware_resource": category == "Resource" and ".hardware" in primary_lower,
        "is_textile_resource": category == "Resource"
        and (
            ".textile" in primary_lower
            or any(tag in raw_tags for tag in ("base:rope", "base:twine", "base:binding", "base:fishingline"))
        ),
        "is_binding_resource": category == "Resource"
        and (
            any(tag in raw_tags for tag in ("base:binding", "base:rope", "base:twine"))
            or any(token in item_lower for token in ("rope", "twine", "string"))
        ),
        "is_sheet_material_resource": category == "Resource"
        and (
            "sheetmetal" in item_lower
            or "smallsheetmetal" in raw_tags
            or "smeltablesteel" in raw_tags
        ),
        "is_metal_resource": is_metal_resource,
        "metal_family": metal_family,
        "metal_form": metal_form,
        "is_noble_metal_resource": is_metal_resource and metal_family in ("gold", "silver"),
        "is_metal_ingot_resource": is_metal_resource and metal_form == "ingot",
        "is_metal_coin_resource": is_metal_resource and metal_form == "coin",
        "is_metal_scrap_resource": is_metal_resource and metal_form == "scrap",
        "is_metal_ore_resource": is_metal_resource and metal_form == "ore",
        "is_masonry_resource": category == "Resource"
        and (
            ".mineral" in primary_lower
            or any(token in item_lower for token in ("concrete", "plaster", "gravel", "sandbag", "mortar", "cement", "brick", "stone"))
        ),
        "is_powder_resource": category == "Resource" and any(token in item_lower for token in ("powder", "cement", "plaster", "concrete")),
        "is_stack_resource": category == "Resource"
        and (
            any(token in item_lower for token in ("stack", "bundle"))
            or "unstack_items" in props_lower
        ),
        "is_bag_fill_resource": category == "Resource"
        and (
            "replaceondeplete = base.emptysandbag" in props_lower
            or any(token in item_lower for token in ("sandbag", "gravelbag"))
        ),
        "is_smeltable_resource": category == "Resource" and "smeltable" in raw_tags,
        "is_fire_tinder_resource": category == "Resource" and "base:isfiretinder" in raw_tags,
        "is_log_resource": category == "Resource" and ("base:log" in raw_tags or item_lower == "log"),
        "is_bulk_resource_bundle": category == "Resource" and ("openbox" in props_lower or "opencarton" in props_lower or "unstack_items" in props_lower),
    }
