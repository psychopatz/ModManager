"""
Spawn analysis and rarity calculation commands
"""
from pathlib import Path
from ...analyze.spawn_analyzer import (
    get_rarity_statistics,
    get_items_by_rarity,
    find_distribution_files
)


def find_rarity(distributions_dir, tier, full_output=False):
    """Find items by rarity tier"""
    valid_tiers = ['UltraRare', 'Legendary', 'Rare', 'Uncommon', 'Common']
    
    if tier not in valid_tiers:
        print(f"❌ Invalid rarity tier: {tier}")
        print(f"   Valid tiers: {', '.join(valid_tiers)}")
        return
    
    print(f"\n🔍 Finding {tier} items...")
    print("-" * 60)
    
    # When full_output is True, show all items (remove limit)
    limit = None if full_output else 50
    items = get_items_by_rarity(tier, distributions_dir, limit=limit)
    
    if not items:
        print(f"❌ No {tier} items found")
        return
    
    print(f"✅ Found {len(items)} {tier} items:\n")
    
    for item_name, avg_weight, spawn_count in items:
        print(f"  {item_name:40s} weight: {avg_weight:6.3f}  locations: {spawn_count:3d}")
    
    print(f"\n📊 Total: {len(items)} {tier} items shown")


def rarity_stats(distributions_dir):
    """Show spawn rarity statistics"""
    print("\n📊 Spawn Rarity Statistics")
    print("-" * 60)
    
    stats = get_rarity_statistics(distributions_dir)
    
    if 'error' in stats:
        print(f"❌ {stats['error']}")
        return
    
    total = stats['total_items']
    print(f"\n Total items analyzed: {total}\n")
    print(f" Rarity Distribution:")
    print(f"   Ultra Rare: {stats['ultra_rare']:4d} items ({stats['ultra_rare']/total*100:5.1f}%)")
    print(f"   Legendary:  {stats['legendary']:4d} items ({stats['legendary']/total*100:5.1f}%)")
    print(f"   Rare:       {stats['rare']:4d} items ({stats['rare']/total*100:5.1f}%)")
    print(f"   Uncommon:   {stats['uncommon']:4d} items ({stats['uncommon']/total*100:5.1f}%)")
    print(f"   Common:     {stats['common']:4d} items ({stats['common']/total*100:5.1f}%)")
    print()


def analyze_spawns(distributions_dir, full_output=False):
    """Generate Item_Spawn_Rates.md documentation"""
    print("\n📝 Analyzing spawn rates from Distribution*.lua files...")
    print("-" * 60)
    
    stats = get_rarity_statistics(distributions_dir)
    
    if 'error' in stats:
        print(f"❌ {stats['error']}")
        return
    
    # Generate documentation
    docs_dir = Path(__file__).parent.parent.parent.parent / 'Docs'
    docs_dir.mkdir(exist_ok=True)
    doc_file = docs_dir / 'Item_Spawn_Rates.md'
    
    # When full_output, show all items per tier instead of just top 20
    items_per_tier = None if full_output else 20
    
    with open(doc_file, 'w', encoding='utf-8') as f:
        f.write("# Project Zomboid - Item Spawn Rates Analysis\n\n")
        f.write(f"Analysis of {stats['total_items']} items from Distribution*.lua files\n\n")
        f.write("## Rarity Distribution\n\n")
        f.write("| Tier | Count | Percentage |\n")
        f.write("|------|-------|------------|\n")
        f.write(f"| Ultra Rare | {stats['ultra_rare']} | {stats['ultra_rare']/stats['total_items']*100:.1f}% |\n")
        f.write(f"| Legendary | {stats['legendary']} | {stats['legendary']/stats['total_items']*100:.1f}% |\n")
        f.write(f"| Rare | {stats['rare']} | {stats['rare']/stats['total_items']*100:.1f}% |\n")
        f.write(f"| Uncommon | {stats['uncommon']} | {stats['uncommon']/stats['total_items']*100:.1f}% |\n")
        f.write(f"| Common | {stats['common']} | {stats['common']/stats['total_items']*100:.1f}% |\n\n")
        
        # Add examples for each tier
        for tier in ['UltraRare', 'Legendary', 'Rare', 'Uncommon', 'Common']:
            items = get_items_by_rarity(tier, distributions_dir, limit=items_per_tier)
            if items:
                tier_label = f"{tier} Items" if items_per_tier is None else f"{tier} Items (Top {items_per_tier})"
                f.write(f"## {tier_label}\n\n")
                for item_name, avg_weight, spawn_count in items:
                    f.write(f"- {item_name} (weight: {avg_weight:.3f}, locations: {spawn_count})\n")
                f.write("\n")
    
    # Count distribution files
    dist_dir = Path(distributions_dir) if distributions_dir else None
    dist_files = find_distribution_files(str(dist_dir)) if dist_dir else []
    
    print(f"✅ Documentation written to {doc_file}")
    print(f"📊 Analyzed from {len(dist_files)} distribution files:")
    print(f"   Ultra Rare: {stats['ultra_rare']:4d} ({stats['ultra_rare']/stats['total_items']*100:5.1f}%)")
    print(f"   Legendary:  {stats['legendary']:4d} ({stats['legendary']/stats['total_items']*100:5.1f}%)")
    print(f"   Rare:       {stats['rare']:4d} ({stats['rare']/stats['total_items']*100:5.1f}%)")
    print(f"   Uncommon:   {stats['uncommon']:4d} ({stats['uncommon']/stats['total_items']*100:5.1f}%)")
    print(f"   Common:     {stats['common']:4d} ({stats['common']/stats['total_items']*100:5.1f}%)")
