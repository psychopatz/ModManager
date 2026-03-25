"""Override management commands"""

from ...parse.overrides import (
    load_overrides, add_override, remove_override,
    find_invalid_overrides, find_duplicate_overrides,
    get_override_stats
)


def show_overrides():
    """Display current override configuration"""
    overrides = load_overrides()
    
    print("\n" + "=" * 60)
    print("📝 OVERRIDE CONFIGURATION")
    print("=" * 60)
    
    if not overrides:
        print("\n⚠️  No overrides configured")
        print("\nTo add an override:")
        print("  python main.py --override-add <item_id> [--price <value>] [--stock-min <value>] [--stock-max <value>]")
        return
    
    print(f"\nTotal overrides: {len(overrides)}\n")
    
    for i, override in enumerate(overrides, 1):
        item_id = override.get("item", "Unknown")
        print(f"\n{i}. {item_id}")
        
        if "basePrice" in override:
            print(f"   💰 Base Price: {override['basePrice']}")
        
        if "tags" in override:
            print(f"   🏷️  Tags: {', '.join(override['tags'])}")
        
        if "stockRange" in override:
            stock = override["stockRange"]
            min_stock = stock.get("min", "default")
            max_stock = stock.get("max", "default")
            print(f"   📦 Stock Range: {min_stock} - {max_stock}")
        
        if "description" in override:
            print(f"   📄 Description: {override['description']}")
    
    print("\n" + "=" * 60)


def show_override_stats():
    """Display override statistics"""
    stats = get_override_stats()
    invalid = find_invalid_overrides()
    duplicates = find_duplicate_overrides()
    
    print("\n" + "=" * 60)
    print("📊 OVERRIDE STATISTICS")
    print("=" * 60)
    
    print(f"\nTotal Overrides:       {stats['total']}")
    print(f"Invalid Overrides:     {stats['invalid']}")
    print(f"Duplicate Item IDs:    {stats['duplicates']}")
    
    if invalid:
        print("\n⚠️  INVALID OVERRIDES:")
        for override, error in invalid:
            item_id = override.get("item", "Unknown")
            print(f"   • {item_id}: {error}")
    
    if duplicates:
        print("\n⚠️  DUPLICATE ITEM IDS:")
        for item_id in duplicates:
            print(f"   • {item_id}")
    
    print("\n" + "=" * 60)


def add_override_command(item_id: str, **kwargs):
    """Add an override via command line"""
    try:
        add_override(item_id, **kwargs)
    except ValueError as e:
        print(f"❌ Error: {e}")


def remove_override_command(item_id: str):
    """Remove an override via command line"""
    remove_override(item_id)
