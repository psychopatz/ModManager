from __future__ import annotations

from .common import clamp, make_component


def _soft_cap(value, threshold, overflow_multiplier):
    if value <= threshold:
        return value
    return threshold + ((value - threshold) * overflow_multiplier)


def evaluate_food(context, config):
    shelf_cap = config["max_shelf_life_days"]
    if not context["is_canned"] and not context["is_packaged"] and not context["is_dried_staple"]:
        shelf_cap = min(shelf_cap, config["fresh_unpacked_shelf_cap"])
    shelf_days = min(context["days_fresh"] + context["days_rotten"], shelf_cap)
    mood_penalty = (context["unhappy"] + context["boredom"] + context["stress"]) * (config["mood_penalty_weight"] / 100.0)
    large_food_moderation = False
    hunger_basis = context["hunger"]
    thirst_basis = context["thirst"]
    calorie_basis = context["calories"]
    if (
        context["hunger"] >= config["large_food_hunger_threshold"]
        or context["thirst"] >= config["large_food_thirst_threshold"]
        or context["weight"] >= config["large_food_weight_threshold"]
    ):
        large_food_moderation = True
        hunger_basis = _soft_cap(
            context["hunger"],
            config["large_food_hunger_threshold"],
            config["large_food_hunger_overflow"],
        )
        thirst_basis = _soft_cap(
            context["thirst"],
            config["large_food_thirst_threshold"],
            config["large_food_thirst_overflow"],
        )
        calorie_basis = _soft_cap(
            context["calories"],
            config["large_food_calorie_threshold"],
            config["large_food_calorie_overflow"],
        )

    hunger_score = hunger_basis * config["hunger_weight"]
    thirst_score = thirst_basis * config["thirst_weight"]
    calorie_score = calorie_basis * config["calorie_weight"]
    shelf_score = shelf_days * config["shelf_life_weight"]
    fresh_penalty = 0.0
    if shelf_days > 0 and shelf_days <= 6 and not context["is_canned"] and not context["is_packaged"]:
        fresh_penalty = config["fresh_penalty"]

    prep_multiplier = 1.0
    if context["is_prepared_food_required"]:
        prep_multiplier = config["prepared_food_multiplier"]
    if context["is_cant_eat"] and context["is_dried_staple"]:
        prep_multiplier = config["dry_staple_multiplier"]
    if context["is_cant_eat"] and context["is_preserved_ingredient"]:
        prep_multiplier = config["preserved_ingredient_multiplier"]

    if prep_multiplier == 1.0 and context["is_dried_staple"] and not context["is_drink_item"]:
        prep_multiplier = config["dry_staple_multiplier"]

    if prep_multiplier != 1.0:
        hunger_score *= prep_multiplier
        thirst_score *= prep_multiplier
        calorie_score *= prep_multiplier
        shelf_score *= prep_multiplier

    drink_bonus = 0.0
    if context["is_drink_item"]:
        drink_bonus += config["drink_bonus"]
        drink_bonus += context["fluid_capacity"] * config["fluid_capacity_weight"]
        if context["is_alcohol_drink"]:
            drink_bonus += config["alcohol_bonus"]
        else:
            drink_bonus += config["hydration_bonus"]

    score = (
        config["base"]
        + hunger_score
        + thirst_score
        + calorie_score
        + shelf_score
        + drink_bonus
        + (config["canned_bonus"] if context["is_canned"] else 0.0)
        + (config["packaged_bonus"] if context["is_packaged"] else 0.0)
        - fresh_penalty
        - mood_penalty
        - context["weight"] * config["weight_penalty"]
    )

    if context["is_spice_food"]:
        score = score * config["spice_multiplier"]

    components = [
        make_component("Base", config["base"]),
        make_component("Hunger", hunger_score),
        make_component("Thirst", thirst_score),
        make_component("Calories", calorie_score),
        make_component("Shelf life", shelf_score),
    ]
    if large_food_moderation:
        components.append(make_component("Large portion moderation", 1.0, "soft-cap"))
    if prep_multiplier != 1.0:
        components.append(make_component("Prep requirement", prep_multiplier, "multiplier"))
    if drink_bonus:
        components.append(make_component("Drink utility", drink_bonus))
    if context["is_canned"]:
        components.append(make_component("Preservation bonus", config["canned_bonus"], "Canned"))
    elif context["is_packaged"]:
        components.append(make_component("Preservation bonus", config["packaged_bonus"], "Packaged"))
    if fresh_penalty:
        components.append(make_component("Spoilage risk", -fresh_penalty))
    if mood_penalty:
        components.append(make_component("Mood penalty", -mood_penalty))
    if context["weight"]:
        components.append(make_component("Bulk penalty", -(context["weight"] * config["weight_penalty"])))
    if context["is_spice_food"]:
        components.append(make_component("Spice multiplier", config["spice_multiplier"], "multiplier"))

    return {
        "score": clamp(score, config["price_floor"], config["price_ceiling"]),
        "components": components,
    }
