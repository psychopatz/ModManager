from __future__ import annotations

import re
from pathlib import Path
from typing import Dict

from ..models import ItemDef, TagDef
from .lua_utils import find_lua_files, parse_quoted_list, read_text


ITEM_BLOCK_RE = re.compile(r'\{([^}]+)\}', re.DOTALL)

REGISTER_TAG_RE = re.compile(
    r'DynamicTrading\.RegisterTag\(\s*"([^"]+)"\s*,\s*\{([^}]*)\}\s*\)',
    re.DOTALL,
)

def get_mod_id_from_path(file_path: Path) -> str | None:
    """Finds the mod ID by looking for mod.info in parent directories."""
    # This matches the logic in our migration scripts
    current = file_path.parent
    # Stop searching if we hit the workshop root or go too high
    while current.parts:
        info_file = current / "mod.info"
        if info_file.exists():
            try:
                content = info_file.read_text(encoding="utf-8", errors="ignore")
                match = re.search(r"^id=(.+)$", content, re.MULTILINE)
                if match:
                    return match.group(1).strip()
            except Exception:
                pass
        if current.name == "Workshop" or current.parent == current:
            break
        current = current.parent
    return None


def parse_items(items_root: Path) -> Dict[str, ItemDef]:
    items: Dict[str, ItemDef] = {}
    for lua_file in find_lua_files(items_root):
        rel_file = str(lua_file.relative_to(items_root))
        content = read_text(lua_file)
        
        # Resolve mod ID from path as a fallback
        default_module = get_mod_id_from_path(lua_file)
        
        # We look for table entries inside DynamicTrading.RegisterBatch({ ... })
        # or simplified blocks.
        for match in ITEM_BLOCK_RE.finditer(content):
            block = match.group(1)
            
            # Extract fields using targeted regexes for flexibility
            item_id_match = re.search(r'item\s*=\s*"([^"]+)"', block)
            if not item_id_match:
                continue
            
            item_id = item_id_match.group(1).strip()
            
            price_match = re.search(r'basePrice\s*=\s*([-]?\d+(?:\.\d+)?)', block)
            base_price = float(price_match.group(1)) if price_match else 0.0
            
            tags_match = re.search(r'tags\s*=\s*\{([^}]*)\}', block)
            tags = parse_quoted_list(tags_match.group(1)) if tags_match else []
            
            stock_match = re.search(r'stockRange\s*=\s*\{\s*min\s*=\s*(\d+)\s*,\s*max\s*=\s*(\d+)\s*\}', block)
            stock_min = int(stock_match.group(1)) if stock_match else 0
            stock_max = int(stock_match.group(2)) if stock_match else 0
            
            chance_match = re.search(r'chance\s*=\s*([-]?\d+(?:\.\d+)?)', block)
            chance = float(chance_match.group(1)) if chance_match else None
            
            module_match = re.search(r'module\s*=\s*"([^"]+)"', block)
            module_id = module_match.group(1).strip() if module_match else default_module
            
            items[item_id] = ItemDef(
                item_id=item_id,
                base_price=base_price,
                tags=tags,
                stock_min=stock_min,
                stock_max=stock_max,
                chance=chance,
                module=module_id,
                source_file=rel_file,
            )
    return items


def parse_tags(tags_file: Path) -> Dict[str, TagDef]:
    tags: Dict[str, TagDef] = {}
    if not tags_file.exists():
        return tags

    default_module = get_mod_id_from_path(tags_file)
    content = read_text(tags_file)
    for match in REGISTER_TAG_RE.finditer(content):
        tag_name = match.group(1).strip()
        body = match.group(2)
        pm = re.search(r"priceMult\s*=\s*([-]?\d+(?:\.\d+)?)", body)
        wm = re.search(r"weight\s*=\s*([-]?\d+(?:\.\d+)?)", body)
        module_match = re.search(r'module\s*=\s*"([^"]+)"', body)
        
        tags[tag_name] = TagDef(
            tag=tag_name,
            price_mult=float(pm.group(1)) if pm else 1.0,
            weight=float(wm.group(1)) if wm else 50.0,
            module=module_match.group(1).strip() if module_match else default_module,
        )
    return tags
