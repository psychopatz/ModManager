"""
Config-backed pricing calculation with category heuristics and price breakdowns.
"""
from __future__ import annotations

from typing import Any, Dict

from .config_store import get_pricing_config
from .heuristics import (
    build_item_context,
    evaluate_building,
    evaluate_fallback,
    evaluate_food,
    evaluate_medical,
    evaluate_tool,
    evaluate_weapon,
)
from .heuristics.common import clamp, make_component
from .tag_utils import category_parts, expand_hierarchy, normalize_tags_dict


def _category_config(config: Dict[str, Any], category: str) -> Dict[str, float]:
    categories = config.get("categories", {})
    return categories.get(category, categories.get("Misc", {}))



def _evaluate_fluid(context: Dict[str, Any]) -> Dict[str, Any]:
    primary = context.get('primary_tag', '')
    capacity = max(float(context.get('fluid_capacity') or context.get('capacity') or 0.0), 0.1)
    weight = max(float(context.get('weight') or 0.0), 0.05)

    if 'Fluid.Fuel' in primary:
        per_liter = 18.0
    elif 'Fluid.Water.Tainted' in primary:
        per_liter = 3.0
    elif 'Fluid.Water' in primary:
        per_liter = 6.0
    elif 'Fluid.Medical' in primary:
        per_liter = 20.0
    elif 'Fluid.Cleaning' in primary:
        per_liter = 14.0
    elif 'Fluid.Appearance' in primary:
        per_liter = 24.0
    elif 'Fluid.Drink.Alcohol' in primary:
        per_liter = 16.0
    elif 'Fluid.Drink.NonAlcoholic' in primary:
        per_liter = 10.0
    else:
        per_liter = 8.0

    bulk_penalty = weight * 2.0
    score = max(1.0, (capacity * per_liter) - bulk_penalty)
    return {
        'score': score,
        'components': [
            make_component('Fluid volume', capacity * per_liter),
            make_component('Bulk penalty', -bulk_penalty),
        ],
    }


def _apply_shared_multipliers(
    raw_score: float,
    context: Dict[str, Any],
    config: Dict[str, Any],
) -> tuple[float, list[dict[str, Any]], dict[str, Any]]:
    global_cfg = config["global"]
    tags_dict = context["tags_dict"]
    adjustments: list[dict[str, Any]] = []

    price = raw_score * global_cfg.get("base_multiplier", 1.0)
    if global_cfg.get("base_multiplier", 1.0) != 1.0:
        adjustments.append(make_component("Global multiplier", global_cfg["base_multiplier"], "multiplier"))

    rarity = tags_dict.get("rarity") or "Common"
    rarity_mult = config["rarity_multipliers"].get(rarity, 1.0)
    price *= rarity_mult
    if rarity_mult != 1.0:
        adjustments.append(make_component(f"Rarity: {rarity}", rarity_mult, "multiplier"))

    quality = tags_dict.get("quality")
    if quality:
        quality_mult = config["quality_multipliers"].get(quality, 1.0)
        price *= quality_mult
        if quality_mult != 1.0:
            adjustments.append(make_component(f"Quality: {quality}", quality_mult, "multiplier"))

    origin = tags_dict.get("origin")
    if origin:
        origin_mult = config["origin_multipliers"].get(origin, 1.0)
        price *= origin_mult
        if origin_mult != 1.0:
            adjustments.append(make_component(f"Origin: {origin}", origin_mult, "multiplier"))

    for theme in tags_dict.get("theme", []):
        theme_name = theme.split(".", 1)[1] if theme.startswith("Theme.") else theme
        theme_mult = config.get("theme_multipliers", {}).get(theme_name, 1.0)
        price *= theme_mult
        if theme_mult != 1.0:
            adjustments.append(make_component(f"Theme: {theme_name}", theme_mult, "multiplier"))

    if (
        context["total_uses"] > 1
        and not context.get("is_hygiene_item")
        and (not context.get("is_drainable") or context.get("category") in ("Food", "Medical"))
    ):
        extra_uses = max(0, context["total_uses"] - 1)
        uses_mult = 1.0 + (extra_uses * global_cfg.get("extra_use_bonus", 0.0))
        uses_mult = min(uses_mult, global_cfg.get("max_use_multiplier", uses_mult))
        price *= uses_mult
        if uses_mult != 1.0:
            adjustments.append(make_component("Usage count", uses_mult, "multiplier"))

    if context["is_opened"]:
        opened_mult = global_cfg.get("opened_penalty", 1.0)
        price *= opened_mult
        if opened_mult != 1.0:
            adjustments.append(make_component("Opened penalty", opened_mult, "multiplier"))

    override = config.get("item_overrides", {}).get(context["item_id"])
    if override is not None:
        adjustments.append(make_component("Item override", override))
        return float(override), adjustments, {
            "pre_global_clamp_price": float(override),
            "global_price_clamped": False,
            "global_price_clamp": None,
            "global_min_price": float(global_cfg.get("min_price", 1.0)),
            "global_max_price": None,
        }

    unclamped_price = float(price)
    min_price = float(global_cfg.get("min_price", 1.0))
    price = max(price, min_price)
    clamp_direction = None
    if price != unclamped_price:
        clamp_direction = "min"

    return price, adjustments, {
        "pre_global_clamp_price": round(unclamped_price, 3),
        "global_price_clamped": price != unclamped_price,
        "global_price_clamp": clamp_direction,
        "global_min_price": min_price,
        "global_max_price": None,
    }


def _apply_tag_base_additions(
    result: Dict[str, Any],
    context: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    additions = config.get("tag_price_additions", {})
    if not additions:
        return result

    all_tags = context["tags_dict"].get("all_tags") or [context["primary_tag"]]
    matched_tags = expand_hierarchy(all_tags)

    total_addition = 0.0
    components = list(result.get("components", []))
    for tag in matched_tags:
        value = additions.get(tag)
        if value:
            total_addition += float(value)
            components.append(make_component(f"Tag base: {tag}", float(value)))

    if not total_addition:
        return result

    updated = dict(result)
    updated["score"] = float(result["score"]) + total_addition
    updated["components"] = components
    return updated


def calculate_price_details(item_id: str, props: str, tags_dict: Any, pricing_config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not props or len((props or "").strip()) < 10:
        return {
            "item_id": item_id,
            "price": 10,
            "category": "Misc",
            "primary_tag": "Misc.General",
            "components": [],
            "adjustments": [],
            "raw_score": 10.0,
        }

    config = pricing_config or get_pricing_config()
    normalized_tags = normalize_tags_dict(tags_dict)
    context = build_item_context(item_id, props, normalized_tags)
    category = context["category"]
    category_cfg = _category_config(config, category)

    effective_category = category
    if (
        category == "Weapon"
        and context.get("is_tool_like")
        and not context.get("is_firearm")
        and not context.get("is_ammo")
        and not context.get("is_explosive")
    ):
        effective_category = "Tool"

    category_cfg = _category_config(config, effective_category)

    if effective_category == "Fluid":
        result = _evaluate_fluid(context)
    elif effective_category == "Food":
        result = evaluate_food(context, category_cfg)
    elif effective_category == "Medical":
        result = evaluate_medical(context, category_cfg)
    elif effective_category == "Weapon":
        result = evaluate_weapon(context, category_cfg)
    elif effective_category == "Tool":
        result = evaluate_tool(context, category_cfg)
    elif effective_category == "Building":
        result = evaluate_building(context, category_cfg)
    else:
        result = evaluate_fallback(context, category_cfg)

    result = _apply_tag_base_additions(result, context, config)

    raw_score = max(float(result["score"]), float(category_cfg.get("price_floor", 1.0)))
    price, adjustments, clamp_meta = _apply_shared_multipliers(raw_score, context, config)

    return {
        "item_id": item_id,
        "price": max(1, int(round(price))),
        "category": effective_category,
        "primary_tag": context["primary_tag"],
        "subcategory_path": context["subcategories"],
        "raw_score": round(raw_score, 3),
        "components": result["components"],
        "adjustments": adjustments,
        "tags_dict": normalized_tags,
        **clamp_meta,
    }


def calculate_price(item_id: str, props: str, tags_dict: Any, pricing_config: Dict[str, Any] | None = None) -> int:
    return int(calculate_price_details(item_id, props, tags_dict, pricing_config)["price"])


def get_category_from_tags(tags_dict):
    normalized = normalize_tags_dict(tags_dict)
    category, subcategories = category_parts(normalized["primary"])
    return [category], subcategories
