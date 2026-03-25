from __future__ import annotations

from .common import clamp, make_component


def evaluate_building(context, config):
    role_bonus = 0.0
    role_components: list[dict] = []

    def add_role(label: str, amount: float, enabled: bool) -> None:
        nonlocal role_bonus
        if enabled and amount:
            role_bonus += amount
            role_components.append(make_component(label, amount))

    add_role("Garden base", config["garden_bonus"], context["is_garden_building"])
    add_role("Seed value", config["seed_bonus"], context["is_seed_building"])
    add_role("Garden supplies", config["garden_supply_bonus"], context["is_garden_supply_building"])
    add_role("Crop treatment", config["crop_treatment_bonus"], context["is_crop_treatment_building"])
    add_role("Farm bulk", config["farm_bulk_bonus"], context["is_farm_bulk_building"])

    add_role("Survival base", config["survival_bonus"], context["is_survival_building"])
    add_role("Shelter value", config["shelter_bonus"], context["is_survival_shelter_building"])
    add_role("Trap value", config["trap_bonus"], context["is_trap_building"])
    add_role("Packed utility", config["packed_bonus"], context["is_packed_building"])

    add_role("Appliance utility", config["appliance_bonus"], context["is_building_appliance"])
    add_role("Plumbing utility", config["plumbing_bonus"], context["is_building_plumbing"])
    add_role("Storage utility", config["storage_bonus"], context["is_building_storage"])
    add_role("Counter utility", config["counter_bonus"], context["is_building_counter"])
    add_role("Table utility", config["table_bonus"], context["is_building_table"])
    add_role("Chair utility", config["chair_bonus"], context["is_building_chair"])
    add_role("Bench utility", config["bench_bonus"], context["is_building_bench"])
    add_role("Bed comfort", config["bed_bonus"], context["is_building_bed"])
    add_role("Lighting utility", config["lighting_bonus"], context["is_building_lighting"])
    add_role("Communication utility", config["communication_bonus"], context["is_building_communication"])
    add_role("Hardware utility", config["hardware_bonus"], context["is_building_hardware"])
    add_role("Utility station", config["utility_station_bonus"], context["is_building_utility_station"])

    add_role("Vehicle container", config["vehicle_container_bonus"], context["is_vehicle_container_building"])
    add_role("Vehicle maintenance", config["vehicle_maintenance_bonus"], context["is_vehicle_maintenance_building"])
    add_role("Vehicle body part", config["vehicle_body_bonus"], context["is_vehicle_body_building"])
    add_role(
        "Vehicle salvage",
        config["vehicle_bonus"],
        context["is_vehicle_building"]
        and not (
            context["is_vehicle_container_building"]
            or context["is_vehicle_maintenance_building"]
            or context["is_vehicle_body_building"]
        ),
    )

    add_role(
        "Fixture utility",
        config["fixture_bonus"],
        context["is_fixture_building"]
        and not (
            context["is_building_appliance"]
            or context["is_building_plumbing"]
            or context["is_building_storage"]
            or context["is_building_communication"]
            or context["is_building_hardware"]
            or context["is_building_utility_station"]
        ),
    )
    add_role(
        "Moveable utility",
        config["moveable_bonus"],
        context["is_moveable_building"]
        and not (
            context["is_building_appliance"]
            or context["is_building_plumbing"]
            or context["is_building_storage"]
            or context["is_building_decor"]
            or context["is_building_utility_station"]
        ),
    )

    capacity_score = 0.0
    vehicle_capacity_basis = max(context["capacity"], context.get("vehicle_max_capacity", 0.0))
    if context["is_vehicle_container_building"]:
        capacity_score = vehicle_capacity_basis * config["vehicle_capacity_weight"]
    elif context["is_building_storage"]:
        capacity_score = context["capacity"] * config["storage_capacity_weight"]

    wr_score = context["weight_reduction"] * config["weight_reduction_weight"]
    salvage_score = min(context["metal_value"], config["salvage_cap"]) * config["salvage_weight"]
    use_score = 0.0
    if context["use_delta"] > 0:
        use_score = min(context["total_uses"], config["utility_use_cap"]) * config["utility_use_weight"]

    decor_bonus = 0.0
    if context["is_building_decor"]:
        decor_bonus = config["decor_bonus"]

    weight_penalty = context["weight"] * config["weight_penalty"]
    raw_score = (
        config["base"]
        + role_bonus
        + capacity_score
        + wr_score
        + salvage_score
        + use_score
        + decor_bonus
        - weight_penalty
    )

    utility_flags = (
        context["is_building_appliance"]
        or context["is_building_plumbing"]
        or context["is_building_storage"]
        or context["is_building_counter"]
        or context["is_building_table"]
        or context["is_building_chair"]
        or context["is_building_bench"]
        or context["is_building_bed"]
        or context["is_building_lighting"]
        or context["is_building_communication"]
        or context["is_building_hardware"]
        or context["is_building_utility_station"]
        or context["is_vehicle_container_building"]
        or context["is_vehicle_maintenance_building"]
        or context["is_vehicle_body_building"]
        or context["is_survival_shelter_building"]
        or context["is_trap_building"]
        or context["is_seed_building"]
        or context["is_garden_supply_building"]
        or context["is_crop_treatment_building"]
        or context["is_farm_bulk_building"]
    )
    if context["is_building_decor"] and not utility_flags:
        raw_score *= config["decor_multiplier"]

    score = clamp(raw_score, config["price_floor"], config["price_ceiling"])
    components = [make_component("Base", config["base"])]
    components.extend(role_components)
    if capacity_score:
        components.append(make_component("Capacity utility", capacity_score))
    if wr_score:
        components.append(make_component("Weight reduction", wr_score))
    if salvage_score:
        components.append(make_component("Salvage value", salvage_score))
    if use_score:
        components.append(make_component("Repeat use bonus", use_score))
    if decor_bonus:
        components.append(make_component("Decor value", decor_bonus))
    if context["is_building_decor"] and not utility_flags and config["decor_multiplier"] != 1.0:
        components.append(make_component("Decor discount", config["decor_multiplier"], "multiplier"))
    if weight_penalty:
        components.append(make_component("Bulk penalty", -weight_penalty))

    return {
        "score": score,
        "components": components,
    }
