"""Interactive menu display and handling"""

import sys
from pathlib import Path
from datetime import datetime


def display_interactive_menu():
    """Display the reorganized interactive menu"""
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 13 + "ItemGenerator - Interactive Menu" + " " * 13 + "║")
    print("╚" + "═" * 58 + "╝")
    print("\nSelect an operation:")
    
    print("\n📦 ITEM MANAGEMENT:")
    print("  1. 🔄 Refresh all items (format, price, blacklist, overrides)")
    print("  2. ➕ Add items (Press Enter = add all)")
    print("  3. 🗑️  Delete all items (reset registries)")
    print("  4. 📋 Show blacklist configuration")
    print("  5. 📊 Show blacklist statistics")
    print("  6. 📝 Show override configuration")
    print("  7. 📈 Show override statistics")
    print("  8. 🧹 Cleanup blacklisted items from Lua files")
    
    print("\n🔍 ITEM ANALYSIS:")
    print("  9. 🔎 Find items by property")
    print("  a. 📝 List all properties")
    print("  b. 📚 Analyze properties (generate docs)")
    print("  c. 🎲 Find items by rarity")
    print("  d. 📈 Show rarity statistics")
    print("  e. 📊 Analyze spawns (generate docs)")
    
    print("\n❓ OTHER:")
    print("  h. ❓ Show help")
    print("  0. 🚪 Exit")
    print()
    
    while True:
        choice = input("Enter choice: ").strip().lower()
        valid_choices = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'h', '0']
        if choice in valid_choices:
            return choice
        print("❌ Invalid choice. Please enter 1-9, a-e, h, or 0.")


def generate_output_filename(cmd_name):
    """Generate timestamped output filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).parent.parent.parent / "Output"
    output_dir.mkdir(exist_ok=True)
    return str(output_dir / f"{cmd_name}_{timestamp}.md")


def save_to_markdown_file(text_content, filename):
    """Save output to markdown with collapsible sections"""
    lines = text_content.strip().split('\n')
    md_parts = ['# Analysis Results\n']
    current_section = None
    section_lines = []
    
    for line in lines:
        if line.strip() and any(line.strip().startswith(e) for e in ['🔍', '📊', '📁', '📝', '✅', '❌']):
            if section_lines and current_section:
                md_parts.append('<details>')
                md_parts.append(f'<summary><strong>{current_section}</strong></summary>\n')
                md_parts.append('```')
                md_parts.extend(section_lines)
                md_parts.append('```')
                md_parts.append('</details>\n')
            current_section = line.strip()
            section_lines = []
        else:
            section_lines.append(line)
    
    if section_lines and current_section:
        md_parts.append('<details>')
        md_parts.append(f'<summary><strong>{current_section}</strong></summary>\n')
        md_parts.append('```')
        md_parts.extend(section_lines)
        md_parts.append('```')
        md_parts.append('</details>\n')
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_parts))


class OutputCapture:
    """Capture stdout for saving to file"""
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout
        self.captured = []
    
    def write(self, text):
        self.original_stdout.write(text)
        self.captured.append(text)
    
    def flush(self):
        self.original_stdout.flush()
    
    def get_content(self):
        return ''.join(self.captured)


def handle_menu_choice(choice, vanilla_items, chunk_limit, vanilla_scripts_dir, distributions_dir):
    """Handle the selected menu choice"""
    from .commands import (
        find_property, list_properties, analyze_properties,
        find_rarity, rarity_stats, analyze_spawns,
        update, add, delete_all_items,
        show_blacklist, show_blacklist_stats, cleanup_blacklist,
        show_overrides, show_override_stats,
    )
    
    # ITEM MANAGEMENT
    if choice == '1':
        # Refresh all items (format, price, blacklist, overrides)
        print("\n🔄 This will refresh all items with:")
        print("   • Lua format normalization")
        print("   • Price and stock recalculation")
        print("   • Blacklist filtering")
        print("   • Override application")
        regen = input("\n🏷️  Regenerate tags using new tagging system? (y/n): ").lower().startswith('y')
        update(vanilla_items, regenerate_tags=regen)
        return True
    
    elif choice == '2':
        # Add items - if empty, add all
        batch_input = input("➕ Enter number of items to add (press Enter to add all remaining): ").strip()
        if not batch_input:
            # Empty input - add all
            if input("📦 Add ALL remaining items? (yes/no): ").lower().startswith('y'):
                add(vanilla_items, 'all')
            else:
                print("❌ Cancelled.")
        else:
            # Custom batch size
            try:
                batch_size = int(batch_input)
                if batch_size > 0:
                    add(vanilla_items, batch_size)
                else:
                    print("❌ Must be a positive number.")
            except ValueError:
                print("❌ Please enter a valid number.")
        return True
    
    elif choice == '3':
        # Delete all items
        delete_all_items()
        input("\n⏸️  Press Enter to continue...")
        return False
    
    elif choice == '4':
        # Show blacklist configuration
        show_blacklist()
        input("\n⏸️  Press Enter to continue...")
        return False
    
    elif choice == '5':
        # Show blacklist statistics
        show_blacklist_stats()
        input("\n⏸️  Press Enter to continue...")
        return False
    
    elif choice == '6':
        # Show override configuration
        show_overrides()
        input("\n⏸️  Press Enter to continue...")
        return False
    
    elif choice == '7':
        # Show override statistics
        show_override_stats()
        input("\n⏸️  Press Enter to continue...")
        return False
    
    elif choice == '8':
        # Cleanup blacklisted items
        dry_run = input("🧹 Dry run first? (y/n): ").lower().startswith('y')
        print("\n🧹 Starting cleanup...")
        cleanup_blacklist(vanilla_items, dry_run=dry_run)
        input("\n⏸️  Press Enter to continue...")
        return False
    
    # ITEM ANALYSIS
    elif choice == '9':
        # Cleanup blacklisted items
        dry_run = input("🧹 Dry run first? (y/n): ").lower().startswith('y')
        print("\n🧹 Starting cleanup...")
        cleanup_blacklist(vanilla_items, dry_run=dry_run)
        input("\n⏸️  Press Enter to continue...")
        return False
    
    # ITEM ANALYSIS
    elif choice == '9':
        # Find items by property
        prop_name = input("🔎 Enter property name (e.g., StressChange): ").strip()
        if prop_name:
            value_filter = input("   Enter value filter (optional, press Enter to skip): ").strip() or None
            save_opt = input("   Save to file? (y/n): ").lower().startswith('y')
            
            if save_opt:
                output_file = generate_output_filename(f"find_property_{prop_name}")
                original_stdout = sys.stdout
                capture = OutputCapture(original_stdout)
                try:
                    sys.stdout = capture
                    find_property(vanilla_scripts_dir, prop_name, value_filter, chunk_limit=chunk_limit)
                finally:
                    sys.stdout = original_stdout
                    save_to_markdown_file(capture.get_content(), output_file)
                print(f"\n✅ Output saved to: {output_file}")
            else:
                find_property(vanilla_scripts_dir, prop_name, value_filter, chunk_limit=chunk_limit)
        
        input("\n⏸️  Press Enter to continue...")
        return False
    
    elif choice == 'a':
        # List all properties
        min_usage = input("📝 Minimum usage count (default 1): ").strip()
        min_usage = int(min_usage) if min_usage.isdigit() else 1
        save_opt = input("   Save to file? (y/n): ").lower().startswith('y')
        
        if save_opt:
            output_file = generate_output_filename("list_properties")
            original_stdout = sys.stdout
            capture = OutputCapture(original_stdout)
            try:
                sys.stdout = capture
                list_properties(vanilla_scripts_dir, min_usage, chunk_limit=chunk_limit)
            finally:
                sys.stdout = original_stdout
                save_to_markdown_file(capture.get_content(), output_file)
            print(f"\n✅ Output saved to: {output_file}")
        else:
            list_properties(vanilla_scripts_dir, min_usage, chunk_limit=chunk_limit)
        
        input("\n⏸️  Press Enter to continue...")
        return False
    
    elif choice == 'b':
        # Analyze properties (generate docs)
        save_opt = input("📚 Save to file? (y/n): ").lower().startswith('y')
        
        if save_opt:
            output_file = generate_output_filename("analyze_properties")
            original_stdout = sys.stdout
            capture = OutputCapture(original_stdout)
            try:
                sys.stdout = capture
                analyze_properties(vanilla_scripts_dir, chunk_limit=chunk_limit)
            finally:
                sys.stdout = original_stdout
                save_to_markdown_file(capture.get_content(), output_file)
            print(f"\n✅ Output saved to: {output_file}")
        else:
            analyze_properties(vanilla_scripts_dir, chunk_limit=chunk_limit)
        
        input("\n⏸️  Press Enter to continue...")
        return False
    
    elif choice == 'c':
        # Find items by rarity
        print("\n🎲 Rarity tiers: UltraRare, Legendary, Rare, Uncommon, Common")
        tier = input("   Enter rarity tier: ").strip()
        
        if tier in ['UltraRare', 'Legendary', 'Rare', 'Uncommon', 'Common']:
            save_opt = input("   Save to file? (y/n): ").lower().startswith('y')
            
            if save_opt:
                output_file = generate_output_filename(f"find_rarity_{tier}")
                original_stdout = sys.stdout
                capture = OutputCapture(original_stdout)
                try:
                    sys.stdout = capture
                    find_rarity(distributions_dir, tier, full_output=True)
                finally:
                    sys.stdout = original_stdout
                    save_to_markdown_file(capture.get_content(), output_file)
                print(f"\n✅ Output saved to: {output_file}")
            else:
                find_rarity(distributions_dir, tier, full_output=False)
        else:
            print("❌ Invalid tier name")
        
        input("\n⏸️  Press Enter to continue...")
        return False
    
    elif choice == 'd':
        # Show rarity statistics
        save_opt = input("📈 Save to file? (y/n): ").lower().startswith('y')
        
        if save_opt:
            output_file = generate_output_filename("rarity_stats")
            original_stdout = sys.stdout
            capture = OutputCapture(original_stdout)
            try:
                sys.stdout = capture
                rarity_stats(distributions_dir)
            finally:
                sys.stdout = original_stdout
                save_to_markdown_file(capture.get_content(), output_file)
            print(f"\n✅ Output saved to: {output_file}")
        else:
            rarity_stats(distributions_dir)
        
        input("\n⏸️  Press Enter to continue...")
        return False
    
    elif choice == 'e':
        # Analyze spawns (generate docs)
        save_opt = input("📊 Save to file? (y/n): ").lower().startswith('y')
        
        if save_opt:
            output_file = generate_output_filename("analyze_spawns")
            original_stdout = sys.stdout
            capture = OutputCapture(original_stdout)
            try:
                sys.stdout = capture
                analyze_spawns(distributions_dir, full_output=True)
            finally:
                sys.stdout = original_stdout
                save_to_markdown_file(capture.get_content(), output_file)
            print(f"\n✅ Output saved to: {output_file}")
        else:
            analyze_spawns(distributions_dir, full_output=False)
        
        input("\n⏸️  Press Enter to continue...")
        return False
    
    # OTHER
    elif choice == 'h':
        # Show help
        show_help()
        input("\n⏸️  Press Enter to continue...")
        return False
    
    elif choice == '0':
        # Exit
        print("\n👋 Goodbye!")
        return True
    
    return False


def show_help():
    """Display help information"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║          ItemGenerator - Command Reference                ║
╚═══════════════════════════════════════════════════════════╝

INTERACTIVE MODE:
  python main.py                    # Launch interactive menu

ITEM MANAGEMENT:
  python main.py update             # Update prices/stock for existing items
  python main.py add [count]        # Add new items (default: 50)
  python main.py add --all          # Add all remaining items

PROPERTY ANALYSIS:
  python main.py --find-property <name> [value] [--txt] [--chunk [size]]
      Search items by property name (e.g., StressChange, Alcoholic)
      Optional: filter by value
      
  python main.py --list-properties [min_usage] [--txt] [--chunk [size]]
      List all properties with usage counts (default: 1)
      
  python main.py --dump-property <name> [format] [--txt] [--chunk [size]]
      Dump all values for a property (formats: table, csv, dict)
      
  python main.py --analyze-properties [--txt] [--chunk [size]]
      Generate comprehensive property documentation

SPAWN ANALYSIS:
  python main.py --find-rarity <tier> [--txt]
      Find items by rarity (UltraRare, Legendary, Rare, Uncommon, Common)
      
  python main.py --rarity-stats [--txt]
      Show spawn rarity distribution statistics
      
  python main.py --analyze-spawns [--txt]
      Generate comprehensive spawn rate documentation

BLACKLIST MANAGEMENT:
  python main.py --blacklist-show        # Show current blacklist configuration
  python main.py --blacklist-stats       # Show blacklist statistics
  python main.py --blacklist-add-id <id> # Add item ID to blacklist
  python main.py --blacklist-add-prop <name>  # Add property name to blacklist
  python main.py --blacklist-add-value <prop> <value>  # Add property:value to blacklist
  python main.py --blacklist-cleanup     # Remove blacklisted items from all Lua files
  python main.py --blacklist-cleanup --dry-run  # Preview what would be removed

FLAGS:
  --txt                Save output to markdown file in Output/ folder
  --chunk [size]       Truncate long outputs (default when omitted: full output)
  --help               Display this help message

EXAMPLES:
  python main.py --find-property StressChange
  python main.py --find-rarity Rare --txt
  python main.py --list-properties 100 --txt
  python main.py add 200
""")
