import os
import re
from pathlib import Path

# Paths to the workshop mods
WORKSHOP_PATH = Path("/home/psychopatz/Zomboid/Workshop")

# Regex to find RegisterArchetype calls
# Matches: DynamicTrading.RegisterArchetype("ID", { ...
REGISTER_RE = re.compile(r'DynamicTrading\.RegisterArchetype\s*\(\s*"([^"]+)"\s*,\s*\{')

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
    
    # Fallback based on path segments if mod.info not found
    path_str = str(file_path)
    if "DynamicTradingCommon" in path_str: return "DynamicTradingCommon"
    if "DynamicTradingV2" in path_str: return "DynamicTradingV2"
    if "DynamicColonies" in path_str: return "DynamicColonies"
    if "CurrencyExpanded" in path_str: return "CurrencyExpanded"
    return "DynamicTradingCommon"

def migrate_archetype(file_path: Path):
    content = file_path.read_text(encoding="utf-8")
    mod_id = get_mod_id_for_path(file_path)
    
    # Check if 'module' is already present
    if re.search(r'module\s*=', content):
        print(f"Skipping {file_path.name} (already has module field)")
        return False

    # Find the registration call
    match = REGISTER_RE.search(content)
    if not match:
        return False

    # Inject 'module = "ModID",' after the opening brace
    insert_pos = match.end()
    new_content = (
        content[:insert_pos]
        + f'\n    module = "{mod_id}",'
        + content[insert_pos:]
    )
    
    file_path.write_text(new_content, encoding="utf-8")
    print(f"Migrated {file_path.name} -> module: {mod_id}")
    return True

def main():
    count = 0
    # Walk through all workshop mods looking for media/lua/shared scripts
    for root, _, files in os.walk(WORKSHOP_PATH):
        for file in files:
            if file.endswith(".lua"):
                file_path = Path(root) / file
                if "ArchetypeDefinitions" in str(file_path):
                    if migrate_archetype(file_path):
                        count += 1
    
    print(f"\nMigration complete. Updated {count} archetype files.")

if __name__ == "__main__":
    main()
