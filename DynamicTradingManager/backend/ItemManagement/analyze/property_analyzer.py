"""
Property Analyzer - Extract and query item properties from vanilla scripts
Provides functions to analyze all properties and find items by specific property values
"""
import re
from collections import defaultdict
from pathlib import Path


def parse_item_file(filepath):
    """Parse a single item file and extract all properties with examples"""
    properties = defaultdict(lambda: {'type': set(), 'examples': [], 'count': 0, 'items': []})
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all item blocks
    item_blocks = re.finditer(r'item\s+(\w+)\s*\{([^}]+)\}', content, re.DOTALL)
    
    for match in item_blocks:
        item_name = match.group(1)
        item_content = match.group(2)
        
        # Parse each property line
        lines = item_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            
            # Match property = value pattern
            prop_match = re.match(r'(\w+)\s*=\s*(.+?),?\s*$', line)
            if prop_match:
                prop_name = prop_match.group(1)
                prop_value = prop_match.group(2).rstrip(',').strip()
                
                # Determine type
                value_type = get_value_type(prop_value)
                
                properties[prop_name]['type'].add(value_type)
                properties[prop_name]['count'] += 1
                properties[prop_name]['items'].append(item_name)
                
                properties[prop_name]['examples'].append({
                    'value': prop_value,
                    'item': item_name
                })
    
    return properties


def get_value_type(value):
    """Determine the type of a property value"""
    # Check for boolean
    if value.lower() in ['true', 'false']:
        return 'Boolean'
    
    # Check for float
    if re.match(r'^-?\d+\.\d+$', value):
        return 'Float'
    
    # Check for integer
    if re.match(r'^-?\d+$', value):
        return 'Integer'
    
    # Check for string (quoted or unquoted)
    return 'String'


def merge_properties(all_props, file_props):
    """Merge properties from a file into the global collection"""
    for prop, data in file_props.items():
        all_props[prop]['type'].update(data['type'])
        all_props[prop]['count'] += data['count']
        all_props[prop]['items'].extend(data['items'])
        all_props[prop]['examples'].extend(data['examples'])


def analyze_all_properties(vanilla_dir):
    """
    Analyze all vanilla item scripts and extract property information
    
    Returns:
        dict: {property_name: {type, count, examples, items}}
    """
    all_properties = defaultdict(lambda: {'type': set(), 'examples': [], 'count': 0, 'items': []})
    
    # Process all item files
    item_files = Path(vanilla_dir).rglob("*.txt")
    for item_file in item_files:
        file_props = parse_item_file(item_file)
        merge_properties(all_properties, file_props)
    
    return dict(all_properties)


def find_items_with_property(vanilla_dir, property_name, value_filter=None):
    """
    Find all items that have a specific property
    
    Args:
        vanilla_dir: Path to vanilla scripts directory
        property_name: Property to search for (e.g., "StressChange", "Alcoholic")
        value_filter: Optional filter for property value (e.g., "-10", "true")
    
    Returns:
        list: [(item_name, property_value, file_path), ...]
    """
    results = []
    
    item_files = Path(vanilla_dir).rglob("*.txt")
    for item_file in item_files:
        with open(item_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all item blocks
        item_blocks = re.finditer(r'item\s+(\w+)\s*\{([^}]+)\}', content, re.DOTALL)
        
        for match in item_blocks:
            item_name = match.group(1)
            item_content = match.group(2)
            
            # Search for the property
            prop_pattern = rf'{property_name}\s*=\s*(.+?),?\s*$'
            prop_matches = re.finditer(prop_pattern, item_content, re.MULTILINE)
            
            for prop_match in prop_matches:
                prop_value = prop_match.group(1).rstrip(',').strip()
                
                # Apply value filter if specified
                if value_filter is None or value_filter.lower() in prop_value.lower():
                    results.append((item_name, prop_value, str(item_file.name)))
    
    return results


def find_items_by_multiple_properties(vanilla_dir, property_filters):
    """
    Find items that match multiple property criteria
    
    Args:
        vanilla_dir: Path to vanilla scripts directory
        property_filters: dict of {property_name: value_filter}
                         e.g., {"StressChange": "-", "Alcoholic": "true"}
    
    Returns:
        list: [(item_name, {prop: value}, file_path), ...]
    """
    results = []
    
    item_files = Path(vanilla_dir).rglob("*.txt")
    for item_file in item_files:
        with open(item_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all item blocks
        item_blocks = re.finditer(r'item\s+(\w+)\s*\{([^}]+)\}', content, re.DOTALL)
        
        for match in item_blocks:
            item_name = match.group(1)
            item_content = match.group(2)
            
            # Check all property filters
            matched_props = {}
            all_match = True
            
            for prop_name, value_filter in property_filters.items():
                prop_pattern = rf'{prop_name}\s*=\s*(.+?),?\s*$'
                prop_match = re.search(prop_pattern, item_content, re.MULTILINE)
                
                if prop_match:
                    prop_value = prop_match.group(1).rstrip(',').strip()
                    
                    # Check if value matches filter
                    if value_filter is None or value_filter.lower() in prop_value.lower():
                        matched_props[prop_name] = prop_value
                    else:
                        all_match = False
                        break
                else:
                    all_match = False
                    break
            
            if all_match and matched_props:
                results.append((item_name, matched_props, str(item_file.name)))
    
    return results


def get_property_statistics(vanilla_dir):
    """
    Get comprehensive statistics about all properties
    
    Returns:
        dict: Statistics including counts, types, distribution
    """
    all_props = analyze_all_properties(vanilla_dir)
    
    stats = {
        'total_properties': len(all_props),
        'boolean_count': sum(1 for p in all_props.values() if 'Boolean' in p['type']),
        'numeric_count': sum(1 for p in all_props.values() if {'Float', 'Integer'} & p['type']),
        'string_count': sum(1 for p in all_props.values() if 'String' in p['type']),
        'most_common': sorted(all_props.items(), key=lambda x: x[1]['count'], reverse=True)[:20],
    }
    
    return stats


def dump_items_by_property(vanilla_dir, property_name, output_format='table'):
    """
    Dump all items that have a specific property
    
    Args:
        vanilla_dir: Path to vanilla scripts directory
        property_name: Property to search for
        output_format: 'table', 'csv', or 'dict'
    
    Returns:
        Formatted output of items with the property
    """
    items = find_items_with_property(vanilla_dir, property_name)
    
    if output_format == 'table':
        output = f"\n{'='*80}\n"
        output += f"Items with property: {property_name}\n"
        output += f"Total found: {len(items)}\n"
        output += f"{'='*80}\n\n"
        
        output += f"{'Item Name':<30} {'Value':<20} {'File':<30}\n"
        output += f"{'-'*80}\n"
        
        for item_name, value, file_name in sorted(items):
            output += f"{item_name:<30} {value:<20} {file_name:<30}\n"
        
        return output
    
    elif output_format == 'csv':
        output = "ItemName,PropertyValue,FileName\n"
        for item_name, value, file_name in sorted(items):
            output += f"{item_name},{value},{file_name}\n"
        return output
    
    elif output_format == 'dict':
        return {
            'property': property_name,
            'count': len(items),
            'items': [
                {'name': name, 'value': val, 'file': file}
                for name, val, file in sorted(items)
            ]
        }
    
    return items


def list_all_properties(vanilla_dir, min_usage=1):
    """
    List all properties found in vanilla items with usage counts
    
    Args:
        vanilla_dir: Path to vanilla scripts directory
        min_usage: Minimum usage count to include in results
    
    Returns:
        list: [(property_name, count, types), ...] sorted by usage
    """
    all_props = analyze_all_properties(vanilla_dir)
    
    results = []
    for prop_name, data in all_props.items():
        if data['count'] >= min_usage:
            types = '/'.join(sorted(data['type']))
            results.append((prop_name, data['count'], types))
    
    # Sort by usage count descending
    results.sort(key=lambda x: x[1], reverse=True)
    
    return results
