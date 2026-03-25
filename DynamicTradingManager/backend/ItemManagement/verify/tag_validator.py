"""
Tag validation and dynamic tag library loading
"""
import re
import os


def get_dynamic_tags(tag_ref_path=None):
    """
    Extracts the FULL tag library from Docs/Tags_Reference.md
    
    Args:
        tag_ref_path: Optional path to Tags_Reference.md
                      If not provided, searches relative to this module
    
    Returns:
        tuple: (all_tags, roots) - List of all tags and their root categories
    """
    if not tag_ref_path:
        # Search relative to this module
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tag_ref_path = os.path.join(script_dir, "../../../Docs/Tags_Reference.md")
        tag_ref_path = os.path.normpath(tag_ref_path)
    
    all_tags = []
    
    if os.path.exists(tag_ref_path):
        with open(tag_ref_path, "r") as f:
            content = f.read()
            # Find everything inside backticks that looks like a tag (Root.Sub or Global.*)
            # This captures full hierarchies like Food.NonPerishable.Canned
            all_tags = re.findall(r"`([A-Z][a-zA-Z]+\.[^`]+)`", content)
    
    # Sort and get unique tags
    all_tags = sorted(list(set(all_tags)))
    
    # Extract root categories
    roots = sorted(list(set([t.split('.')[0] for t in all_tags if '.' in t])))
    
    return all_tags, roots


def validate_tag(tag, all_tags):
    """
    Check if tag exists in the library
    
    Args:
        tag: Tag string to validate
        all_tags: List of valid tags
    
    Returns:
        bool: True if tag is valid
    """
    return tag in all_tags


def get_tags_by_root(root, all_tags):
    """
    Get all tags for a specific root category
    
    Args:
        root: Root category name (e.g., "Food", "Weapon")
        all_tags: List of all tags
    
    Returns:
        list: Tags matching the root
    """
    return [t for t in all_tags if t.startswith(root + ".")]


def suggest_tag(partial_tag, all_tags, max_suggestions=5):
    """
    Suggest valid tags based on partial input
    
    Args:
        partial_tag: Partial tag string
        all_tags: List of valid tags
        max_suggestions: Maximum suggestion count
    
    Returns:
        list: Suggested tags
    """
    partial_lower = partial_tag.lower()
    matches = [t for t in all_tags if partial_lower in t.lower()]
    return matches[:max_suggestions]


def parse_tags_from_lua(tags_str):
    """
    Parse Lua tags array string into components
    
    Args:
        tags_str: Lua tags string like: "Food.Drink.Alcohol", "Rarity.Rare"
    
    Returns:
        dict: Parsed tag components
    """
    tag_dict = {
        'primary': None,
        'rarity': 'Common',
        'quality': None,
        'origin': None,
        'theme': []
    }
    
    tags = re.findall(r'"([^"]+)"', tags_str) if '"' in tags_str else [tags_str]
    
    for tag in tags:
        parts = tag.split('.')
        root = parts[0]
        
        category_roots = ['Food', 'Weapon', 'Tool', 'Medical', 'Container', 'Resource', 
                         'Literature', 'Electronics', 'Appliance', 'Clothing', 'Vehicle', 'Misc']
        
        if root in category_roots:
            tag_dict['primary'] = tag
        elif root == 'Rarity' and len(parts) > 1:
            tag_dict['rarity'] = parts[1]
        elif root == 'Quality' and len(parts) > 1:
            tag_dict['quality'] = parts[1]
        elif root == 'Origin' and len(parts) > 1:
            tag_dict['origin'] = parts[1]
        elif root == 'Theme':
            tag_dict['theme'].append('.'.join(parts[1:]) if len(parts) > 1 else 'General')
    
    return tag_dict


def get_category_from_tags(tags_dict):
    """
    Extract category hierarchy from primary tag
    
    Args:
        tags_dict: Parsed tags dictionary
    
    Returns:
        tuple: (main_category, subcategories)
    """
    if not tags_dict['primary']:
        return ['Misc'], []
    
    parts = tags_dict['primary'].split('.')
    return parts[0:1], parts[1:] if len(parts) > 1 else []
