"""
Resource property-based signatures.
Detects crafting stock, salvage, and production inputs through material-focused
display categories, tags, and resource-specific item patterns.
"""
import re

from .helpers import (
    extract_tags_from_props,
    get_display_category,
    id_matches_pattern,
    PropertyAnalyzer,
)


RESOURCE_DISPLAY_CATEGORIES = {'material', 'reciperesource'}
NON_RESOURCE_DISPLAY_CATEGORIES = {
    'food', 'firstaid', 'literature', 'skillbook', 'cartography', 'electronics',
    'camping', 'trapping', 'furniture', 'household', 'vehiclemaintenance',
}

PART_PATTERNS = [
    'AxeHead', 'HatchetHead', 'HammerHead', 'MaceHead', 'SpearHead',
    'KnifeBlade', 'SwordBlade', 'MacheteBlade', 'ClawhammerHead',
    'FireAxeHead', 'Blade_NoTang', 'BladeHead', 'ToolHead',
]
LIQUID_FUEL_PATTERNS = [
    'Gasoline', 'Petrol', 'Diesel', 'Kerosene',
    'LighterFluid', 'StarterFluid', 'BBQStarterFluid',
    'GasCan', 'FuelCan', 'JerryCan',
]
GAS_FUEL_PATTERNS = [
    'Propane', 'GasTank',
]
SOLID_FUEL_PATTERNS = ['Charcoal', 'Coal', 'Firewood', 'Kindling']
AMMO_MATERIAL_PATTERNS = ['GunPowder', 'BlackPowder', 'Primer', 'Wad', 'Pellet', 'Shotshell', 'Casing', 'BulletTip']
METAL_PATTERNS = [
    'Metal', 'Steel', 'Iron', 'Copper', 'Aluminum', 'Brass', 'Bronze',
    'Lead', 'Silver', 'Gold', 'Ingot', 'Rebar',
]
HARDWARE_PATTERNS = [
    'Nail', 'Screw', 'Bolt', 'Nut', 'Rivet', 'Wire', 'BarbedWire',
    'Chain', 'Doorknob', 'Hinge', 'Buckle', 'Button', 'Sawblade',
    'Pipe', 'Valve', 'Handle', 'Latch',
]
WOOD_PATTERNS = ['Wood', 'Plank', 'Log', 'Lumber', 'Timber', 'Beam', 'Twig', 'Branch', 'Firewood']
TEXTILE_PATTERNS = [
    'Fabric', 'Cloth', 'Denim', 'Burlap', 'CheeseCloth', 'Thread', 'Yarn',
    'Twine', 'Rope', 'String', 'Canvas', 'Flax', 'Linen', 'Wool',
    'Cotton', 'Strips', 'Floss',
]
LEATHER_PATTERNS = ['Leather', 'Hide', 'Pelt', 'Fur', 'BrainTan', 'HideStrip']
GLASS_PATTERNS = ['Glass', 'Shard', 'Lens']
MINERAL_PATTERNS = [
    'Ore', 'Stone', 'Clay', 'Gravel', 'Sand', 'Hematite', 'Malachite',
    'Gypsum', 'Limestone', 'Chalk', 'Rock', 'Flint', 'Brick',
    'Concrete', 'Cement', 'Plaster', 'Mortar',
]
CERAMIC_PATTERNS = ['Ceramic', 'Crucible', 'TeacupUnfired', 'MortarandPestleUnfired']
ADHESIVE_PATTERNS = ['Glue', 'Epoxy', 'Tape', 'Paste', 'Caulk', 'Resin', 'Adhesive']
CHEMICAL_PATTERNS = ['Lye', 'Sulfur', 'Saltpeter', 'Pigment', 'Dye', 'Flux', 'Powder', 'Oxygen']
PAPER_PATTERNS = ['Paper', 'Cardboard', 'BookBinding', 'Label', 'Roll']
PACKAGING_PATTERNS = ['Box', 'Bag', 'Sack', 'Bundle', 'Carton', 'Package', 'Parcel', 'Wrapper']

RESOURCE_TAG_HINTS = {
    'base:hasmetal',
    'base:steelmaterial',
    'base:toolhead',
    'base:glass',
    'base:glue',
    'base:epoxy',
    'base:tape',
    'base:binding',
    'base:simpleweaponbinding',
    'base:ingot',
}

METAL_FAMILY_PATTERNS = {
    'Gold': ('gold',),
    'Silver': ('silver',),
    'Copper': ('copper',),
    'Brass': ('brass',),
    'Bronze': ('bronze',),
    'Steel': ('steel',),
    'Iron': ('iron',),
    'Aluminum': ('aluminum', 'aluminium'),
    'Lead': ('lead',),
    'Tin': ('tin',),
}

METAL_FORM_PATTERNS = [
    ('Mold', ('mold', 'cast')),
    ('Ore', ('ore',)),
    ('Scrap', ('scrap',)),
    ('Coin', ('coin',)),
    ('Sheet', ('sheet',)),
    ('Ingot', ('ingot',)),
    ('Bloom', ('bloom',)),
    ('Block', ('block',)),
    ('Chunk', ('chunk',)),
    ('Piece', ('piece',)),
    ('Rod', ('rod',)),
    ('Band', ('band',)),
    ('Slug', ('slug',)),
    ('Bar', ('bar',)),
    ('Fragment', ('fragment',)),
]


def _has_prop_value(props, key, value):
    return re.search(rf"\b{re.escape(key)}\s*=\s*{re.escape(value)}\b", props, re.IGNORECASE) is not None


def _matches_liquid_fuel(item_id, display_category, analyzer):
    item_lower = item_id.lower()
    if id_matches_pattern(item_id, LIQUID_FUEL_PATTERNS):
        return True
    return (
        analyzer.get_stat('UseDelta') > 0 and
        display_category in {'material', 'household'} and
        any(token in item_lower for token in ['gasoline', 'petrol', 'diesel', 'kerosene', 'lighterfluid', 'starterfluid'])
    )


def _matches_gas_fuel(item_id, display_category, analyzer):
    item_lower = item_id.lower()
    if 'propane' in item_lower:
        return True
    if 'gastank' in item_lower and display_category in {'vehiclemaintenance', 'material'}:
        return True
    return False


def _item_tokens(item_id):
    normalized = re.sub(r'([a-z])([A-Z])', r'\1 \2', item_id or "")
    normalized = normalized.replace('_', ' ')
    return [token.lower() for token in re.findall(r'[A-Za-z]+', normalized)]


def _get_metal_family(item_id):
    item_tokens = _item_tokens(item_id)
    for family, family_tokens in METAL_FAMILY_PATTERNS.items():
        if any(token in item_tokens for token in family_tokens):
            return family
    return None


def _get_metal_form(item_id):
    item_tokens = _item_tokens(item_id)
    for form, tokens in METAL_FORM_PATTERNS:
        if any(token in item_tokens for token in tokens):
            return form
    return None


def _get_resource_subtype(item_id, display_category, script_tags, analyzer):
    item_lower = item_id.lower()
    item_tokens = _item_tokens(item_id)

    if id_matches_pattern(item_id, PART_PATTERNS) or 'base:toolhead' in script_tags:
        return 'Parts'

    if _matches_liquid_fuel(item_id, display_category, analyzer):
        return 'Fuel.Liquid'
    if _matches_gas_fuel(item_id, display_category, analyzer):
        return 'Fuel.Gas'
    if id_matches_pattern(item_id, SOLID_FUEL_PATTERNS):
        return 'Fuel.Solid'

    if id_matches_pattern(item_id, AMMO_MATERIAL_PATTERNS):
        return 'Material.Ammo'

    if id_matches_pattern(item_id, ADHESIVE_PATTERNS) or script_tags.intersection({'base:glue', 'base:epoxy', 'base:tape'}):
        return 'Material.Adhesive'

    if id_matches_pattern(item_id, CERAMIC_PATTERNS):
        return 'Material.Ceramic'

    if id_matches_pattern(item_id, LEATHER_PATTERNS):
        return 'Material.Leather'

    if (
        id_matches_pattern(item_id, TEXTILE_PATTERNS) or
        script_tags.intersection({'base:binding', 'base:simpleweaponbinding'})
    ):
        return 'Material.Textile'

    if id_matches_pattern(item_id, HARDWARE_PATTERNS):
        return 'Material.Hardware'

    if (
        id_matches_pattern(item_id, MINERAL_PATTERNS) or
        script_tags.intersection({'base:concrete'}) or
        'base:concrete' in analyzer.props_lower
    ):
        return 'Material.Mineral'

    if id_matches_pattern(item_id, GLASS_PATTERNS) or 'base:glass' in script_tags:
        return 'Material.Glass'

    if any(pattern.lower() in item_tokens for pattern in METAL_PATTERNS) or script_tags.intersection({'base:hasmetal', 'base:ingot', 'base:steelmaterial'}):
        return 'Material.Metal'

    if id_matches_pattern(item_id, WOOD_PATTERNS):
        return 'Material.Wood'

    if id_matches_pattern(item_id, CHEMICAL_PATTERNS):
        return 'Material.Chemical'

    if (
        id_matches_pattern(item_id, PAPER_PATTERNS) or
        (display_category == 'reciperesource' and ('paper' in item_lower or 'card' in item_lower))
    ):
        return 'Material.Paper'

    if (
        item_lower.endswith('_empty') or
        'bagseed' in item_lower or
        id_matches_pattern(item_id, PACKAGING_PATTERNS)
    ):
        return 'Material.Packaging'

    return 'Material.General'


def matches_resource_signature(item_id, props):
    """
    Check if item matches the resource signature.

    Resources are crafting/salvage inputs, raw materials, or production stock,
    usually identified by material-oriented display categories and tags.
    """
    analyzer = PropertyAnalyzer(props)
    display_category = (get_display_category(props) or '').lower()
    script_tags = {tag.lower() for tag in extract_tags_from_props(props)}
    item_lower = item_id.lower()

    is_material_display = display_category in RESOURCE_DISPLAY_CATEGORIES
    is_weapon_part = id_matches_pattern(item_id, PART_PATTERNS) or 'base:toolhead' in script_tags
    is_liquid_fuel = _matches_liquid_fuel(item_id, display_category, analyzer)
    is_gas_fuel = _matches_gas_fuel(item_id, display_category, analyzer)
    is_fuel_resource = is_liquid_fuel or is_gas_fuel or id_matches_pattern(item_id, SOLID_FUEL_PATTERNS)
    has_resource_tags = bool(script_tags.intersection(RESOURCE_TAG_HINTS))
    is_drainable = analyzer.get_stat('UseDelta') > 0
    has_weapon_damage = analyzer.get_stat('MinDamage') >= 0.5 or analyzer.get_stat('MaxDamage') >= 0.5

    if has_weapon_damage and not (is_material_display or is_weapon_part):
        return False, 0.0, {}

    if analyzer.has_property('BodyLocation'):
        return False, 0.0, {}

    if analyzer.has_property('ItemType', 'base:container') and not is_material_display:
        return False, 0.0, {}

    if analyzer.has_property('ItemType', 'base:literature') and display_category != 'reciperesource':
        return False, 0.0, {}

    if (
        display_category in NON_RESOURCE_DISPLAY_CATEGORIES and
        not is_material_display and
        not is_weapon_part and
        not is_fuel_resource
    ):
        return False, 0.0, {}

    subtype = _get_resource_subtype(item_id, display_category, script_tags, analyzer)
    looks_like_resource = (
        is_material_display or
        has_resource_tags or
        is_weapon_part or
        is_fuel_resource or
        subtype != 'Material.General' or
        (is_drainable and display_category == 'material')
    )

    if not looks_like_resource:
        return False, 0.0, {}

    evidence = []
    details = {
        'resource_type': subtype,
        'display_category': display_category or None,
        'is_craftable': is_material_display or subtype.startswith('Material.') or subtype == 'Parts',
        'is_harvestable': analyzer.has_property('HarvestType') or analyzer.has_property('Harvestable'),
    }

    if is_material_display:
        evidence.append(0.55 if display_category == 'material' else 0.45)

    if has_resource_tags:
        evidence.append(0.25)

    if is_weapon_part:
        evidence.append(0.35)

    if is_fuel_resource:
        evidence.append(0.3)

    if is_drainable and (is_material_display or subtype in {'Material.Adhesive', 'Material.Chemical', 'Material.Ammo'}):
        evidence.append(0.2)
        details['use_delta'] = analyzer.get_stat('UseDelta')

    if subtype != 'Material.General':
        evidence.append(0.25)

    if details['is_harvestable']:
        evidence.append(0.15)

    confidence = min(1.0, sum(evidence)) if evidence else 0.0
    return confidence >= 0.45, confidence, details


def get_resource_tags(item_id, props):
    """Generate Resource.* tags based on the matched resource subtype."""
    matches, _confidence, details = matches_resource_signature(item_id, props)
    if not matches:
        return []

    primary_tag = f"Resource.{details.get('resource_type', 'Material.General')}"
    tags = [primary_tag]

    if primary_tag == 'Resource.Material.Metal':
        metal_family = _get_metal_family(item_id)
        metal_form = _get_metal_form(item_id)
        if metal_family:
            tags.append(f'Resource.Material.MetalFamily.{metal_family}')
        if metal_form:
            tags.append(f'Resource.Material.MetalForm.{metal_form}')

    if details.get('is_craftable') and 'Resource.Craftable' not in tags:
        tags.append('Resource.Craftable')

    if details.get('is_harvestable') and 'Resource.Harvestable' not in tags:
        tags.append('Resource.Harvestable')

    return tags
