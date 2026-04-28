import os
import re
from pathlib import Path

# Paths to the workshop mods
WORKSHOP_PATH = Path("/home/psychopatz/Zomboid/Workshop")

def get_mod_id_for_path(file_path: Path) -> str:
    """Finds the mod ID by looking for mod.info in parent directories."""
    current = file_path.parent
    while current != WORKSHOP_PATH and current != current.parent:
        info_file = current / "mod.info"
        if info_file.exists():
            content = info_file.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r"^id=(.+)$", content, re.MULTILINE)
            if match:
                return match.group(1).strip()
        current = current.parent
    return "DynamicTradingCommon"

def migrate_tags(content: str, mod_id: str) -> str:
    # Target: DynamicTrading.RegisterTag("Tag", { ... })
    def replace_tag(match):
        tag_id = match.group(1)
        body = match.group(2)
        if 'module =' in body:
            return match.group(0)
        return f'DynamicTrading.RegisterTag("{tag_id}", {{\n        module = "{mod_id}",{body}}})'

    return re.sub(r'DynamicTrading\.RegisterTag\(\s*"([^"]+)"\s*,\s*\{([^}]*)\}\s*\)', replace_tag, content, flags=re.DOTALL)

def migrate_items(content: str, mod_id: str) -> str:
    # Target: { item="...", ... }
    # We want to insert 'module = "ModID",' after the opening brace '{'
    def replace_item(match):
        body = match.group(1)
        if 'module =' in body:
            return match.group(0)
        # Check if it's actually an item entry (has item="...")
        if 'item="' not in body and "item = \"" not in body:
            return match.group(0)
        
        # Determine indentation
        if '\n' in match.group(0):
            return f'{{ module = "{mod_id}", {body}}}'
        else:
            return f'{{ module = "{mod_id}", {body}}}'

    # Note: This regex is greedy on whitespace but careful with nested braces
    return re.sub(r'\{([^{}]+)\}', replace_item, content)

def main():
    updated_files = 0
    for root, _, files in os.walk(WORKSHOP_PATH):
        for file in files:
            if file.endswith(".lua"):
                file_path = Path(root) / file
                
                # Check if it's an item or tag definition file
                content = file_path.read_text(encoding="utf-8")
                mod_id = get_mod_id_for_path(file_path)
                
                new_content = migrate_tags(content, mod_id)
                new_content = migrate_items(new_content, mod_id)
                
                if new_content != content:
                    file_path.write_text(new_content, encoding="utf-8")
                    updated_files += 1
                    print(f"Updated {file_path.relative_to(WORKSHOP_PATH)}")

    print(f"\nMigration complete. Updated {updated_files} files.")

if __name__ == "__main__":
    main()
