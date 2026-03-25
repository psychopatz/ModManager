"""
Utils package for ItemGenerator
Modular components for item processing and generation
"""

from .config import *
from .commons.vanilla_loader import load_vanilla_items, get_stat, has_property
from .commons.helpers import sanitize_path
from .commons.parse import get_opening_maps, get_vanilla_data
from .tag.tagging import generate_tags, parse_tags, categorize_item, get_category_from_tags
from .pricing.config_store import get_pricing_config, load_pricing_config, save_pricing_config, validate_pricing_config
from .pricing.audit import build_pricing_audit
from .pricing.tag_pricing import build_pricing_tag_catalog, preview_pricing_tag, warm_pricing_tag_cache
from .pricing.pricing import calculate_price, calculate_price_details
from .pricing.stock import calculate_base_max_stock, apply_category_multiplier, calculate_min_stock
from .pricing.economy import calculate_worth
from .parse import write_mod_duplicates, write_hierarchical_files, load_blacklist, is_item_blacklisted, filter_items, get_blacklist_stats, reload_blacklist, add_item_to_blacklist
from .commons.lua_handler import process_lua_file, add_items_to_file, get_registered_items, collect_unregistered_items, add_new_items
from .analyze.property_analyzer import (
    find_items_with_property,
    dump_items_by_property,
    list_all_properties,
    analyze_all_properties,
    find_items_by_multiple_properties
)
from .analyze.spawn_analyzer import (
    load_spawn_data,
    get_spawn_weight,
    get_spawn_locations,
    calculate_rarity_from_spawn,
    calculate_rarity_score,
    get_rarity_statistics,
    get_items_by_rarity,
    calculate_enhanced_rarity_score
)
