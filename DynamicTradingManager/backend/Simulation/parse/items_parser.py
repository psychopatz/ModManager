from __future__ import annotations

import re
from pathlib import Path
from typing import Dict

from ..models import ItemDef, TagDef
from .lua_utils import find_lua_files, parse_quoted_list, read_text


ITEM_ENTRY_RE = re.compile(
    r'\{\s*item\s*=\s*"([^"]+)"\s*,\s*basePrice\s*=\s*([-]?\d+(?:\.\d+)?)\s*,\s*tags\s*=\s*\{([^}]*)\}\s*,\s*stockRange\s*=\s*\{\s*min\s*=\s*(\d+)\s*,\s*max\s*=\s*(\d+)\s*\}(?:\s*,\s*chance\s*=\s*([-]?\d+(?:\.\d+)?))?\s*\}',
    re.DOTALL,
)

REGISTER_TAG_RE = re.compile(
    r'DynamicTrading\.RegisterTag\(\s*"([^"]+)"\s*,\s*\{([^}]*)\}\s*\)',
    re.DOTALL,
)


def parse_items(items_root: Path) -> Dict[str, ItemDef]:
    items: Dict[str, ItemDef] = {}
    for lua_file in find_lua_files(items_root):
        rel_file = str(lua_file.relative_to(items_root))
        content = read_text(lua_file)
        for match in ITEM_ENTRY_RE.finditer(content):
            item_id = match.group(1).strip()
            tags = parse_quoted_list(match.group(3))
            items[item_id] = ItemDef(
                item_id=item_id,
                base_price=float(match.group(2)),
                tags=tags,
                stock_min=int(match.group(4)),
                stock_max=int(match.group(5)),
                chance=float(match.group(6)) if match.group(6) is not None else None,
                source_file=rel_file,
            )
    return items


def parse_tags(tags_file: Path) -> Dict[str, TagDef]:
    tags: Dict[str, TagDef] = {}
    if not tags_file.exists():
        return tags

    content = read_text(tags_file)
    for match in REGISTER_TAG_RE.finditer(content):
        tag_name = match.group(1).strip()
        body = match.group(2)
        pm = re.search(r"priceMult\s*=\s*([-]?\d+(?:\.\d+)?)", body)
        wm = re.search(r"weight\s*=\s*([-]?\d+(?:\.\d+)?)", body)
        tags[tag_name] = TagDef(
            tag=tag_name,
            price_mult=float(pm.group(1)) if pm else 1.0,
            weight=float(wm.group(1)) if wm else 50.0,
        )
    return tags
