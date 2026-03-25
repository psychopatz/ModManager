"""
Mod item data loader and duplicate detection
"""
import os
import re


def get_mod_data(mod_path, silent=False):
    """
    Scan mod registries and extract referenced item IDs
    
    Args:
        mod_path: Path to mod item Lua files
        silent: Suppress print output
    
    Returns:
        tuple: (mod_data, mod_duplicates) dictionaries
    """
    mod_data = {}
    mod_duplicates = {}
    
    if not silent:
        print(f"[*] Scanning Mod Registries: {mod_path}")
    
    if not os.path.exists(mod_path):
        if not silent:
            print(f"[!] Mod path not found: {mod_path}")
        return mod_data, mod_duplicates
    
    for root, dirs, files in os.walk(mod_path):
        for file in sorted(files):
            if not file.endswith(".lua"):
                continue
            
            file_path = os.path.join(root, file)
            file_rel = os.path.relpath(file_path, mod_path)
            
            with open(file_path, "r", errors="ignore") as f:
                content = f.read()
                
                # Find item references: both item = "Base.X" and ["Base.X"] patterns
                found = re.findall(r'(?:item\s*=\s*|\[)"Base\.(\w+)"', content)
                
                for item_id in found:
                    if item_id in mod_data:
                        # Track duplicates
                        if item_id not in mod_duplicates:
                            mod_duplicates[item_id] = [mod_data[item_id]['origin']]
                        mod_duplicates[item_id].append(file_rel)
                    
                    mod_data[item_id] = {'origin': file_rel}
    
    return mod_data, mod_duplicates


def get_mod_duplicates(mod_data):
    """
    Find duplicate item registrations across mod files
    
    Args:
        mod_data: Dictionary of mod items
    
    Returns:
        dict: Mapping of item_id -> list of origins
    """
    duplicates = {}
    
    for item_id, data in mod_data.items():
        if isinstance(data.get('origin'), list):
            if len(data['origin']) > 1:
                duplicates[item_id] = data['origin']
    
    return duplicates


def find_item_in_mod(item_id, mod_data):
    """
    Check if item exists in mod data
    
    Args:
        item_id: Item ID to search for
        mod_data: Mod data dictionary
    
    Returns:
        dict: Item metadata or None
    """
    return mod_data.get(item_id)


def get_items_by_origin(origin_pattern, mod_data):
    """
    Get all items registered in files matching origin pattern
    
    Args:
        origin_pattern: File path pattern to match
        mod_data: Mod data dictionary
    
    Returns:
        list: Item IDs matching the pattern
    """
    matches = []
    for item_id, data in mod_data.items():
        if origin_pattern.lower() in data.get('origin', '').lower():
            matches.append(item_id)
    return matches


def count_items_by_file(mod_data):
    """
    Count item registrations per file
    
    Args:
        mod_data: Mod data dictionary
    
    Returns:
        dict: File -> count mapping
    """
    counts = {}
    for item_id, data in mod_data.items():
        origin = data.get('origin', 'Unknown')
        counts[origin] = counts.get(origin, 0) + 1
    return counts
