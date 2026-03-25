"""
Clothing property-based signatures.
Resolves apparel, accessories, jewelry, and explicit armor separately.
"""
import re

from .helpers import get_display_category, id_matches_pattern, PropertyAnalyzer


EXCLUDED_BODY_LOCATIONS = {
    'base:zeddmg', 'base:wound', 'base:bandage',
}
COSMETIC_BODY_LOCATIONS = {
    'base:makeup_fullface', 'base:makeup_eyes', 'base:makeup_eyesshadow', 'base:makeup_lips',
}
TEXTURE_ONLY_LOCATIONS = set()

HEAD_LOCATIONS = {'base:hat', 'base:fullhat', 'base:jackethat', 'base:sweaterhat', 'base:fullsuithead'}
FACE_LOCATIONS = {'base:mask', 'base:maskeyes', 'base:maskfull', 'base:scba', 'base:scbanotank'}
EYE_LOCATIONS = {'base:eyes', 'base:lefteye', 'base:righteye'}
HAND_LOCATIONS = {'base:hands', 'base:handsleft', 'base:handsright'}
FOOT_LOCATIONS = {'base:shoes', 'base:socks', 'base:gaiter_left', 'base:gaiter_right'}
TOP_LOCATIONS = {'base:tshirt', 'base:shirt', 'base:shortsleeveshirt', 'base:tanktop', 'base:sweater', 'base:jersey', 'base:fulltop'}
OUTERWEAR_LOCATIONS = {
    'base:jacket', 'base:jacketsuit', 'base:jacket_bulky', 'base:jacket_down',
    'base:torsoextra', 'base:torsoextravest', 'base:bathrobe',
}
BOTTOM_LOCATIONS = {
    'base:pants', 'base:pants_skinny', 'base:shortpants', 'base:shortsshort',
    'base:skirt', 'base:longskirt', 'base:legs1', 'base:pantsextra',
}
UNDERWEAR_TOP_LOCATIONS = {'base:underweartop', 'base:underwearextra1', 'base:underwearextra2'}
UNDERWEAR_BOTTOM_LOCATIONS = {'base:underwearbottom'}
UNDERWEAR_FULL_LOCATIONS = {'base:underwear'}
DRESS_LOCATIONS = {'base:dress', 'base:longdress'}
FULLBODY_LOCATIONS = {'base:boilersuit', 'base:fullsuit', 'base:torso1legs1'}
UTILITY_ACCESSORY_LOCATIONS = {
    'base:belt', 'base:beltextra', 'base:webbing', 'base:ammostrap',
    'base:fannypackfront', 'base:fannypackback', 'base:shoulderholster',
    'base:ankleholster', 'base:back', 'base:satchel',
}
NECK_ACCESSORY_LOCATIONS = {'base:scarf', 'base:neck'}
WRIST_LOCATIONS = {'base:leftwrist', 'base:rightwrist'}
JEWELRY_EAR_LOCATIONS = {'base:ears', 'base:eartop'}
JEWELRY_NECK_LOCATIONS = {'base:necklace', 'base:necklace_long'}
JEWELRY_RING_LOCATIONS = {
    'base:left_middlefinger', 'base:right_middlefinger',
    'base:left_ringfinger', 'base:right_ringfinger',
}
JEWELRY_OTHER_LOCATIONS = {'base:bellybutton', 'base:nose'}

ARMOR_LOCATIONS = {
    'base:torsoextravestbullet', 'base:cuirass', 'base:gorget',
    'base:calf_right', 'base:calf_left', 'base:thigh_right', 'base:thigh_left',
    'base:forearm_right', 'base:forearm_left', 'base:elbow_right', 'base:elbow_left',
    'base:knee_right', 'base:knee_left', 'base:shoulderpadleft', 'base:shoulderpadright',
    'base:sportshoulderpad', 'base:sportshoulderpadontop', 'base:rightarm', 'base:leftarm',
    'base:codpiece',
    'base:calf_left_texture', 'base:calf_right_texture',
}
ARMOR_ID_PATTERNS = [
    'Armor', 'Armour', 'BulletVest', 'Greave', 'Vambrace', 'Gorget',
    'Cuirass', 'ShoulderPad', 'KneeGuard', 'ShinKneeGuard', 'GasMask',
    'Helmet', 'Visor', 'ThighBodyArmour', 'ForearmBodyArmour',
]
LIGHT_ARMOR_THRESHOLD = 25
MEDIUM_ARMOR_THRESHOLD = 60
HEAVY_ARMOR_THRESHOLD = 90


def _get_body_location(props):
    match = re.search(r"BodyLocation\s*=\s*([^,\n\s;]+)", props, re.IGNORECASE)
    return match.group(1).lower() if match else ''


def _get_max_defense(analyzer):
    values = {
        'bite': analyzer.get_stat('BiteDefense'),
        'scratch': analyzer.get_stat('ScratchDefense'),
        'bullet': analyzer.get_stat('BulletDefense'),
        'blunt': analyzer.get_stat('BluntDefense'),
    }
    return max(values.values()), values


def _is_visual_overlay(item_id, body_location):
    item_lower = item_id.lower()
    return (
        body_location in EXCLUDED_BODY_LOCATIONS
        or item_lower.startswith('zeddmg_')
        or item_lower.startswith('wound_')
        or item_lower.startswith('bandage_')
    )


def _is_explicit_armor(item_id, display_category, body_location, analyzer, max_defense):
    return (
        display_category == 'protectivegear'
        or body_location in ARMOR_LOCATIONS
        or analyzer.get_stat('BulletDefense') > 0
        or id_matches_pattern(item_id, ARMOR_ID_PATTERNS)
        or max_defense >= HEAVY_ARMOR_THRESHOLD
    )


def _resolve_armor_slot(body_location):
    if body_location in HEAD_LOCATIONS:
        return 'Head'
    if body_location in FACE_LOCATIONS:
        return 'Face'
    if body_location in HAND_LOCATIONS:
        return 'Hands'
    if body_location in FOOT_LOCATIONS:
        return 'Feet'
    if body_location in {'base:gorget'}:
        return 'Neck'
    if body_location in {
        'base:forearm_right', 'base:forearm_left', 'base:elbow_right', 'base:elbow_left',
        'base:shoulderpadleft', 'base:shoulderpadright', 'base:sportshoulderpad',
        'base:sportshoulderpadontop', 'base:rightarm', 'base:leftarm',
    }:
        return 'Arms'
    if body_location in {
        'base:calf_right', 'base:calf_left', 'base:calf_left_texture', 'base:calf_right_texture',
        'base:thigh_right', 'base:thigh_left',
        'base:knee_right', 'base:knee_left', 'base:codpiece',
    }:
        return 'Legs'
    return 'Torso'


def _resolve_nonarmor_slot(item_id, display_category, body_location):
    item_lower = item_id.lower()

    if body_location in COSMETIC_BODY_LOCATIONS:
        return 'Accessory.Cosmetic'
    if body_location == 'base:tail':
        return 'Accessory.Cosmetic'
    if body_location in JEWELRY_EAR_LOCATIONS:
        return 'Accessory.Jewelry.Ears'
    if body_location in JEWELRY_NECK_LOCATIONS:
        return 'Accessory.Jewelry.Necklace'
    if body_location in JEWELRY_RING_LOCATIONS:
        return 'Accessory.Jewelry.Ring'
    if body_location == 'base:bellybutton':
        return 'Accessory.Jewelry.Belly'
    if body_location == 'base:nose':
        return 'Accessory.Jewelry.Nose'
    if body_location in WRIST_LOCATIONS:
        if 'bracelet' in item_lower:
            return 'Accessory.Jewelry.Wrist'
        if 'watch' in item_lower:
            return 'Accessory.Wrist.Watch'
        return 'Accessory.Wrist'
    if body_location in EYE_LOCATIONS:
        return 'Accessory.Eyes'
    if body_location in NECK_ACCESSORY_LOCATIONS:
        return 'Accessory.Neck'
    if body_location == 'base:neck_texture':
        return 'Accessory.Neck'
    if body_location in UTILITY_ACCESSORY_LOCATIONS:
        return 'Accessory.Utility'
    if body_location in HEAD_LOCATIONS:
        return 'Head'
    if body_location in FACE_LOCATIONS:
        return 'Face'
    if body_location in HAND_LOCATIONS:
        return 'Hands'
    if body_location in FOOT_LOCATIONS:
        return 'Feet'
    if body_location in UNDERWEAR_TOP_LOCATIONS:
        return 'Underwear.Top'
    if body_location in UNDERWEAR_BOTTOM_LOCATIONS:
        return 'Underwear.Bottom'
    if body_location in UNDERWEAR_FULL_LOCATIONS:
        return 'Underwear.General'
    if body_location in DRESS_LOCATIONS:
        return 'Dress'
    if body_location in FULLBODY_LOCATIONS:
        return 'FullBody'
    if body_location in OUTERWEAR_LOCATIONS:
        return 'Outerwear'
    if body_location == 'base:vesttexture':
        return 'Outerwear'
    if body_location in TOP_LOCATIONS:
        return 'Top'
    if body_location in BOTTOM_LOCATIONS:
        return 'Bottom'

    if display_category == 'accessory':
        if any(token in item_lower for token in ('ring', 'necklace', 'earring', 'bracelet', 'locket', 'dogtag')):
            return 'Accessory.Jewelry'
        return 'Accessory'

    if any(token in item_lower for token in ('dress', 'gown')):
        return 'Dress'
    if any(token in item_lower for token in ('jacket', 'coat', 'vest', 'robe', 'poncho')):
        return 'Outerwear'
    if any(token in item_lower for token in ('shirt', 'tshirt', 'sweater', 'jumper', 'blouse', 'jersey')):
        return 'Top'
    if any(token in item_lower for token in ('pants', 'trousers', 'shorts', 'skirt')):
        return 'Bottom'
    if any(token in item_lower for token in ('shoe', 'boot', 'sneaker', 'sock')):
        return 'Feet'
    if any(token in item_lower for token in ('glove', 'mitt')):
        return 'Hands'
    if any(token in item_lower for token in ('hat', 'cap', 'helmet')):
        return 'Head'
    if any(token in item_lower for token in ('mask', 'gasmask')):
        return 'Face'
    return 'General'


def matches_clothing_signature(item_id, props):
    """
    Check whether the item belongs to the clothing taxonomy.
    """
    analyzer = PropertyAnalyzer(props)
    body_location = _get_body_location(props)
    display_category = (get_display_category(props) or '').lower()
    is_clothing_type = analyzer.has_property('Type', 'Clothing') or analyzer.has_property('ItemType', 'base:clothing')
    is_alarm_clock_clothing = analyzer.has_property('ItemType', 'base:alarmclockclothing')
    can_equip = bool(body_location) or is_clothing_type or is_alarm_clock_clothing

    if not can_equip or _is_visual_overlay(item_id, body_location) or body_location in TEXTURE_ONLY_LOCATIONS:
        return False, 0.0, {}

    max_defense, defense_stats = _get_max_defense(analyzer)
    is_armor = _is_explicit_armor(item_id, display_category, body_location, analyzer, max_defense)
    clothing_type = f"Armor.{_resolve_armor_slot(body_location)}" if is_armor else _resolve_nonarmor_slot(item_id, display_category, body_location)

    evidence = []
    details = {
        'body_location': body_location or None,
        'display_category': display_category or None,
        'clothing_type': clothing_type,
        'is_armor': is_armor,
        'armor_tier': 'Light',
        'max_defense': max_defense,
    }
    details.update(defense_stats)

    if is_clothing_type:
        evidence.append(0.35)
    if is_alarm_clock_clothing:
        evidence.append(0.35)
    if body_location:
        evidence.append(0.3)
    if display_category in {'clothing', 'accessory', 'protectivegear'}:
        evidence.append(0.2)
    if max_defense > 0:
        evidence.append(0.1)
    if clothing_type != 'General':
        evidence.append(0.1)

    if max_defense >= HEAVY_ARMOR_THRESHOLD:
        details['armor_tier'] = 'Heavy'
    elif max_defense >= MEDIUM_ARMOR_THRESHOLD:
        details['armor_tier'] = 'Medium'
    elif max_defense >= LIGHT_ARMOR_THRESHOLD:
        details['armor_tier'] = 'Light'

    confidence = min(1.0, sum(evidence)) if evidence else 0.0
    return confidence >= 0.45, confidence, details


def get_clothing_tags(item_id, props):
    """
    Generate clothing tags based on the resolved clothing subtype.
    """
    matches, _confidence, details = matches_clothing_signature(item_id, props)
    if not matches:
        return []

    primary_tag = f"Clothing.{details.get('clothing_type', 'General')}"
    tags = [primary_tag]

    if details.get('is_armor'):
        armor_tier = details.get('armor_tier')
        if armor_tier:
            tier_tag = f"Clothing.Armor.{armor_tier}"
            if tier_tag not in tags:
                tags.append(tier_tag)
    elif details.get('max_defense', 0) >= LIGHT_ARMOR_THRESHOLD:
        tags.append('Clothing.Protective')

    if details.get('bite', 0) >= 20:
        tags.append('Clothing.BiteResistant')
    if details.get('scratch', 0) >= 20:
        tags.append('Clothing.ScratchResistant')
    if details.get('bullet', 0) > 0:
        tags.append('Clothing.BulletResistant')
    if details.get('blunt', 0) >= 20:
        tags.append('Clothing.BluntResistant')

    insulation = PropertyAnalyzer(props).get_stat('Insulation')
    wind = PropertyAnalyzer(props).get_stat('WindResistance')
    if insulation > 0.5:
        tags.append('Clothing.Insulated')
    if wind > 0.5:
        tags.append('Clothing.WindResistant')

    if id_matches_pattern(item_id, ['Police', 'Sheriff']):
        tags.append('Clothing.Authority')
    elif id_matches_pattern(item_id, ['Military', 'Tactical', 'Army', 'SWAT']):
        tags.append('Clothing.Tactical')
    elif id_matches_pattern(item_id, ['Medical', 'Doctor', 'Hospital']):
        tags.append('Clothing.Medical')

    unique_tags = []
    for tag in tags:
        if tag not in unique_tags:
            unique_tags.append(tag)
    return unique_tags
