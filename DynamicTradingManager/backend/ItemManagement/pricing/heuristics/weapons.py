from __future__ import annotations

from .common import clamp, make_component


def evaluate_weapon(context, config):
    if context["is_ammo"]:
        score = (
            config["ammo_base"]
            + max(context["weight"], 0.05) * config["ammo_weight"]
            + max(0, context["total_uses"] - 1) * 0.5
        )
        if context["is_carton"]:
            score *= config["ammo_carton_multiplier"]
        components = [
            make_component("Ammo base", config["ammo_base"]),
            make_component("Carried mass", max(context["weight"], 0.05) * config["ammo_weight"]),
            make_component("Carton discount", config["ammo_carton_multiplier"], "multiplier") if context["is_carton"] else None,
        ]
        return {
            "score": clamp(score, config["price_floor"], config["price_ceiling"]),
            "components": [component for component in components if component is not None],
        }

    avg_damage = (context["min_damage"] + max(context["max_damage"], context["min_damage"])) / 2.0
    damage_score = avg_damage * config["damage_weight"]
    range_score = context["max_range"] * config["range_weight"]
    hit_score = max(context["max_hit"], 1.0) * config["multi_hit_weight"]
    durability_score = context["condition_max"] * config["durability_weight"]
    reliability_score = context["reliability"] * config["reliability_weight"]
    firearm_bonus = config["firearm_bonus"] if context["is_firearm"] else 0.0
    explosive_bonus = config["explosive_bonus"] if context["is_explosive"] else 0.0
    two_handed_bonus = config["two_handed_bonus"] if context["is_two_handed"] else 0.0
    speed_penalty = context["swing_time"] * config["swing_penalty"]
    weight_penalty = context["weight"] * config["weight_penalty"]

    score = (
        config["base"]
        + damage_score
        + range_score
        + hit_score
        + durability_score
        + reliability_score
        + firearm_bonus
        + explosive_bonus
        + two_handed_bonus
        - speed_penalty
        - weight_penalty
    )

    components = [
        make_component("Base", config["base"]),
        make_component("Damage", damage_score),
        make_component("Range", range_score),
        make_component("Hit count", hit_score),
        make_component("Durability", durability_score),
    ]
    if reliability_score:
        components.append(make_component("Reliability", reliability_score))
    if firearm_bonus:
        components.append(make_component("Firearm bonus", firearm_bonus))
    if explosive_bonus:
        components.append(make_component("Explosive bonus", explosive_bonus))
    if two_handed_bonus:
        components.append(make_component("Two-handed bonus", two_handed_bonus))
    if speed_penalty:
        components.append(make_component("Swing penalty", -speed_penalty))
    if weight_penalty:
        components.append(make_component("Bulk penalty", -weight_penalty))

    return {
        "score": clamp(score, config["price_floor"], config["price_ceiling"]),
        "components": components,
    }
