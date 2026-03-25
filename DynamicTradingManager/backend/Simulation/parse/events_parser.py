from __future__ import annotations

import re
from pathlib import Path
from typing import Dict

from ..models import EventDef, EventEffect
from .lua_utils import (
    extract_balanced_block,
    find_lua_files,
    parse_lua_map_numbers,
    parse_quoted_list,
    read_text,
    table_field_block,
)


REGISTER_EVENT_RE = re.compile(r'DynamicTrading\.Events\.Register\(\s*"([^"]+)"\s*,\s*\{', re.DOTALL)
EFFECT_ENTRY_RE = re.compile(r'\[\s*"([^"]+)"\s*\]\s*=\s*\{([^}]*)\}', re.DOTALL)


def _infer_condition_kind(condition_source: str) -> tuple[str, str]:
    if not condition_source:
        return "none", ""

    season_match = re.search(r'getSeasonName\(\)\s*==\s*"([^"]+)"', condition_source)
    if season_match:
        return "season", season_match.group(1)

    nights_match = re.search(r'getNightsSurvived\(\)\s*>\s*(\d+)', condition_source)
    if nights_match:
        return "nights_gt", nights_match.group(1)

    days_match = re.search(r'getDaysSurvived\(\)\s*>\s*(\d+)', condition_source)
    if days_match:
        return "days_gt", days_match.group(1)

    return "custom", ""


def parse_events(events_root: Path) -> Dict[str, EventDef]:
    events: Dict[str, EventDef] = {}

    for lua_file in find_lua_files(events_root):
        if lua_file.name == "DT_EventManager.lua":
            continue
        content = read_text(lua_file)

        for match in REGISTER_EVENT_RE.finditer(content):
            event_id = match.group(1).strip()
            block = extract_balanced_block(content, match.end() - 1)
            if not block:
                continue

            name = _field_string(block, "name", event_id)
            event_type = _field_string(block, "type", "flash")
            sentiment = _field_string(block, "sentiment", "Neutral")
            description = _field_string(block, "description", "")

            effects: dict[str, EventEffect] = {}
            effects_block = table_field_block(block, "effects")
            for em in EFFECT_ENTRY_RE.finditer(effects_block):
                body = em.group(2)
                pm = re.search(r'price\s*=\s*([-]?\d+(?:\.\d+)?)', body)
                vm = re.search(r'vol\s*=\s*([-]?\d+(?:\.\d+)?)', body)
                effects[em.group(1)] = EventEffect(
                    price=float(pm.group(1)) if pm else None,
                    vol=float(vm.group(1)) if vm else None,
                )

            inject = parse_lua_map_numbers(table_field_block(block, "inject"))
            stock_block = table_field_block(block, "stock")
            stock_injections = parse_lua_map_numbers(table_field_block(stock_block, "injections"))
            stock_expert_tags = parse_quoted_list(table_field_block(stock_block, "expertTags"))
            stock_forbid_tags = parse_quoted_list(table_field_block(stock_block, "forbidTags"))

            vm = re.search(r'volumeMult\s*=\s*([-]?\d+(?:\.\d+)?)', stock_block)
            stock_volume_mult = float(vm.group(1)) if vm else None

            can_spawn_source = _field_function_source(block, "canSpawn")
            condition_source = _field_function_source(block, "condition")
            condition_kind, condition_value = _infer_condition_kind(condition_source)

            events[event_id] = EventDef(
                event_id=event_id,
                name=name,
                event_type=event_type,
                sentiment=sentiment,
                description=description,
                effects=effects,
                inject=inject,
                stock_volume_mult=stock_volume_mult,
                stock_injections=stock_injections,
                stock_expert_tags=stock_expert_tags,
                stock_forbid_tags=stock_forbid_tags,
                can_spawn_source=can_spawn_source,
                condition_source=condition_source,
                condition_kind=condition_kind,
                condition_value=condition_value,
            )

    return events


def _field_string(block: str, field: str, default: str) -> str:
    m = re.search(rf'{re.escape(field)}\s*=\s*"([^"]*)"', block)
    return m.group(1).strip() if m else default


def _field_function_source(block: str, field: str) -> str:
    m = re.search(rf'{re.escape(field)}\s*=\s*function\s*\([^)]*\)', block)
    if not m:
        return ""

    i = m.end()
    depth = 1
    out = [block[m.start() : m.end()]]

    while i < len(block):
        if block.startswith("function", i):
            depth += 1
        elif block.startswith("end", i):
            depth -= 1
            out.append("end")
            i += 3
            if depth == 0:
                break
            continue
        out.append(block[i])
        i += 1

    return "".join(out).strip()
