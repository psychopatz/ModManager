"""
Container property-based signatures.
Separates carry bags, wearable storage, liquid vessels, stash containers,
and utility organizers.
"""
from .helpers import (
    extract_tags_from_props,
    get_body_location,
    get_display_category,
    id_matches_pattern,
    PropertyAnalyzer,
)


BACKPACK_ID_PATTERNS = [
    'Backpack', 'Rucksack', 'HikingBag', 'Schoolbag',
    'Knapsack', 'GolfBag',
]
DUFFEL_ID_PATTERNS = [
    'Duffel', 'ToolBag', 'WeaponBag', 'MedicalBag',
    'MoneyBag', 'ShotgunBag', 'WorkerBag',
]
SATCHEL_ID_PATTERNS = ['Satchel']
HANDBAG_ID_PATTERNS = ['Purse', 'Handbag']
COOLER_ID_PATTERNS = ['Cooler']
SACK_ID_PATTERNS = ['Sack', 'Sandbag', 'WheatSack', 'SeedSack']
BAG_ID_PATTERNS = [
    'Bag_', 'Purse', 'Tote', 'Plasticbag', 'Garbagebag', 'Lunchbag',
    'Briefcase', 'Satchel', 'Handbag', 'GroceryBag', 'Sack', 'Sandbag', 'Cooler',
]
LIQUID_WEARABLE_BODY_LOCATIONS = {'base:satchel', 'base:back'}
WEARABLE_FANNY_LOCATIONS = {'base:fannypackfront', 'base:fannypackback'}
WEARABLE_RIG_LOCATIONS = {'base:webbing'}
WEARABLE_BANDOLIER_LOCATIONS = {'base:ammostrap'}
WEARABLE_HOLSTER_LOCATIONS = {'base:shoulderholster', 'base:ankleholster'}
LIQUID_BUCKET_PATTERNS = ['Bucket', 'Pail', 'WaterDish']
LIQUID_JAR_PATTERNS = ['Jar']
LIQUID_BOTTLE_PATTERNS = ['Bottle', 'Flask', 'Canteen', 'Wineskin', 'WaterBag']
LIQUID_CUP_PATTERNS = ['Mug', 'Cup', 'Glass', 'Goblet', 'Tumbler', 'Bowl']
LIQUID_CAN_PATTERNS = ['Can']
STASH_CASE_PATTERNS = ['Lunchbox', 'CookieJar', 'Case', 'Box', 'Tin', 'Cache', 'Parcel', 'Present', 'Album']
COOKWARE_LIQUID_EXCLUDES = ['Saucepan', 'CookingPot', 'Pot', 'Kettle']

LOW_CAPACITY_THRESHOLD = 3
MEDIUM_CAPACITY_THRESHOLD = 10
HIGH_CAPACITY_THRESHOLD = 20


def _classify_capacity_band(capacity):
    if capacity >= HIGH_CAPACITY_THRESHOLD:
        return 'High'
    if capacity >= MEDIUM_CAPACITY_THRESHOLD:
        return 'Medium'
    if capacity > LOW_CAPACITY_THRESHOLD:
        return 'Low'
    return 'Tiny'


def _get_property_value(props, key):
    import re
    match = re.search(rf"{key}\s*=\s*([^,\n]+)", props, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def matches_container_signature(item_id, props):
    """
    Check whether an item belongs to the container taxonomy.
    """
    analyzer = PropertyAnalyzer(props)
    capacity = analyzer.get_stat('Capacity')
    if capacity <= 0:
        return False, 0.0, {}

    display_category = (get_display_category(props) or '').lower()
    body_location = (get_body_location(props) or '').lower()
    script_tags = {tag.lower() for tag in extract_tags_from_props(props)}
    item_lower = item_id.lower()
    container_name = _get_property_value(props, 'ContainerName').lower()

    has_fluid_container = 'component fluidcontainer' in analyzer.props_lower
    is_container_type = analyzer.has_property('ItemType', 'base:container')
    is_clothing_type = analyzer.has_property('ItemType', 'base:clothing') or analyzer.has_property('ItemType', 'base:alarmclockclothing')
    weight_reduction = analyzer.get_stat('WeightReduction')
    has_container_io = any(
        analyzer.has_property(prop)
        for prop in (
            'CloseSound', 'OpenSound', 'PutInSound', 'ReplaceInPrimaryHand',
            'ReplaceInSecondHand', 'CanBeEquipped', 'AcceptItemFunction',
        )
    )
    can_be_equipped = analyzer.has_property('CanBeEquipped')
    is_hollow_book = 'base:hollowbook' in script_tags or 'hollowbook' in item_lower
    is_keyring = 'base:keyring' in script_tags or analyzer.has_property('AcceptItemFunction', 'AcceptItemFunction.KeyRing')
    is_ammo_case = 'base:ammocase' in script_tags
    is_cookware_liquid = (
        has_fluid_container and
        display_category in {'cooking', 'cookingweapon'} and
        id_matches_pattern(item_id, COOKWARE_LIQUID_EXCLUDES)
    )

    if is_cookware_liquid:
        return False, 0.0, {}

    if not (has_fluid_container or is_container_type or is_clothing_type or has_container_io):
        return False, 0.0, {}

    if has_fluid_container:
        if body_location in LIQUID_WEARABLE_BODY_LOCATIONS or (can_be_equipped and (is_clothing_type or body_location)):
            container_type = 'Liquid.Wearable'
        elif id_matches_pattern(item_id, LIQUID_BUCKET_PATTERNS) or 'base:bucket' in script_tags:
            container_type = 'Liquid.Bucket'
        elif id_matches_pattern(item_id, LIQUID_JAR_PATTERNS) or 'base:jar' in script_tags:
            container_type = 'Liquid.Jar'
        elif id_matches_pattern(item_id, LIQUID_CAN_PATTERNS) or 'base:emptycan' in analyzer.props_lower or 'can' in container_name:
            container_type = 'Liquid.Can'
        elif id_matches_pattern(item_id, LIQUID_BOTTLE_PATTERNS) or 'bottle' in container_name:
            container_type = 'Liquid.Bottle'
        elif id_matches_pattern(item_id, LIQUID_CUP_PATTERNS) or any(token in container_name for token in ('glass', 'mug', 'cup', 'bowl')):
            container_type = 'Liquid.Cup'
        else:
            container_type = 'Liquid.General'
    elif is_keyring:
        container_type = 'Utility.KeyRing'
    elif is_hollow_book:
        container_type = 'Stash.Book'
    elif body_location in WEARABLE_FANNY_LOCATIONS:
        container_type = 'Bag.Fanny'
    elif body_location in WEARABLE_RIG_LOCATIONS:
        container_type = 'Bag.Rig'
    elif body_location in WEARABLE_BANDOLIER_LOCATIONS or is_ammo_case:
        container_type = 'Bag.Bandolier'
    elif body_location in WEARABLE_HOLSTER_LOCATIONS:
        container_type = 'Bag.Holster'
    elif id_matches_pattern(item_id, DUFFEL_ID_PATTERNS):
        container_type = 'Bag.Duffel'
    elif id_matches_pattern(item_id, SATCHEL_ID_PATTERNS):
        container_type = 'Bag.Satchel'
    elif id_matches_pattern(item_id, HANDBAG_ID_PATTERNS):
        container_type = 'Bag.Handbag'
    elif id_matches_pattern(item_id, COOLER_ID_PATTERNS):
        container_type = 'Bag.Cooler'
    elif id_matches_pattern(item_id, SACK_ID_PATTERNS):
        container_type = 'Bag.Sack'
    elif analyzer.has_property('CanBeEquipped', 'base:back') or body_location == 'base:back' or id_matches_pattern(item_id, BACKPACK_ID_PATTERNS):
        container_type = 'Bag.Backpack'
    elif display_category == 'bag' or id_matches_pattern(item_id, BAG_ID_PATTERNS):
        container_type = 'Bag.General'
    elif id_matches_pattern(item_id, STASH_CASE_PATTERNS) or (is_container_type and capacity <= 4 and not body_location and not can_be_equipped):
        container_type = 'Stash.Case'
    elif is_container_type:
        container_type = 'General'
    else:
        return False, 0.0, {}

    evidence = []
    details = {
        'container_type': container_type,
        'capacity': capacity,
        'capacity_band': _classify_capacity_band(capacity),
        'weight_reduction': weight_reduction,
        'display_category': display_category or None,
        'body_location': body_location or None,
        'is_liquid': has_fluid_container,
        'is_wearable': bool(body_location or can_be_equipped),
    }

    evidence.append(0.3)
    if has_fluid_container:
        evidence.append(0.3)
    if is_container_type:
        evidence.append(0.25)
    if is_clothing_type and has_fluid_container:
        evidence.append(0.15)
    if has_container_io:
        evidence.append(0.15)
    if body_location or can_be_equipped:
        evidence.append(0.1)
    if weight_reduction > 0:
        evidence.append(0.1)
    if container_type != 'General':
        evidence.append(0.15)

    confidence = min(1.0, sum(evidence)) if evidence else 0.0
    return confidence >= 0.45, confidence, details


def get_container_tags(item_id, props):
    """
    Generate container tags based on the resolved subtype.
    """
    matches, _confidence, details = matches_container_signature(item_id, props)
    if not matches:
        return []

    primary_tag = f"Container.{details.get('container_type', 'General')}"
    tags = [primary_tag]

    capacity_band = details.get('capacity_band', 'Low')
    tags.append(f"Container.Capacity.{capacity_band}")

    weight_reduction = details.get('weight_reduction', 0)
    if weight_reduction >= 80:
        tags.append('Container.WeightReduction.High')
    elif weight_reduction >= 50:
        tags.append('Container.WeightReduction.Medium')
    elif weight_reduction > 0:
        tags.append('Container.WeightReduction.Low')

    if details.get('is_liquid'):
        tags.append('Container.Liquid')
    if details.get('is_wearable'):
        tags.append('Container.Wearable')

    unique_tags = []
    for tag in tags:
        if tag not in unique_tags:
            unique_tags.append(tag)
    return unique_tags
