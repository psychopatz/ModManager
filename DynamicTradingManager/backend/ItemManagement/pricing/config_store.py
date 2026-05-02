from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from config.server_settings import get_server_settings


CONFIG_PATH = Path(__file__).with_name("config.json")

DEFAULT_PRICING_CONFIG: Dict[str, Any] = {
    "version": 1,
    "global": {
        "min_price": 1,
        "max_price": 1e30,
        "base_multiplier": 1.0,
        "opened_penalty": 0.72,
        "extra_use_bonus": 0.08,
        "max_use_multiplier": 2.0,
        "stock_ultralight_max": 50,
        "stock_light_max": 25,
        "stock_small_max": 15,
        "stock_medium_max": 10,
        "stock_heavy_max": 5,
        "stock_massive_max": 2,
        "stock_max_cap": 100,
        "stock_default_min_ratio": 0.2,
        "stock_common_multiplier": 1.0,
        "stock_uncommon_multiplier": 0.85,
        "stock_rare_multiplier": 0.55,
        "stock_legendary_multiplier": 0.22,
        "stock_ultrarare_multiplier": 0.1,
        "stock_waste_multiplier": 1.2,
        "stock_luxury_multiplier": 0.7,
        "stock_theme_police_multiplier": 0.8,
        "stock_theme_militia_multiplier": 0.75,
        "stock_theme_clinical_multiplier": 0.75,
        "stock_theme_industrial_multiplier": 0.9,
        "stock_theme_primitive_multiplier": 0.8,
        "stock_rare_min_ratio": 0.0,
        "stock_opened_multiplier": 0.7,
    },
    "rarity_multipliers": {
        "Common": 1.0,
        "Uncommon": 1.18,
        "Rare": 1.45,
        "Legendary": 2.1,
        "UltraRare": 2.75,
    },
    "quality_multipliers": {
        "Waste": 0.3,
        "Sterile": 1.18,
        "Luxury": 1.6,
    },
    "origin_multipliers": {
        "Vanilla": 1.0,
    },
    "theme_multipliers": {
        "Police": 1.08,
        "Militia": 1.15,
        "Clinical": 1.12,
        "Industrial": 1.06,
        "Primitive": 1.05,
    },
    "tag_price_additions": {},
    "item_overrides": {},
    "categories": {
        "Food": {
            "price_floor": 6,
            "price_ceiling": 1e30,
            "base": 7.0,
            "hunger_weight": 160.0,
            "thirst_weight": 90.0,
            "calorie_weight": 0.025,
            "shelf_life_weight": 1.35,
            "max_shelf_life_days": 90.0,
            "fresh_unpacked_shelf_cap": 21.0,
            "canned_bonus": 24.0,
            "packaged_bonus": 10.0,
            "drink_bonus": 8.0,
            "hydration_bonus": 6.0,
            "alcohol_bonus": 12.0,
            "fluid_capacity_weight": 10.0,
            "large_food_hunger_threshold": 0.45,
            "large_food_thirst_threshold": 0.5,
            "large_food_weight_threshold": 0.9,
            "large_food_calorie_threshold": 1200.0,
            "large_food_hunger_overflow": 0.15,
            "large_food_thirst_overflow": 0.15,
            "large_food_calorie_overflow": 0.1,
            "dry_staple_multiplier": 0.42,
            "prepared_food_multiplier": 0.55,
            "preserved_ingredient_multiplier": 0.45,
            "fresh_penalty": 7.0,
            "weight_penalty": 1.2,
            "mood_penalty_weight": 40.0,
            "spice_multiplier": 0.45,
            "stock_multiplier": 0.9,
            "stock_min_ratio": 0.18,
            "fresh_stock_multiplier": 0.55,
            "fresh_min_ratio": 0.0,
            "canned_stock_multiplier": 1.15,
            "canned_min_ratio": 0.2,
            "packaged_stock_multiplier": 1.05,
            "drink_stock_multiplier": 1.15,
            "dried_staple_stock_multiplier": 1.2,
            "dried_staple_min_ratio": 0.22,
        },
        "Medical": {
            "price_floor": 12,
            "price_ceiling": 1e30,
            "base": 18.0,
            "sterile_bonus": 14.0,
            "dose_weight": 4.0,
            "dose_cap": 6.0,
            "pill_dose_cap": 9.0,
            "tobacco_dose_cap": 8.0,
            "bandage_bonus": 28.0,
            "bandaid_bonus": 10.0,
            "disinfectant_bonus": 22.0,
            "painkiller_bonus": 18.0,
            "sleep_bonus": 14.0,
            "beta_blocker_bonus": 16.0,
            "antidepressant_bonus": 15.0,
            "vitamin_bonus": 10.0,
            "surgical_bonus": 34.0,
            "splint_bonus": 20.0,
            "box_bundle_bonus": 24.0,
            "carton_bundle_bonus": 48.0,
            "tobacco_stress_weight": 2.0,
            "tobacco_morale_weight": 0.35,
            "tobacco_pack_bonus": 18.0,
            "tobacco_carton_bonus": 80.0,
            "weight_penalty": 0.8,
            "tobacco_multiplier": 0.5,
            "hygiene_multiplier": 0.35,
            "stock_multiplier": 0.75,
            "stock_min_ratio": 0.1,
            "bandage_stock_multiplier": 1.35,
            "bandage_min_ratio": 0.18,
            "pill_stock_multiplier": 0.95,
            "surgical_stock_multiplier": 0.55,
            "surgical_min_ratio": 0.0,
            "tobacco_stock_multiplier": 1.1,
        },
        "Weapon": {
            "price_floor": 8,
            "price_ceiling": 1e30,
            "base": 18.0,
            "damage_weight": 28.0,
            "range_weight": 4.0,
            "multi_hit_weight": 10.0,
            "durability_weight": 2.2,
            "reliability_weight": 0.6,
            "ammo_base": 10.0,
            "ammo_weight": 40.0,
            "ammo_carton_multiplier": 0.62,
            "explosive_bonus": 45.0,
            "firearm_bonus": 65.0,
            "two_handed_bonus": 12.0,
            "swing_penalty": 9.0,
            "weight_penalty": 1.4,
            "stock_multiplier": 0.6,
            "stock_min_ratio": 0.05,
            "ammo_stock_multiplier": 1.5,
            "ammo_min_ratio": 0.2,
            "firearm_stock_multiplier": 0.55,
            "firearm_min_ratio": 0.0,
            "explosive_stock_multiplier": 0.3,
            "explosive_min_ratio": 0.0,
            "tool_weapon_stock_multiplier": 1.0,
        },
        "Tool": {
            "price_floor": 8,
            "price_ceiling": 1e30,
            "base": 14.0,
            "durability_weight": 1.8,
            "capacity_weight": 1.2,
            "weight_reduction_weight": 0.2,
            "multi_use_bonus": 4.0,
            "powered_bonus": 10.0,
            "medical_bonus": 12.0,
            "farming_bonus": 12.0,
            "fishing_bonus": 12.0,
            "crafting_bonus": 20.0,
            "pry_bonus": 24.0,
            "salvage_weight": 0.2,
            "salvage_cap": 80.0,
            "repeat_use_cap": 18.0,
            "weight_penalty": 0.7,
            "stock_multiplier": 0.8,
            "stock_min_ratio": 0.12,
            "common_tool_stock_multiplier": 1.15,
            "common_tool_min_ratio": 0.18,
            "powered_stock_multiplier": 0.7,
            "specialized_stock_multiplier": 0.8,
        },
        "Container": {
            "price_floor": 10,
            "price_ceiling": 1e30,
            "base": 14.0,
            "capacity_weight": 4.0,
            "weight_reduction_weight": 0.65,
            "debug_multiplier": 0.12,
            "weight_penalty": 1.0,
            "stock_multiplier": 0.85,
            "stock_min_ratio": 0.12,
            "large_container_stock_multiplier": 0.7,
            "wearable_stock_multiplier": 0.9,
        },
        "Clothing": {
            "price_floor": 2,
            "price_ceiling": 1e30,
            "base": 4.0,
            "defense_weight": 0.35,
            "warmth_weight": 10.0,
            "wind_weight": 8.0,
            "speed_penalty_weight": 20.0,
            "weight_penalty": 0.7,
            "stock_multiplier": 0.95,
            "stock_min_ratio": 0.18,
        },
        "Electronics": {
            "price_floor": 8,
            "price_ceiling": 1e30,
            "base": 14.0,
            "power_bonus": 8.0,
            "light_bonus": 14.0,
            "radio_bonus": 36.0,
            "portable_bonus": 12.0,
            "battery_bonus": 10.0,
            "car_battery_bonus": 40.0,
            "generator_bonus": 240.0,
            "lantern_power_cap": 6.0,
            "power_value_cap": 15.0,
            "weight_penalty": 0.5,
            "stock_multiplier": 0.55,
            "stock_min_ratio": 0.05,
        },
        "Literature": {
            "price_floor": 3,
            "price_ceiling": 1e30,
            "base": 5.0,
            "recipe_weight": 18.0,
            "skill_book_bonus": 16.0,
            "skill_level_weight": 11.0,
            "magazine_bonus": 4.0,
            "map_bonus": 8.0,
            "weight_penalty": 0.6,
            "stock_multiplier": 1.0,
            "stock_min_ratio": 0.16,
        },
        "Resource": {
            "price_floor": 3,
            "price_ceiling": 1e30,
            "base": 7.0,
            "metal_weight": 0.8,
            "carton_metal_multiplier": 0.3,
            "metal_family_generic_bonus": 4.0,
            "metal_family_gold_bonus": 60.0,
            "metal_family_silver_bonus": 34.0,
            "metal_family_copper_bonus": 22.0,
            "metal_family_brass_bonus": 18.0,
            "metal_family_bronze_bonus": 16.0,
            "metal_family_steel_bonus": 18.0,
            "metal_family_iron_bonus": 12.0,
            "metal_family_aluminum_bonus": 14.0,
            "metal_family_lead_bonus": 10.0,
            "metal_family_tin_bonus": 9.0,
            "metal_form_raw_bonus": 4.0,
            "metal_form_mold_bonus": -6.0,
            "metal_form_ore_bonus": -8.0,
            "metal_form_scrap_bonus": -7.0,
            "metal_form_coin_bonus": 6.0,
            "metal_form_sheet_bonus": 28.0,
            "metal_form_ingot_bonus": 20.0,
            "metal_form_bloom_bonus": 6.0,
            "metal_form_block_bonus": 18.0,
            "metal_form_chunk_bonus": 12.0,
            "metal_form_piece_bonus": 7.0,
            "metal_form_rod_bonus": 8.0,
            "metal_form_band_bonus": 9.0,
            "metal_form_slug_bonus": 8.0,
            "metal_form_bar_bonus": 16.0,
            "metal_form_fragment_bonus": 5.0,
            "fuel_weight": 1.2,
            "fire_fuel_weight": 15.0,
            "crafting_bonus": 8.0,
            "survival_bonus": 4.0,
            "noble_metal_bonus": 6.0,
            "ingot_role_bonus": 4.0,
            "gas_fuel_bonus": 18.0,
            "solid_fuel_bonus": 8.0,
            "propane_bonus": 30.0,
            "fuel_container_bonus": 28.0,
            "hardware_bonus": 2.0,
            "hardware_box_bonus": 4.0,
            "hardware_carton_bonus": 8.0,
            "sheet_material_bonus": 10.0,
            "masonry_bonus": 10.0,
            "powder_bonus": 7.0,
            "textile_bonus": 4.0,
            "binding_bonus": 9.0,
            "stack_bonus": 8.0,
            "bag_fill_bonus": 7.0,
            "smeltable_bonus": 4.0,
            "fire_tinder_bonus": 2.0,
            "log_bonus": 8.0,
            "depleting_supply_bonus": 6.0,
            "bulk_bundle_bonus": 5.0,
            "weight_penalty": 0.18,
            "stock_multiplier": 1.1,
            "stock_min_ratio": 0.18,
            "metal_stock_multiplier": 0.95,
            "metal_noble_stock_multiplier": 0.35,
            "metal_noble_min_ratio": 0.0,
            "metal_ingot_stock_multiplier": 0.5,
            "metal_ingot_min_ratio": 0.0,
            "metal_coin_stock_multiplier": 0.8,
            "metal_scrap_stock_multiplier": 1.2,
            "metal_ore_stock_multiplier": 0.6,
            "metal_ore_min_ratio": 0.0,
            "hardware_stock_multiplier": 1.35,
            "hardware_min_ratio": 0.2,
            "hardware_carton_stock_multiplier": 0.35,
            "hardware_carton_min_ratio": 0.0,
            "fuel_gas_stock_multiplier": 0.45,
            "fuel_gas_min_ratio": 0.0,
            "solid_fuel_stock_multiplier": 1.0,
            "masonry_stock_multiplier": 0.9,
            "powder_stock_multiplier": 0.85,
            "textile_stock_multiplier": 1.25,
            "textile_min_ratio": 0.2,
            "binding_stock_multiplier": 1.1,
            "sheet_stock_multiplier": 0.75,
            "bag_fill_stock_multiplier": 0.9,
            "parts_stock_multiplier": 0.65,
        },
        "Building": {
            "price_floor": 1,
            "price_ceiling": 1e30,
            "base": 5.0,
            "survival_bonus": 8.0,
            "shelter_bonus": 12.0,
            "trap_bonus": 8.0,
            "fixture_bonus": 4.0,
            "vehicle_bonus": 8.0,
            "moveable_bonus": 1.0,
            "garden_bonus": 4.0,
            "garden_supply_bonus": 10.0,
            "crop_treatment_bonus": 5.0,
            "farm_bulk_bonus": 6.0,
            "seed_bonus": 7.0,
            "packed_bonus": 4.0,
            "survival_gear_bonus": 5.0,
            "replaceable_bag_bonus": 3.0,
            "appliance_bonus": 18.0,
            "plumbing_bonus": 14.0,
            "storage_bonus": 10.0,
            "counter_bonus": 6.0,
            "table_bonus": 4.0,
            "chair_bonus": 2.0,
            "bench_bonus": 4.0,
            "bed_bonus": 10.0,
            "lighting_bonus": 6.0,
            "communication_bonus": 7.0,
            "hardware_bonus": 7.0,
            "utility_station_bonus": 16.0,
            "vehicle_container_bonus": 10.0,
            "vehicle_maintenance_bonus": 16.0,
            "vehicle_body_bonus": 10.0,
            "storage_capacity_weight": 0.18,
            "vehicle_capacity_weight": 0.28,
            "weight_reduction_weight": 0.12,
            "salvage_weight": 0.12,
            "salvage_cap": 80.0,
            "decor_bonus": 2.0,
            "decor_multiplier": 0.55,
            "utility_use_weight": 0.7,
            "utility_use_cap": 5.0,
            "weight_penalty": 0.35,
            "stock_multiplier": 0.9,
            "stock_min_ratio": 0.1,
            "seed_stock_multiplier": 1.8,
            "seed_min_ratio": 0.2,
            "garden_supply_stock_multiplier": 0.95,
            "farm_bulk_stock_multiplier": 0.7,
            "moveable_stock_multiplier": 1.4,
            "vehicle_stock_multiplier": 0.55,
            "vehicle_min_ratio": 0.0,
            "survival_stock_multiplier": 0.75,
            "trap_stock_multiplier": 1.1,
            "packed_stock_multiplier": 0.8,
        },
        "Misc": {
            "price_floor": 1,
            "price_ceiling": 1e30,
            "base": 2.0,
            "value_weight": 0.75,
            "utility_bonus": 5.0,
            "material_cap": 20.0,
            "trinket_material_cap": 6.0,
            "firestarter_bonus": 12.0,
            "water_purifier_bonus": 26.0,
            "filter_bonus": 18.0,
            "hygiene_bonus": 8.0,
            "cosmetic_bonus": 4.0,
            "morale_bonus": 6.0,
            "crafting_bonus": 16.0,
            "jar_box_bonus": 18.0,
            "key_bonus": 8.0,
            "camera_bonus": 10.0,
            "weight_penalty": 0.5,
            "stock_multiplier": 1.0,
            "stock_min_ratio": 0.16,
        },
    },
}

_CONFIG_CACHE: Dict[str, Any] | None = None
_CONFIG_MTIME: float | None = None


def _deep_merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _ensure_number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be numeric")
    return float(value)


def _normalize_named_numeric_map(data: Any, path: str) -> dict[str, float]:
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be an object")
    out: dict[str, float] = {}
    for key, value in data.items():
        out[str(key)] = _ensure_number(value, f"{path}.{key}")
    return out


def _normalize_category_map(data: Any) -> dict[str, dict[str, float]]:
    if not isinstance(data, dict):
        raise ValueError("categories must be an object")
    out: dict[str, dict[str, float]] = {}
    for category, values in data.items():
        if not isinstance(values, dict):
            raise ValueError(f"categories.{category} must be an object")
        out[str(category)] = {
            str(key): _ensure_number(value, f"categories.{category}.{key}")
            for key, value in values.items()
        }
    return out


def _migrate_legacy_theme_pricing(merged: Dict[str, Any]) -> None:
    global_cfg = merged.setdefault("global", {})
    legacy_origin_stock_keys = {
        "stock_origin_police_multiplier": "stock_theme_police_multiplier",
        "stock_origin_militia_multiplier": "stock_theme_militia_multiplier",
        "stock_origin_clinical_multiplier": "stock_theme_clinical_multiplier",
        "stock_origin_industrial_multiplier": "stock_theme_industrial_multiplier",
    }
    for legacy_key, theme_key in legacy_origin_stock_keys.items():
        if legacy_key in global_cfg and theme_key not in global_cfg:
            global_cfg[theme_key] = global_cfg[legacy_key]

    origin_multipliers = dict(merged.get("origin_multipliers", {}) or {})
    theme_multipliers = dict(merged.get("theme_multipliers", {}) or {})
    for legacy_name in ("Police", "Militia", "Clinical", "Industrial", "Primitive"):
        if legacy_name in origin_multipliers and legacy_name not in theme_multipliers:
            theme_multipliers[legacy_name] = origin_multipliers[legacy_name]

    vanilla_multiplier = origin_multipliers.get("Vanilla", 1.0)
    merged["origin_multipliers"] = {"Vanilla": vanilla_multiplier}
    merged["theme_multipliers"] = theme_multipliers


def validate_pricing_config(candidate: Dict[str, Any] | None) -> Dict[str, Any]:
    merged = _deep_merge(DEFAULT_PRICING_CONFIG, candidate or {})
    _migrate_legacy_theme_pricing(merged)
    normalized: Dict[str, Any] = {
        "version": int(merged.get("version", 1)),
        "global": _normalize_named_numeric_map(merged.get("global", {}), "global"),
        "rarity_multipliers": _normalize_named_numeric_map(
            merged.get("rarity_multipliers", {}),
            "rarity_multipliers",
        ),
        "quality_multipliers": _normalize_named_numeric_map(
            merged.get("quality_multipliers", {}),
            "quality_multipliers",
        ),
        "origin_multipliers": _normalize_named_numeric_map(
            merged.get("origin_multipliers", {}),
            "origin_multipliers",
        ),
        "theme_multipliers": _normalize_named_numeric_map(
            merged.get("theme_multipliers", {}),
            "theme_multipliers",
        ),
        "tag_price_additions": _normalize_named_numeric_map(
            merged.get("tag_price_additions", {}),
            "tag_price_additions",
        ),
        "categories": _normalize_category_map(merged.get("categories", {})),
        "item_overrides": _normalize_named_numeric_map(
            merged.get("item_overrides", {}),
            "item_overrides",
        ),
    }

    if normalized["global"]["min_price"] < 0:
        raise ValueError("global.min_price must be >= 0")
    if normalized["global"]["max_price"] < normalized["global"]["min_price"]:
        raise ValueError("global.max_price must be >= global.min_price")

    return normalized


def _write_config(config: Dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _tag_additions_lua_path() -> Path:
    settings = get_server_settings()
    return (
        Path(settings.dynamic_trading_path)
        / "Contents"
        / "mods"
        / "DynamicTradingCommon"
        / "common"
        / "media"
        / "lua"
        / "shared"
        / "DT"
        / "Common"
        / "Pricing"
        / "DT_TagPriceAdditions_Data.lua"
    )


def _write_tag_additions_lua(config: Dict[str, Any]) -> dict[str, Any]:
    target = _tag_additions_lua_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    additions = config.get("tag_price_additions", {}) or {}
    rows: list[str] = []
    for tag, value in sorted(additions.items(), key=lambda x: str(x[0]).lower()):
        number = float(value)
        if abs(number) < 1e-9:
            continue
        escaped_tag = str(tag).replace("\\", "\\\\").replace('"', '\\"')
        rows.append(f'        ["{escaped_tag}"] = {number:g},')

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = "\n".join(rows)
    lua_text = (
        "-- DynamicTrading Tag Price Additions\n"
        f"-- Auto-generated by ModManager on {timestamp}\n"
        "-- This file is consumed by DT_RuntimeRules.lua for runtime tag pricing adjustments.\n"
        "\n"
        "return {\n"
        "    tagAdditions = {\n"
        f"{body}\n"
        "    },\n"
        "}\n"
    )
    target.write_text(lua_text, encoding="utf-8")
    return {"path": str(target), "count": len(rows)}


def get_pricing_config(force_reload: bool = False, return_copy: bool = False) -> Dict[str, Any]:
    global _CONFIG_CACHE, _CONFIG_MTIME

    if not CONFIG_PATH.exists():
        _write_config(DEFAULT_PRICING_CONFIG)

    mtime = CONFIG_PATH.stat().st_mtime
    if not force_reload and _CONFIG_CACHE is not None and _CONFIG_MTIME == mtime:
        return copy.deepcopy(_CONFIG_CACHE) if return_copy else _CONFIG_CACHE

    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        raw = copy.deepcopy(DEFAULT_PRICING_CONFIG)

    normalized = validate_pricing_config(raw)
    _CONFIG_CACHE = normalized
    _CONFIG_MTIME = mtime
    return copy.deepcopy(normalized) if return_copy else normalized


def load_pricing_config(force_reload: bool = False) -> Dict[str, Any]:
    return get_pricing_config(force_reload=force_reload, return_copy=True)


def save_pricing_config(config: Dict[str, Any]) -> Dict[str, Any]:
    global _CONFIG_CACHE, _CONFIG_MTIME

    normalized = validate_pricing_config(config)
    _write_config(normalized)
    lua_sync = _write_tag_additions_lua(normalized)
    _CONFIG_CACHE = normalized
    _CONFIG_MTIME = CONFIG_PATH.stat().st_mtime
    result = copy.deepcopy(normalized)
    result["__lua_sync"] = lua_sync
    return result
