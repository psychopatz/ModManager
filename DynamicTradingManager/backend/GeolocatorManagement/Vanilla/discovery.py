from __future__ import annotations

import os
from pathlib import Path
from ..discovery import _is_valid_map_folder

def discover_vanilla_maps(media_path: str | Path) -> list[Path]:
    maps_root = Path(media_path) / "maps"
    if not maps_root.is_dir():
        return []
    
    vanilla_folders: list[Path] = []
    for child in maps_root.iterdir():
        if child.is_dir() and _is_valid_map_folder(child):
            # For vanilla, we consider all valid map folders under media/maps
            vanilla_folders.append(child)
    
    vanilla_folders.sort(key=lambda item: item.name.lower())
    return vanilla_folders
