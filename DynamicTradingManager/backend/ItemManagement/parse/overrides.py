"""
Override system for forcing specific stats on items
Allows partial overrides - missing parameters use defaults
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

OVERRIDES_FILE = Path(__file__).parent.parent / "overrides.json"


def load_overrides() -> List[Dict[str, Any]]:
    """Load overrides from configuration file"""
    if not OVERRIDES_FILE.exists():
        # Create default overrides file
        default_config = {
            "overrides": []
        }
        OVERRIDES_FILE.write_text(json.dumps(default_config, indent=2))
        return []
    
    try:
        config = json.loads(OVERRIDES_FILE.read_text())
        return config.get("overrides", [])
    except json.JSONDecodeError:
        print(f"⚠️  Warning: Invalid JSON in {OVERRIDES_FILE}")
        return []


def save_overrides(overrides: List[Dict[str, Any]]):
    """Save overrides to configuration file"""
    config = {"overrides": overrides}
    OVERRIDES_FILE.write_text(json.dumps(config, indent=2))


def get_override_for_item(item_id: str, overrides: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """Get override configuration for a specific item ID"""
    if overrides is None:
        overrides = load_overrides()
    
    for override in overrides:
        if override.get("item") == item_id:
            return override
    return None


def validate_override(override: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate an override configuration
    Returns (is_valid, error_message)
    """
    if "item" not in override:
        return False, "Override must have 'item' field"
    
    item_id = override["item"]
    if not isinstance(item_id, str) or not item_id:
        return False, "Override 'item' must be a non-empty string"
    
    # Validate optional fields if present
    if "basePrice" in override:
        if not isinstance(override["basePrice"], (int, float)) or override["basePrice"] < 0:
            return False, f"basePrice for {item_id} must be a non-negative number"
    
    if "tags" in override:
        if not isinstance(override["tags"], list):
            return False, f"tags for {item_id} must be a list"
        for tag in override["tags"]:
            if not isinstance(tag, str):
                return False, f"Each tag for {item_id} must be a string"
    
    if "stockRange" in override:
        stock = override["stockRange"]
        if not isinstance(stock, dict):
            return False, f"stockRange for {item_id} must be an object"
        if "min" in stock and not isinstance(stock["min"], (int, float)):
            return False, f"stockRange.min for {item_id} must be a number"
        if "max" in stock and not isinstance(stock["max"], (int, float)):
            return False, f"stockRange.max for {item_id} must be a number"
        if "min" in stock and "max" in stock and stock["min"] > stock["max"]:
            return False, f"stockRange.min cannot be greater than max for {item_id}"
    
    return True, None


def find_invalid_overrides() -> List[Tuple[Dict[str, Any], str]]:
    """
    Find all invalid overrides in the configuration
    Returns list of (override, error_message) tuples
    """
    overrides = load_overrides()
    invalid = []
    
    for override in overrides:
        is_valid, error = validate_override(override)
        if not is_valid:
            invalid.append((override, error))
    
    return invalid


def find_duplicate_overrides() -> List[str]:
    """Find item IDs that have multiple override entries"""
    overrides = load_overrides()
    seen = set()
    duplicates = set()
    
    for override in overrides:
        item_id = override.get("item")
        if item_id:
            if item_id in seen:
                duplicates.add(item_id)
            seen.add(item_id)
    
    return sorted(duplicates)


def apply_override(
    item_id: str,
    base_price: float,
    tags: List[str],
    stock_min: int,
    stock_max: int,
    overrides: Optional[List[Dict[str, Any]]] = None
) -> Tuple[float, List[str], int, int, bool]:
    """
    Apply override configuration to item stats
    Returns (price, tags, stock_min, stock_max, was_overridden)
    """
    override = get_override_for_item(item_id, overrides)
    
    if not override:
        return base_price, tags, stock_min, stock_max, False
    
    # Apply overrides (use original values if not specified)
    overridden_price = override.get("basePrice", base_price)
    overridden_tags = override.get("tags", tags)
    
    stock_range = override.get("stockRange", {})
    overridden_min = stock_range.get("min", stock_min)
    overridden_max = stock_range.get("max", stock_max)
    
    return overridden_price, overridden_tags, overridden_min, overridden_max, True


def add_override(
    item_id: str,
    base_price: Optional[float] = None,
    tags: Optional[List[str]] = None,
    stock_min: Optional[int] = None,
    stock_max: Optional[int] = None,
    description: Optional[str] = None
):
    """Add a new override to the configuration"""
    overrides = load_overrides()
    
    # Remove existing override for this item
    overrides = [o for o in overrides if o.get("item") != item_id]
    
    # Build new override
    new_override = {"item": item_id}
    if base_price is not None:
        new_override["basePrice"] = base_price
    if tags is not None:
        new_override["tags"] = tags
    if stock_min is not None or stock_max is not None:
        new_override["stockRange"] = {}
        if stock_min is not None:
            new_override["stockRange"]["min"] = stock_min
        if stock_max is not None:
            new_override["stockRange"]["max"] = stock_max
    if description:
        new_override["description"] = description
    
    # Validate before adding
    is_valid, error = validate_override(new_override)
    if not is_valid:
        raise ValueError(f"Invalid override: {error}")
    
    overrides.append(new_override)
    save_overrides(overrides)
    print(f"✅ Added override for: {item_id}")


def remove_override(item_id: str) -> bool:
    """Remove an override from the configuration"""
    overrides = load_overrides()
    original_count = len(overrides)
    overrides = [o for o in overrides if o.get("item") != item_id]
    
    if len(overrides) < original_count:
        save_overrides(overrides)
        print(f"✅ Removed override for: {item_id}")
        return True
    else:
        print(f"⚠️  No override found for: {item_id}")
        return False


def get_override_stats() -> Dict[str, int]:
    """Get statistics about overrides"""
    overrides = load_overrides()
    invalid = find_invalid_overrides()
    duplicates = find_duplicate_overrides()
    
    return {
        "total": len(overrides),
        "invalid": len(invalid),
        "duplicates": len(duplicates)
    }
