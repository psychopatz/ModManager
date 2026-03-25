"""Weapon property-based signatures used by live item categorization."""
from .helpers import extract_tags_from_props, get_display_category, id_matches_pattern, PropertyAnalyzer


EXPLOSIVE_ID_PATTERNS = ['Aerosol', 'Grenade', 'Explosive', 'Bomb', 'Molotov', 'PipeBomb', 'SmokeBomb']
FIREARM_ID_PATTERNS = ['Gun', 'Pistol', 'Rifle', 'Shotgun', 'Revolver', 'Carbine']
AXE_ID_PATTERNS = ['Axe', 'Hatchet', 'PickAxe']
BLADE_ID_PATTERNS = ['Blade', 'Knife', 'Machete', 'Sword', 'Katana', 'Scalpel', 'Cleaver']
BLUNT_ID_PATTERNS = ['Bat', 'Club', 'Hammer', 'Pipe', 'Wrench', 'Crowbar', 'Mallet', 'Nightstick', 'Mace']
MAGAZINE_ID_PATTERNS = ['clip', 'magazine', 'drum']
COOKWARE_WEAPON_PATTERNS = [
    'BakingPan', 'BakingTray', 'FryingPan', 'GridlePan', 'GriddlePan',
    'Saucepan', 'CookingPot', 'RoastingPan', 'Kettle',
]
COOKWARE_SCRIPT_TAGS = {'base:cookable', 'base:canopener'}


def matches_weapon_signature(item_id, props):
    """Check whether an item belongs to the weapon taxonomy."""
    analyzer = PropertyAnalyzer(props)
    item_lower = item_id.lower()
    display_category = (get_display_category(props) or '').lower()
    script_tags = {tag.lower() for tag in extract_tags_from_props(props)}

    cookware_context = (
        display_category in {'cooking', 'cookingweapon'} and (
            id_matches_pattern(item_id, COOKWARE_WEAPON_PATTERNS) or
            bool(script_tags.intersection(COOKWARE_SCRIPT_TAGS)) or
            analyzer.has_property('IsCookable') or
            analyzer.has_property('PourType') or
            analyzer.has_property('EatType')
        )
    )

    if display_category == 'firstaidweapon' or cookware_context:
        return False, 0.0, {
            'display_category': display_category,
            'excluded_medical_weapon': display_category == 'firstaidweapon',
            'excluded_cookware_weapon': cookware_context,
            'is_firearm': False,
            'is_explosive': False,
            'is_melee': False,
            'is_magazine': False,
            'is_part_accessory': False,
        }

    has_damage = analyzer.get_stat('MinDamage') > 0 or analyzer.get_stat('MaxDamage') > 0
    is_weapon_type = analyzer.has_property('Type', 'Weapon') or analyzer.has_property('Type', 'Base:Weapon')
    has_ammo_type = analyzer.has_property('AmmoType')
    has_magazine_type = analyzer.has_property('MagazineType')
    has_part_mount = analyzer.has_property('MountOn') or analyzer.has_property('PartType')
    is_magazine_name = any(pattern in item_lower for pattern in MAGAZINE_ID_PATTERNS) and 'magnesium' not in item_lower

    details = {
        'display_category': display_category,
        'is_firearm': False,
        'is_explosive': False,
        'is_melee': False,
        'is_magazine': False,
        'is_part_accessory': False,
    }

    if display_category == 'weaponpart' or has_part_mount:
        details['is_part_accessory'] = True
        details['subtype'] = 'Part.Accessory'
        return True, 0.95, details

    if display_category == 'ammo':
        if has_magazine_type or (has_ammo_type and (analyzer.has_property('CanStack', 'false') or is_magazine_name)):
            details['is_magazine'] = True
            details['subtype'] = 'Part.Ammo'
            return True, 0.95, details

        details['subtype'] = 'Ranged.Ammo'
        return True, 0.9, details

    # Some ammo scripts omit DisplayCategory, so fall back to ammo properties.
    if has_ammo_type and not is_weapon_type and not has_damage:
        if has_magazine_type or analyzer.has_property('CanStack', 'false') or is_magazine_name:
            details['is_magazine'] = True
            details['subtype'] = 'Part.Ammo'
            return True, 0.92, details

        details['subtype'] = 'Ranged.Ammo'
        return True, 0.88, details

    if id_matches_pattern(item_id, EXPLOSIVE_ID_PATTERNS):
        details['is_explosive'] = True
        details['subtype'] = 'Explosive'
        return True, 0.95, details

    # Only use name-pattern subtype routing after we already know the item is a weapon.
    if is_weapon_type or has_damage:
        if has_ammo_type or analyzer.has_property('Ranged', 'true') or analyzer.has_property('IsAimedFirearm', 'true'):
            details['is_firearm'] = True
            details['subtype'] = 'Ranged.Firearm'
            return True, 0.9, details

        details['is_melee'] = True
        if id_matches_pattern(item_id, AXE_ID_PATTERNS):
            details['subtype'] = 'Melee.Axe'
        elif id_matches_pattern(item_id, BLADE_ID_PATTERNS):
            details['subtype'] = 'Melee.Blade'
        elif id_matches_pattern(item_id, BLUNT_ID_PATTERNS):
            details['subtype'] = 'Melee.Blunt'
        else:
            details['subtype'] = 'Melee.General'
        return True, 0.8, details

    return False, 0.0, details


def get_weapon_tags(item_id, props):
    """Generate weapon tags based on the resolved weapon subtype."""
    matches, confidence, details = matches_weapon_signature(item_id, props)

    if not matches:
        return []

    subtype = details.get('subtype', 'Melee.General')
    tags = [f"Weapon.{subtype}"]
    return tags
