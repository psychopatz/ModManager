from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, Iterable, List

from ..config import BuildConfig
from ..models import Allocation, ArchetypeDef, EventDef, ItemDef, TagDef
from .tag_logic import find_first_want_bonus, has_forbidden_tag, matches_all_tags, tag_price_mult


@dataclass
class EventModifiers:
    price_tag_mult: Dict[str, float]
    volume_tag_mult: Dict[str, float]
    global_stock_mult: float
    injections: Dict[str, float]
    expert_tags: Dict[str, bool]
    forbid_tags: Dict[str, bool]


def build_event_modifiers(events: Iterable[EventDef]) -> EventModifiers:
    price_tag_mult: dict[str, float] = {}
    volume_tag_mult: dict[str, float] = {}
    injections: dict[str, float] = {}
    expert_tags: dict[str, bool] = {}
    forbid_tags: dict[str, bool] = {}
    global_stock_mult = 1.0

    for event_def in events:
        if event_def.stock_volume_mult is not None:
            global_stock_mult *= event_def.stock_volume_mult

        for tag, effect in event_def.effects.items():
            if effect.price is not None:
                price_tag_mult[tag] = price_tag_mult.get(tag, 1.0) * effect.price
            if effect.vol is not None:
                volume_tag_mult[tag] = volume_tag_mult.get(tag, 1.0) * effect.vol

        for tag, count in event_def.inject.items():
            injections[tag] = injections.get(tag, 0.0) + float(count)
        for tag, count in event_def.stock_injections.items():
            injections[tag] = injections.get(tag, 0.0) + float(count)

        for tag in event_def.stock_expert_tags:
            expert_tags[tag] = True
        for tag in event_def.stock_forbid_tags:
            forbid_tags[tag] = True

    return EventModifiers(
        price_tag_mult=price_tag_mult,
        volume_tag_mult=volume_tag_mult,
        global_stock_mult=global_stock_mult,
        injections=injections,
        expert_tags=expert_tags,
        forbid_tags=forbid_tags,
    )


def generate_stock(
    archetype: ArchetypeDef,
    items: Dict[str, ItemDef],
    tags: Dict[str, TagDef],
    config: BuildConfig,
    modifiers: EventModifiers,
    rng: random.Random,
) -> Dict[str, dict]:
    if not items:
        return {}

    min_slots = max(1, math.floor(15 * config.stock_mult * modifiers.global_stock_mult))
    max_slots = max(min_slots, math.floor(25 * config.stock_mult * modifiers.global_stock_mult))
    total_slots = rng.randint(min_slots, max_slots)

    slots_filled = 0
    pool_keys: Dict[str, bool] = {}

    priority_list: List[Allocation] = list(archetype.allocations)
    for inject_tag, count in modifiers.injections.items():
        priority_list.append(Allocation(count=int(count), tags=[inject_tag]))

    for alloc in priority_list:
        if slots_filled >= total_slots:
            break

        valid_items = _resolve_allocation_items(alloc, archetype, items, modifiers)
        if not valid_items:
            continue

        for _ in range(alloc.count):
            if slots_filled >= total_slots:
                break
            pick = rng.choice(valid_items)
            pool_keys[pick] = True
            slots_filled += 1

    if slots_filled < total_slots:
        weighted_pool: list[tuple[str, float]] = []
        for item_id, item_def in items.items():
            if _is_forbidden_item(item_def, archetype, modifiers):
                continue

            if item_def.chance is not None:
                base_weight = float(item_def.chance)
            else:
                primary = item_def.tags[0] if item_def.tags else ""
                base_weight = tags.get(primary, TagDef(primary)).weight if primary else 50.0

            final_weight = base_weight + config.rarity_bonus
            if final_weight > 0:
                weighted_pool.append((item_id, final_weight))

        while slots_filled < total_slots and weighted_pool:
            pick = weighted_choice(weighted_pool, rng)
            pool_keys[pick] = True
            slots_filled += 1

    stock: Dict[str, dict] = {}
    for item_id in sorted(pool_keys.keys()):
        item_def = items[item_id]
        qty = rng.randint(item_def.stock_min, item_def.stock_max)

        vol_mult = 1.0
        for tag in item_def.tags:
            vol_mult *= modifiers.volume_tag_mult.get(tag, 1.0)

        qty = max(1, math.floor(qty * config.stock_mult * modifiers.global_stock_mult * vol_mult))

        is_expert = False
        for tag in item_def.tags:
            if tag in archetype.expert_tags or tag in modifiers.expert_tags:
                is_expert = True
                break

        stock[item_id] = {
            "qty": qty,
            "basePrice": item_def.base_price,
            "isExpert": is_expert,
            "tags": item_def.tags,
        }

    return stock


def calculate_buy_price(
    item_def: ItemDef,
    tags: Dict[str, TagDef],
    config: BuildConfig,
    modifiers: EventModifiers,
) -> int:
    tag_price_map = {tag_name: tag_def.price_mult for tag_name, tag_def in tags.items()}
    price = float(item_def.base_price)
    price *= tag_price_mult(item_def.tags, tag_price_map)

    event_mult = 1.0
    for tag in item_def.tags:
        event_mult *= modifiers.price_tag_mult.get(tag, 1.0)
    price *= event_mult

    price *= config.buy_mult
    return max(1, int(math.ceil(price)))


def calculate_sell_price(
    item_def: ItemDef,
    archetype: ArchetypeDef,
    config: BuildConfig,
    modifiers: EventModifiers,
) -> int:
    price = float(item_def.base_price) * config.sell_mult

    event_mult = 1.0
    for tag in item_def.tags:
        event_mult *= modifiers.price_tag_mult.get(tag, 1.0)
    price *= event_mult

    price *= find_first_want_bonus(item_def.tags, archetype.wants)
    return max(0, int(math.floor(price)))


def is_tradeable_for_archetype(item_def: ItemDef, archetype: ArchetypeDef, modifiers: EventModifiers) -> bool:
    if _is_forbidden_item(item_def, archetype, modifiers):
        return False

    if any(alloc.item == item_def.item_id for alloc in archetype.allocations if alloc.item):
        return True

    for alloc in archetype.allocations:
        if alloc.tags and matches_all_tags(item_def.tags, alloc.tags):
            return True

    # Wildcard pool behavior: non-forbidden items are still possible candidates.
    return True


def compute_unserved_items(items: Dict[str, ItemDef], archetypes: Dict[str, ArchetypeDef]) -> List[str]:
    served: set[str] = set()

    for archetype in archetypes.values():
        for alloc in archetype.allocations:
            if alloc.item and alloc.item in items:
                served.add(alloc.item)
                continue
            if alloc.tags:
                for item_id, item_def in items.items():
                    if matches_all_tags(item_def.tags, alloc.tags):
                        served.add(item_id)

    unserved = [item_id for item_id in items.keys() if item_id not in served]
    return sorted(unserved)


def weighted_choice(pool: List[tuple[str, float]], rng: random.Random) -> str:
    total = sum(weight for _, weight in pool)
    if total <= 0:
        return rng.choice([key for key, _ in pool])

    roll = rng.uniform(0.0, total)
    cur = 0.0
    for key, weight in pool:
        cur += weight
        if roll <= cur:
            return key
    return pool[-1][0]


def _resolve_allocation_items(
    allocation: Allocation,
    archetype: ArchetypeDef,
    items: Dict[str, ItemDef],
    modifiers: EventModifiers,
) -> List[str]:
    if allocation.item:
        if allocation.item in items and not _is_forbidden_item(items[allocation.item], archetype, modifiers):
            return [allocation.item]
        return []

    if not allocation.tags:
        return []

    out: list[str] = []
    for item_id, item_def in items.items():
        if _is_forbidden_item(item_def, archetype, modifiers):
            continue
        if matches_all_tags(item_def.tags, allocation.tags):
            out.append(item_id)
    return out


def _is_forbidden_item(item_def: ItemDef, archetype: ArchetypeDef, modifiers: EventModifiers) -> bool:
    if has_forbidden_tag(item_def.tags, archetype.forbid):
        return True
    if has_forbidden_tag(item_def.tags, modifiers.forbid_tags.keys()):
        return True
    return False
