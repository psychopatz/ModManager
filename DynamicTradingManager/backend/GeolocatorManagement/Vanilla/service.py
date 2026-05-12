from __future__ import annotations

import logging
from pathlib import Path

from config.server_settings import get_server_settings
from ..bounds import build_map_bounds
from ..parsers import (
    parse_lotheader_cells,
    parse_spawnpoints,
    parse_spawnregions,
    parse_worldmap_annotations,
    parse_worldmap_features,
)
from ..discovery import sanitize_pascal_case, strip_version_tokens
from .discovery import discover_vanilla_maps

logger = logging.getLogger(__name__)

def build_vanilla_map_definitions() -> list[dict[str, object]]:
    settings = get_server_settings()
    game_media_path = settings.game_media_path
    
    vanilla_folders = discover_vanilla_maps(game_media_path)
    definitions: list[dict[str, object]] = []
    
    for map_folder in vanilla_folders:
        try:
            definition = _process_vanilla_map_folder(map_folder)
            if definition:
                definitions.append(definition)
        except Exception as e:
            logger.error(f"Failed to process vanilla map folder {map_folder}: {e}")
            
    return definitions

def _process_vanilla_map_folder(map_folder: Path) -> dict[str, object] | None:
    map_name = map_folder.name
    spawnregions_path = map_folder / "spawnregions.lua"
    annotations_path = map_folder / "worldmap-annotations.lua"
    worldmap_path = map_folder / "worldmap.xml"

    spawnregions = parse_spawnregions(spawnregions_path) if spawnregions_path.exists() else []
    
    # Vanilla specific: if no spawnregions.lua, it might be a sub-map or the base map
    # We'll collect spawnpoints from the map folder itself
    spawnpoints_path = map_folder / "spawnpoints.lua"
    spawnpoints = parse_spawnpoints(spawnpoints_path) if spawnpoints_path.exists() else []
    
    annotations = parse_worldmap_annotations(annotations_path) if annotations_path.exists() else []
    world_features = parse_worldmap_features(worldmap_path) if worldmap_path.exists() else []
    lotheader_cells = parse_lotheader_cells(map_folder)

    if not lotheader_cells and not spawnpoints:
        return None

    bounds, _ = build_map_bounds(lotheader_cells, spawnpoints, annotations)
    
    short_name = strip_version_tokens(map_name) or map_name
    file_base_name = sanitize_pascal_case(short_name)
    
    return {
        "id": file_base_name,
        "name": short_name,
        "folder": map_name,
        "bounds": bounds,
        "isVanilla": True,
        "spawnPointCount": len(spawnpoints),
        "annotationCount": len(annotations),
        "featureCount": len(world_features),
        "cellCount": len(lotheader_cells),
    }
