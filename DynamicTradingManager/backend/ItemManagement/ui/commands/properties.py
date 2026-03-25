"""
Property analysis and querying commands
"""
from collections import defaultdict
from ...analyze.property_analyzer import (
    analyze_all_properties,
    find_items_with_property,
    dump_items_by_property
)


def find_property(vanilla_dir, property_name, value_filter=None, chunk_limit=None):
    """Find items with specific property"""
    print(f"\n🔍 Searching for items with property: {property_name}")
    if value_filter:
        print(f"   Filter: {value_filter}")
    if chunk_limit is not None:
        print(f"   Chunk limit: {chunk_limit}")
    print("-" * 60)
    
    results = find_items_with_property(vanilla_dir, property_name, value_filter)
    
    if not results:
        print(f"❌ No items found with property '{property_name}'")
        if value_filter:
            print(f"   Try without the value filter to see all items with this property")
        return
    
    print(f"✅ Found {len(results)} items:\n")
    
    # Group by value for better readability
    by_value = defaultdict(list)
    for item_name, value, file_path in results:
        by_value[value].append(item_name)
    
    for value, items in sorted(by_value.items()):
        print(f"  {property_name} = {value}:")
        sorted_items = sorted(items)
        display_items = sorted_items if chunk_limit is None else sorted_items[:chunk_limit]

        for item in display_items:
            print(f"    - {item}")
        if chunk_limit is not None and len(items) > chunk_limit:
            print(f"    ... and {len(items) - chunk_limit} more")
        print()
    
    print(f"📊 Total: {len(results)} items with '{property_name}'")


def list_properties(vanilla_dir, min_usage=1, chunk_limit=None):
    """List all properties with usage counts"""
    print(f"\n📋 Listing all item properties (min usage: {min_usage})...")
    if chunk_limit is not None:
        print(f"   Chunk limit: {chunk_limit}")
    print("-" * 60)
    
    all_properties = analyze_all_properties(vanilla_dir)
    
    if not all_properties:
        print("❌ No properties found")
        return
    
    # Filter by minimum usage and group by type
    by_type = {'Boolean': [], 'Numeric': [], 'String': []}
    for prop_name, prop_data in all_properties.items():
        if prop_data['count'] >= min_usage:
            # Convert set to sorted string
            prop_types = prop_data['type']
            if isinstance(prop_types, set):
                # Determine primary type (use first if multiple)
                primary_type = sorted(prop_types)[0] if prop_types else 'Unknown'
            else:
                primary_type = prop_types
            
            if primary_type in by_type:
                by_type[primary_type].append((prop_name, prop_data['count']))
    
    for prop_type, items in by_type.items():
        if not items:
            continue
        print(f"\n{prop_type} Properties ({len(items)}):")
        sorted_items = sorted(items, key=lambda x: x[1], reverse=True)
        display_items = sorted_items if chunk_limit is None else sorted_items[:chunk_limit]

        for name, count in display_items:
            print(f"  {name:30s} - used by {count:4d} items")
        if chunk_limit is not None and len(items) > chunk_limit:
            print(f"  ... and {len(items) - chunk_limit} more")
    
    total = sum(len(items) for items in by_type.values())
    print(f"\n📊 Total: {total} unique properties")


def dump_property(vanilla_dir, property_name, output_format='table'):
    """Export property data in specified format"""
    print(f"\n💾 Dumping items with property: {property_name}")
    print(f"   Format: {output_format}")
    print("-" * 60)
    
    result = dump_items_by_property(vanilla_dir, property_name, output_format)
    
    if not result:
        print(f"❌ No items found with property '{property_name}'")
        return
    
    if output_format == 'table':
        print(result)
    elif output_format == 'csv':
        # Save to file
        from pathlib import Path
        output_file = Path(f"property_{property_name}.csv")
        with open(output_file, 'w') as f:
            f.write(result)
        print(f"✅ Saved to {output_file}")
    elif output_format == 'dict':
        import json
        from pathlib import Path
        output_file = Path(f"property_{property_name}.json")
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"✅ Saved to {output_file}")


def analyze_properties(vanilla_dir, chunk_limit=None):
    """Generate Item_Script_Parameters.md documentation"""
    print("\n📝 Analyzing all item properties...")
    print("-" * 60)
    
    properties = analyze_all_properties(vanilla_dir)
    
    # Generate documentation
    from pathlib import Path
    docs_dir = Path(__file__).parent.parent.parent.parent / 'Docs'
    docs_dir.mkdir(exist_ok=True)
    doc_file = docs_dir / 'Item_Script_Parameters.md'

    def format_examples(examples):
        formatted = []
        for example in examples:
            if isinstance(example, dict):
                item = example.get('item', 'Unknown')
                value = example.get('value', '')
                formatted.append(f"{item}={value}")
            else:
                formatted.append(str(example))
        return ', '.join(formatted) if formatted else 'None'
    
    with open(doc_file, 'w', encoding='utf-8') as f:
        f.write("# Project Zomboid - Item Script Parameters\n\n")
        f.write(f"Comprehensive list of all {len(properties)} item properties found in vanilla scripts.\n\n")
        f.write("## Table of Contents\n\n")
        f.write("- [Boolean Flags](#boolean-flags)\n")
        f.write("- [Numeric Properties](#numeric-properties)\n")
        f.write("- [String Properties](#string-properties)\n\n")
        
        # Group by type
        by_type = {'Boolean': {}, 'Numeric': {}, 'String': {}}
        for prop_name, prop_data in properties.items():
            prop_types = prop_data['type']
            if isinstance(prop_types, set):
                primary_type = sorted(prop_types)[0] if prop_types else 'Unknown'
            else:
                primary_type = prop_types
            
            if primary_type in by_type:
                by_type[primary_type][prop_name] = prop_data
        
        # Boolean flags
        f.write("## Boolean Flags\n\n")
        f.write(f"Total: {len(by_type['Boolean'])} properties\n\n")
        for name in sorted(by_type['Boolean'].keys()):
            data = by_type['Boolean'][name]
            examples = data['examples'] if chunk_limit is None else data['examples'][:chunk_limit]
            f.write(f"### {name}\n")
            f.write(f"- **Usage**: {data['count']} items\n")
            f.write(f"- **Examples**: {format_examples(examples)}\n\n")
        
        # Numeric properties
        f.write("## Numeric Properties\n\n")
        f.write(f"Total: {len(by_type['Numeric'])} properties\n\n")
        for name in sorted(by_type['Numeric'].keys()):
            data = by_type['Numeric'][name]
            examples = data['examples'] if chunk_limit is None else data['examples'][:chunk_limit]
            f.write(f"### {name}\n")
            f.write(f"- **Usage**: {data['count']} items\n")
            f.write(f"- **Examples**: {format_examples(examples)}\n\n")
        
        # String properties
        f.write("## String Properties\n\n")
        f.write(f"Total: {len(by_type['String'])} properties\n\n")
        for name in sorted(by_type['String'].keys()):
            data = by_type['String'][name]
            examples = data['examples'] if chunk_limit is None else data['examples'][:chunk_limit]
            f.write(f"### {name}\n")
            f.write(f"- **Usage**: {data['count']} items\n")
            f.write(f"- **Examples**: {format_examples(examples)}\n\n")
    
    print(f"✅ Documentation written to {doc_file}")
    print(f"📊 Total properties documented: {len(properties)}")
