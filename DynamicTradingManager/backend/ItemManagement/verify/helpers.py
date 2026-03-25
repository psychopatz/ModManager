"""
Utility functions for item verification
"""
import re


def sanitize_path(name):
    """Sanitize and truncate names for folder safety."""
    if not name:
        return "General"
    clean = re.sub(r'[<>:"/\\|?*;]', '_', name)
    return clean[:50].strip()


def get_stat(key, default=0.0, props=""):
    """
    Extract numeric property value from props string
    Case-insensitive search for the key
    
    Args:
        key: Property name to search for
        default: Default value if not found
        props: Properties string to search in
    
    Returns:
        float: Extracted value or default
    """
    if not props:
        return default
    m = re.search(fr"{key}\s*=\s*(-?\d+\.?\d*)", props, re.IGNORECASE)
    return float(m.group(1)) if m else default


def has_property(props, key):
    """
    Check if property exists in props string
    
    Args:
        props: Properties string
        key: Property name to check
    
    Returns:
        bool: True if property exists
    """
    pattern = fr"\b{key}\b\s*=\s*(?:true|false|[\d\.\-]+|['\"][^'\"]*['\"])"
    return bool(re.search(pattern, props, re.IGNORECASE))


def extract_string_property(props, key):
    """
    Extract string property value
    
    Args:
        props: Properties string  
        key: Property name
    
    Returns:
        str: Property value or Empty string
    """
    m = re.search(fr"{key}\s*=\s*([^,\n\s;]+)", props, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def parse_categories(props):
    """
    Parse category, subcategory, and other classification fields
    
    Args:
        props: Properties string
    
    Returns:
        dict: Extracted categories
    """
    cat_match = re.search(r"DisplayCategory\s*=\s*([^,\n\s;]+)", props)
    eat_match = re.search(r"EatType\s*=\s*([^,\n\s;]+)", props)
    tag_match = re.search(r"Tags\s*=\s*([^,\n\s;]+)", props)
    
    category = sanitize_path(cat_match.group(1).strip() if cat_match else "Uncategorized")
    eat_type = eat_match.group(1).strip() if eat_match else "None"
    tags = tag_match.group(1).strip() if tag_match else "None"
    
    subcat = "General"
    if eat_match:
        subcat = sanitize_path(eat_type)
    elif tag_match:
        first_tag = tags.split(';')[0].split(',')[0].strip()
        subcat = sanitize_path(first_tag)
    
    return {
        "category": category,
        "subcat": subcat,
        "eat_type": eat_type,
        "tags": tags
    }


def parse_body_locations(body_location_str):
    """
    Parse body location string into readable format
    
    Args:
        body_location_str: Location string (e.g., "base:rightwrist")
    
    Returns:
        list: Parsed locations
    """
    if not body_location_str:
        return []
    
    locations = body_location_str.replace("base:", "").split(";")
    return [loc.strip() for loc in locations if loc.strip()]


def count_recipes(props):
    """
    Count learned recipes in properties
    
    Args:
        props: Properties string
    
    Returns:
        int: Number of recipes
    """
    return len(re.findall(r"LearnedRecipes\s*=\s*([^,\n\s;]+)", props))
