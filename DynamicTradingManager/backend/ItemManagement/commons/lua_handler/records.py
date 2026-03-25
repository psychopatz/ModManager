"""Item record creation and tag normalization helpers."""
# pyright: reportMissingImports=false

import re

from ...tag.tagging import parse_tags
from ...pricing.stock import calculate_stock_range
from ...pricing.pricing import calculate_price
from ...parse.overrides import load_overrides, apply_override
from .parsing import format_item_record


def tags_list_to_dict(tags_list):
    """Convert generated tag list into dict schema used by pricing/stock logic."""
    tag_dict = {
        'primary': 'Misc.General',
        'rarity': 'Common',
        'quality': None,
        'origin': 'Vanilla',
        'theme': [],
        'all_tags': [tag for tag in (tags_list or []) if isinstance(tag, str)],
    }

    for tag in tags_list or []:
        if not isinstance(tag, str):
            continue
        if tag.startswith('Rarity.'):
            tag_dict['rarity'] = tag.split('.', 1)[1] if '.' in tag else 'Common'
        elif tag.startswith('Quality.'):
            tag_dict['quality'] = tag.split('.', 1)[1] if '.' in tag else None
        elif tag.startswith('Origin.'):
            tag_dict['origin'] = tag.split('.', 1)[1] if '.' in tag else None
        elif tag.startswith('Theme.'):
            tag_dict['theme'].append(tag.split('.', 1)[1] if '.' in tag else 'General')
        elif tag_dict['primary'] == 'Misc.General':
            tag_dict['primary'] = tag

    return tag_dict


def tags_list_to_lua(tags_list):
    """Serialize Python tag list into Lua array literal body: \"a\", \"b\"."""
    return ', '.join(f'"{tag}"' for tag in (tags_list or []) if isinstance(tag, str))


def parse_lua_tags(tags_str):
    """Convert Lua tags string body into parsed tags dict."""
    tags_list = re.findall(r'"([^"]+)"', tags_str)
    tags_body = ', '.join(f'"{tag}"' for tag in tags_list)
    tags_dict = parse_tags('{' + tags_body + '}')
    tags_dict['all_tags'] = tags_list
    return tags_body, tags_dict


def create_item_record(item_data, vanilla_items):
    """Create a structured record for an item row."""
    item_id = item_data['item_id']
    props = item_data['props']
    tags = item_data['tags']

    tags_dict = tags_list_to_dict(tags)

    price = calculate_price(item_id, props, tags_dict)

    stock_range = calculate_stock_range(item_id, props, tags_dict)
    final_min = stock_range['min']
    final_max = stock_range['max']

    overrides = load_overrides()
    final_price, final_tags, final_min_override, final_max_override, was_overridden = apply_override(
        item_id,
        price,
        tags,
        final_min,
        final_max,
        overrides,
    )

    if was_overridden:
        print(f'  🔧 Applied override to: {item_id}')

    return {
        'item_id': item_id,
        'base_price': int(final_price),
        'tags': final_tags,
        'stock_min': int(final_min_override),
        'stock_max': int(final_max_override),
    }


def create_item_entry(item_data, vanilla_items):
    """Create a Lua entry for an item."""
    record = create_item_record(item_data, vanilla_items)
    return format_item_record(record)
