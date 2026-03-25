"""
Spawn Analyzer - Parse all Distribution*.lua files for spawn rate data
Provides functions to get spawn weights and calculate rarity scores
Analyzes ProceduralDistributions.lua and Distribution_*.lua files
"""
import re
from collections import defaultdict
from pathlib import Path


_spawn_cache = None


def find_distribution_files(distributions_dir):
    """
    Find all Lua files with spawn distribution data
    
    Looks for:
    - ProceduralDistributions.lua
    - Distribution_*.lua files
    
    Args:
        distributions_dir: Path to directory containing distribution files
    
    Returns:
        list: Paths to all distribution files
    """
    dist_dir = Path(distributions_dir)
    if not dist_dir.exists():
        return []
    
    # Find ProceduralDistributions.lua
    proc_files = list(dist_dir.glob("ProceduralDistributions.lua"))
    
    # Find all Distribution_*.lua files
    dist_files = list(dist_dir.glob("Distribution_*.lua"))
    
    return proc_files + dist_files


def parse_distribution_file(dist_file):
    """Parse a single Distribution*.lua file and extract spawn data"""
    
    with open(dist_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Store spawn data: {item_name: [(location, spawn_weight, source), ...]}
    spawn_data = defaultdict(list)
    
    # Find all distribution lists
    # Pattern: location = { items = { "ItemName", Weight, "ItemName2", Weight2, ... } }
    distribution_blocks = re.findall(
        r'(\w+)\s*=\s*\{[^}]*items\s*=\s*\{([^}]+)\}',
        content,
        re.DOTALL
    )
    
    source = Path(dist_file).name
    
    for location, items_str in distribution_blocks:
        # Remove Lua comments (-- ...) from the string
        # Split by lines, remove comment part, rejoin
        lines = items_str.split('\n')
        cleaned_lines = []
        for line in lines:
            # Remove everything after -- (Lua comment)
            if '--' in line:
                line = line[:line.index('--')]
            cleaned_lines.append(line)
        items_str = '\n'.join(cleaned_lines)
        
        # Parse items and weights
        items_list = [x.strip() for x in items_str.split(',')]
        
        i = 0
        while i < len(items_list) - 1:
            item_entry = items_list[i]
            
            # Skip empty entries
            if not item_entry:
                i += 1
                continue
            
            # Check if this is an item name (quoted string)
            if '"' in item_entry or "'" in item_entry:
                item_name = item_entry.strip('"\'')
                
                # Next should be weight
                try:
                    weight_str = items_list[i + 1].strip()
                    # Skip if next entry is empty
                    if not weight_str:
                        i += 1
                        continue
                    
                    weight = float(weight_str)
                    
                    # Handle Base. prefix
                    if item_name.startswith('Base.'):
                        item_name = item_name.split('.', 1)[1]
                    
                    spawn_data[item_name].append((location, weight, source))
                    i += 2
                except (ValueError, IndexError):
                    i += 1
            else:
                i += 1
    
    return dict(spawn_data)




def merge_spawn_data(*spawn_dicts):
    """Merge spawn data from multiple files"""
    merged = defaultdict(list)
    
    for spawn_dict in spawn_dicts:
        for item_name, spawns in spawn_dict.items():
            merged[item_name].extend(spawns)
    
    return dict(merged)


def load_spawn_data(distributions_dir=None, force_reload=False):
    """
    Load spawn weights from ALL Distribution*.lua files
    Uses caching to avoid repeated file parsing
    
    Args:
        distributions_dir: Path to directory with distribution files (auto-detects if None)
        force_reload: Force reload from files even if cached
    
    Returns:
        dict: {item_name: [(location, spawn_weight, source_file), ...]}
    """
    global _spawn_cache
    
    if _spawn_cache and not force_reload:
        return _spawn_cache
    
    # Auto-detect directory location
    if distributions_dir is None:
        possible_paths = [
            "/home/psychopatz/.steam/steam/steamapps/common/ProjectZomboid/projectzomboid/media/lua/server/Items/",
            "/home/psychopatz/.steam/steamapps/common/ProjectZomboid/projectzomboid/media/lua/server/Items/",
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                distributions_dir = path
                break
        
        if distributions_dir is None:
            raise FileNotFoundError("Could not locate distribution files directory")
    
    # Find all distribution files
    dist_files = find_distribution_files(distributions_dir)
    
    if not dist_files:
        raise FileNotFoundError(f"No Distribution*.lua files found in {distributions_dir}")
    
    print(f"📁 Found {len(dist_files)} distribution files to parse")
    
    # Parse all files and merge data
    all_spawn_data = []
    for dist_file in sorted(dist_files):
        print(f"   Parsing {Path(dist_file).name}...", end=" ", flush=True)
        try:
            spawn_data = parse_distribution_file(dist_file)
            all_spawn_data.append(spawn_data)
            print(f"✅ ({len(spawn_data)} unique items)")
        except Exception as e:
            print(f"⚠️  Error: {e}")
    
    _spawn_cache = merge_spawn_data(*all_spawn_data)
    
    print(f"✅ Merged spawn data from all files: {len(_spawn_cache)} total unique items")
    
    return _spawn_cache


def get_spawn_weight(item_id, distributions_dir=None):
    """
    Get average spawn weight for an item
    
    Args:
        item_id: Item name (without Base. prefix)
        distributions_dir: Optional path to distributions directory
    
    Returns:
        float: Average spawn weight (5.0 default if not found)
    """
    try:
        data = load_spawn_data(distributions_dir)
        spawns = data.get(item_id, [])
        
        if not spawns:
            return 5.0  # Default medium rarity
        
        # Average weight across all locations and sources
        return sum(w[1] for w in spawns) / len(spawns)
    except FileNotFoundError:
        return 5.0  # Default if distribution files not found


def get_spawn_locations(item_id, distributions_dir=None):
    """
    Get all spawn locations for an item
    
    Args:
        item_id: Item name
        distributions_dir: Optional path to distributions directory
    
    Returns:
        list: [(location, weight, source_file), ...]
    """
    try:
        data = load_spawn_data(distributions_dir)
        return data.get(item_id, [])
    except FileNotFoundError:
        return []


def get_spawn_sources(item_id, distributions_dir=None):
    """
    Get which distribution files contain spawn data for an item
    
    Args:
        item_id: Item name
        distributions_dir: Optional path to distributions directory
    
    Returns:
        dict: {source_file: [(location, weight), ...]}
    """
    try:
        spawns = get_spawn_locations(item_id, distributions_dir)
        sources = defaultdict(list)
        
        for location, weight, source in spawns:
            sources[source].append((location, weight))
        
        return dict(sources)
    except FileNotFoundError:
        return {}


def calculate_rarity_from_spawn(spawn_weight):
    """
    Convert spawn weight to rarity tier
    
    Args:
        spawn_weight: Numeric spawn weight
    
    Returns:
        str: Rarity tier (UltraRare, Legendary, Rare, Uncommon, Common)
    """
    if spawn_weight < 0.1:
        return "UltraRare"
    elif spawn_weight < 0.5:
        return "Legendary"
    elif spawn_weight < 2.0:
        return "Rare"
    elif spawn_weight < 5.0:
        return "Uncommon"
    else:
        return "Common"


def calculate_rarity_score(spawn_weight):
    """
    Calculate rarity score (0-100) from spawn weight
    Lower spawn weight = higher score
    
    Args:
        spawn_weight: Numeric spawn weight
    
    Returns:
        float: Score from 0-100
    """
    return max(0, min(100, 100 - spawn_weight * 10))


def get_rarity_statistics(distributions_dir=None):
    """
    Get statistics about spawn rates distribution
    
    Returns:
        dict: Statistics about rarity distribution
    """
    try:
        data = load_spawn_data(distributions_dir)
        
        stats = {
            'total_items': len(data),
            'ultra_rare': 0,
            'legendary': 0,
            'rare': 0,
            'uncommon': 0,
            'common': 0,
        }
        
        for item, spawns in data.items():
            if not spawns:
                continue
            
            # Calculate average spawn weight from all sources
            avg_weight = sum(w[1] for w in spawns) / len(spawns)
            tier = calculate_rarity_from_spawn(avg_weight)
            
            if tier == 'UltraRare':
                stats['ultra_rare'] += 1
            elif tier == 'Legendary':
                stats['legendary'] += 1
            elif tier == 'Rare':
                stats['rare'] += 1
            elif tier == 'Uncommon':
                stats['uncommon'] += 1
            else:
                stats['common'] += 1
        
        return stats
    except FileNotFoundError:
        return {'total_items': 0, 'error': 'Distribution files not found'}


def get_items_by_rarity(rarity_tier, distributions_dir=None, limit=None):
    """
    Get all items of a specific rarity tier
    
    Args:
        rarity_tier: "UltraRare", "Legendary", "Rare", "Uncommon", or "Common"
        distributions_dir: Optional path to distributions directory
        limit: Optional limit on number of items returned
    
    Returns:
        list: [(item_name, avg_spawn_weight, spawn_count), ...]
    """
    try:
        data = load_spawn_data(distributions_dir)
        results = []
        
        for item, spawns in data.items():
            if not spawns:
                continue
            
            avg_weight = sum(w[1] for w in spawns) / len(spawns)
            tier = calculate_rarity_from_spawn(avg_weight)
            
            if tier == rarity_tier:
                results.append((item, avg_weight, len(spawns)))
        
        # Sort by spawn weight (ascending for rarest first)
        results.sort(key=lambda x: x[1])
        
        if limit:
            results = results[:limit]
        
        return results
    except FileNotFoundError:
        return []


def find_items_with_spawn_weight_range(min_weight, max_weight, distributions_dir=None):
    """
    Find items with spawn weights in a specific range
    
    Args:
        min_weight: Minimum spawn weight
        max_weight: Maximum spawn weight
        distributions_dir: Optional path to distributions directory
    
    Returns:
        list: [(item_name, avg_weight, source_count), ...]
    """
    try:
        data = load_spawn_data(distributions_dir)
        results = []
        
        for item, spawns in data.items():
            if not spawns:
                continue
            
            avg_weight = sum(w[1] for w in spawns) / len(spawns)
            
            if min_weight <= avg_weight <= max_weight:
                results.append((item, avg_weight, len(spawns)))
        
        results.sort(key=lambda x: x[1])
        return results
    except FileNotFoundError:
        return []


def calculate_enhanced_rarity_score(item_id, item_props, distributions_dir=None):
    """
    Calculate comprehensive rarity score using spawn data + item properties
    
    Args:
        item_id: Item name
        item_props: Dictionary of item properties
        distributions_dir: Optional path to distributions directory
    
    Returns:
        tuple: (final_score, rarity_tier, breakdown)
    """
    # 1. Spawn frequency (60% weight)
    spawn_weight = get_spawn_weight(item_id, distributions_dir)
    spawn_score = calculate_rarity_score(spawn_weight)
    
    # 2. Combat/utility stats (20% weight)
    stat_score = 0
    if 'MaxDamage' in item_props:
        try:
            stat_score = float(item_props['MaxDamage']) * 50
        except (ValueError, TypeError):
            pass
    elif 'BloodDefense' in item_props:
        try:
            blood = float(item_props.get('BloodDefense', 0))
            bite = float(item_props.get('BitDefense', 0))
            stat_score = (blood + bite) * 10
        except (ValueError, TypeError):
            pass
    
    # 3. Durability (10% weight)
    durability_score = 0
    if 'ConditionMax' in item_props:
        try:
            durability_score = float(item_props['ConditionMax']) * 2
        except (ValueError, TypeError):
            pass
    
    # 4. Tags & categories (10% weight)
    tag_score = 0
    tags_str = str(item_props.get('Tags', '')).lower()
    if 'military' in tags_str:
        tag_score += 30
    if 'police' in tags_str:
        tag_score += 20
    if 'tactical' in tags_str:
        tag_score += 25
    
    category = item_props.get('DisplayCategory', '')
    if category == 'SurvivalGear':
        tag_score += 20
    
    # 5. Boolean indicators (bonuses)
    bonus = 0
    if item_props.get('TwoHandWeapon', '').lower() == 'true':
        bonus += 10
    if item_props.get('RequiresEquippedBothHands', '').lower() == 'true':
        bonus += 15
    if item_props.get('IsHighTier', '').lower() == 'true':
        bonus += 20
    if item_props.get('Sterile', '').lower() == 'true':
        bonus += 10
    
    # Calculate weighted score
    final_score = (
        spawn_score * 0.6 +
        min(100, stat_score) * 0.2 +
        min(100, durability_score) * 0.1 +
        min(100, tag_score) * 0.1 +
        bonus
    )
    
    # Cap at 100
    final_score = min(100, final_score)
    
    # Determine tier
    if final_score >= 90:
        tier = 'UltraRare'
    elif final_score >= 75:
        tier = 'Legendary'
    elif final_score >= 60:
        tier = 'Rare'
    elif final_score >= 40:
        tier = 'Uncommon'
    else:
        tier = 'Common'
    
    breakdown = {
        'spawn_score': spawn_score,
        'spawn_weight': spawn_weight,
        'stat_score': stat_score,
        'durability_score': durability_score,
        'tag_score': tag_score,
        'bonus': bonus,
        'final_score': final_score,
        'tier': tier
    }
    
    return final_score, tier, breakdown
