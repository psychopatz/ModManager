"""
Property extraction and validation helpers for auto-tagging.
Provides utilities for analyzing item properties and ID patterns.
"""
import re


def get_stat(key, props, default=0.0):
    """
    Extract numeric property value from props string.
    Case-insensitive search.
    
    Args:
        key: Property name (e.g., "Weight", "MaxDamage")
        props: Properties string block
        default: Default value if not found
    
    Returns:
        float: Property value or default
    """
    match = re.search(fr"{key}\s*=\s*(-?\d+\.?\d*)", props, re.IGNORECASE)
    return float(match.group(1)) if match else default


def has_property(key, props, value=None):
    """
    Check if property exists in props.
    
    Args:
        key: Property name
        props: Properties string block
        value: Optional specific value to match
    
    Returns:
        bool: True if property exists (and matches value if specified)
    """
    if value is None:
        # Just check existence
        return re.search(fr"{key}\s*=", props, re.IGNORECASE) is not None
    else:
        # Check specific value
        pattern = fr"{key}\s*=\s*{re.escape(str(value))}"
        return re.search(pattern, props, re.IGNORECASE) is not None


def extract_tags_from_props(props):
    """
    Extract tags array from properties string.
    
    Args:
        props: Properties string block
    
    Returns:
        list: List of tags found
    """
    match = re.search(r"Tags\s*=\s*([^,\n;]+)", props, re.IGNORECASE)
    if not match:
        return []
    
    tags_str = match.group(1)
    # Split by semicolon, comma, or pipe
    tags = re.split(r'[;,|]', tags_str)
    return [t.strip() for t in tags if t.strip()]


def count_recipes(props):
    """Count number of LearnedRecipes in properties."""
    matches = re.findall(r"LearnedRecipes\s*=\s*([^,\n\s;]+)", props)
    return len(matches)


def get_type_field(props):
    """
    Extract Type field from properties.
    
    Returns:
        str: Type value (e.g., "Weapon", "Food", "Literature")
    """
    match = re.search(r"Type\s*=\s*([^,\n\s;]+)", props, re.IGNORECASE)
    return match.group(1) if match else None


def get_display_category(props):
    """
    Extract DisplayCategory from properties.
    
    Returns:
        str: DisplayCategory value
    """
    match = re.search(r"DisplayCategory\s*=\s*([^,\n\s;]+)", props, re.IGNORECASE)
    return match.group(1) if match else None


def get_body_location(props):
    """Extract BodyLocation for clothing items."""
    match = re.search(r"BodyLocation\s*=\s*([^,\n\s;]+)", props, re.IGNORECASE)
    return match.group(1) if match else None


def count_body_parts(props):
    """Count number of BodyLocation entries."""
    matches = re.findall(r"BodyLocation\s*=\s*([^,\n\s;]+)", props)
    return len(matches)


def id_matches_pattern(item_id, patterns):
    """
    Check if item ID matches any pattern in list.
    Case-insensitive substring matching.
    
    Args:
        item_id: Item identifier
        patterns: List of substrings or regex patterns
    
    Returns:
        bool: True if match found
    """
    item_id_lower = item_id.lower()
    for pattern in patterns:
        if pattern.lower() in item_id_lower:
            return True
    return False


def extract_numeric_suffix(item_id):
    """
    Extract trailing numbers from item ID.
    
    Returns:
        int or None: Numeric suffix or None
    """
    match = re.search(r'(\d+)$', item_id)
    return int(match.group(1)) if match else None


class PropertyAnalyzer:
    """Utility class for comprehensive property analysis."""
    
    def __init__(self, props):
        """Initialize with properties string."""
        self.props = props
        self.props_lower = props.lower()
    
    def get_stat(self, key, default=0.0):
        """Get numeric stat."""
        return get_stat(key, self.props, default)
    
    def has_property(self, key, value=None):
        """Check if property exists."""
        return has_property(key, self.props, value)
    
    def get_defense_stats(self):
        """Extract all defense-related stats."""
        return {
            'bite_defense': self.get_stat('BiteDefense'),
            'scratch_defense': self.get_stat('ScratchDefense'),
            'bullet_defense': self.get_stat('BulletDefense'),
            'blunt_defense': self.get_stat('BluntDefense'),
            'fire_resistance': self.get_stat('FireResistance'),
        }
    
    def get_damage_stats(self):
        """Extract all damage-related stats."""
        return {
            'min_damage': self.get_stat('MinDamage'),
            'max_damage': self.get_stat('MaxDamage'),
            'avg_damage': (self.get_stat('MinDamage') + self.get_stat('MaxDamage')) / 2,
            'max_range': self.get_stat('MaxRange', 1.0),
            'max_hit_count': self.get_stat('MaxHitcount', 1.0),
        }
    
    def get_food_stats(self):
        """Extract all food-related stats."""
        return {
            'hunger_change': self.get_stat('HungerChange'),
            'thirst_change': self.get_stat('ThirstChange'),
            'calories': self.get_stat('Calories'),
            'days_fresh': self.get_stat('DaysFresh'),
            'days_rotten': self.get_stat('DaysTotallyRotten'),
            'unhappy_change': self.get_stat('UnhappyChange'),
            'boredom_change': self.get_stat('BoredomChange'),
        }
    
    def get_container_stats(self):
        """Extract container-related stats."""
        return {
            'capacity': self.get_stat('Capacity'),
            'weight_reduction': self.get_stat('WeightReduction'),
        }
    
    def get_clothing_stats(self):
        """Extract clothing-specific stats."""
        return {
            'insulation': self.get_stat('Insulation'),
            'wind_resistance': self.get_stat('WindResistance'),
            'encumbrance': self.get_stat('Encumbrance'),
            'run_speed_mod': self.get_stat('RunSpeedModifier', 1.0),
            'combat_speed_mod': self.get_stat('CombatSpeedModifier', 1.0),
        }
    
    def get_tool_stats(self):
        """Extract tool-related stats."""
        return {
            'use_delta': self.get_stat('UseDelta'),
            'condition_max': self.get_stat('ConditionMax'),
            'condition_lower_chance': self.get_stat('ConditionLowerChanceOneIn', 1.0),
        }
    
    def is_drainable(self):
        """Check if item has UseDelta (is drainable/consumable)."""
        return self.get_stat('UseDelta') > 0
    
    def is_melee_weapon(self):
        """Check if this is likely a melee weapon."""
        return self.get_stat('MinDamage') > 0 and self.has_property('ConditionMax')
    
    def is_firearm(self):
        """Check if this is a firearm."""
        return self.has_property('AmmoType')
    
    def can_equip(self):
        """Check if item can be equipped."""
        return self.has_property('BodyLocation') or self.has_property('Hands')
