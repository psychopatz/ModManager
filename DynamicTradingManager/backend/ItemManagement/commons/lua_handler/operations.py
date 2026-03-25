"""Core operations for updating and maintaining Lua registries."""
# pyright: reportMissingImports=false

import re
from pathlib import Path
from collections import defaultdict

from ...config import MOD_ITEMS_DIR, CATEGORY_FILE_MAP
from ...tag.tagging import generate_tags, is_excluded
from ...pricing.stock import calculate_stock_range
from ...pricing.pricing import calculate_price
from ...parse.blacklist import is_item_blacklisted
from .builders import cleanup_empty_lua_files, ensure_lua_file_exists
from .parsing import find_register_batch_bounds, extract_item_records, build_grouped_items_text
from .records import tags_list_to_dict, tags_list_to_lua, parse_lua_tags, create_item_record


FOOD_SUBCATEGORY_RULES = [
    ('Alcohol', ['Food.Drink.Alcohol', '.Alcohol']),
    ('Drink', ['Food.Drink.', '.Drink']),
    ('Meat', ['.Meat', '.Fish']),
    ('Vegetable', ['.Vegetable']),
    ('Fruit', ['.Fruit']),
    ('Spice', ['.Spice']),
    ('Sweets', ['.Sweets']),
    ('Grain', ['.Grain']),
    ('Canned', ['.Canned']),
    ('Cooking', ['Food.Cooking', '.Cooking']),
]


def determine_food_subcategory(tags):
    """Determine specific food subcategory from the full tag list."""
    for subcategory, patterns in FOOD_SUBCATEGORY_RULES:
        for tag in tags:
            if any(pattern in tag for pattern in patterns):
                return subcategory
    return 'General'


def process_lua_file(filepath, vanilla_items, dry_run=False, regenerate_tags=False):
    """Process a single Lua file and update prices/stock for RegisterBatch rows."""
    with open(filepath, 'r', encoding='utf-8') as handle:
        content = handle.read()

    pattern = r'\{\s*item="Base\.(\w+)",\s*basePrice=(\d+),\s*tags=(\{[^}]+\}),\s*stockRange=(\{[^}]+\})\s*\}'

    updates = []
    matches = list(re.finditer(pattern, content))

    print(f'\n📄 Processing: {filepath.name}')
    print(f'   Found {len(matches)} items')

    for match in matches:
        item_id = match.group(1)
        old_price = int(match.group(2))
        tags_raw = match.group(3)
        old_stock = match.group(4)

        props = vanilla_items.get(item_id, '')
        tags_body, tags_dict = parse_lua_tags(tags_raw)

        if regenerate_tags:
            generated_tags = generate_tags(item_id, props)
            tags_dict = tags_list_to_dict(generated_tags)
            tags_body = tags_list_to_lua(generated_tags)

        new_price = calculate_price(item_id, props, tags_dict)

        stock_range = calculate_stock_range(item_id, props, tags_dict)
        final_min = stock_range['min']
        final_max = stock_range['max']

        new_stock = f'{{min={final_min}, max={final_max}}}'
        new_entry = f'{{ item="Base.{item_id}", basePrice={new_price}, tags={{{tags_body}}}, stockRange={new_stock} }}'

        if new_price != old_price or new_stock != old_stock or match.group(3) != f'{{{tags_body}}}':
            updates.append({
                'old': match.group(0),
                'new': new_entry,
                'item_id': item_id,
                'old_price': old_price,
                'new_price': new_price,
                'old_tags': match.group(3),
                'new_tags': f'{{{tags_body}}}',
                'old_stock': old_stock,
                'new_stock': new_stock,
            })

    if updates and not dry_run:
        new_content = content
        for update in updates:
            new_content = new_content.replace(update['old'], update['new'], 1)

        with open(filepath, 'w', encoding='utf-8') as handle:
            handle.write(new_content)

        print(f'   ✅ Updated {len(updates)} items')
    elif updates:
        print(f'   🔍 [DRY RUN] Would update {len(updates)} items:')
        for update in updates[:3]:
            print(
                f"      {update['item_id']}: ${update['old_price']} → ${update['new_price']}, "
                f"{update['old_stock']} → {update['new_stock']}"
            )
        if len(updates) > 3:
            print(f"      ... and {len(updates) - 3} more")
    else:
        print('   ✓ No changes needed')

    return len(updates)


def get_registered_items():
    """Get set of all currently registered item IDs."""
    registered = set()
    items_dir = Path(MOD_ITEMS_DIR)
    lua_files = list(items_dir.rglob('*.lua'))

    # Filter out lines starting with -- (comments)
    pattern = r'^\s*\{\s*item="Base\.(\w+)"'
    for lua_file in lua_files:
        try:
            with open(lua_file, 'r', encoding='utf-8') as handle:
                for line in handle:
                    match = re.search(pattern, line)
                    if match:
                        registered.add(match.group(1))
        except Exception as error:
            print(f'⚠️  Error reading {lua_file.name}: {error}')

    return registered


def collect_unregistered_items(vanilla_items, registered_items):
    """Collect all vanilla items not yet registered."""
    unregistered = {}

    for item_id, props in vanilla_items.items():
        if item_id in registered_items:
            continue
        if is_excluded(item_id):
            continue
        if not props or len(props.strip()) < 10:
            continue
        unregistered[item_id] = props

    return unregistered


def group_items_by_category(items_dict):
    """Group items by their primary category."""
    grouped = defaultdict(list)

    for item_id, props in items_dict.items():
        tags = generate_tags(item_id, props)
        primary_tag = tags[0]
        category = primary_tag.split('.')[0]

        grouped[category].append({
            'item_id': item_id,
            'props': props,
            'tags': tags,
            'primary_tag': primary_tag,
        })

    return grouped


def add_items_to_file(filepath, new_items, vanilla_items=None):
    """Add new items and normalize existing + new items in a RegisterBatch file."""
    with open(filepath, 'r', encoding='utf-8') as handle:
        content = handle.read()

    brace_start, brace_end = find_register_batch_bounds(content)
    if brace_start is None or brace_end is None:
        print(f'  ⚠️  Cannot find RegisterBatch insertion point in {filepath.name}')
        return 0

    items_block = content[brace_start + 1:brace_end]
    existing_records = extract_item_records(items_block)
    existing_ids = {record['item_id'] for record in existing_records}

    if vanilla_items is not None:
        from ..vanilla_loader import _parse_properties_for_blacklist

        filtered_existing = []
        removed_count = 0

        for record in existing_records:
            item_id = record['item_id']
            props = vanilla_items.get(item_id, '')
            properties_dict = _parse_properties_for_blacklist(props) if props else {}
            is_blacklisted, reason = is_item_blacklisted(item_id, properties_dict)

            if is_blacklisted:
                removed_count += 1
                print(f'  🚫 Removing blacklisted item: {item_id} ({reason})')
            else:
                filtered_existing.append(record)

        existing_records = filtered_existing
        if removed_count > 0:
            print(f'  ✅ Removed {removed_count} blacklisted item(s)')

    new_records = [create_item_record(item_data, vanilla_items or {}) for item_data in new_items]
    added_count = sum(1 for record in new_records if record['item_id'] not in existing_ids)

    merged = {record['item_id']: record for record in existing_records}
    for record in new_records:
        if vanilla_items is not None:
            from ..vanilla_loader import _parse_properties_for_blacklist

            item_id = record['item_id']
            item_data = next((item for item in new_items if item.get('item_id') == item_id), None)
            if item_data:
                props = vanilla_items.get(item_id, '')
                properties_dict = _parse_properties_for_blacklist(props) if props else {}
                is_blacklisted, reason = is_item_blacklisted(item_id, properties_dict)

                if is_blacklisted:
                    print(f'  🚫 Skipping blacklisted item: {item_id} ({reason})')
                    continue

        merged[record['item_id']] = record

    normalized_items_text = build_grouped_items_text(list(merged.values()))
    new_content = content[:brace_start + 1] + '\n' + normalized_items_text + content[brace_end:]

    with open(filepath, 'w', encoding='utf-8') as handle:
        handle.write(new_content)

    return added_count


def determine_target_file(category, subcategory):
    """Determine which Lua file should receive items for a subcategory."""
    if category in CATEGORY_FILE_MAP:
        subcat_map = CATEGORY_FILE_MAP[category]

        if subcategory in subcat_map:
            return Path(MOD_ITEMS_DIR) / subcat_map[subcategory]

        for key in subcat_map:
            if subcategory == key or subcategory.startswith(f'{key}.'):
                return Path(MOD_ITEMS_DIR) / subcat_map[key]

        return Path(MOD_ITEMS_DIR) / list(subcat_map.values())[0]

    return Path(MOD_ITEMS_DIR) / 'Misc/DT_General.lua'


def add_new_items(vanilla_items, batch_size=50):
    """Add new unregistered items to the trading system."""
    print('\n' + '=' * 60)
    print('Adding New Unregistered Items')
    print('=' * 60)

    print('\n✓ Preparing Lua file structure...')
    Path(MOD_ITEMS_DIR).mkdir(parents=True, exist_ok=True)

    print('\n📋 Collecting registered items...')
    registered = get_registered_items()
    print(f'   Found {len(registered)} registered items')

    print('\n🔍 Finding unregistered items...')
    unregistered = collect_unregistered_items(vanilla_items, registered)
    print(f'   Found {len(unregistered)} unregistered items')

    if not unregistered:
        print('\n✅ All vanilla items are already registered!')
        return 0

    if batch_size is not None and len(unregistered) > batch_size:
        print(f'\n⚠️  Limiting to {batch_size} items per run')
        unregistered = dict(list(unregistered.items())[:batch_size])

    print('\n🗂️  Categorizing items...')
    grouped = group_items_by_category(unregistered)

    total_added = 0
    for category, items in grouped.items():
        print(f'\n📁 {category}: {len(items)} items')

        by_subcat = defaultdict(list)
        for item_data in items:
            if category == 'Food':
                subcat = determine_food_subcategory(item_data['tags'])
            else:
                primary = item_data['primary_tag']
                parts = primary.split('.')
                subcat = '.'.join(parts[1:]) if len(parts) > 1 else 'General'
            by_subcat[subcat].append(item_data)

        for subcat, subcat_items in by_subcat.items():
            target_file = determine_target_file(category, subcat)

            if not target_file.exists():
                relative_path = target_file.relative_to(Path(MOD_ITEMS_DIR))
                ensure_lua_file_exists(str(relative_path))

            try:
                added = add_items_to_file(target_file, subcat_items, vanilla_items)
                total_added += added
                print(f'  ✅ Added {added} items to {target_file.name}')
            except Exception as error:
                print(f'  ❌ Error adding to {target_file.name}: {error}')

    removed_count = cleanup_empty_lua_files()
    if removed_count:
        print(f'\n🧹 Removed {removed_count} empty Lua file(s)')

    return total_added


def cleanup_blacklisted_items(vanilla_items, dry_run=False):
    """Remove all blacklisted items from RegisterBatch Lua files."""
    from ..vanilla_loader import _parse_properties_for_blacklist

    print('\n' + '=' * 60)
    print('🧹 Cleaning Up Blacklisted Items' + (' (DRY RUN)' if dry_run else ''))
    print('=' * 60)

    items_dir = Path(MOD_ITEMS_DIR)
    lua_files = list(items_dir.rglob('*.lua'))

    total_removed = 0
    files_modified = 0

    for lua_file in lua_files:
        try:
            with open(lua_file, 'r', encoding='utf-8') as handle:
                content = handle.read()

            brace_start, brace_end = find_register_batch_bounds(content)
            if brace_start is None or brace_end is None:
                continue

            items_block = content[brace_start + 1:brace_end]
            existing_records = extract_item_records(items_block)
            if not existing_records:
                continue

            filtered_records = []
            removed_items = []

            for record in existing_records:
                item_id = record['item_id']
                props = vanilla_items.get(item_id, '')
                properties_dict = _parse_properties_for_blacklist(props) if props else {}
                is_blacklisted, reason = is_item_blacklisted(item_id, properties_dict)

                if is_blacklisted:
                    removed_items.append((item_id, reason))
                else:
                    filtered_records.append(record)

            if removed_items:
                print(f'\n📄 {lua_file.name}')
                print(f'   Found {len(existing_records)} items, removing {len(removed_items)}:')

                for item_id, reason in removed_items[:5]:
                    print(f'     🚫 {item_id}: {reason}')
                    total_removed += 1

                if len(removed_items) > 5:
                    print(f'     ... and {len(removed_items) - 5} more')
                    total_removed += len(removed_items) - 5

                if not dry_run:
                    normalized_items_text = build_grouped_items_text(filtered_records)
                    new_content = content[:brace_start + 1] + '\n' + normalized_items_text + content[brace_end:]

                    with open(lua_file, 'w', encoding='utf-8') as handle:
                        handle.write(new_content)

                    files_modified += 1
                    print('   ✅ File updated')

        except Exception as error:
            print(f'   ❌ Error processing {lua_file.name}: {error}')

    print('\n' + '=' * 60)
    if dry_run:
        print(f'📊 Would remove {total_removed} blacklisted items from {files_modified} files')
    else:
        print(f'✅ Removed {total_removed} blacklisted items from {files_modified} files')
    print('=' * 60 + '\n')

    return total_removed
