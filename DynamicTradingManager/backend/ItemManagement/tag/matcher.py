"""
Signature matcher - coordinates property-based matching across all categories.
Runs items against all 8 signature patterns and selects best match.
"""
from .signatures import (
    matches_weapon_signature, get_weapon_tags,
    matches_fishing_signature, get_fishing_tags,
    matches_clothing_signature, get_clothing_tags,
    matches_food_signature, get_food_tags,
    matches_tool_signature, get_tool_tags,
    matches_electronics_signature, get_electronics_tags,
    matches_medical_signature, get_medical_tags,
    matches_container_signature, get_container_tags,
    matches_resource_signature, get_resource_tags,
    matches_building_signature, get_building_tags,
)


# Signature definitions in evaluation order (priority)
# Building is placed before Resource/Tool/Electronics because Mov_* and
# DisplayCategory-matched items should be routed unambiguously.
SIGNATURES = [
    ('Fishing', matches_fishing_signature, get_fishing_tags),
    ('Weapon', matches_weapon_signature, get_weapon_tags),
    ('Food', matches_food_signature, get_food_tags),
    ('Clothing', matches_clothing_signature, get_clothing_tags),
    ('Container', matches_container_signature, get_container_tags),
    ('Medical', matches_medical_signature, get_medical_tags),
    ('Building', matches_building_signature, get_building_tags),
    ('Tool', matches_tool_signature, get_tool_tags),
    ('Electronics', matches_electronics_signature, get_electronics_tags),
    ('Resource', matches_resource_signature, get_resource_tags),
]
SIGNATURE_ORDER = {name: index for index, (name, _, _) in enumerate(SIGNATURES)}


def match_item(item_id, props):
    """
    Match item against all signatures and return best match.
    
    Args:
        item_id: Item identifier
        props: Properties string
    
    Returns:
        dict: Match result with keys:
            - category: Category name (str)
            - confidence: Confidence score (0-1)
            - details: Category-specific details (dict)
            - tags: Auto-generated tags (list)
            - all_matches: All category matches (list)
    """
    all_matches = []
    
    # Try all signatures
    for category_name, matcher_func, tag_func in SIGNATURES:
        matches, confidence, details = matcher_func(item_id, props)
        
        all_matches.append({
            'category': category_name,
            'matches': matches,
            'confidence': confidence,
            'details': details,
            'tags': tag_func(item_id, props) if matches else []
        })
    
    # Prefer signatures that explicitly matched. If none matched, keep the
    # highest-confidence candidate for debugging/fallback visibility.
    matched_candidates = [m for m in all_matches if m['matches']]
    valid_matches = matched_candidates or [m for m in all_matches if m['confidence'] > 0]

    if not valid_matches:
        # No match found - return generic result
        return {
            'category': 'Unknown',
            'confidence': 0.0,
            'details': {},
            'tags': [],
            'all_matches': all_matches,
            'matched': False
        }
    
    best_match = max(
        valid_matches,
        key=lambda x: (x['confidence'], -SIGNATURE_ORDER[x['category']])
    )
    
    return {
        'category': best_match['category'],
        'confidence': best_match['confidence'],
        'details': best_match['details'],
        'tags': best_match['tags'],
        'all_matches': all_matches,
        'matched': best_match['matches']
    }


def match_batch(items_dict):
    """
    Match multiple items at once.
    
    Args:
        items_dict: Dict of {item_id: props}
    
    Returns:
        dict: Dict of {item_id: match_result}
    """
    results = {}
    for item_id, props in items_dict.items():
        results[item_id] = match_item(item_id, props)
    return results


def get_multi_category_matches(item_id, props, min_confidence=0.3):
    """
    Get all category matches above minimum confidence.
    Useful for items that could fit multiple categories.
    
    Args:
        item_id: Item identifier
        props: Properties string
        min_confidence: Minimum confidence threshold
    
    Returns:
        list: List of matching categories with confidence
    """
    result = match_item(item_id, props)
    
    matches = []
    for match in result['all_matches']:
        if match['confidence'] >= min_confidence:
            matches.append({
                'category': match['category'],
                'confidence': match['confidence'],
                'tags': match['tags']
            })
    
    # Sort by confidence descending
    return sorted(matches, key=lambda x: x['confidence'], reverse=True)


def compare_signatures(item_id, props):
    """
    Compare all signatures for an item (debugging utility).
    
    Args:
        item_id: Item identifier
        props: Properties string
    
    Returns:
        dict: Detailed comparison of all signatures
    """
    result = match_item(item_id, props)
    
    comparison = {
        'item_id': item_id,
        'best_match': result['category'],
        'best_confidence': result['confidence'],
        'all_signatures': []
    }
    
    for match in result['all_matches']:
        comparison['all_signatures'].append({
            'category': match['category'],
            'confidence': round(match['confidence'], 3),
            'matched': match['matches'],
            'details': match['details']
        })
    
    # Sort by confidence
    comparison['all_signatures'].sort(
        key=lambda x: x['confidence'],
        reverse=True
    )
    
    return comparison
