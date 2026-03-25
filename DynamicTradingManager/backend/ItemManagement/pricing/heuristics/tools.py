from __future__ import annotations

from .common import clamp, make_component


def evaluate_tool(context, config):
    subtype_bonus = 0.0
    subtype_label = None

    if context["is_medical_tool"]:
        subtype_bonus = config["medical_bonus"]
        subtype_label = "Medical precision"
    elif context["is_farming_tool"]:
        subtype_bonus = config["farming_bonus"]
        subtype_label = "Farming utility"
    elif context["is_fishing_tool"]:
        subtype_bonus = config["fishing_bonus"]
        subtype_label = "Fishing utility"
    elif context["is_crafting_tool"]:
        subtype_bonus = config["crafting_bonus"]
        subtype_label = "Crafting utility"

    durability_score = context["condition_max"] * config["durability_weight"]
    capacity_score = context["capacity"] * config["capacity_weight"]
    wr_score = context["weight_reduction"] * config["weight_reduction_weight"]
    effective_uses = min(max(0, context["total_uses"] - 1), config["repeat_use_cap"])
    use_bonus = effective_uses * config["multi_use_bonus"]
    powered_bonus = config["powered_bonus"] if context["is_powered_tool"] else 0.0
    pry_bonus = config["pry_bonus"] if context["is_pry_tool"] else 0.0
    salvage_score = min(context["metal_value"], config["salvage_cap"]) * config["salvage_weight"]
    weight_penalty = context["weight"] * config["weight_penalty"]

    score = (
        config["base"]
        + durability_score
        + capacity_score
        + wr_score
        + use_bonus
        + powered_bonus
        + pry_bonus
        + salvage_score
        + subtype_bonus
        - weight_penalty
    )

    components = [
        make_component("Base", config["base"]),
        make_component("Durability", durability_score),
    ]
    if capacity_score:
        components.append(make_component("Capacity", capacity_score))
    if wr_score:
        components.append(make_component("Weight reduction", wr_score))
    if use_bonus:
        components.append(make_component("Repeat use bonus", use_bonus))
    if powered_bonus:
        components.append(make_component("Powered bonus", powered_bonus))
    if pry_bonus:
        components.append(make_component("Pry utility", pry_bonus))
    if salvage_score:
        components.append(make_component("Salvage value", salvage_score))
    if subtype_bonus:
        components.append(make_component(subtype_label or "Tool role", subtype_bonus))
    if weight_penalty:
        components.append(make_component("Bulk penalty", -weight_penalty))

    return {
        "score": clamp(score, config["price_floor"], config["price_ceiling"]),
        "components": components,
    }
