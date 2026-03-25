from __future__ import annotations

from .common import clamp, make_component


def _evaluate_container(context, config):
    score = (
        config["base"]
        + context["capacity"] * config["capacity_weight"]
        + context["weight_reduction"] * config["weight_reduction_weight"]
        - context["weight"] * config["weight_penalty"]
    )
    if context["is_debug_item"]:
        score *= config["debug_multiplier"]
    components = [
        make_component("Base", config["base"]),
        make_component("Capacity", context["capacity"] * config["capacity_weight"]),
        make_component("Weight reduction", context["weight_reduction"] * config["weight_reduction_weight"]),
        make_component("Bulk penalty", -(context["weight"] * config["weight_penalty"])),
        make_component("Debug discount", config["debug_multiplier"], "multiplier") if context["is_debug_item"] else None,
    ]
    return {
        "score": clamp(score, config["price_floor"], config["price_ceiling"]),
        "components": [component for component in components if component is not None],
    }


def _evaluate_clothing(context, config):
    defense_score = (
        context["bite_defense"] * 1.3
        + context["scratch_defense"] * 0.8
        + context["bullet_defense"] * 1.4
    ) * config["defense_weight"]
    warmth_score = context["insulation"] * config["warmth_weight"]
    wind_score = context["wind_resistance"] * config["wind_weight"]
    speed_penalty = (
        (1.0 - context["run_modifier"]) * config["speed_penalty_weight"]
        + (1.0 - context["combat_modifier"]) * (config["speed_penalty_weight"] / 2.0)
    )
    weight_penalty = context["weight"] * config["weight_penalty"]
    score = config["base"] + defense_score + warmth_score + wind_score - speed_penalty - weight_penalty
    return {
        "score": clamp(score, config["price_floor"], config["price_ceiling"]),
        "components": [
            make_component("Base", config["base"]),
            make_component("Protection", defense_score),
            make_component("Warmth", warmth_score),
            make_component("Wind resistance", wind_score),
            make_component("Speed penalty", -speed_penalty),
            make_component("Bulk penalty", -weight_penalty),
        ],
    }


def _evaluate_electronics(context, config):
    role_bonus = 0.0
    if context["is_generator"]:
        role_bonus += config["generator_bonus"]
    if context["is_radio"]:
        role_bonus += config["radio_bonus"]
    if context["is_light_source"]:
        role_bonus += config["light_bonus"]
    if context["is_portable"]:
        role_bonus += config["portable_bonus"]
    if context["is_small_battery"]:
        role_bonus += config["battery_bonus"]
    if context["is_car_battery"]:
        role_bonus += config["car_battery_bonus"]

    power_basis = context["fuel_value"] + context["metal_value"]
    if context["is_lantern"]:
        power_basis = min(power_basis, config["lantern_power_cap"])
    elif not context["is_generator"]:
        power_basis = min(power_basis, config["power_value_cap"])
    power_score = power_basis * config["power_bonus"]
    weight_penalty = context["weight"] * config["weight_penalty"]
    score = config["base"] + role_bonus + power_score - weight_penalty
    components = [
        make_component("Base", config["base"]),
        make_component("Role bonus", role_bonus),
        make_component("Power value", power_score),
        make_component("Bulk penalty", -weight_penalty),
    ]
    if context["is_lantern"]:
        components.append(make_component("Lantern power cap", config["lantern_power_cap"], "cap"))
    return {
        "score": clamp(score, config["price_floor"], config["price_ceiling"]),
        "components": [component for component in components if component is not None],
    }


def _evaluate_literature(context, config):
    recipe_score = context["recipes"] * config["recipe_weight"]
    skill_bonus = 0.0
    if context["is_skill_book"]:
        skill_bonus = config["skill_book_bonus"] + (context.get("skill_level", 0.0) * config["skill_level_weight"])
    magazine_bonus = config["magazine_bonus"] if context["is_magazine"] else 0.0
    map_bonus = config["map_bonus"] if context["is_map"] else 0.0
    weight_penalty = context["weight"] * config["weight_penalty"]
    score = config["base"] + recipe_score + skill_bonus + magazine_bonus + map_bonus - weight_penalty
    return {
        "score": clamp(score, config["price_floor"], config["price_ceiling"]),
        "components": [
            make_component("Base", config["base"]),
            make_component("Recipe knowledge", recipe_score),
            make_component("Skill book bonus", skill_bonus),
            make_component("Magazine bonus", magazine_bonus),
            make_component("Map bonus", map_bonus),
            make_component("Bulk penalty", -weight_penalty),
        ],
    }


def _evaluate_resource(context, config):
    metal_score = context["metal_value"] * config["metal_weight"]
    if context["is_carton"]:
        metal_score *= config["carton_metal_multiplier"]
    metal_family_bonus = 0.0
    metal_form_bonus = 0.0
    if context.get("is_metal_resource"):
        metal_family_bonus = config.get(
            f"metal_family_{context.get('metal_family', 'generic')}_bonus",
            config.get("metal_family_generic_bonus", 0.0),
        )
        metal_form_bonus = config.get(
            f"metal_form_{context.get('metal_form', 'raw')}_bonus",
            config.get("metal_form_raw_bonus", 0.0),
        )
    fuel_score = context["fuel_value"] * config["fuel_weight"]
    burn_score = context["fire_fuel_ratio"] * config["fire_fuel_weight"]
    crafting_bonus = config["crafting_bonus"] if context["use_delta"] > 0 else 0.0

    role_bonus = 0.0
    if context["has_survival_gear"]:
        role_bonus += config["survival_bonus"]
    if context["is_gas_fuel_resource"]:
        role_bonus += config["gas_fuel_bonus"]
    elif context["is_solid_fuel_resource"]:
        role_bonus += config["solid_fuel_bonus"]
    if context["is_propane_tank"]:
        role_bonus += config["propane_bonus"]
    if context["is_fuel_container"]:
        role_bonus += config["fuel_container_bonus"]
    if context["is_hardware_resource"] and not context["is_carton"]:
        role_bonus += config["hardware_bonus"]
    if context["is_hardware_resource"] and context["is_box_bundle"]:
        role_bonus += config["hardware_box_bonus"]
    if context["is_hardware_resource"] and context["is_carton"]:
        role_bonus += config["hardware_carton_bonus"]
    if context["is_sheet_material_resource"]:
        role_bonus += config["sheet_material_bonus"]
    if context["is_masonry_resource"]:
        role_bonus += config["masonry_bonus"]
    if context["is_powder_resource"]:
        role_bonus += config["powder_bonus"]
    if context["is_textile_resource"]:
        role_bonus += config["textile_bonus"]
    if context["is_binding_resource"]:
        role_bonus += config["binding_bonus"]
    if context["is_stack_resource"]:
        role_bonus += config["stack_bonus"]
    if context["is_bag_fill_resource"]:
        role_bonus += config["bag_fill_bonus"]
    if context["is_smeltable_resource"]:
        role_bonus += config["smeltable_bonus"]
    if context["is_fire_tinder_resource"]:
        role_bonus += config["fire_tinder_bonus"]
    if context["is_log_resource"]:
        role_bonus += config["log_bonus"]
    if context["use_delta"] > 0 or context["is_replaceable_bag_supply"]:
        role_bonus += config["depleting_supply_bonus"]
    if context["is_bulk_resource_bundle"] and not context["is_hardware_resource"]:
        role_bonus += config["bulk_bundle_bonus"]
    if context.get("is_noble_metal_resource"):
        role_bonus += config.get("noble_metal_bonus", 0.0)
    if context.get("is_metal_ingot_resource"):
        role_bonus += config.get("ingot_role_bonus", 0.0)

    weight_penalty = context["weight"] * config["weight_penalty"]
    score = (
        config["base"]
        + metal_score
        + metal_family_bonus
        + metal_form_bonus
        + fuel_score
        + burn_score
        + crafting_bonus
        + role_bonus
        - weight_penalty
    )
    components = [
        make_component("Base", config["base"]),
        make_component("Metal value", metal_score),
        make_component("Metal family", metal_family_bonus),
        make_component("Metal form", metal_form_bonus),
        make_component("Fuel value", fuel_score),
        make_component("Burn value", burn_score),
        make_component("Crafting bonus", crafting_bonus),
        make_component("Role bonus", role_bonus),
        make_component("Bulk penalty", -weight_penalty),
        make_component("Carton discount", config["carton_metal_multiplier"], "multiplier") if context["is_carton"] else None,
    ]
    return {
        "score": clamp(score, config["price_floor"], config["price_ceiling"]),
        "components": [component for component in components if component is not None],
    }


def _evaluate_building(context, config):
    role_bonus = 0.0
    if context["is_survival_building"]:
        role_bonus += config["survival_bonus"]
    if context["is_trap_building"]:
        role_bonus += config["trap_bonus"]
    if context["is_fixture_building"]:
        role_bonus += config["fixture_bonus"]
    if context["is_vehicle_building"]:
        role_bonus += config["vehicle_bonus"]
    if context["is_moveable_building"]:
        role_bonus += config["moveable_bonus"]
    if context["is_garden_building"]:
        role_bonus += config["garden_bonus"]
    if context["is_garden_supply_building"]:
        role_bonus += config["garden_supply_bonus"]
    if context["is_crop_treatment_building"]:
        role_bonus += config["crop_treatment_bonus"]
    if context["is_farm_bulk_building"]:
        role_bonus += config["farm_bulk_bonus"]
    if context["is_seed_building"]:
        role_bonus += config["seed_bonus"]
    if context["is_packed_building"]:
        role_bonus += config["packed_bonus"]
    if context["has_survival_gear"]:
        role_bonus += config["survival_gear_bonus"]
    if context["is_replaceable_bag_supply"]:
        role_bonus += config["replaceable_bag_bonus"]

    use_utility = 0.0
    if context["use_delta"] > 0:
        use_utility = min(context["total_uses"], config["utility_use_cap"]) * config["utility_use_weight"]

    weight_penalty = context["weight"] * config["weight_penalty"]
    score = config["base"] + role_bonus + use_utility - weight_penalty
    return {
        "score": clamp(score, config["price_floor"], config["price_ceiling"]),
        "components": [
            make_component("Base", config["base"]),
            make_component("Role bonus", role_bonus),
            make_component("Use utility", use_utility),
            make_component("Bulk penalty", -weight_penalty),
        ],
    }


def _evaluate_misc(context, config):
    material_basis = context["metal_value"] + context["fuel_value"] + max(context["capacity"], 0.0)
    if context["is_metal_trinket_misc"]:
        material_basis = min(material_basis, config["trinket_material_cap"])
    else:
        material_basis = min(material_basis, config["material_cap"])
    raw_value = material_basis * config["value_weight"]

    utility_bonus = config["utility_bonus"] if context["use_delta"] > 0 or context["total_uses"] > 1 else 0.0
    if context["is_firestarter_misc"]:
        utility_bonus += config["firestarter_bonus"]
    if context["is_water_purifier_misc"]:
        utility_bonus += config["water_purifier_bonus"]
    if context["is_filter_misc"]:
        utility_bonus += config["filter_bonus"]
    if context["is_hygiene_misc"]:
        utility_bonus += config["hygiene_bonus"]
    if context["is_cosmetic_misc"]:
        utility_bonus += config["cosmetic_bonus"]
    if context["is_morale_misc"]:
        utility_bonus += config["morale_bonus"]
    if context["is_crafting_misc"]:
        utility_bonus += config["crafting_bonus"]
    if context["is_jar_box_misc"]:
        utility_bonus += config["jar_box_bonus"]
    if context["is_key_misc"]:
        utility_bonus += config["key_bonus"]
    if context["is_camera_misc"]:
        utility_bonus += config["camera_bonus"]

    weight_penalty = context["weight"] * config["weight_penalty"]
    score = config["base"] + raw_value + utility_bonus - weight_penalty
    return {
        "score": clamp(score, config["price_floor"], config["price_ceiling"]),
        "components": [
            make_component("Base", config["base"]),
            make_component("Material value", raw_value),
            make_component("Utility bonus", utility_bonus),
            make_component("Bulk penalty", -weight_penalty),
        ],
    }


def evaluate_fallback(context, config):
    category = context["category"]
    if category == "Container":
        return _evaluate_container(context, config)
    if category == "Clothing":
        return _evaluate_clothing(context, config)
    if category == "Electronics":
        return _evaluate_electronics(context, config)
    if category == "Literature":
        return _evaluate_literature(context, config)
    if category == "Resource":
        return _evaluate_resource(context, config)
    if category == "Building":
        return _evaluate_building(context, config)
    return _evaluate_misc(context, config)
