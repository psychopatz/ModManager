"""
Fishing property-based signatures.
Routes fishing tackle, bait, and fishing weapons into dedicated Tool/Resource tags.
"""
import re

from .helpers import id_matches_pattern, extract_tags_from_props, get_display_category, PropertyAnalyzer


FISHING_DISPLAY_CATEGORIES = {'fishing', 'fishingweapon'}
FISHING_RESOURCE_TAGS = {'base:fishinghook', 'base:fishingline', 'base:fishingnet'}
FISHING_TOOL_TAGS = {'base:fishingrod'}

FISHING_TOOL_ID_PATTERNS = [
    'FishingRod',
    'Gaffhook',
]

FISHING_RESOURCE_ID_PATTERNS = [
    'FishingLine',
    'FishingHook',
    'FishingNet',
    'Bobber',
    'Lure',
    'FishingTrash',
]

BAIT_RESOURCE_ID_PATTERNS = [
    'Bait',
    'Chum',
    'Worm',
    'Cricket',
    'Grasshopper',
    'Maggot',
    'Caterpillar',
    'Leech',
    'Tadpole',
    'Slug',
    'Snail',
    'Termite',
    'Centipede',
    'Cockroach',
    'Pillbug',
    'SawflyLarva',
    'Millipede',
    'FishGuts',
]

RESOURCE_TOOLTIP_MARKERS = {
    'Tooltip_FishingTackle',
    'Tooltip_BrokenRod',
    'Bobber',
}


def _get_property_value(props, key):
    match = re.search(rf"{key}\s*=\s*([^,\n]+)", props, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _get_item_type(props):
    for key in ('ItemType', 'Type'):
        value = _get_property_value(props, key)
        if value:
            return value.lower()
    return ''


def _get_script_tags(props):
    return {tag.lower() for tag in extract_tags_from_props(props)}


def _has_fishing_oncreate(props):
    return bool(re.search(r"OnCreate\s*=\s*Fishing\.", props, re.IGNORECASE))


def _is_food_like(analyzer):
    return any([
        analyzer.get_stat('HungerChange') != 0,
        analyzer.get_stat('ThirstChange') != 0,
        analyzer.get_stat('Calories') > 0,
        analyzer.get_stat('Carbohydrates') > 0,
        analyzer.get_stat('Lipids') > 0,
        analyzer.get_stat('Proteins') > 0,
        analyzer.get_stat('DaysFresh') > 0,
        analyzer.get_stat('DaysTotallyRotten') > 0,
        analyzer.has_property('IsCookable'),
    ])


def _is_fishing_tool(item_id, item_type, display_category, script_tags, props):
    if display_category == 'fishingweapon':
        return True
    if script_tags & FISHING_TOOL_TAGS:
        return True
    if _has_fishing_oncreate(props) and 'fishingrod' in item_id.lower():
        return True
    if 'weapon' in item_type and id_matches_pattern(item_id, FISHING_TOOL_ID_PATTERNS):
        return True
    return False


def _is_bait_resource(item_id, display_category, analyzer, props):
    if id_matches_pattern(item_id, BAIT_RESOURCE_ID_PATTERNS):
        return True
    if display_category == 'fishing' and analyzer.has_property('FishingLure'):
        return True
    if _has_fishing_oncreate(props) and 'chum' in item_id.lower():
        return True
    return False


def _is_fishing_resource(item_id, item_type, display_category, script_tags, analyzer, props):
    if script_tags & FISHING_RESOURCE_TAGS:
        return True
    if display_category == 'fishing' and item_type not in {'base:container', 'base:clothing', 'base:literature'}:
        return True
    if analyzer.has_property('FishingLure') and (
        display_category == 'fishing' or _is_bait_resource(item_id, display_category, analyzer, props)
    ):
        return True
    if id_matches_pattern(item_id, FISHING_RESOURCE_ID_PATTERNS):
        return True
    return False


def matches_fishing_signature(item_id, props):
    """
    Detect fishing-specific gear before the generic Food/Weapon/Tool/Resource flows.
    """
    analyzer = PropertyAnalyzer(props)
    display_category = (get_display_category(props) or '').lower()
    item_type = _get_item_type(props)
    script_tags = _get_script_tags(props)

    if display_category not in FISHING_DISPLAY_CATEGORIES and not _has_fishing_oncreate(props):
        if not (script_tags & (FISHING_RESOURCE_TAGS | FISHING_TOOL_TAGS)):
            if not analyzer.has_property('FishingLure'):
                return False, 0.0, {}

    is_tool = _is_fishing_tool(item_id, item_type, display_category, script_tags, props)
    is_resource = _is_fishing_resource(item_id, item_type, display_category, script_tags, analyzer, props)
    is_bait_resource = _is_bait_resource(item_id, display_category, analyzer, props)

    if not is_tool and not is_resource:
        return False, 0.0, {}

    evidence = []
    if display_category in FISHING_DISPLAY_CATEGORIES:
        evidence.append(0.35)
    if is_tool:
        evidence.append(0.35)
    if is_bait_resource:
        evidence.append(0.7)
    if script_tags & (FISHING_RESOURCE_TAGS | FISHING_TOOL_TAGS):
        evidence.append(0.3)
    if _has_fishing_oncreate(props):
        evidence.append(0.25)
    if analyzer.has_property('FishingLure'):
        evidence.append(0.15)
    if id_matches_pattern(item_id, FISHING_TOOL_ID_PATTERNS + FISHING_RESOURCE_ID_PATTERNS + BAIT_RESOURCE_ID_PATTERNS):
        evidence.append(0.15)
    if _get_property_value(props, 'Tooltip') in RESOURCE_TOOLTIP_MARKERS:
        evidence.append(0.1)

    fishing_type = 'Tool' if is_tool else 'Resource'
    details = {
        'fishing_type': fishing_type,
        'display_category': display_category,
        'item_type': item_type,
        'script_tags': sorted(script_tags),
        'is_bait_resource': is_bait_resource,
        'food_like': _is_food_like(analyzer),
    }

    confidence = min(1.0, sum(evidence)) if evidence else 0.0
    return confidence >= 0.4, confidence, details


def get_fishing_tags(item_id, props):
    matches, _, details = matches_fishing_signature(item_id, props)
    if not matches:
        return []

    fishing_type = details.get('fishing_type', 'Resource')
    if fishing_type == 'Tool':
        return ['Tool.Fishing']
    return ['Resource.Fishing']
