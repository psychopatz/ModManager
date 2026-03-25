"""
Item data classes and utilities
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import math


@dataclass
class ItemData:
    """Standardized item data structure"""
    item_id: str
    price: int
    weight: float
    tags: List[str]
    stock_min: int
    stock_max: int
    rarity: str = "Common"
    quality: Optional[str] = None
    origin: Optional[str] = None
    themes: Optional[List[str]] = None


@dataclass
class PriceBreakdown:
    """Pricing calculation breakdown"""
    item_id: str
    base_price: int
    condition_multiplier: float = 1.0
    rarity_multiplier: float = 1.0
    quality_multiplier: float = 1.0
    theme_multiplier: float = 1.0
    final_price: int = 0


def calculate_price_breakdown(item_id: str, base_props: Dict, tags_dict: Dict) -> PriceBreakdown:
    """
    Calculate price with detailed breakdown
    Returns PriceBreakdown with all multipliers
    """
    from .vanilla_loader import get_stat
    from ..pricing.pricing import calculate_price
    
    final = calculate_price(item_id, base_props, tags_dict)
    base = get_stat(base_props, "BasePrice", 0) if base_props else 0
    
    breakdown = PriceBreakdown(
        item_id=item_id,
        base_price=int(base),
        final_price=final
    )
    
    if base > 0:
        breakdown.condition_multiplier = final / base
    
    return breakdown


def should_include_item(item_id: str, vanilla_items: Dict, min_price: int = 0, max_price: int = 999999) -> Tuple[bool, str]:
    """
    Determine if an item should be included in trading system
    Returns (should_include, reason)
    """
    if not item_id:
        return False, "Empty item ID"
    
    if item_id not in vanilla_items:
        return False, "Not in vanilla items"
    
    props = vanilla_items[item_id]
    if not isinstance(props, str) or len(props.strip()) < 10:
        return False, "Invalid properties"
    
    if "clothing" in props.lower():
        return True, "Clothing item"
    
    if "weapon" in props.lower() or "ranged" in props.lower():
        return True, "Weapon item"
    
    if any(keyword in props.lower() for keyword in ["medical", "health", "pill", "medicine"]):
        return True, "Medical item"
    
    return False, "No matching category"


def merge_items(items_list: List[Dict]) -> Dict:
    """Merge multiple item lists, preferring most recent entries"""
    merged = {}
    
    for items in items_list:
        if isinstance(items, dict):
            merged.update(items)
    
    return merged


def sort_items_by_price(items: Dict[str, ItemData]) -> List[Tuple[str, ItemData]]:
    """Sort items by price in descending order"""
    return sorted(items.items(), key=lambda x: x[1].price, reverse=True)


def filter_items_by_tag(items: Dict[str, ItemData], tag: str) -> Dict[str, ItemData]:
    """Filter items that have a specific tag"""
    return {
        item_id: data
        for item_id, data in items.items()
        if tag in data.tags
    }


def calculate_price_tier(price: int) -> str:
    """Determine item price tier"""
    if price < 25:
        return "Budget"
    elif price < 100:
        return "Common"
    elif price < 500:
        return "Premium"
    elif price < 2000:
        return "Luxury"
    else:
        return "Elite"


def estimate_stock_variance(base_max: int, rarity: str) -> Tuple[int, int]:
    """
    Estimate stock variance based on rarity
    Returns (min_variance, max_variance) as percentages
    """
    variance_map = {
        "Ultra": (10, 20),
        "Super": (15, 30),
        "High": (20, 40),
        "Medium": (30, 50),
        "Common": (40, 60),
        "Abundant": (50, 70)
    }
    
    min_var, max_var = variance_map.get(rarity, (30, 50))
    return (
        max(1, int(base_max * min_var / 100)),
        max(1, int(base_max * max_var / 100))
    )


def validate_item_entry(item_data: ItemData) -> Tuple[bool, List[str]]:
    """
    Validate item entry for integrity
    Returns (is_valid, list_of_errors)
    """
    errors = []
    
    if not item_data.item_id or not isinstance(item_data.item_id, str):
        errors.append("Invalid item_id")
    
    if item_data.price < 0:
        errors.append("Negative price")
    
    if item_data.weight < 0:
        errors.append("Negative weight")
    
    if not item_data.tags or len(item_data.tags) == 0:
        errors.append("No tags")
    
    if item_data.stock_max < item_data.stock_min:
        errors.append("stock_max < stock_min")
    
    if item_data.stock_min < 0 or item_data.stock_max < 0:
        errors.append("Negative stock values")
    
    return len(errors) == 0, errors
