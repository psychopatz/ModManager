"""
Stock range calculation logic
Determines min/max stock levels using weight, tags, and item roles.
"""
from __future__ import annotations

import math
from typing import Any, Dict

from .config_store import get_pricing_config
from .heuristics.common import build_item_context
from .tag_utils import normalize_tags_dict


def calculate_base_max_stock(weight: float, global_cfg: Dict[str, float] | None = None) -> int:
    """
    Determine the base max stock from weight.
    The thresholds are configurable through the pricing config's global block.
    """
    cfg = global_cfg or {}
    if weight <= 0.05:
        return int(cfg.get("stock_ultralight_max", 50))
    if weight <= 0.2:
        return int(cfg.get("stock_light_max", 25))
    if weight <= 0.5:
        return int(cfg.get("stock_small_max", 15))
    if weight <= 1.5:
        return int(cfg.get("stock_medium_max", 10))
    if weight <= 5.0:
        return int(cfg.get("stock_heavy_max", 5))
    return int(cfg.get("stock_massive_max", 2))


def apply_category_multiplier(base_max: int, tags_dict: Dict[str, Any], subcategories: list[str] | None = None) -> int:
    """
    Legacy helper retained for compatibility.
    New code paths should prefer calculate_stock_range().
    """
    primary = str(tags_dict.get("primary", "") or "")
    rarity = str(tags_dict.get("rarity", "Common") or "Common")
    quality = str(tags_dict.get("quality", "") or "")

    if "Perishable" in primary or "Fresh" in primary:
        return max(1, math.floor(base_max * 0.5))
    if any(token in primary for token in ("Ammo", "Material", "Currency")):
        return max(1, math.floor(base_max * 2.0))
    if rarity in ("Rare", "Legendary", "UltraRare") or quality == "Luxury":
        return max(1, math.floor(base_max * 0.4))
    return max(1, int(base_max))


def calculate_min_stock(max_stock: int, tags_dict: Dict[str, Any], subcategories: list[str] | None = None) -> int:
    """
    Legacy helper retained for compatibility.
    New code paths should prefer calculate_stock_range().
    """
    primary = str(tags_dict.get("primary", "") or "")
    rarity = str(tags_dict.get("rarity", "Common") or "Common")

    if "Fresh" in primary or rarity in ("Rare", "Legendary", "UltraRare"):
        return 0
    if "Currency" in primary:
        return math.floor(max_stock * 0.8)
    if any(token in primary for token in ("Ammo", "Material", "Resource")):
        return math.floor(max_stock * 0.4)
    return math.floor(max_stock * 0.2)


def _category_stock_config(config: Dict[str, Any], category: str) -> Dict[str, float]:
    categories = config.get("categories", {})
    return categories.get(category, categories.get("Misc", {}))


def _stock_role_values(context: Dict[str, Any], category_cfg: Dict[str, float]) -> tuple[float, float]:
    category = context["category"]
    max_mult = category_cfg.get("stock_multiplier", 1.0)
    min_ratio = category_cfg.get("stock_min_ratio", 0.2)

    if category == "Food":
        if context["is_canned"]:
            max_mult *= category_cfg.get("canned_stock_multiplier", 1.0)
            min_ratio = max(min_ratio, category_cfg.get("canned_min_ratio", min_ratio))
        if context["is_packaged"]:
            max_mult *= category_cfg.get("packaged_stock_multiplier", 1.0)
        if context["is_drink_item"]:
            max_mult *= category_cfg.get("drink_stock_multiplier", 1.0)
        if context["is_dried_staple"]:
            max_mult *= category_cfg.get("dried_staple_stock_multiplier", 1.0)
            min_ratio = max(min_ratio, category_cfg.get("dried_staple_min_ratio", min_ratio))
        if context["days_fresh"] > 0 and not context["is_canned"] and not context["is_packaged"]:
            max_mult *= category_cfg.get("fresh_stock_multiplier", 1.0)
            min_ratio = min(min_ratio, category_cfg.get("fresh_min_ratio", min_ratio))

    elif category == "Medical":
        if context["is_bandage"]:
            max_mult *= category_cfg.get("bandage_stock_multiplier", 1.0)
            min_ratio = max(min_ratio, category_cfg.get("bandage_min_ratio", min_ratio))
        if context["is_pills"]:
            max_mult *= category_cfg.get("pill_stock_multiplier", 1.0)
        if context["is_surgical"]:
            max_mult *= category_cfg.get("surgical_stock_multiplier", 1.0)
            min_ratio = min(min_ratio, category_cfg.get("surgical_min_ratio", min_ratio))
        if context["is_tobacco"]:
            max_mult *= category_cfg.get("tobacco_stock_multiplier", 1.0)

    elif category == "Weapon":
        if context["is_ammo"]:
            max_mult *= category_cfg.get("ammo_stock_multiplier", 1.0)
            min_ratio = max(min_ratio, category_cfg.get("ammo_min_ratio", min_ratio))
        elif context["is_firearm"]:
            max_mult *= category_cfg.get("firearm_stock_multiplier", 1.0)
            min_ratio = min(min_ratio, category_cfg.get("firearm_min_ratio", min_ratio))
        elif context["is_explosive"]:
            max_mult *= category_cfg.get("explosive_stock_multiplier", 1.0)
            min_ratio = min(min_ratio, category_cfg.get("explosive_min_ratio", min_ratio))
        elif context["is_tool_like"]:
            max_mult *= category_cfg.get("tool_weapon_stock_multiplier", 1.0)

    elif category == "Tool":
        if context["is_tool_like"]:
            max_mult *= category_cfg.get("common_tool_stock_multiplier", 1.0)
            min_ratio = max(min_ratio, category_cfg.get("common_tool_min_ratio", min_ratio))
        if context["is_powered_tool"]:
            max_mult *= category_cfg.get("powered_stock_multiplier", 1.0)
        if context["is_medical_tool"] or context["is_farming_tool"] or context["is_fishing_tool"]:
            max_mult *= category_cfg.get("specialized_stock_multiplier", 1.0)

    elif category == "Container":
        if context["capacity"] >= 20:
            max_mult *= category_cfg.get("large_container_stock_multiplier", 1.0)
        if "wearable" in context["primary_tag"].lower():
            max_mult *= category_cfg.get("wearable_stock_multiplier", 1.0)

    elif category == "Resource":
        if context.get("is_metal_resource"):
            max_mult *= category_cfg.get("metal_stock_multiplier", 1.0)
        if context.get("is_noble_metal_resource"):
            max_mult *= category_cfg.get("metal_noble_stock_multiplier", 1.0)
            min_ratio = min(min_ratio, category_cfg.get("metal_noble_min_ratio", min_ratio))
        if context.get("is_metal_ingot_resource"):
            max_mult *= category_cfg.get("metal_ingot_stock_multiplier", 1.0)
            min_ratio = min(min_ratio, category_cfg.get("metal_ingot_min_ratio", min_ratio))
        if context.get("is_metal_coin_resource"):
            max_mult *= category_cfg.get("metal_coin_stock_multiplier", 1.0)
        if context.get("is_metal_scrap_resource"):
            max_mult *= category_cfg.get("metal_scrap_stock_multiplier", 1.0)
        if context.get("is_metal_ore_resource"):
            max_mult *= category_cfg.get("metal_ore_stock_multiplier", 1.0)
            min_ratio = min(min_ratio, category_cfg.get("metal_ore_min_ratio", min_ratio))
        if context["is_hardware_resource"]:
            max_mult *= category_cfg.get("hardware_stock_multiplier", 1.0)
            min_ratio = max(min_ratio, category_cfg.get("hardware_min_ratio", min_ratio))
        if context["is_hardware_resource"] and context["is_carton"]:
            max_mult *= category_cfg.get("hardware_carton_stock_multiplier", 1.0)
            min_ratio = min(min_ratio, category_cfg.get("hardware_carton_min_ratio", min_ratio))
        if context["is_gas_fuel_resource"]:
            max_mult *= category_cfg.get("fuel_gas_stock_multiplier", 1.0)
            min_ratio = min(min_ratio, category_cfg.get("fuel_gas_min_ratio", min_ratio))
        elif context["is_solid_fuel_resource"]:
            max_mult *= category_cfg.get("solid_fuel_stock_multiplier", 1.0)
        if context["is_masonry_resource"]:
            max_mult *= category_cfg.get("masonry_stock_multiplier", 1.0)
        if context["is_powder_resource"]:
            max_mult *= category_cfg.get("powder_stock_multiplier", 1.0)
        if context["is_textile_resource"]:
            max_mult *= category_cfg.get("textile_stock_multiplier", 1.0)
            min_ratio = max(min_ratio, category_cfg.get("textile_min_ratio", min_ratio))
        if context["is_binding_resource"]:
            max_mult *= category_cfg.get("binding_stock_multiplier", 1.0)
        if context["is_sheet_material_resource"]:
            max_mult *= category_cfg.get("sheet_stock_multiplier", 1.0)
        if context["is_bag_fill_resource"]:
            max_mult *= category_cfg.get("bag_fill_stock_multiplier", 1.0)
        if ".parts" in context["primary_tag"].lower():
            max_mult *= category_cfg.get("parts_stock_multiplier", 1.0)

    elif category == "Building":
        if context["is_seed_building"]:
            max_mult *= category_cfg.get("seed_stock_multiplier", 1.0)
            min_ratio = max(min_ratio, category_cfg.get("seed_min_ratio", min_ratio))
        if context["is_garden_supply_building"]:
            max_mult *= category_cfg.get("garden_supply_stock_multiplier", 1.0)
        if context["is_farm_bulk_building"]:
            max_mult *= category_cfg.get("farm_bulk_stock_multiplier", 1.0)
        if context["is_moveable_building"]:
            max_mult *= category_cfg.get("moveable_stock_multiplier", 1.0)
        if context["is_vehicle_building"]:
            max_mult *= category_cfg.get("vehicle_stock_multiplier", 1.0)
            min_ratio = min(min_ratio, category_cfg.get("vehicle_min_ratio", min_ratio))
        if context["is_survival_building"]:
            max_mult *= category_cfg.get("survival_stock_multiplier", 1.0)
        if context["is_trap_building"]:
            max_mult *= category_cfg.get("trap_stock_multiplier", 1.0)
        if context["is_packed_building"]:
            max_mult *= category_cfg.get("packed_stock_multiplier", 1.0)

    return max_mult, min_ratio


def _apply_global_stock_modifiers(
    max_stock: int,
    min_ratio: float,
    context: Dict[str, Any],
    global_cfg: Dict[str, float],
) -> tuple[int, float]:
    rarity = context["tags_dict"].get("rarity") or "Common"
    quality = context["tags_dict"].get("quality")
    themes = context["tags_dict"].get("theme") or []

    rarity_mult = {
        "Common": global_cfg.get("stock_common_multiplier", 1.0),
        "Uncommon": global_cfg.get("stock_uncommon_multiplier", 0.85),
        "Rare": global_cfg.get("stock_rare_multiplier", 0.55),
        "Legendary": global_cfg.get("stock_legendary_multiplier", 0.22),
        "UltraRare": global_cfg.get("stock_ultrarare_multiplier", 0.1),
    }.get(rarity, 1.0)
    max_stock = max(1, math.floor(max_stock * rarity_mult))

    if quality == "Waste":
        max_stock = max(1, math.floor(max_stock * global_cfg.get("stock_waste_multiplier", 1.2)))
    elif quality == "Luxury":
        max_stock = max(1, math.floor(max_stock * global_cfg.get("stock_luxury_multiplier", 0.7)))

    theme_stock_keys = {
        "Police": "stock_theme_police_multiplier",
        "Militia": "stock_theme_militia_multiplier",
        "Clinical": "stock_theme_clinical_multiplier",
        "Industrial": "stock_theme_industrial_multiplier",
        "Primitive": "stock_theme_primitive_multiplier",
    }
    for theme in themes:
        theme_name = theme.split(".", 1)[1] if isinstance(theme, str) and theme.startswith("Theme.") else str(theme)
        stock_key = theme_stock_keys.get(theme_name)
        if stock_key:
            max_stock = max(1, math.floor(max_stock * global_cfg.get(stock_key, 1.0)))

    if rarity in ("Rare", "Legendary", "UltraRare"):
        min_ratio = min(min_ratio, global_cfg.get("stock_rare_min_ratio", 0.0))
    if context["is_opened"]:
        max_stock = max(1, math.floor(max_stock * global_cfg.get("stock_opened_multiplier", 0.7)))
    return max_stock, min_ratio


def calculate_stock_range(
    item_id: str,
    props: str,
    tags_dict: Any,
    pricing_config: Dict[str, Any] | None = None,
) -> Dict[str, int]:
    config = pricing_config or get_pricing_config()
    normalized_tags = normalize_tags_dict(tags_dict)
    context = build_item_context(item_id, props or "", normalized_tags)
    global_cfg = config.get("global", {})
    category_cfg = _category_stock_config(config, context["category"])

    base_max = calculate_base_max_stock(context["weight"], global_cfg)
    role_mult, min_ratio = _stock_role_values(context, category_cfg)
    max_stock = max(1, math.floor(base_max * role_mult))
    max_stock, min_ratio = _apply_global_stock_modifiers(max_stock, min_ratio, context, global_cfg)

    max_cap = int(global_cfg.get("stock_max_cap", 100))
    max_stock = max(1, min(max_stock, max_cap))
    min_stock = max(0, min(max_stock, math.floor(max_stock * min_ratio)))
    return {"min": min_stock, "max": max_stock}
