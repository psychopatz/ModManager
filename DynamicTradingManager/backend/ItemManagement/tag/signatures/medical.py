"""
Medical property-based signatures.
Detects medical supplies and consumables through first-aid, healing, and
healthcare-specific properties.
"""
import re

from .helpers import (
    extract_tags_from_props,
    get_display_category,
    id_matches_pattern,
    PropertyAnalyzer,
)


MEDICAL_SUPPLY_ID_PATTERNS = [
    'Bandage', 'Bandaid', 'Pills', 'Antibiotics', 'Disinfectant',
    'Cotton', 'Coldpack', 'Cataplasm', 'Comfrey', 'Plantain',
    'Garlic', 'Mallow', 'Ginseng', 'BlackSage', 'AlcoholWipes',
    'AlcoholBandage', 'Splint',
]
DRUG_ID_PATTERNS = [
    'Cigarette', 'Cigar', 'Cigarillo', 'Tobacco',
    'SmokingPipe_Tobacco', 'CanPipe_Tobacco',
]
PILLS_PATTERNS = ['Pills', 'Antibiotics', 'Tablet', 'Capsule']
VITAMIN_PATTERNS = ['Vitamin']
BOTANICAL_PATTERNS = ['Comfrey', 'Plantain', 'Garlic', 'Mallow', 'Ginseng', 'BlackSage', 'Cataplasm']
MEDICAL_SUPPLY_TAGS = {
    'base:consumable', 'base:comfrey', 'base:plantain',
    'base:wildgarlic', 'base:commonmallow', 'base:herbaltea',
}
DRUG_TAGS = {'base:smokable', 'base:chewingtobacco', 'base:tobacco'}
MEDICAL_TOOL_PATTERNS = ['Tweezers', 'Forceps', 'Suture', 'Scalpel', 'Stethoscope', 'TongueDepressor']


def matches_medical_signature(item_id, props):
    """
    Check if item matches the medical supply signature.

    Medical supplies have:
    - First-aid display categories or explicit medical flags
    - Health-treatment properties like bandaging or infection reduction
    - Pill/herbal/healthcare item patterns

    Args:
        item_id: Item identifier
        props: Properties string

    Returns:
        tuple: (matches: bool, confidence: float, details: dict)
    """
    analyzer = PropertyAnalyzer(props)

    display_category = (get_display_category(props) or '').lower()
    script_tags = {tag.lower() for tag in extract_tags_from_props(props)}
    tags_match = re.search(r"Tags\s*=\s*([^\n]+)", props, re.IGNORECASE)
    raw_tags = tags_match.group(1).lower() if tags_match else ''
    item_lower = item_id.lower()
    bandage_power = analyzer.get_stat('BandagePower')
    reduce_infection = analyzer.get_stat('ReduceInfectionPower')
    alcohol_power = analyzer.get_stat('AlcoholPower')
    on_eat = analyzer.has_property('OnEat', 'RecipeCodeOnEat.consumeNicotine')
    custom_context_smoke = analyzer.has_property('CustomContextMenu', 'Smoke')
    custom_context_chew = analyzer.has_property('CustomContextMenu', 'Chew')
    eat_type = (
        analyzer.has_property('EatType', 'Cigarettes') or
        analyzer.has_property('EatType', 'Pipe')
    )
    has_smoking_gear_requirement = analyzer.has_property('RequireInHandOrInventory')
    has_drug_tags = bool(script_tags.intersection(DRUG_TAGS)) or any(tag in raw_tags for tag in DRUG_TAGS)
    is_drug_id = id_matches_pattern(item_id, DRUG_ID_PATTERNS)
    has_tobacco_world_model = analyzer.has_property('WorldStaticModel', 'TobaccoLeaf') or analyzer.has_property('WorldStaticModel', 'TobaccoLeafDried')
    is_tobacco_material = (
        'tobacco' in item_lower and
        display_category in {'junk', 'tool'} and
        not item_lower.endswith('seed') and
        'bagseed' not in item_lower and
        not analyzer.has_property('ItemType', 'base:literature') and
        not analyzer.has_property('ItemType', 'base:container') and
        (has_drug_tags or has_tobacco_world_model or analyzer.has_property('CantEat', 'true'))
    )
    is_cigarette_bundle = (
        display_category == 'junk' and
        (
            analyzer.has_property('DoubleClickRecipe', 'UnpackCigaretteCarton') or
            analyzer.has_property('DoubleClickRecipe', 'OpenPackOfCigarettes')
        )
    )
    is_nicotine_drug = (
        not analyzer.has_property('Alcoholic', 'true') and
        alcohol_power == 0 and
        not analyzer.has_property('ItemType', 'base:container') and
        not analyzer.has_property('CustomContextMenu', 'Eat') and
        'base:rollingpaper' not in script_tags and
        (
            on_eat or
            custom_context_smoke or
            custom_context_chew or
            eat_type or
            has_drug_tags or
            is_tobacco_material or
            (is_drug_id and display_category in {'junk', 'tool'} and (on_eat or custom_context_smoke or custom_context_chew or has_drug_tags or is_cigarette_bundle))
        )
    )

    is_first_aid = display_category in {'firstaid', 'bandage'}
    is_medical_flag = analyzer.has_property('Medical', 'true') or analyzer.has_property('Medical')
    is_container = analyzer.has_property('ItemType', 'base:container') or item_lower.startswith('firstaidkit')
    is_clothing = analyzer.has_property('BodyLocation')
    is_medical_tool = (
        display_category == 'firstaidweapon' or
        id_matches_pattern(item_id, MEDICAL_TOOL_PATTERNS) or
        'base:removeglass' in script_tags or
        'base:removebullet' in script_tags or
        'base:tweezers' in script_tags
    )

    if is_container or is_clothing or is_medical_tool or item_lower.startswith('bandage_'):
        return False, 0.0, {}

    if not (is_first_aid or is_medical_flag or id_matches_pattern(item_id, MEDICAL_SUPPLY_ID_PATTERNS) or is_nicotine_drug):
        return False, 0.0, {}

    evidence = []
    details = {
        'medical_type': 'General',
        'display_category': display_category or None,
        'is_first_aid': is_first_aid,
        'is_medical_flag': is_medical_flag,
        'is_consumable': False,
    }

    if is_first_aid:
        evidence.append(0.35)

    if is_medical_flag:
        evidence.append(0.35)

    if id_matches_pattern(item_id, MEDICAL_SUPPLY_ID_PATTERNS):
        evidence.append(0.2)

    if is_nicotine_drug:
        evidence.append(0.45)
        details['nicotine_drug'] = True

    if on_eat:
        evidence.append(0.35)
    if custom_context_smoke or custom_context_chew:
        evidence.append(0.2)
    if eat_type:
        evidence.append(0.15)
    if has_drug_tags:
        evidence.append(0.2)
    if has_smoking_gear_requirement and (on_eat or custom_context_smoke):
        evidence.append(0.15)

    if bandage_power > 0:
        evidence.append(0.25)
        details['bandage_power'] = bandage_power

    if analyzer.has_property('CanBandage', 'true'):
        evidence.append(0.3)
        details['can_bandage'] = True

    if reduce_infection > 0:
        evidence.append(0.3)
        details['reduce_infection_power'] = reduce_infection

    if alcohol_power > 0:
        evidence.append(0.25)
        details['alcohol_power'] = alcohol_power

    if analyzer.has_property('Alcoholic', 'true') and is_first_aid:
        evidence.append(0.2)

    if analyzer.has_property('ItemType', 'base:drainable') and (is_first_aid or is_medical_flag):
        evidence.append(0.2)
        details['is_consumable'] = True

    if analyzer.has_property('ItemType', 'base:food') and (is_first_aid or is_medical_flag):
        evidence.append(0.2)
        details['is_consumable'] = True

    if analyzer.has_property('CantEat', 'true') and is_first_aid:
        evidence.append(0.15)

    if script_tags.intersection(MEDICAL_SUPPLY_TAGS):
        evidence.append(0.1)

    if is_nicotine_drug:
        details['medical_type'] = 'General.Drug'
        if analyzer.has_property('ItemType', 'base:drainable') or analyzer.has_property('ItemType', 'base:food'):
            details['is_consumable'] = True
    elif id_matches_pattern(item_id, VITAMIN_PATTERNS):
        details['medical_type'] = 'General.Vitamin'
        details['is_consumable'] = True
    elif (
        id_matches_pattern(item_id, PILLS_PATTERNS) or
        (
            analyzer.has_property('ItemType', 'base:drainable') and
            (is_first_aid or is_medical_flag)
        )
    ):
        details['medical_type'] = 'General.Pills'
        details['is_consumable'] = True
    elif (
        id_matches_pattern(item_id, BOTANICAL_PATTERNS) or
        script_tags.intersection({'base:comfrey', 'base:plantain', 'base:wildgarlic', 'base:commonmallow', 'base:herbaltea'}) or
        analyzer.has_property('FoodType', 'Herb') or
        (analyzer.has_property('CantEat', 'true') and is_first_aid)
    ):
        details['medical_type'] = 'Healthcare.Botanical'
    elif (
        analyzer.has_property('CanBandage', 'true') or
        bandage_power > 0 or
        reduce_infection > 0 or
        alcohol_power > 0 or
        id_matches_pattern(item_id, ['Bandage', 'Bandaid', 'Disinfectant', 'Cotton', 'Coldpack', 'Splint'])
    ):
        details['medical_type'] = 'Healthcare'

    confidence = min(1.0, sum(evidence)) if evidence else 0.0
    matches = confidence >= 0.45

    return matches, confidence, details


def get_medical_tags(item_id, props):
    """
    Generate medical tags based on signature match.

    Args:
        item_id: Item identifier
        props: Properties string

    Returns:
        list: Tag list for this medical item
    """
    matches, confidence, details = matches_medical_signature(item_id, props)

    if not matches:
        return []

    med_type = details.get('medical_type', 'General')
    primary_tag = f"Medical.{med_type}"
    tags = [primary_tag]

    if details.get('is_consumable') and 'Medical.Consumable' not in tags:
        tags.append('Medical.Consumable')

    return tags
