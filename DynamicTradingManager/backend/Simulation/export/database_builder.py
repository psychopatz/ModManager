from __future__ import annotations

import json
import random
from dataclasses import asdict
from pathlib import Path

from ..config import BuildConfig, Paths
from ..parse.archetypes_parser import parse_archetypes
from ..parse.events_parser import parse_events
from ..parse.items_parser import parse_items, parse_tags
from ..sim.economy import (
    build_event_modifiers,
    calculate_buy_price,
    calculate_sell_price,
    compute_unserved_items,
    generate_stock,
    is_tradeable_for_archetype,
)
from ..sim.event_timeline import TimelineState, compute_active_events

try:
    from ItemManagement import calculate_price, load_vanilla_items
    from ItemManagement.commons.lua_handler.records import tags_list_to_dict
except ImportError:
    calculate_price = None
    load_vanilla_items = None
    tags_list_to_dict = None


def build_database(paths: Paths, config: BuildConfig) -> dict:
    items = parse_items(paths.mod_common / "Items")
    tags = parse_tags(paths.mod_common / "Tags.lua")
    archetypes = parse_archetypes(paths.mod_common / "ArchetypeDefinitions")
    events = parse_events(paths.mod_common / "Events")

    if calculate_price and load_vanilla_items and tags_list_to_dict:
        vanilla_items = load_vanilla_items()
        for item_def in items.values():
            bare_id = item_def.item_id.split(".", 1)[1] if "." in item_def.item_id else item_def.item_id
            props = vanilla_items.get(bare_id)
            if not props:
                continue
            item_def.base_price = float(calculate_price(bare_id, props, tags_list_to_dict(item_def.tags)))

    rng = random.Random(config.seed)
    timeline_state = TimelineState(day=0)
    active = compute_active_events(events, config, timeline_state, rng)
    active_event_defs = [events[event_id] for event_id in active.ids if event_id in events]
    modifiers = build_event_modifiers(active_event_defs)

    trader_samples: dict[str, dict] = {}
    for arch_id, archetype in archetypes.items():
        stock = generate_stock(archetype, items, tags, config, modifiers, rng)
        trader_samples[arch_id] = {
            "name": archetype.name,
            "stock": stock,
        }

    trade_matrix: dict[str, dict[str, dict]] = {}
    for item_id, item_def in items.items():
        row: dict[str, dict] = {}
        for arch_id, archetype in archetypes.items():
            row[arch_id] = {
                "tradeable": is_tradeable_for_archetype(item_def, archetype, modifiers),
                "buyPrice": calculate_buy_price(item_def, tags, config, modifiers),
                "sellPrice": calculate_sell_price(item_def, archetype, config, modifiers),
            }
        trade_matrix[item_id] = row

    unserved = compute_unserved_items(items, archetypes)

    payload = {
        "meta": {
            "name": "SimulateGame",
            "parityMode": "Option B",
            "seed": config.seed,
            "generatedFrom": str(paths.mod_common),
        },
        "config": asdict(config),
        "items": {k: asdict(v) for k, v in items.items()},
        "tags": {k: asdict(v) for k, v in tags.items()},
        "archetypes": {k: asdict(v) for k, v in archetypes.items()},
        "events": {k: asdict(v) for k, v in events.items()},
        "day0": {
            "season": active.season,
            "activeEventIds": active.ids,
            "traderSamples": trader_samples,
            "tradeMatrix": trade_matrix,
            "unservedItems": unserved,
        },
    }

    return payload


def write_database(payload: dict, output_json: Path, output_js: Path | None = None) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(payload, indent=2)
    output_json.write_text(json_text, encoding="utf-8")

    if output_js is not None:
        output_js.parent.mkdir(parents=True, exist_ok=True)
        # Support opening the generated site directly via file:// without fetch CORS issues.
        output_js.write_text(f"window.SIM_DATA = {json_text};\n", encoding="utf-8")
