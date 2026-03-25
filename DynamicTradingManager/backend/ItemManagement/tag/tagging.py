"""
Tagging system for intelligent item categorization
Generates nested tags based on item properties and ID patterns
"""
import re
from ..commons.vanilla_loader import get_stat, has_property, count_learned_recipes
from ..config import EXCLUDED_PATTERNS
from .signatures.fishing import get_fishing_tags
from .signatures.food import get_food_tags
from .signatures.medical import get_medical_tags
from .signatures.containers import get_container_tags
from .signatures.clothing import get_clothing_tags
from .signatures.resources import get_resource_tags
from .signatures.building import matches_building_signature, get_building_tags
from .signatures.tools import matches_tool_signature, get_tool_tags
from .signatures.weapons import get_weapon_tags
from .signatures.electronics import get_electronics_tags


LITERATURE_DISPLAY_CATS = {'literature', 'skillbook', 'book', 'reciperesource', 'cartography'}
RESOURCE_PART_PATTERNS = [
    'AxeHead', 'HatchetHead', 'HammerHead', 'MaceHead', 'SpearHead',
    'Blade', 'SwordBlade', 'KnifeBlade', 'MacheteBlade',
    'NoTang', 'Shard', 'Mold', 'Unfired',
]


CARD_ID_PATTERNS = [
    'card_',
    'postcard',
    'carddeck',
    'tarotcarddeck',
]


def _get_display_category(props):
    """Extract lowercase DisplayCategory from raw item properties."""
    m = re.search(r"DisplayCategory\s*=\s*([^,\n\s;]+)", props, re.IGNORECASE)
    return m.group(1).lower() if m else ''


def _get_type_token(props):
    """Extract normalized lowercase Type token from raw item properties."""
    m = re.search(r"Type\s*=\s*([^,\n\s;]+)", props, re.IGNORECASE)
    return m.group(1).lower() if m else ''


def _item_tokens(item_id):
    normalized = re.sub(r'([a-z])([A-Z])', r'\1 \2', item_id or '')
    normalized = normalized.replace('_', ' ')
    return [token.lower() for token in re.findall(r'[A-Za-z]+', normalized)]


def _is_card_item(item_lower):
    """Detect greeting/deck/post cards for Literature.Cards subcategory."""
    return any(pattern in item_lower for pattern in CARD_ID_PATTERNS)


def _is_literature_item(item_id, props):
    """Heuristic detector for books/magazines/recipe-learning items."""
    item_lower = item_id.lower()
    disp_cat = _get_display_category(props)
    type_token = _get_type_token(props)

    has_type_literature = type_token in {'literature', 'base:literature'}
    has_type_map = type_token == 'base:map'
    if type_token == 'base:container':
        return False
    has_map_property = bool(re.search(r"\bMap\s*=\s*", props, re.IGNORECASE))
    has_media_category = bool(re.search(r"\bMediaCategory\s*=\s*", props, re.IGNORECASE))
    has_recipe_learning = bool(re.search(r"(LearnedRecipes|TeachedRecipes)\s*=", props, re.IGNORECASE))
    has_skill_learning = bool(re.search(r"(SkillTrained|LvlSkillTrained|NumLevelsTrained)\s*=", props, re.IGNORECASE))
    has_reading_meta = bool(re.search(r"(NumberOfPages|PageToWrite|CanBeWrite|LiteratureOnRead)\s*=", props, re.IGNORECASE))

    # Covers vanilla + many modded naming conventions.
    looks_like_literature_id = bool(re.search(
        r"(skillbook|book\d*$|mag\d*$|magazine|comic|schematic|manual|guide|journal|recipeclipping|tarotcarddeck|carddeck|card_|postcard)",
        item_lower,
        re.IGNORECASE,
    ))
    looks_like_media_id = bool(re.search(r"(vhs|cassette|disc_|dvd|cdplayer|cd$)", item_lower, re.IGNORECASE))

    # Prevent plantables/seed sacks that also expose recipe-like fields.
    is_garden_seed_like = ('bagseed' in item_lower or item_lower.endswith('seed') or '_seed' in item_lower)
    if is_garden_seed_like:
        return False

    # Never treat explicit ammo/weapon payloads as reading material.
    if has_property(props, "AmmoType") or has_property(props, "ProjectileCount"):
        return False
    if type_token in {'weapon', 'base:weapon'}:
        return False

    if has_type_literature or has_type_map:
        return True
    if has_map_property:
        return True
    if has_media_category:
        return True
    if disp_cat in LITERATURE_DISPLAY_CATS:
        return True
    if looks_like_literature_id:
        return True
    if disp_cat == 'entertainment' and looks_like_media_id:
        return True
    if (has_recipe_learning or has_skill_learning or has_reading_meta) and (looks_like_literature_id or disp_cat == 'reciperesource'):
        return True

    return (
        looks_like_literature_id and (has_recipe_learning or has_skill_learning or has_reading_meta)
    ) or (looks_like_media_id and has_media_category)


def _is_resource_part_item(item_id, props):
    """Detect salvage/crafting components that should be Resource.Parts."""
    item_lower = item_id.lower()
    if any(p.lower() in item_lower for p in RESOURCE_PART_PATTERNS):
        # Avoid matching common seed names that include "seed" in IDs.
        if 'bagseed' in item_lower or item_lower.endswith('seed') or '_seed' in item_lower:
            return False
        return True

    # Script-tag evidence for component/tool-head items.
    if re.search(r"Tags\s*=\s*[^\n]*base:toolhead", props, re.IGNORECASE):
        return True

    return False


def is_excluded(item_id):
    """Check if item should be excluded from registration"""
    for pattern in EXCLUDED_PATTERNS:
        if re.search(pattern, item_id, re.IGNORECASE):
            return True
    return False


def determine_rarity(item_id, props):
    """Determine rarity based on item properties"""
    if has_property(props, "WorldStaticModel"):
        return "Rare"
    
    if any(x in item_id for x in ['Police', 'Military', 'Army', 'Swat']):
        return "Uncommon"
    
    if has_property(props, "Sterile"):
        return "Uncommon"
    
    # Skill books by level
    if 'SkillBook' in item_id or 'Book' in item_id:
        level_match = re.search(r'(\d+)$', item_id)
        if level_match:
            level = int(level_match.group(1))
            if level >= 5:
                return "Legendary"
            elif level >= 3:
                return "Rare"
            elif level >= 2:
                return "Uncommon"
    
    return "Common"


def determine_quality(item_id, props):
    """Determine quality descriptor"""
    item_tokens = _item_tokens(item_id)
    if has_property(props, "Sterile"):
        return "Quality.Sterile"
    
    if any(token in item_tokens for token in ['gold', 'diamond', 'designer', 'expensive']):
        return "Quality.Luxury"
    
    has_empty_hint = bool(re.search(r"Tooltip_item_empty_", props, re.IGNORECASE))
    if any(x in item_id.lower() for x in ['empty', 'dirty', 'broken', 'scrap']):
        return "Quality.Waste"
    if has_empty_hint:
        return "Quality.Waste"
    
    return None


def determine_origin(item_id, props):
    """Determine source-of-item origin descriptor."""
    return "Origin.Vanilla"


def determine_theme(item_id, props):
    """Determine theme descriptors"""
    themes = []

    item_lower = item_id.lower()
    item_tokens = set(_item_tokens(item_id))

    if any(x in item_lower for x in ['camp', 'outdoor', 'wilderness', 'survival']):
        themes.append("Theme.Survival")

    if any(x in item_lower for x in ['weapon', 'combat', 'tactical', 'armor']):
        themes.append("Theme.Combat")

    if any(x in item_lower for x in ['winter', 'warm', 'insulated', 'thermal']):
        insulation = get_stat(props, "Insulation", 0)
        if insulation > 0.5:
            themes.append("Theme.Winter")

    if item_tokens.intersection({'police', 'sheriff', 'cop'}):
        themes.append("Theme.Police")
    if item_tokens.intersection({'military', 'army', 'tactical'}):
        themes.append("Theme.Militia")
    if item_tokens.intersection({'doctor', 'medic', 'medical', 'surgical', 'hospital'}):
        themes.append("Theme.Clinical")
    if item_tokens.intersection({'industrial', 'factory', 'warehouse'}):
        themes.append("Theme.Industrial")
    if item_tokens.intersection({'primitive', 'tribal', 'stoneage', 'ancestral'}):
        themes.append("Theme.Primitive")

    deduped = []
    seen = set()
    for theme in themes:
        if theme not in seen:
            deduped.append(theme)
            seen.add(theme)

    return deduped


def _get_medical_tool_tags(item_id, props):
    """Return tool tags only for medical instruments."""
    matches, _confidence, details = matches_tool_signature(item_id, props)
    if matches and details.get('tool_type', '').startswith('Medical'):
        return get_tool_tags(item_id, props)
    return []


def _get_cookware_tool_tags(item_id, props):
    """Return tool tags only for cookware-adjacent items."""
    matches, _confidence, details = matches_tool_signature(item_id, props)
    if matches and details.get('tool_type') == 'Cookware':
        return get_tool_tags(item_id, props)
    return []


def _get_farming_tool_tags(item_id, props):
    """Return tool tags only for farming/gardening implements."""
    matches, _confidence, details = matches_tool_signature(item_id, props)
    if not matches or details.get('tool_type') != 'Farming':
        return []

    item_lower = item_id.lower()
    disp_cat = _get_display_category(props)
    strong_farming_id = any(token in item_lower for token in [
        'shovel', 'rake', 'gardenfork', 'handfork', 'gardenhoe',
        'pickaxe', 'scythe', 'handscythe', 'primitivescythe', 'sickle',
    ])
    strong_farming_tag = bool(re.search(
        r"Tags\s*=\s*[^\n]*(base:digplow|base:digworms|base:cutplant|base:scythe|base:pickaxe|base:clearashes|base:takedirt|base:takedung|base:removestump)",
        props,
        re.IGNORECASE,
    ))
    crafted_weapon_like = (
        disp_cat in {'weaponcrafted', 'materialweapon'} or
        any(token in item_lower for token in ['baseballbat_', 'cudgel_', 'spear', 'scrapweapon', 'longhandle_', 'head'])
    )

    if not crafted_weapon_like and (disp_cat == 'gardeningweapon' or strong_farming_id or strong_farming_tag):
        return get_tool_tags(item_id, props)
    return []


def categorize_item(item_id, props):
    """
    Intelligently categorize item and generate nested tags
    Returns: (primary_tag, additional_tags[])
    """
    fishing_tags = get_fishing_tags(item_id, props)
    if fishing_tags:
        return fishing_tags[0], fishing_tags[1:]

    # === LITERATURE ===
    if _is_literature_item(item_id, props):
        recipes = count_learned_recipes(props)
        has_teached = bool(re.search(r"TeachedRecipes\s*=", props, re.IGNORECASE))
        has_skill_learning = bool(re.search(r"(SkillTrained|LvlSkillTrained|NumLevelsTrained)\s*=", props, re.IGNORECASE))
        item_lower = item_id.lower()
        disp_cat = _get_display_category(props)
        type_token = _get_type_token(props)
        has_map_property = bool(re.search(r"\bMap\s*=\s*", props, re.IGNORECASE))
        has_media_category = bool(re.search(r"\bMediaCategory\s*=\s*", props, re.IGNORECASE))

        if recipes > 0 or has_teached or 'schematic' in item_lower or 'recipe' in item_lower:
            return "Literature.Recipe", []
        elif has_media_category or any(x in item_lower for x in ['vhs', 'cassette', 'disc_', 'dvd']):
            return "Literature.Media", []
        elif has_skill_learning or 'skillbook' in item_lower:
            return "Literature.SkillBook", []
        elif _is_card_item(item_lower):
            return "Literature.Cards", []
        elif type_token == 'base:map' or has_map_property or disp_cat == 'cartography':
            return "Literature.Media", []
        elif any(x in item_lower for x in ['mag', 'magazine', 'comic']):
            return "Literature.Media", []
        else:
            return "Literature.Book", []

    # === MEDICAL TOOLS ===
    medical_tool_tags = _get_medical_tool_tags(item_id, props)
    if medical_tool_tags:
        return medical_tool_tags[0], medical_tool_tags[1:]

    # === MEDICAL SUPPLIES ===
    medical_tags = get_medical_tags(item_id, props)
    if medical_tags:
        return medical_tags[0], medical_tags[1:]

    # === FOOD ===
    food_tags = get_food_tags(item_id, props)
    if food_tags:
        return food_tags[0], food_tags[1:]

    # === CONTAINER ===
    container_tags = get_container_tags(item_id, props)
    if container_tags:
        return container_tags[0], container_tags[1:]

    # === CLOTHING ===
    clothing_tags = get_clothing_tags(item_id, props)
    if clothing_tags:
        return clothing_tags[0], clothing_tags[1:]

    # === COOKWARE TOOLS ===
    cookware_tool_tags = _get_cookware_tool_tags(item_id, props)
    if cookware_tool_tags:
        return cookware_tool_tags[0], cookware_tool_tags[1:]

    # === FARMING / GARDEN TOOLS ===
    farming_tool_tags = _get_farming_tool_tags(item_id, props)
    if farming_tool_tags:
        return farming_tool_tags[0], farming_tool_tags[1:]

    # === WEAPON ===
    weapon_tags = get_weapon_tags(item_id, props)
    if weapon_tags:
        return weapon_tags[0], weapon_tags[1:]

    # === ELECTRONICS ===
    electronics_tags = get_electronics_tags(item_id, props)
    if electronics_tags:
        return electronics_tags[0], electronics_tags[1:]

    # === TOOL ===
    tool_tags = get_tool_tags(item_id, props)
    if tool_tags:
        return tool_tags[0], tool_tags[1:]

    # === RESOURCE ===
    resource_tags = get_resource_tags(item_id, props)
    if resource_tags:
        return resource_tags[0], resource_tags[1:]

    # === BUILDING / CONSTRUCTION ===
    # Let moveables and fixtures route out after explicit resource matching.
    building_matches, _building_conf, _building_details = matches_building_signature(item_id, props)
    if building_matches:
        building_tags = get_building_tags(item_id, props)
        return building_tags[0], building_tags[1:]

    # === MISC (fallback) ===
    return "Misc.General", []


def generate_tags(item_id, props):
    """Generate complete tag set for an item"""
    primary, additional_tags = categorize_item(item_id, props)
    
    tags = [primary]
    tags.append(f"Rarity.{determine_rarity(item_id, props)}")
    
    quality = determine_quality(item_id, props)
    if quality:
        tags.append(quality)
    
    origin = determine_origin(item_id, props)
    if origin:
        tags.append(origin)
    
    tags.extend(determine_theme(item_id, props))
    tags.extend(additional_tags)
    
    return tags


def parse_tags(tags_str):
    """Parse nested tags from Lua tags array string"""
    tag_dict = {
        'primary': None,
        'rarity': 'Common',
        'quality': None,
        'origin': 'Vanilla',
        'theme': []
    }
    
    tags = re.findall(r'"([^"]+)"', tags_str)
    
    for tag in tags:
        parts = tag.split('.')
        root = parts[0]

        if root == 'Rarity' and len(parts) > 1:
            tag_dict['rarity'] = parts[1]
        elif root == 'Quality' and len(parts) > 1:
            tag_dict['quality'] = parts[1]
        elif root == 'Origin' and len(parts) > 1:
            tag_dict['origin'] = parts[1]
        elif root == 'Theme':
            tag_dict['theme'].append('.'.join(parts[1:]) if len(parts) > 1 else 'General')
        elif '.' in tag and tag_dict['primary'] is None:
            # Any non-descriptor dotted tag is considered primary.
            tag_dict['primary'] = tag
    
    return tag_dict


def get_category_from_tags(tags_dict):
    """Extract category hierarchy from primary tag"""
    if not tags_dict['primary']:
        return ['Misc'], []
    
    parts = tags_dict['primary'].split('.')
    return parts[0:1], parts[1:] if len(parts) > 1 else []
