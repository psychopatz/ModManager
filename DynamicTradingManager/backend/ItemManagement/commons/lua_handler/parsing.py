"""Parsing and formatting utilities for Lua item records."""
# pyright: reportMissingImports=false

import re
from collections import defaultdict


def find_register_batch_bounds(content):
    """Return (brace_start, brace_end) for DynamicTrading.RegisterBatch body."""
    batch_start = content.find('DynamicTrading.RegisterBatch(')
    if batch_start == -1:
        return None, None

    brace_start = content.find('{', batch_start)
    if brace_start == -1:
        return None, None

    depth = 0
    for index in range(brace_start, len(content)):
        char = content[index]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return brace_start, index

    return None, None


def extract_item_records(items_block):
    """Parse item rows from a RegisterBatch items block."""
    pattern = (
        r'\{\s*item="Base\.(\w+)"\s*,'
        r'\s*basePrice=(\d+)\s*,'
        r'\s*tags=\{([^}]*)\}\s*,'
        r'\s*stockRange=\{\s*min=(\d+)\s*,\s*max=(\d+)\s*\}\s*\}'
    )

    records = []
    for match in re.finditer(pattern, items_block):
        item_id, base_price, tags_raw, stock_min, stock_max = match.groups()
        tags = re.findall(r'"([^"]+)"', tags_raw)
        records.append({
            'item_id': item_id,
            'base_price': int(base_price),
            'tags': tags,
            'stock_min': int(stock_min),
            'stock_max': int(stock_max),
        })

    return records


def _get_primary_tag(tags):
    for tag in tags:
        if not tag.startswith(('Rarity.', 'Quality.', 'Origin.', 'Theme.')):
            return tag
    return 'Misc.General'


def _get_rarity_tag(tags):
    for tag in tags:
        if tag.startswith('Rarity.'):
            return tag
    return 'Rarity.Common'


def format_item_record(record):
    """Format a structured item record as a single Lua table row."""
    tags_str = ', '.join(f'"{tag}"' for tag in record['tags'])
    return (
        f'    {{ item="Base.{record["item_id"]}", basePrice={record["base_price"]}, '
        f'tags={{{tags_str}}}, stockRange={{min={record["stock_min"]}, max={record["stock_max"]}}} }},'
    )


def build_grouped_items_text(records):
    """Group records by primary+rarity tags and build normalized items text."""
    grouped = defaultdict(list)

    for record in sorted(
        records,
        key=lambda row: (_get_primary_tag(row['tags']), _get_rarity_tag(row['tags']), row['item_id'].lower()),
    ):
        grouped[(_get_primary_tag(record['tags']), _get_rarity_tag(record['tags']))].append(record)

    lines = [
        '    -- The items are grouped by Primary tag and Rarity',
        '',
    ]

    for primary_tag, rarity_tag in sorted(grouped.keys()):
        items_in_group = grouped[(primary_tag, rarity_tag)]
        item_word = 'item' if len(items_in_group) == 1 else 'items'
        lines.append(f'    -- [{primary_tag}] [{rarity_tag}] ({len(items_in_group)} {item_word})')

        for record in items_in_group:
            lines.append(format_item_record(record))

        lines.append('')

    return '\n'.join(lines).rstrip() + '\n'
