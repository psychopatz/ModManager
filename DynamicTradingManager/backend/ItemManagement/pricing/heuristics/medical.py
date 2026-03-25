from __future__ import annotations

from .common import clamp, make_component


def evaluate_medical(context, config):
    family_bonus = 0.0
    bonus_components = []

    if context["is_surgical"]:
        family_bonus += config["surgical_bonus"]
        bonus_components.append(("Surgical", config["surgical_bonus"]))
    if context["is_disinfectant"]:
        family_bonus += config["disinfectant_bonus"]
        bonus_components.append(("Disinfectant", config["disinfectant_bonus"]))
    if context["is_bandage"]:
        bandage_bonus = config["bandaid_bonus"] if context["is_bandaid"] else config["bandage_bonus"]
        family_bonus += bandage_bonus
        bonus_components.append(("Bandage care", bandage_bonus))
    if context["is_beta"]:
        family_bonus += config["beta_blocker_bonus"]
        bonus_components.append(("Beta blockers", config["beta_blocker_bonus"]))
    if context["is_antidepressant"]:
        family_bonus += config["antidepressant_bonus"]
        bonus_components.append(("Antidepressants", config["antidepressant_bonus"]))
    if context["is_sleep_aid"]:
        family_bonus += config["sleep_bonus"]
        bonus_components.append(("Sleep aid", config["sleep_bonus"]))
    if context["is_vitamin"]:
        family_bonus += config["vitamin_bonus"]
        bonus_components.append(("Vitamin support", config["vitamin_bonus"]))
    if context["is_pills"]:
        family_bonus += config["painkiller_bonus"]
        bonus_components.append(("Pill dosage", config["painkiller_bonus"]))
    if context["is_splint"]:
        family_bonus += config["splint_bonus"]
        bonus_components.append(("Fracture support", config["splint_bonus"]))

    dose_cap = config["dose_cap"]
    if context["is_pills"]:
        dose_cap = config["pill_dose_cap"]
    if context["is_tobacco"]:
        dose_cap = config["tobacco_dose_cap"]

    dose_bonus = min(max(0, context["total_uses"] - 1), dose_cap) * config["dose_weight"]
    sterile_bonus = config["sterile_bonus"] if context["is_sterile"] else 0.0
    bundle_bonus = 0.0
    if not context["is_hygiene_item"]:
        if context["is_carton"]:
            bundle_bonus += config["carton_bundle_bonus"]
            bonus_components.append(("Bulk bundle", config["carton_bundle_bonus"]))
        elif context["is_box_bundle"]:
            bundle_bonus += config["box_bundle_bonus"]
            bonus_components.append(("Supply bundle", config["box_bundle_bonus"]))

    tobacco_stress_bonus = 0.0
    if context["is_tobacco"]:
        tobacco_stress_bonus = context["stress_relief"] * config["tobacco_stress_weight"]
        if tobacco_stress_bonus:
            family_bonus += tobacco_stress_bonus
            bonus_components.append(("Stress relief", tobacco_stress_bonus))
        morale_relief_bonus = (
            context["unhappy_relief"] + context["boredom_relief"]
        ) * config["tobacco_morale_weight"]
        if morale_relief_bonus:
            family_bonus += morale_relief_bonus
            bonus_components.append(("Mood relief", morale_relief_bonus))
        if "pack" in context["item_lower"]:
            family_bonus += config["tobacco_pack_bonus"]
            bonus_components.append(("Pack convenience", config["tobacco_pack_bonus"]))
        if context["is_carton"]:
            family_bonus += config["tobacco_carton_bonus"]
            bonus_components.append(("Bulk tobacco", config["tobacco_carton_bonus"]))

    weight_penalty = context["weight"] * config["weight_penalty"]

    score = config["base"] + sterile_bonus + dose_bonus + bundle_bonus + family_bonus - weight_penalty
    if context["is_tobacco"]:
        score = score * config["tobacco_multiplier"]
    if context["is_hygiene_item"]:
        score = score * config["hygiene_multiplier"]

    components = [
        make_component("Base", config["base"]),
        make_component("Dose count", dose_bonus),
    ]
    if sterile_bonus:
        components.append(make_component("Sterility", sterile_bonus))
    for label, value in bonus_components:
        components.append(make_component(label, value))
    if weight_penalty:
        components.append(make_component("Bulk penalty", -weight_penalty))
    if context["is_tobacco"]:
        components.append(make_component("Tobacco multiplier", config["tobacco_multiplier"], "multiplier"))
    if context["is_hygiene_item"]:
        components.append(make_component("Hygiene discount", config["hygiene_multiplier"], "multiplier"))

    return {
        "score": clamp(score, config["price_floor"], config["price_ceiling"]),
        "components": components,
    }
