"""
Commons subsystem - Reusable utilities and infrastructure
"""
# pyright: reportMissingImports=false

# Vanilla loader utilities
from .vanilla_loader import (
    load_vanilla_items,
    get_stat,
    get_property_value,
    count_learned_recipes
)

# Tagging
from ..tag.tagging import parse_tags, generate_tags, is_excluded, get_category_from_tags

# Pricing
from ..pricing.pricing import calculate_price

# Stock
from ..pricing.stock import calculate_base_max_stock, apply_category_multiplier, calculate_min_stock



# Item data structures and utilities
from .items import (
    ItemData,
    PriceBreakdown,
    calculate_price_breakdown,
    should_include_item,
    filter_items_by_tag,
    calculate_price_tier,
    validate_item_entry
)

# Error handling
from .error_handler import (
    ItemGeneratorError,
    DataLoadError,
    ValidationError,
    PricingError,
    OutputError,
    ErrorHandler,
    safe_int_conversion,
    safe_float_conversion,
    validate_required_field,
    validate_file_exists
)

__all__ = [
    # Vanilla loader
    'load_vanilla_items',
    'get_stat',
    'get_property_value',
    'count_learned_recipes',
    
    # Tagging
    'parse_tags',
    'generate_tags',
    'is_excluded',
    'get_category_from_tags',
    
    # Pricing
    'calculate_price',
    'calculate_base_max_stock',
    'apply_category_multiplier',
    'calculate_min_stock',
    

    # Items
    'ItemData',
    'PriceBreakdown',
    'calculate_price_breakdown',
    'should_include_item',
    'filter_items_by_tag',
    'calculate_price_tier',
    'validate_item_entry',
    
    # Error handling
    'ItemGeneratorError',
    'DataLoadError',
    'ValidationError',
    'PricingError',
    'OutputError',
    'ErrorHandler',
    'safe_int_conversion',
    'safe_float_conversion',
    'validate_required_field',
    'validate_file_exists'
]
