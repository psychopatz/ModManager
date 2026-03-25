"""
Tools property-based signatures.
Detects tools through usage delta, condition, and ID patterns.
"""
import re

from .helpers import (
    extract_tags_from_props,
    get_display_category,
    id_matches_pattern,
    PropertyAnalyzer,
)


TOOL_ID_PATTERNS = [
    'Tool', 'Hammer', 'Saw', 'Drill', 'Wrench', 'Screwdriver',
    'Shovel', 'Rake', 'Hoe', 'Trowel', 'Pickaxe',
    'Flashlight', 'Rope', 'Lock', 'Key', 'Crowbar'
]

CRAFTING_TOOL_PATTERNS = [
    'Hammer', 'Saw', 'Drill', 'Wrench', 'Screwdriver', 'Welder'
]

FARMING_TOOL_PATTERNS = [
    'Shovel', 'Rake', 'LeafRake', 'Hoe', 'GardenHoe',
    'HandShovel', 'HandFork', 'GardenFork', 'Pitchfork',
    'Pickaxe', 'Scythe', 'HandScythe', 'PrimitiveScythe', 'Sickle'
]

MEDICAL_TOOL_PATTERNS = [
    'Tweezers', 'Forceps', 'Suture', 'Scalpel',
    'Stethoscope', 'TongueDepressor', 'Medical',
]
SURGICAL_TOOL_PATTERNS = ['Scalpel', 'Suture', 'Forceps']
MEDICAL_TOOL_TAGS = {'base:removeglass', 'base:removebullet', 'base:tweezers'}
COOKWARE_TOOL_PATTERNS = [
    'BakingPan', 'BakingTray', 'FryingPan', 'GridlePan', 'GriddlePan',
    'Saucepan', 'CookingPot', 'RoastingPan', 'Kettle',
    'TinOpener', 'CanOpener',
    'BastingBrush', 'BottleOpener', 'CheeseGrater', 'GrillBrush',
    'KitchenTongs', 'Ladle', 'MuffinTray', 'OvenMitt',
    'PizzaCutter', 'SkewersWooden', 'Spatula', 'Strainer', 'Whisk',
    'WoodenSpoon',
]
COOKWARE_SCRIPT_TAGS = {
    'base:canopener', 'base:mixingutensil', 'base:grater', 'base:bottleopener',
}
COOKWARE_WEAK_SCRIPT_TAGS = {'base:cookable'}
COOKWARE_DISPLAY_CATEGORIES = {'cooking', 'cookingweapon'}
COOKWARE_EXCLUDE_PATTERNS = [
    'BeerCanPack', 'BeerPack', 'BoxOfJars', 'JarLid',
    'EmptyJar', 'JarCrafted', 'Teacup', 'Plate',
    'PlasticFork', 'PlasticKnife', 'PlasticSpoon', 'CocktailUmbrella',
    'Chopsticks',
]
COOKWARE_FOODSAFE_CONTAINER_TAGS = {'base:sealedbeveragecan', 'base:emptycan', 'base:cookablemicrowave'}

MIN_TOOL_CONDITION = 3.0


def _tokenize_identifier(value):
    normalized = re.sub(r'[^A-Za-z0-9]+', ' ', value)
    spaced = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', normalized)
    return [token.lower() for token in spaced.split() if token]


def _token_spans(value):
    tokens = [re.sub(r'\d+$', '', token) for token in _tokenize_identifier(value)]
    tokens = [token for token in tokens if token]
    spans = set()
    for start in range(len(tokens)):
        combined = ''
        for end in range(start, min(len(tokens), start + 3)):
            combined += tokens[end]
            spans.add(combined)
    return spans


def _matches_tool_patterns(item_id, patterns):
    item_spans = _token_spans(item_id)
    for pattern in patterns:
        pattern_key = ''.join(_tokenize_identifier(pattern))
        if pattern_key and pattern_key in item_spans:
            return True
    return False


def matches_tool_signature(item_id, props):
    """
    Check if item matches tool signature.

    Tools have:
    - UseDelta or durability
    - Tool-related ID patterns
    - A dedicated medical-tool branch for clinical and surgical instruments

    Args:
        item_id: Item identifier
        props: Properties string

    Returns:
        tuple: (matches: bool, confidence: float, details: dict)
    """
    analyzer = PropertyAnalyzer(props)
    use_delta = analyzer.get_stat('UseDelta')
    condition_max = analyzer.get_stat('ConditionMax')
    display_category = (get_display_category(props) or '').lower()
    script_tags = {tag.lower() for tag in extract_tags_from_props(props)}
    min_damage = analyzer.get_stat('MinDamage')
    max_damage = analyzer.get_stat('MaxDamage')
    has_cookware_tag = bool(script_tags.intersection(COOKWARE_SCRIPT_TAGS))
    has_weak_cookware_tag = bool(script_tags.intersection(COOKWARE_WEAK_SCRIPT_TAGS))
    is_cookware_id = _matches_tool_patterns(item_id, COOKWARE_TOOL_PATTERNS)
    has_cooking_properties = any(
        analyzer.has_property(prop)
        for prop in ('IsCookable', 'PourType', 'EatType')
    )
    is_normal_item = analyzer.has_property('ItemType', 'base:normal') or analyzer.has_property('Type', 'Normal')
    has_world_model = analyzer.has_property('WorldStaticModel') or analyzer.has_property('StaticModel')
    has_fluid_container = 'component fluidcontainer' in analyzer.props_lower
    is_survival_storage = analyzer.has_property('SurvivalGear', 'true')
    is_cookware_exclusion = id_matches_pattern(item_id, COOKWARE_EXCLUDE_PATTERNS)
    is_foodsafe_container = bool(script_tags.intersection(COOKWARE_FOODSAFE_CONTAINER_TAGS))
    is_food_or_junk_drink_container = (
        display_category in {'food', 'junk'} and
        has_fluid_container and
        (is_foodsafe_container or analyzer.has_property('CustomDrinkSound'))
    )
    is_cooking_normal_tool = (
        display_category == 'cooking' and
        is_normal_item and
        not has_fluid_container and
        not is_survival_storage and
        not is_cookware_exclusion
    )
    cookware_context = (
        has_cookware_tag or
        has_cooking_properties or
        is_cooking_normal_tool or
        (
            display_category in COOKWARE_DISPLAY_CATEGORIES and
            (is_cookware_id or has_weak_cookware_tag)
        )
    )

    if cookware_context and not is_food_or_junk_drink_container:
        evidence = []
        details = {
            'is_drainable': use_delta > 0,
            'condition_max': condition_max,
            'tool_type': 'Cookware',
            'display_category': display_category or None,
            'total_uses': 0,
        }

        if display_category in COOKWARE_DISPLAY_CATEGORIES:
            evidence.append(0.35 if display_category == 'cookingweapon' else 0.3)
        if has_cookware_tag:
            evidence.append(0.35)
        if has_weak_cookware_tag and display_category in COOKWARE_DISPLAY_CATEGORIES:
            evidence.append(0.15)
        if is_cookware_id:
            evidence.append(0.25)
        if has_cooking_properties:
            evidence.append(0.2)
        if is_cooking_normal_tool:
            evidence.append(0.2)
        if has_world_model:
            evidence.append(0.1)
        if condition_max >= 1:
            evidence.append(0.1)
        if use_delta > 0:
            evidence.append(0.1)
            total_uses = int(1.0 / use_delta) if use_delta > 0 else 1
            details['total_uses'] = total_uses
            details['use_delta'] = use_delta

        confidence = min(1.0, sum(evidence)) if evidence else 0.0
        matches = confidence >= 0.45
        return matches, confidence, details

    is_medical_display = display_category in {'firstaid', 'firstaidweapon'}
    is_medical_flag = analyzer.has_property('Medical', 'true') or analyzer.has_property('Medical')
    has_medical_tool_tags = bool(script_tags.intersection(MEDICAL_TOOL_TAGS))
    is_medical_tool_id = _matches_tool_patterns(item_id, MEDICAL_TOOL_PATTERNS)
    is_surgical_tool = (
        display_category == 'firstaidweapon' or
        _matches_tool_patterns(item_id, SURGICAL_TOOL_PATTERNS)
    )

    medical_tool_context = (
        display_category == 'firstaidweapon' or
        has_medical_tool_tags or
        is_medical_tool_id or
        ((is_medical_display or is_medical_flag) and (condition_max >= 1 or min_damage > 0 or max_damage > 0))
    )

    if medical_tool_context:
        evidence = []
        details = {
            'is_drainable': use_delta > 0,
            'condition_max': condition_max,
            'tool_type': 'Medical.Surgical' if is_surgical_tool else 'Medical',
            'display_category': display_category or None,
            'total_uses': 0,
        }

        if is_medical_display:
            evidence.append(0.45 if display_category == 'firstaidweapon' else 0.35)
        if is_medical_flag:
            evidence.append(0.3)
        if has_medical_tool_tags:
            evidence.append(0.35)
        if is_medical_tool_id:
            evidence.append(0.2)
        if condition_max >= 1:
            evidence.append(0.1)
        if min_damage > 0 or max_damage > 0:
            evidence.append(0.2)
            details['min_damage'] = min_damage
            details['max_damage'] = max_damage
        if is_surgical_tool:
            evidence.append(0.3)

        if use_delta > 0:
            total_uses = int(1.0 / use_delta) if use_delta > 0 else 1
            details['total_uses'] = total_uses
            details['use_delta'] = use_delta

        confidence = min(1.0, sum(evidence)) if evidence else 0.0
        matches = confidence >= 0.45
        return matches, confidence, details

    if use_delta == 0 and condition_max < MIN_TOOL_CONDITION:
        return False, 0.0, {}

    evidence = []
    details = {
        'is_drainable': use_delta > 0,
        'condition_max': condition_max,
        'tool_type': 'General',
        'total_uses': 0,
    }

    if use_delta > 0:
        evidence.append(0.25)
        total_uses = int(1.0 / use_delta) if use_delta > 0 else 1
        details['total_uses'] = total_uses
        details['use_delta'] = use_delta

    if condition_max > MIN_TOOL_CONDITION:
        evidence.append(0.25)

    if analyzer.has_property('Type', 'Normal'):
        evidence.append(0.15)

    if _matches_tool_patterns(item_id, TOOL_ID_PATTERNS):
        evidence.append(0.2)

    if _matches_tool_patterns(item_id, CRAFTING_TOOL_PATTERNS):
        details['tool_type'] = 'Crafting'
        evidence.append(0.15)
    elif _matches_tool_patterns(item_id, FARMING_TOOL_PATTERNS):
        details['tool_type'] = 'Farming'
        evidence.append(0.15)
    elif _matches_tool_patterns(item_id, ['Crowbar', 'Lock', 'Key']):
        details['tool_type'] = 'Utility'
        evidence.append(0.1)
    elif _matches_tool_patterns(item_id, ['Flashlight', 'Lens', 'Light']):
        details['tool_type'] = 'Light'
        evidence.append(0.1)

    confidence = min(1.0, sum(evidence)) if evidence else 0.0
    matches = confidence > 0.35

    return matches, confidence, details


def get_tool_tags(item_id, props):
    """
    Generate tool tags based on signature match.

    Args:
        item_id: Item identifier
        props: Properties string

    Returns:
        list: Tag list for this tool
    """
    matches, confidence, details = matches_tool_signature(item_id, props)

    if not matches:
        return []

    tool_type = details.get('tool_type', 'General')
    primary_tag = f"Tool.{tool_type}"
    tags = [primary_tag]

    condition = details.get('condition_max', 0)
    if condition > 50:
        tags.append("Tool.Durable")
    elif 0 < condition < 15:
        tags.append("Tool.Fragile")

    total_uses = details.get('total_uses', 0)
    if total_uses > 100:
        tags.append("Tool.HighUse")
    elif total_uses > 30:
        tags.append("Tool.MediumUse")
    elif total_uses > 0:
        tags.append("Tool.LimitedUse")

    return tags
