"""Builders for Lua registry file content."""
# pyright: reportMissingImports=false

from pathlib import Path

from ...config import MOD_ITEMS_DIR


def build_lua_file_content(filename, category, items_body_text=''):
    """Build full Lua file content in DynamicTrading.RegisterBatch format."""
    registry_name = filename.replace('DT_', '').replace('_', ' ').strip() or 'Items'
    batch_body = items_body_text.rstrip()
    if batch_body:
        batch_body = '\n' + batch_body + '\n'
    else:
        batch_body = '\n'

    return f'''-- ============================================================================
-- {category} Items Registry for Dynamic Trading
-- If you want some suggestions or have balancing issues, please report them to
-- my discussion page. Happy to adjust prices and stock based on your feedback! :)
-- https://steamcommunity.com/sharedfiles/filedetails/?id=3635333613
-- ============================================================================

require "DT/Common/Config"
if not DynamicTrading then return end

DynamicTrading.RegisterBatch({{{batch_body}}})

print("[DynamicTrading] {registry_name} Registry Complete")
'''


def ensure_lua_file_exists(file_path):
    """Create a single Lua registry file if it doesn't exist."""
    base_dir = Path(MOD_ITEMS_DIR)
    full_path = base_dir / file_path

    if full_path.exists():
        return False

    full_path.parent.mkdir(parents=True, exist_ok=True)
    category = file_path.split('/')[0] if '/' in file_path else 'Misc'
    filename = file_path.split('/')[-1].replace('.lua', '')

    lua_content = build_lua_file_content(filename, category)
    with open(full_path, 'w', encoding='utf-8') as handle:
        handle.write(lua_content)

    print(f"   ✅ Created {file_path}")
    return True


def ensure_lua_files_exist():
    """Ensure the Lua base directory exists without pre-creating empty files."""
    base_dir = Path(MOD_ITEMS_DIR)
    base_dir.mkdir(parents=True, exist_ok=True)
    return 0


def cleanup_empty_lua_files():
    """Delete Lua registry files that contain an empty RegisterBatch block."""
    from .parsing import find_register_batch_bounds

    base_dir = Path(MOD_ITEMS_DIR)
    if not base_dir.exists():
        return 0

    removed_count = 0
    for lua_file in sorted(base_dir.rglob('*.lua')):
        try:
            with open(lua_file, 'r', encoding='utf-8') as handle:
                content = handle.read()

            brace_start, brace_end = find_register_batch_bounds(content)
            if brace_start is None or brace_end is None:
                continue

            items_block = content[brace_start + 1:brace_end]
            if items_block.strip():
                continue

            lua_file.unlink()
            removed_count += 1
            print(f'   🗑️  Removed empty {lua_file.relative_to(base_dir)}')
        except Exception as error:
            print(f'   ⚠️  Error checking {lua_file.name}: {error}')

    return removed_count
