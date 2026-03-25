from __future__ import annotations

import re
from pathlib import Path
from typing import Dict

from ..models import Allocation, ArchetypeDef
from .lua_utils import (
    extract_balanced_block,
    find_lua_files,
    parse_lua_map_numbers,
    parse_quoted_list,
    read_text,
    table_field_block,
)


REGISTER_ARCH_RE = re.compile(r'DynamicTrading\.RegisterArchetype\(\s*"([^"]+)"\s*,\s*\{', re.DOTALL)
ALLOC_ITEM_RE = re.compile(r'\{\s*item\s*=\s*"([^"]+)"\s*,\s*count\s*=\s*(\d+)\s*\}', re.DOTALL)
ALLOC_TAG_RE = re.compile(r'\{\s*tags\s*=\s*\{([^}]*)\}\s*,\s*count\s*=\s*(\d+)\s*\}', re.DOTALL)


def parse_archetypes(archetypes_root: Path) -> Dict[str, ArchetypeDef]:
    archetypes: Dict[str, ArchetypeDef] = {}

    for lua_file in find_lua_files(archetypes_root):
        if "/Items/" not in str(lua_file).replace("\\", "/"):
            continue

        content = read_text(lua_file)
        for match in REGISTER_ARCH_RE.finditer(content):
            arch_id = match.group(1).strip()
            open_idx = match.end() - 1
            block = extract_balanced_block(content, open_idx)
            if not block:
                continue

            name_match = re.search(r'name\s*=\s*"([^"]+)"', block)
            name = name_match.group(1).strip() if name_match else arch_id

            allocations: list[Allocation] = []
            alloc_block = table_field_block(block, "allocations")
            for am in ALLOC_ITEM_RE.finditer(alloc_block):
                allocations.append(Allocation(item=am.group(1).strip(), count=int(am.group(2))))
            for am in ALLOC_TAG_RE.finditer(alloc_block):
                allocations.append(
                    Allocation(tags=parse_quoted_list(am.group(1)), count=int(am.group(2)))
                )

            expert_tags = parse_quoted_list(table_field_block(block, "expertTags"))
            wants = parse_lua_map_numbers(table_field_block(block, "wants"))
            forbid = parse_quoted_list(table_field_block(block, "forbid"))

            archetypes[arch_id] = ArchetypeDef(
                archetype_id=arch_id,
                name=name,
                allocations=allocations,
                expert_tags=expert_tags,
                wants=wants,
                forbid=forbid,
            )

    return archetypes
