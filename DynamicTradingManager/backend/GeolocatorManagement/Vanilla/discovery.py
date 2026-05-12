from __future__ import annotations

import os
from pathlib import Path
from ..discovery import _is_valid_map_folder

def discover_vanilla_maps(media_path: str | Path) -> list[Path]:
    maps_root = Path(media_path) / "maps"
    if not maps_root.is_dir():
        return []
    
    vanilla_folders: dict[str, Path] = {}
    
    # Recurse up to 2 levels to find maps (e.g. maps/Muldraugh, KY or maps/challengemaps/Kingsmouth)
    for root, dirs, files in os.walk(maps_root):
        root_path = Path(root)
        
        # Check if the current folder is a valid map folder
        if _is_valid_map_folder(root_path):
            # Use relative path as key to avoid duplicates if something weird happens
            rel_path = root_path.relative_to(maps_root)
            vanilla_folders[str(rel_path)] = root_path
            # Don't recurse into subdirectories of a valid map folder
            dirs.clear()
            continue
        
        # Limit recursion depth for safety
        depth = len(root_path.relative_to(maps_root).parts)
        if depth >= 2:
            dirs.clear()

    results = list(vanilla_folders.values())
    results.sort(key=lambda item: item.name.lower())
    return results
