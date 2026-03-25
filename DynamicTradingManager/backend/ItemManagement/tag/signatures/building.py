"""
Building & Construction property-based signatures.
Detects moveable furniture/building objects (Mov_*), raw construction materials,
structural fasteners, and building-support tools.

Tag taxonomy produced:
  Building.Moveable     – moveable world objects (Mov_* prefix in vanilla/mods)
  Building.Material     – raw construction materials (timber, metal, nails, screws …)
  Building.Furniture.*  – seating, surfaces, storage, beds, decor
  Building.Fixture.*    – plumbing, appliances, wiring, hardware, comms fixtures
  Building.Vehicle      – vehicle maintenance parts (engine parts, windows …)
  Building.Garden       – gardening supplies, planting pots, compost, tools
  Building.Garden.Seed  – seeds, bulbs, saplings, and cuttings (plantable items)
  Building.Survival.*   – placeable camping shelter/sleep systems and traps
"""
import re

from .helpers import get_stat, has_property, id_matches_pattern, get_display_category, extract_tags_from_props, PropertyAnalyzer


# --------------------------------------------------------------------------
# ID token lists
# --------------------------------------------------------------------------
MOV_PREFIX = ['Mov_']          # moveable world-objects in vanilla & most mods

MATERIAL_ID = [
    'Plank', 'Lumber', 'Timber', 'Log', 'Beam',
    'Nail', 'Nails', 'Screw', 'Screws', 'Bolt', 'Nut', 'Rivet',
    'Wire', 'BarbedWire', 'WireStack',
    'Sheet', 'MetalSheet', 'SteelSheet',
    'Rebar', 'Rod', 'Bar',
    'Concrete', 'Cement', 'Brick', 'Cinder',
    'Grout', 'Tile', 'Drywall', 'Sheetrock',
    'Aluminum', 'AluminumScrap', 'AluminumFragments',
    'Hematite', 'Malachite',
    'LargePlank', 'LargeStone', 'SmallStone',
    'GlassPanel', 'GlassShard',
    'Insulation', 'Caulk',
    'PaintRoll', 'PaintBrush', 'PaintBucket',
    'Varnish', 'Lacquer', 'Stain',
    'Adhesive', 'DuctTape', 'GlueStick',
    'DrawPlate', 'MetalPipe',
]

FIXTURE_ID = [
    'Valve', 'Pipe', 'PipeWrench', 'PlumbingPipe',
    'Doorknob', 'DoorHinge', 'Hinge', 'Hasp', 'Padlock',
    'Drawer', 'CabinetHandle',
    'LightBulb', 'LightBulbBox', 'LightSwitch',
    'ElectricWire', 'ElectricBox', 'PowerBoxPart',
    'HomeAlarm',
]

FURNITURE_ID = [
    'Mattress', 'Rug', 'Curtain', 'Blind',
    'Candle', 'Lamp', 'Lantern',
    'Shelf', 'Rack', 'Cabinet',
    'Frame', 'PictureFrame',
]

VEHICLE_PART_ID = [
    'EngineDoor', 'EngineParts', 'FrontWindow',
    'LugWrench', 'Jack', 'HoodOrnament',
    'TirePatch', 'TireRepair',
    'BrakeFluid', 'PowerSteering', 'CoolantBottle', 'TransFluid',
]

SEED_ID = [
    'Seed', 'BagSeed', 'SeedPacket', 'SeedPouch',
    'BulbSack', 'Bulb',
    'Sapling', 'Sprout', 'Cutting',
]

GARDEN_ID = [
    'Fertilizer', 'Compost', 'PeatMoss',
    'Planter', 'Trough', 'Herb', 'CropRow',
]

# DisplayCategory values from vanilla that map cleanly to Building
MATERIAL_DISPLAY_CATS = {
    'material', 'reciperesource', 'materialweapon',
}
FURNITURE_DISPLAY_CATS = {
    'furniture',
}
VEHICLE_DISPLAY_CATS = {
    'vehiclemaintenance',
}
GARDEN_DISPLAY_CATS = {
    'gardening',
}
SURVIVAL_DISPLAY_CATS = {
    'camping',
}
TRAPPING_DISPLAY_CATS = {
    'trapping',
}
FIXTURE_DISPLAY_CATS = {
    'household',
}

# Script Tags (PZ Tags = field) that are reliable building indicators
BUILDING_SCRIPT_TAGS = {
    'base:hasmetal',
    'base:smeltablesteelsmall', 'base:smeltablessteellarge',
    'base:smeltableironsmall',  'base:smeltableironmedium',
    'base:smeltableironlarge',
    'base:steelmaterial',
    'base:heavyitem',
    'base:toolhead',
    'base:glass',
}
SURVIVAL_SCRIPT_TAGS = {
    'base:tentbed',
}
SURVIVAL_ID = [
    'SleepingBag', 'Tent', 'Bedroll',
]
MOVEABLE_FIXTURE_ID = [
    'Sink', 'Shower', 'Toilet', 'Urinal',
    'WaterDispenser', 'TowelDispenser', 'NapkinDispenser',
    'Fridge', 'Freezer', 'Oven', 'Stove', 'Microwave',
    'Washer', 'Dryer', 'Dishwasher',
    'RotaryPhone', 'ModernPhone', 'PayPhones',
    'Locker', 'VendingMachine', 'SodaMachine', 'Toaster',
]
PLUMBING_FIXTURE_ID = [
    'Sink', 'Shower', 'Toilet', 'Urinal',
    'Pipe', 'Valve', 'PlumbingPipe', 'WaterDispenser',
]
APPLIANCE_FIXTURE_ID = [
    'Fridge', 'Freezer', 'Oven', 'Stove', 'Microwave',
    'Washer', 'Dryer', 'Dishwasher', 'Toaster',
    'VendingMachine', 'SodaMachine',
]
COMMUNICATION_FIXTURE_ID = [
    'RotaryPhone', 'ModernPhone', 'PayPhones', 'Phone',
]
ELECTRICAL_FIXTURE_ID = [
    'LightBulb', 'LightBulbBox', 'LightSwitch',
    'ElectricWire', 'ElectricBox', 'PowerBoxPart',
]
HARDWARE_FIXTURE_ID = [
    'Doorknob', 'DoorHinge', 'Hinge', 'Hasp', 'Padlock',
    'CabinetHandle', 'Drawer',
]
STORAGE_FIXTURE_ID = [
    'Locker',
]
UTILITY_FIXTURE_ID = [
    'TowelDispenser', 'NapkinDispenser', 'HomeAlarm',
]


# --------------------------------------------------------------------------
# Helper: get normalised DisplayCategory
# --------------------------------------------------------------------------
def _display_cat(props):
    """Return lowercase DisplayCategory value from raw props string."""
    val = get_display_category(props)
    return val.lower() if val else ''


def _script_tags(props):
    """Return set of lowercase script-tag tokens from the Tags= field."""
    return {t.lower() for t in extract_tags_from_props(props)}


def _is_moveable_item(props):
    """Return True for vanilla/mod items marked as moveable world objects."""
    return has_property('ItemType', props, 'base:moveable')


def _is_bedroll_attachment(props):
    """Return True for packed survival placeables that equip as bedrolls."""
    return has_property('AttachmentType', props, 'Bedroll')


def _has_world_placement_model(props):
    """Return True when an item exposes world-placement sprite/model data."""
    return (
        has_property('WorldObjectSprite', props)
        or has_property('StaticModel', props)
        or has_property('WorldStaticModel', props)
    )


def _matches_survival_building(item_id, props, disp_cat, script_tags):
    """
    Detect placeable camping shelter/sleep items without catching generic
    camping supplies like repellents, tablets, or firestarters.
    """
    is_trap_item = has_property('Trap', props, 'true')
    if disp_cat in TRAPPING_DISPLAY_CATS or is_trap_item:
        evidence = []
        if disp_cat in TRAPPING_DISPLAY_CATS:
            evidence.append('display_cat_trapping')
        if is_trap_item:
            evidence.append('trap_property')
        return True, 0.88, {'survival_evidence': evidence, 'survival_subtype': 'Trap'}

    if disp_cat not in SURVIVAL_DISPLAY_CATS:
        return False, 0.0, {}

    has_moveable_item_type = _is_moveable_item(props)
    has_bedroll_attachment = _is_bedroll_attachment(props)
    has_survival_script_tag = bool(script_tags & SURVIVAL_SCRIPT_TAGS)
    has_world_placement = _has_world_placement_model(props)
    looks_like_survival_placeable = id_matches_pattern(item_id, SURVIVAL_ID)
    is_drainable = get_stat('UseDelta', props) > 0
    is_survival_gear = has_property('SurvivalGear', props)

    if is_drainable and not (has_moveable_item_type or has_bedroll_attachment):
        return False, 0.0, {}

    if is_survival_gear and not (has_moveable_item_type or has_bedroll_attachment or has_survival_script_tag):
        return False, 0.0, {}

    evidence = []
    if has_moveable_item_type:
        evidence.append('item_type_moveable')
    if has_bedroll_attachment:
        evidence.append('attachment_bedroll')
    if has_survival_script_tag:
        evidence.append('script_tag_tentbed')
    if looks_like_survival_placeable:
        evidence.append('survival_id')
    if has_world_placement:
        evidence.append('world_placement_model')

    if has_moveable_item_type or has_bedroll_attachment or has_survival_script_tag:
        return True, 0.92, {'survival_evidence': evidence}

    if looks_like_survival_placeable and has_world_placement:
        return True, 0.86, {'survival_evidence': evidence}

    return False, 0.0, {}


def _get_fixture_subtype(item_id, props):
    """Return nested subtype for Building.Fixture.* tags."""
    if id_matches_pattern(item_id, PLUMBING_FIXTURE_ID):
        return 'Plumbing'
    if id_matches_pattern(item_id, APPLIANCE_FIXTURE_ID):
        return 'Appliance'
    if id_matches_pattern(item_id, COMMUNICATION_FIXTURE_ID):
        return 'Communication'
    if id_matches_pattern(item_id, ELECTRICAL_FIXTURE_ID):
        return 'Electrical'
    if id_matches_pattern(item_id, HARDWARE_FIXTURE_ID):
        return 'Hardware'
    if id_matches_pattern(item_id, STORAGE_FIXTURE_ID):
        return 'Storage'
    if id_matches_pattern(item_id, UTILITY_FIXTURE_ID):
        return 'Utility'

    if has_property('RequiresElectricity', props) or has_property('BatteryMod', props):
        return 'Electrical'

    return 'General'


def _get_furniture_subtype(item_id):
    """Return nested subtype for Building.Furniture.* tags."""
    item_lower = item_id.lower()

    if 'benchgrinder' not in item_lower and 'bench' in item_lower:
        return 'Bench'
    if 'chair' in item_lower or 'stool' in item_lower:
        return 'Chair'
    if 'counter' in item_lower:
        return 'Counter'
    if 'table' in item_lower:
        return 'Table'
    if any(token in item_lower for token in (
        'cabinet', 'drawers', 'dresser', 'shelf', 'shelves',
        'bookcase', 'wardrobe', 'crate', 'mailbox',
    )):
        return 'Storage'
    if any(token in item_lower for token in ('mattress', 'bed', 'futon', 'coffin')):
        return 'Bed'
    if any(token in item_lower for token in (
        'curtain', 'lamp', 'clock', 'mirror', 'poster',
        'painting', 'sign', 'flag', 'frame', 'skull',
        'antlers', 'vase', 'neon',
    )):
        return 'Decor'

    return 'General'


def _matches_moveable_subtype(item_id, props, disp_cat):
    """
    Refine Mov_* items into more specific building subtypes when the ID clearly
    describes a fixture or a gardening object.
    """
    is_named_moveable = item_id.startswith('Mov_') or id_matches_pattern(item_id, MOV_PREFIX)
    if not is_named_moveable:
        return False, 0.0, {}

    if disp_cat in GARDEN_DISPLAY_CATS:
        return True, 0.90, {
            'building_type': 'Garden',
            'is_moveable': True,
            'moveable_subtype': 'garden',
        }

    if id_matches_pattern(item_id, MOVEABLE_FIXTURE_ID):
        return True, 0.91, {
            'building_type': 'Fixture',
            'fixture_subtype': _get_fixture_subtype(item_id, props),
            'is_moveable': True,
            'moveable_subtype': 'fixture',
        }

    furniture_subtype = _get_furniture_subtype(item_id)
    if furniture_subtype != 'General':
        return True, 0.90, {
            'building_type': 'Furniture',
            'furniture_subtype': furniture_subtype,
            'is_moveable': True,
            'moveable_subtype': 'furniture',
        }

    return True, 0.95, {
        'building_type': 'Moveable',
        'is_moveable': True,
        'moveable_subtype': 'generic',
    }


# --------------------------------------------------------------------------
# Signature
# --------------------------------------------------------------------------

def matches_building_signature(item_id, props):
    """
    Detect building-related items.

    Evaluation order (stops at first positive sub-type):
      1. Mov_* subtype override → Building.Moveable / Fixture / Garden
      2. Camping placeables     → Building.Survival
      3. DisplayCategory        → direct map
      4. ID token lists         → material / fixture / vehicle / garden / furniture
      5. Script-tag overlap     → general building material

    Returns:
        tuple: (matches: bool, confidence: float, details: dict)
    """
    item_id_lower = item_id.lower()
    disp_cat = _display_cat(props)
    script_tags = _script_tags(props)

    details = {
        'building_type': None,
        'is_moveable': False,
        'display_cat': disp_cat,
    }

    # ── 0. Hard exclusion guards (other categories take precedence) ───────
    # Weapons: anything with real damage stats or explicitly typed as Weapon
    if get_stat('MinDamage', props) >= 0.5 or get_stat('MaxDamage', props) >= 0.5:
        return False, 0.0, details
    if has_property('Type', props, 'Weapon'):
        return False, 0.0, details
    # Clothing
    if has_property('BodyLocation', props):
        return False, 0.0, details
    # Food / drink
    if has_property('HungerChange', props) or has_property('ThirstChange', props):
        return False, 0.0, details
    if disp_cat in {'corpse', 'memento'}:
        return False, 0.0, details
    # Active / consumable light sources should be routed by non-building
    # signatures instead of furniture/fixture heuristics.
    if disp_cat in {'lightsource', 'firesource'}:
        return False, 0.0, details
    # Pure electronics display categories belong to the electronics pipeline.
    if disp_cat == 'electronics':
        return False, 0.0, details
    # Battery-branded items should be handled by electronics even when they are
    # used in vehicle maintenance.
    if id_matches_pattern(item_id, ['Battery']):
        return False, 0.0, details
    # Ammunition
    if has_property('AmmoType', props) or has_property('ProjectileCount', props):
        return False, 0.0, details
    # Recipe books / magazines / schematics (literature-like media)
    if re.search(r"(LearnedRecipes|TeachedRecipes|SkillTrained|LvlSkillTrained|NumLevelsTrained|NumberOfPages|LiteratureOnRead)\s*=", props, re.IGNORECASE):
        if re.search(r"(skillbook|book\d*$|mag\d*$|magazine|comic|schematic|manual|guide|journal|recipeclipping)", item_id, re.IGNORECASE):
            return False, 0.0, details

    # ── 1. Explicit named moveables with subtype refinement ───────────────
    moveable_matches, moveable_confidence, moveable_details = _matches_moveable_subtype(
        item_id, props, disp_cat
    )
    if moveable_matches:
        details.update(moveable_details)
        return True, moveable_confidence, details

    # ── 2. Dedicated survival placeables inside Camping ──────────────────
    survival_matches, survival_confidence, survival_details = _matches_survival_building(
        item_id, props, disp_cat, script_tags
    )
    if survival_matches:
        details['building_type'] = 'Survival'
        details.update(survival_details)
        return True, survival_confidence, details

    # ── 3. DisplayCategory direct map ────────────────────────────────────
    if disp_cat in MATERIAL_DISPLAY_CATS:
        details['building_type'] = 'Material'
        return True, 0.90, details

    if disp_cat in FURNITURE_DISPLAY_CATS:
        details['building_type'] = 'Furniture'
        details['furniture_subtype'] = _get_furniture_subtype(item_id)
        return True, 0.85, details

    if disp_cat in VEHICLE_DISPLAY_CATS:
        details['building_type'] = 'Vehicle'
        return True, 0.85, details

    if disp_cat in GARDEN_DISPLAY_CATS:
        if id_matches_pattern(item_id, SEED_ID):
            details['building_type'] = 'Garden.Seed'
            return True, 0.88, details
        details['building_type'] = 'Garden'
        return True, 0.85, details

    # Fixture/household electronics (distinguishable from true gadgets by
    # absence of AmmoType / BatteryMod and no DrainableUses)
    if disp_cat in FIXTURE_DISPLAY_CATS:
        has_battery = has_property('BatteryMod', props) or has_property('RequiresElectricity', props)
        has_ammo = has_property('AmmoType', props)
        is_drainable = get_stat('UseDelta', props) > 0
        if not has_battery and not has_ammo and not is_drainable:
            details['building_type'] = 'Fixture'
            details['fixture_subtype'] = _get_fixture_subtype(item_id, props)
            return True, 0.80, details

    # ── 4. ID token matching ──────────────────────────────────────────────
    NON_BUILDING_MATERIAL_ID_CATS = {'food', 'memento', 'corpse', 'tool', 'household', 'accessory'}
    if id_matches_pattern(item_id, MATERIAL_ID) and disp_cat not in NON_BUILDING_MATERIAL_ID_CATS:
        details['building_type'] = 'Material'
        return True, 0.80, details

    if id_matches_pattern(item_id, FIXTURE_ID):
        details['building_type'] = 'Fixture'
        details['fixture_subtype'] = _get_fixture_subtype(item_id, props)
        return True, 0.78, details

    if id_matches_pattern(item_id, VEHICLE_PART_ID):
        details['building_type'] = 'Vehicle'
        return True, 0.78, details

    if id_matches_pattern(item_id, SEED_ID):
        details['building_type'] = 'Garden.Seed'
        return True, 0.78, details

    if id_matches_pattern(item_id, GARDEN_ID):
        details['building_type'] = 'Garden'
        return True, 0.75, details

    if id_matches_pattern(item_id, FURNITURE_ID):
        details['building_type'] = 'Furniture'
        details['furniture_subtype'] = _get_furniture_subtype(item_id)
        return True, 0.72, details

    # ── 5. Script-tag overlap ─────────────────────────────────────────────
    # Only use script-tag evidence when the display category isn't clearly
    # non-building (mementos, junk, jewellery, etc.).
    NON_BUILDING_DISPLAY_CATS = {'memento', 'junk', 'jewelry', 'ammo', 'camping',
                                  'fishing', 'cartography', 'firstaid', 'sports',
                                  'animalpart', 'cooking', 'literature', 'skillbook',
                                  'food', 'tool', 'household', 'accessory', 'corpse'}
    if disp_cat not in NON_BUILDING_DISPLAY_CATS:
        overlap = script_tags & BUILDING_SCRIPT_TAGS
        if len(overlap) >= 1:
            details['building_type'] = 'Material'
            details['script_tag_evidence'] = list(overlap)
            return True, 0.70, details

    return False, 0.0, details


# --------------------------------------------------------------------------
# Tag generator
# --------------------------------------------------------------------------

def get_building_tags(item_id, props):
    """
    Generate Building.* tags from the signature match.

    Primary tag hierarchy:
      Building.Moveable   | Building.Material   | Building.Furniture.*
      Building.Fixture.*  | Building.Vehicle    | Building.Garden
      Building.Survival.*

    Additional quality descriptors:
      Quality.Waste   when item name contains "broken"/"scrap"/"damaged"
    """
    matches, confidence, details = matches_building_signature(item_id, props)

    if not matches:
        return []

    building_type = details.get('building_type', 'Material')
    primary_tag = f"Building.{building_type}"

    if building_type == 'Furniture':
        furniture_subtype = details.get('furniture_subtype', 'General')
        primary_tag = f"{primary_tag}.{furniture_subtype}"

    if building_type == 'Fixture':
        fixture_subtype = details.get('fixture_subtype', 'General')
        primary_tag = f"{primary_tag}.{fixture_subtype}"

    if building_type == 'Survival':
        survival_subtype = details.get('survival_subtype')
        if survival_subtype:
            primary_tag = f"{primary_tag}.{survival_subtype}"

    tags = [primary_tag]

    # Quality descriptor
    lower_id = item_id.lower()
    if any(t in lower_id for t in ('broken', 'scrap', 'damaged', 'dirty', 'old', 'rusted')):
        tags.append('Quality.Waste')

    return tags
