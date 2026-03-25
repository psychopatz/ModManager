"""
Food property-based signatures.
Detects edible items through nutrition, freshness, cooking, and drink metadata.
"""
import re

from .helpers import id_matches_pattern, PropertyAnalyzer


FOOD_ID_PATTERNS = [
    'Food', 'Meat', 'Fish', 'Fruit', 'Vegetable', 'Bread', 'Meal',
    'Drink', 'Beverage', 'Alcohol', 'Beer', 'Wine', 'Juice', 'Coffee',
    'Tea', 'Milk', 'Soda', 'Pop', 'Spice', 'Condiment', 'Seasoning',
    'Dessert', 'Candy', 'Chocolate', 'Cereal', 'Soup', 'Stew', 'Snack',
    'Bitters',
    'Dough', 'Batter', 'Canned', 'Bouillon', 'Mushroom', 'Berry',
    'RationCan', 'DentedCan', 'MysteryCan'
]

ALCOHOL_ID_PATTERNS = [
    'Alcohol', 'Ale', 'Beer', 'Brandy', 'Champagne', 'Cider', 'Gin',
    'Lager', 'Liqueur', 'Liquer', 'Liquor', 'Mead', 'Port', 'Rum',
    'Tequila', 'Vodka', 'Whiskey', 'Whisky', 'Wine', 'Bitters'
]
DRINK_ID_PATTERNS = ['Drink', 'Beverage', 'Juice', 'Coffee', 'Tea', 'Pop', 'Soda', 'Cola', 'Milk', 'Water']
MEAT_ID_PATTERNS = ['Meat', 'Fish', 'Chicken', 'Pork', 'Beef', 'Bacon', 'Sausage', 'Rashers']
FRUIT_ID_PATTERNS = ['Fruit', 'Apple', 'Banana', 'Orange', 'Berry', 'Avocado', 'Peach', 'Pear', 'Lemon', 'Lime']
VEGETABLE_ID_PATTERNS = ['Vegetable', 'Carrot', 'Potato', 'Lettuce', 'Tomato', 'Broccoli', 'Cabbage', 'Pepper', 'Leek', 'Onion']
SPICE_ID_PATTERNS = ['Spice', 'Condiment', 'Seasoning', 'Salt', 'Pepper', 'Basil', 'Thyme', 'Oregano', 'Rosemary', 'Sage', 'Bouillon']
GRAIN_ID_PATTERNS = ['Bread', 'Grain', 'Cereal', 'Rice', 'Pasta', 'Noodle', 'Oat', 'Flour', 'Bun', 'Barley', 'Corn', 'Bagel', 'Baguette']
SWEET_ID_PATTERNS = ['Candy', 'Chocolate', 'Cookie', 'Cake', 'Cupcake', 'Dessert', 'Sweet', 'Donut', 'HardCandies', 'Muffin', 'Gummy']
NON_PERISHABLE_ID_PATTERNS = ['Canned', 'Tin', 'Tinned', 'Jar', 'Pack', 'Package', 'Dried', 'Dehydrated', 'Powdered']
COOKING_ID_PATTERNS = ['Dough', 'Batter', 'Mix', 'Soup', 'Stew', 'Chili', 'Bouillon', 'Sauce']
FOOD_TYPE_MARKERS = {'eat', 'eatsmall', 'food'}
COOKING_PROPERTIES = (
    'IsCookable', 'DangerousUncooked', 'ReplaceOnCooked', 'ReplaceOnRotten',
    'BadInMicrowave', 'CantBeFrozen'
)

# Thresholds
MIN_FOOD_HUNGER = 1
MIN_DRINK_THIRST = 1
PERISHABLE_FRESH_DAYS = 30


def _get_property_value(props, key):
    match = re.search(rf"{key}\s*=\s*([^,\n]+)", props, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _extract_script_tags(props):
    """Extract script tags from the raw `Tags = ...` property as lowercase tokens."""
    raw = _get_property_value(props, 'Tags')
    if not raw:
        return []

    tokens = re.split(r'[;|]', raw)
    return [token.strip().lower() for token in tokens if token.strip()]


def _item_tokens(item_id):
    """Split IDs like CannedMilkOpen or Water_RationCan into lowercase tokens."""
    normalized = re.sub(r'[^A-Za-z0-9]+', ' ', item_id)
    spaced = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', normalized)
    return [token.lower() for token in spaced.split() if token]


def _id_matches_tokens(item_id, patterns):
    """Match patterns against tokenized item IDs to avoid accidental substrings."""
    tokens = _item_tokens(item_id)
    token_set = set(tokens)
    for pattern in patterns:
        pattern_lower = pattern.lower()
        if pattern_lower in token_set:
            return True
        for token in tokens:
            if token.startswith(pattern_lower) and token[len(pattern_lower):].isdigit():
                return True
        
    return False


def _is_food_type(type_value):
    type_value = type_value.lower()
    return any(marker in type_value for marker in FOOD_TYPE_MARKERS)


def _is_can_item(item_id):
    item = item_id.lower()
    if item.endswith('can'):
        return True
    return any(token in item for token in ('canned', 'tinned', '_can', 'can_', 'rationcan'))


def _is_drink_like_item(item_id, analyzer):
    return (
        _id_matches_tokens(item_id, DRINK_ID_PATTERNS)
        or _id_matches_tokens(item_id, ALCOHOL_ID_PATTERNS)
        or analyzer.has_property('AlcoholPower')
        or analyzer.has_property('Alcoholic')
    )


def _has_cooking_metadata(analyzer):
    return any(analyzer.has_property(prop) for prop in COOKING_PROPERTIES)


def _has_consumption_metadata(analyzer):
    return (
        analyzer.has_property('CustomEatSound')
        or analyzer.has_property('HerbalistType')
        or analyzer.get_stat('UnhappyChange') != 0
        or analyzer.get_stat('BoredomChange') != 0
        or analyzer.get_stat('StressChange') != 0
        or analyzer.get_stat('FatigueChange') != 0
        or analyzer.get_stat('EnduranceChange') != 0
        or analyzer.get_stat('FluReduction') != 0
        or analyzer.get_stat('ReduceFoodSickness') != 0
    )


def _is_beverage_bundle(item_id, props, analyzer):
    item_lower = item_id.lower()
    recipe_value = _get_property_value(props, 'DoubleClickRecipe').lower()
    opening_recipe = _get_property_value(props, 'OpeningRecipe').lower()

    looks_like_beverage = (
        _id_matches_tokens(item_id, DRINK_ID_PATTERNS)
        or _id_matches_tokens(item_id, ALCOHOL_ID_PATTERNS)
    )
    opens_beverage_pack = 'openpackofbeer' in recipe_value or 'openpackof' in recipe_value
    opens_single_beverage = opening_recipe.startswith('openbottleof') or opening_recipe.startswith('opencanof')

    return (
        looks_like_beverage and (
            opens_beverage_pack or
            opens_single_beverage or
            ('pack' in item_lower and analyzer.has_property('DoubleClickRecipe'))
        )
    )


def _is_perishable(days_fresh, days_rotten):
    return days_fresh > 0 and (days_fresh < PERISHABLE_FRESH_DAYS or days_rotten > 0)


def _classify_food(item_id, analyzer, is_drink, is_perishable, has_animal_head_tag=False, is_beverage_bundle=False):
    if is_drink:
        if (
            analyzer.has_property('AlcoholPower')
            or analyzer.has_property('Alcoholic')
            or _id_matches_tokens(item_id, ALCOHOL_ID_PATTERNS)
            or (is_beverage_bundle and _id_matches_tokens(item_id, ALCOHOL_ID_PATTERNS))
        ):
            return 'Drink', 'Alcohol'
        return 'Drink', 'NonAlcoholic'

    if _is_can_item(item_id) or analyzer.has_property('CannedFood'):
        return 'NonPerishable', 'Canned'

    if analyzer.has_property('Spice') or id_matches_pattern(item_id, SPICE_ID_PATTERNS):
        return 'Cooking', 'Spice'

    if has_animal_head_tag:
        return ('Perishable' if is_perishable else 'NonPerishable'), 'Meat'

    if id_matches_pattern(item_id, MEAT_ID_PATTERNS):
        if 'fish' in item_id.lower():
            return ('Perishable' if is_perishable else 'NonPerishable'), 'Fish'
        return ('Perishable' if is_perishable else 'NonPerishable'), 'Meat'

    if id_matches_pattern(item_id, FRUIT_ID_PATTERNS):
        return ('Perishable' if is_perishable else 'NonPerishable'), 'Fruit'

    if id_matches_pattern(item_id, VEGETABLE_ID_PATTERNS):
        return ('Perishable' if is_perishable else 'NonPerishable'), 'Vegetable'

    if id_matches_pattern(item_id, SWEET_ID_PATTERNS):
        return ('Perishable' if is_perishable else 'NonPerishable'), 'Sweets'

    if id_matches_pattern(item_id, GRAIN_ID_PATTERNS):
        return ('Perishable' if is_perishable else 'NonPerishable'), 'Grain'

    if id_matches_pattern(item_id, NON_PERISHABLE_ID_PATTERNS):
        return 'NonPerishable', 'Canned'

    if _has_cooking_metadata(analyzer) or id_matches_pattern(item_id, COOKING_ID_PATTERNS):
        return 'Cooking', 'Ingredient'

    return ('Perishable' if is_perishable else 'NonPerishable'), 'General'


def matches_food_signature(item_id, props):
    """
    Check if item matches food signature.
    
    Food has a mix of:
    - HungerChange or ThirstChange
    - Calories/macros or freshness tracking
    - Food display/type markers
    - Cooking or consumption metadata
    
    Args:
        item_id: Item identifier
        props: Properties string
    
    Returns:
        tuple: (matches: bool, confidence: float, details: dict)
    """
    analyzer = PropertyAnalyzer(props)
    first_display_category = _get_property_value(props, 'DisplayCategory').lower()

    # First-aid consumables can expose food-like metadata but should be
    # handled by the dedicated medical signature.
    if first_display_category in {'firstaid', 'firstaidweapon', 'bandage'}:
        return False, 0.0, {}
    if analyzer.has_property('Medical', 'true') or analyzer.has_property('Medical'):
        return False, 0.0, {}
    
    hunger_change = analyzer.get_stat('HungerChange')
    thirst_change = analyzer.get_stat('ThirstChange')
    calories = analyzer.get_stat('Calories')

    carbs = analyzer.get_stat('Carbohydrates')
    lipids = analyzer.get_stat('Lipids')
    proteins = analyzer.get_stat('Proteins')
    days_fresh = analyzer.get_stat('DaysFresh')
    days_rotten = analyzer.get_stat('DaysTotallyRotten')
    type_value = _get_property_value(props, 'Type')
    display_category = _get_property_value(props, 'DisplayCategory')
    script_tags = _extract_script_tags(props)

    has_nutrition = any(value > 0 for value in (calories, carbs, lipids, proteins))
    has_freshness = days_fresh > 0 or days_rotten > 0
    has_cooking_metadata = _has_cooking_metadata(analyzer)
    has_consumption_metadata = _has_consumption_metadata(analyzer)
    is_display_food = display_category.lower() == 'food'
    is_display_animal_part = display_category.lower() == 'animalpart'
    is_type_food = _is_food_type(type_value)
    is_can_item = _is_can_item(item_id)
    is_drink_like_item = _is_drink_like_item(item_id, analyzer)
    is_alcoholic = analyzer.has_property('AlcoholPower') or analyzer.has_property('Alcoholic')
    is_beverage_bundle = _is_beverage_bundle(item_id, props, analyzer)
    has_food_script_tag = 'base:food' in script_tags
    has_animal_head_tag = 'base:animalhead' in script_tags
    has_animal_skull_tag = 'base:animalskull' in script_tags
    is_wall_or_moveable = (
        item_id.lower().startswith('mov_')
        or '_wall' in item_id.lower()
        or 'base:moveable' in script_tags
    )

    # Decorative/moveable skulls should never become food from weak context.
    if is_wall_or_moveable and not (hunger_change != 0 or thirst_change != 0 or has_nutrition or has_freshness):
        return False, 0.0, {}

    is_food = hunger_change != 0 or has_nutrition or has_freshness or has_cooking_metadata
    non_food_type = not is_type_food
    is_drink = (
        (is_drink_like_item and (non_food_type or thirst_change < 0))
        or (is_alcoholic and (is_display_food or is_type_food or is_drink_like_item))
        or is_beverage_bundle
        or (thirst_change < 0 and hunger_change == 0 and calories == 0 and (is_display_food or is_type_food))
    )
    is_food_like_id = id_matches_pattern(item_id, FOOD_ID_PATTERNS)

    has_food_context = (
        hunger_change != 0
        or thirst_change != 0
        or has_food_script_tag
        or (has_animal_head_tag and (has_freshness or is_display_animal_part or has_food_script_tag))
        or (has_animal_skull_tag and (hunger_change != 0 or has_nutrition or has_freshness or has_food_script_tag))
        or (is_food_like_id and is_can_item)
        or is_beverage_bundle
        or (is_display_food and (is_can_item or is_drink_like_item))
        or ((is_display_food or is_type_food) and (has_nutrition or has_freshness or has_cooking_metadata or has_consumption_metadata or is_food_like_id))
        or (has_nutrition and (has_freshness or has_cooking_metadata or is_food_like_id))
        or (has_freshness and is_food_like_id)
    )

    if not has_food_context:
        return False, 0.0, {}

    evidence = []
    is_perishable = _is_perishable(days_fresh, days_rotten)
    food_category, food_subcategory = _classify_food(
        item_id,
        analyzer,
        is_drink,
        is_perishable,
        has_animal_head_tag=has_animal_head_tag,
        is_beverage_bundle=is_beverage_bundle,
    )
    details = {
        'is_food': is_food,
        'is_drink': is_drink,
        'is_perishable': is_perishable,
        'food_category': food_category,
        'food_subcategory': food_subcategory,
        'display_category': display_category,
        'type_value': type_value,
        'script_tags': script_tags,
        'is_beverage_bundle': is_beverage_bundle,
    }

    if is_display_food:
        evidence.append(0.25)

    if is_type_food:
        evidence.append(0.2)

    if is_food_like_id:
        evidence.append(0.15)

    if has_food_script_tag:
        evidence.append(0.2)

    if has_animal_head_tag:
        evidence.append(0.25)

    if has_animal_skull_tag and (hunger_change != 0 or has_nutrition or has_freshness or has_food_script_tag):
        evidence.append(0.1)

    if is_can_item:
        evidence.append(0.2)

    if hunger_change != 0:
        evidence.append(0.2 if abs(hunger_change) >= MIN_FOOD_HUNGER * 5 else 0.1)
        details['hunger_change'] = hunger_change

    if thirst_change != 0:
        evidence.append(0.2 if abs(thirst_change) >= MIN_DRINK_THIRST * 3 else 0.1)
        details['thirst_change'] = thirst_change

    if is_drink:
        evidence.append(0.15)

    if has_nutrition:
        evidence.append(0.15)
        details['calories'] = calories

    if has_freshness:
        evidence.append(0.1)
        details['days_fresh'] = days_fresh
        details['days_rotten'] = days_rotten

    if has_cooking_metadata:
        evidence.append(0.1)

    if has_consumption_metadata:
        evidence.append(0.1)

    if is_beverage_bundle:
        evidence.append(0.25)

    if analyzer.has_property('HerbalistType'):
        details['herbalist_type'] = _get_property_value(props, 'HerbalistType')
        evidence.append(0.1)

    if food_category in {'Drink', 'Cooking'} or food_subcategory != 'General':
        evidence.append(0.1)

    confidence = min(1.0, sum(evidence)) if evidence else 0.0

    matches = confidence >= 0.4

    return matches, confidence, details


def get_food_tags(item_id, props):
    """
    Generate food tags based on signature match.
    
    Args:
        item_id: Item identifier
        props: Properties string
    
    Returns:
        list: Tag list for this food item
    """
    matches, confidence, details = matches_food_signature(item_id, props)
    
    if not matches:
        return []
    
    tags = []

    food_category = details.get('food_category', 'NonPerishable')
    food_subcategory = details.get('food_subcategory', 'General')

    tags.append(f"Food.{food_category}.{food_subcategory}")

    calories = details.get('calories', 0)
    hunger = abs(details.get('hunger_change', 0))

    if hunger > 50 or calories > 1000:
        tags.append("Food.HighNutrition")
    elif hunger > 20 or calories > 400:
        tags.append("Food.MediumNutrition")
    else:
        tags.append("Food.LowNutrition")

    unhappy = analyzer.get_stat('UnhappyChange') if (analyzer := PropertyAnalyzer(props)) else 0
    if unhappy > 0:
        tags.append("Food.LowQuality")
    elif details.get('is_perishable') and details.get('days_fresh', 0) > 60:
        tags.append("Food.HighQuality")

    if food_subcategory == 'Alcohol':
        tags.append("Food.Intoxicating")

    unique_tags = []
    for tag in tags:
        if tag not in unique_tags:
            unique_tags.append(tag)

    return unique_tags
