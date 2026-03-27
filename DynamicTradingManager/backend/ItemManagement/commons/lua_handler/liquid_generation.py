"""Generator-owned liquid registry rebuilds."""
# pyright: reportMissingImports=false

import statistics
from pathlib import Path

from ...config import MOD_ITEMS_DIR, SCRIPT_DIR
from ...commons.liquids import has_fluid_container, get_fluid_metadata
from ...pricing.pricing import calculate_price
from ...tag.tagging import (
    generate_tags,
    generate_fluid_tags,
    generate_fluid_container_tags,
    get_fluid_display_name,
)
from ...parse.overrides import load_fluid_overrides, apply_fluid_override
from .builders import build_lua_file_content
from .parsing import find_register_batch_bounds, extract_item_records, build_grouped_items_text
from .records import create_item_record, tags_list_to_dict


LIQUID_REGISTRY_RELATIVE_PATH = Path("Container/DT_Liquid.lua")
FLUID_REGISTRY_PATH = (
    Path(SCRIPT_DIR)
    / "Contents/mods/DynamicTradingCommon/42.13/media/lua/shared/DT/Common/Items/DT_Fluids.lua"
)


def _estimate_container_only_price(item_id, props):
    metadata = get_fluid_metadata(item_id, props)
    capacity = max(0.1, float(metadata.get("capacity", 0.0) or 0.0))
    tags = generate_fluid_container_tags(item_id, props)
    primary_tag = tags[0] if tags else ""

    if "Container.Liquid.Bottle" in primary_tag:
        base_price = 2.0 + (min(capacity, 5.0) * 4.0)
    elif "Container.Liquid.Can" in primary_tag:
        base_price = 3.0 + (min(capacity, 10.0) * 1.8)
    elif "Container.Liquid.Cup" in primary_tag:
        base_price = 1.5 + (min(capacity, 4.0) * 3.0)
    elif "Container.Liquid.Bucket" in primary_tag:
        base_price = 8.0 + (min(capacity, 10.0) * 1.5)
    elif "Container.Liquid.Jar" in primary_tag:
        base_price = 5.0 + (min(capacity, 5.0) * 3.0)
    elif "Container.Liquid.Wearable" in primary_tag:
        base_price = 8.0 + (min(capacity, 8.0) * 3.0)
    else:
        base_price = 3.0 + (min(capacity, 8.0) * 2.5)

    if "Quality.Waste" in tags:
        base_price = base_price * 0.85
    if "Quality.Luxury" in tags:
        base_price = base_price * 1.4
    if "Origin.Militia" in tags:
        base_price = base_price * 1.1

    return max(1, int(round(base_price)))


def _resolve_empty_container_price(item_id, vanilla_items, price_cache):
    if item_id in price_cache:
        return price_cache[item_id]

    props = vanilla_items.get(item_id, "")
    metadata = get_fluid_metadata(item_id, props)
    empty_item_id = metadata.get("replace_on_deplete", "")

    if empty_item_id and empty_item_id != item_id and empty_item_id in vanilla_items:
        empty_props = vanilla_items.get(empty_item_id, "")
        empty_tags = (
            generate_fluid_container_tags(empty_item_id, empty_props)
            if has_fluid_container(empty_props)
            else generate_tags(empty_item_id, empty_props)
        )
        price = calculate_price(empty_item_id, empty_props, tags_list_to_dict(empty_tags))
    else:
        price = _estimate_container_only_price(item_id, props)

    price = max(1, int(round(price)))
    price_cache[item_id] = price
    return price


def _collect_fluid_container_items(vanilla_items):
    fluid_items = {}
    for item_id, props in vanilla_items.items():
        if has_fluid_container(props):
            fluid_items[item_id] = props
    return fluid_items


def _remove_fluid_items_from_other_registries(fluid_item_ids):
    items_dir = Path(MOD_ITEMS_DIR)
    liquid_registry_path = items_dir / LIQUID_REGISTRY_RELATIVE_PATH

    for lua_file in sorted(items_dir.rglob("*.lua")):
        if lua_file == liquid_registry_path:
            continue

        with open(lua_file, "r", encoding="utf-8") as handle:
            content = handle.read()

        brace_start, brace_end = find_register_batch_bounds(content)
        if brace_start is None or brace_end is None:
            continue

        items_block = content[brace_start + 1:brace_end]
        records = extract_item_records(items_block)
        if not records:
            continue

        filtered = [record for record in records if record["item_id"] not in fluid_item_ids]
        if len(filtered) == len(records):
            continue

        normalized_items_text = build_grouped_items_text(filtered)
        new_content = content[:brace_start + 1] + "\n" + normalized_items_text + content[brace_end:]
        with open(lua_file, "w", encoding="utf-8") as handle:
            handle.write(new_content)


def _build_liquid_registry_records(vanilla_items, fluid_items):
    price_cache = {}
    records = []

    for item_id, props in sorted(fluid_items.items()):
        forced_tags = generate_fluid_container_tags(item_id, props)
        if not forced_tags:
            continue

        item_data = {
            "item_id": item_id,
            "props": props,
            "tags": forced_tags,
        }
        container_price = _resolve_empty_container_price(item_id, vanilla_items, price_cache)
        records.append(
            create_item_record(
                item_data,
                vanilla_items,
                forced_tags=forced_tags,
                base_price_override=container_price,
            )
        )

    return records


def _build_fluid_registry_entries(vanilla_items, fluid_items):
    fluid_overrides = load_fluid_overrides()
    price_cache = {}
    grouped = {}

    for item_id, props in sorted(fluid_items.items()):
        metadata = get_fluid_metadata(item_id, props)
        fluid_id = metadata.get("default_fluid")
        capacity = metadata.get("capacity", 0.0)
        if not fluid_id or capacity <= 0:
            continue

        source_tags = generate_tags(item_id, props)
        fluid_tags = generate_fluid_tags(fluid_id, source_tags)
        filled_tags = list(fluid_tags)
        rarity_tag = next((tag for tag in source_tags if isinstance(tag, str) and tag.startswith("Rarity.")), None)
        if rarity_tag:
            filled_tags.append(rarity_tag)

        filled_price = calculate_price(item_id, props, tags_list_to_dict(filled_tags))
        empty_price = _resolve_empty_container_price(item_id, vanilla_items, price_cache)
        candidate = (filled_price - empty_price) / capacity
        if candidate <= 0:
            continue

        bucket = grouped.setdefault(fluid_id, {
            "candidates": [],
            "source_items": set(),
            "source_tags": [],
        })
        bucket["candidates"].append(candidate)
        bucket["source_items"].add(f"Base.{item_id}")
        for tag in source_tags:
            if tag not in bucket["source_tags"]:
                bucket["source_tags"].append(tag)

    entries = []
    for fluid_id, info in sorted(grouped.items()):
        candidates = info["candidates"]
        if not candidates:
            continue

        base_price = round(statistics.median(candidates), 2)
        tags = generate_fluid_tags(fluid_id, info["source_tags"])
        display_name = get_fluid_display_name(fluid_id)
        base_price, tags, display_name, _ = apply_fluid_override(
            fluid_id,
            base_price,
            tags,
            display_name,
            fluid_overrides,
        )

        entries.append({
            "fluid_id": fluid_id,
            "base_price_per_liter": max(0.01, round(float(base_price), 2)),
            "tags": tags,
            "display_name": display_name,
            "source_items": sorted(info["source_items"]),
        })

    water_entry = next((entry for entry in entries if entry["fluid_id"] == "Water"), None)
    if water_entry and not any(entry["fluid_id"] == "TaintedWater" for entry in entries):
        base_price, tags, display_name, _ = apply_fluid_override(
            "TaintedWater",
            max(0.01, round(float(water_entry["base_price_per_liter"]) * 0.5, 2)),
            generate_fluid_tags("TaintedWater", water_entry["tags"]),
            get_fluid_display_name("TaintedWater"),
            fluid_overrides,
        )
        entries.append({
            "fluid_id": "TaintedWater",
            "base_price_per_liter": max(0.01, round(float(base_price), 2)),
            "tags": tags,
            "display_name": display_name,
            "source_items": list(water_entry["source_items"]),
        })

    return entries


def _build_fluid_registry_content(entries):
    lines = [
        "-- ============================================================================",
        "-- Generated Fluid Registry for Dynamic Trading",
        "-- This file is generated by Scripts/ItemGenerator. Do not hand-edit it.",
        "-- ============================================================================",
        "",
        'require "DT/Common/Config"',
        "if not DynamicTrading then return end",
        "",
        "DynamicTrading.Fluids = DynamicTrading.Fluids or {}",
        "",
        "local registry = {",
    ]

    for entry in entries:
        tags_str = ", ".join(f'"{tag}"' for tag in entry["tags"])
        source_items_str = ", ".join(f'"{item}"' for item in entry["source_items"])
        lines.append(
            f'    ["{entry["fluid_id"]}"] = {{ '
            f'basePricePerLiter={entry["base_price_per_liter"]}, '
            f'tags={{{tags_str}}}, '
            f'displayName="{entry["display_name"]}", '
            f'sourceItems={{{source_items_str}}} '
            f'}},'
        )

    lines.extend([
        "}",
        "",
        "for fluidKey, data in pairs(registry) do",
        "    DynamicTrading.Fluids[fluidKey] = data",
        '    if string.sub(fluidKey, 1, 5) ~= "Base." then',
        '        DynamicTrading.Fluids["Base." .. fluidKey] = data',
        "    end",
        "end",
        "",
        'print("[DynamicTrading] Fluid Registry Complete")',
        "",
    ])
    return "\n".join(lines)


def rebuild_liquid_registries(vanilla_items):
    """Rebuild DT_Liquid.lua and DT_Fluids.lua from vanilla fluid-container items."""
    fluid_items = _collect_fluid_container_items(vanilla_items)
    fluid_item_ids = set(fluid_items.keys())

    _remove_fluid_items_from_other_registries(fluid_item_ids)

    liquid_records = _build_liquid_registry_records(vanilla_items, fluid_items)
    liquid_items_text = build_grouped_items_text(liquid_records)
    liquid_registry_path = Path(MOD_ITEMS_DIR) / LIQUID_REGISTRY_RELATIVE_PATH
    liquid_registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(liquid_registry_path, "w", encoding="utf-8") as handle:
        handle.write(build_lua_file_content("DT_Liquid", "Container", liquid_items_text))

    fluid_entries = _build_fluid_registry_entries(vanilla_items, fluid_items)
    FLUID_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FLUID_REGISTRY_PATH, "w", encoding="utf-8") as handle:
        handle.write(_build_fluid_registry_content(fluid_entries))

    return {
        "fluid_container_count": len(fluid_item_ids),
        "fluid_entry_count": len(fluid_entries),
    }
