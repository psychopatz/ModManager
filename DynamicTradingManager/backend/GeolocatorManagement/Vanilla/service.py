import logging
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from ProjectManagement.projects import resolve_project_target
from config.server_settings import get_server_settings
from ..bounds import build_map_bounds
from ..poi import build_map_pois
from ..lua_writer import (
    normalize_generated_content_for_compare,
    parse_generated_metadata,
    render_definition_file,
    write_definition_file,
)
from ..parsers import (
    parse_lotheader_cells,
    parse_objects_lua,
    parse_spawnpoints,
    parse_spawnregions,
    parse_worldmap_annotations,
    parse_worldmap_features,
)
from ..discovery import (
    normalize_registry_key,
    sanitize_pascal_case,
    strip_version_tokens,
)
from .discovery import discover_vanilla_maps

logger = logging.getLogger(__name__)

GEOLOCATOR_DEFINITIONS_SUBPATH = Path(
    "common/media/lua/shared/DT/Common/GeolocatorDefinitions"
)

def build_vanilla_map_definitions(target: str | None = None, module: str = "DynamicTradingCommon") -> list[dict[str, object]]:
    settings = get_server_settings()
    game_media_path = settings.game_media_path
    
    project = resolve_project_target(target)
    module_root = _resolve_module_root(project, module)
    
    vanilla_folders = discover_vanilla_maps(game_media_path)
    definitions: list[dict[str, object]] = []
    
    for map_folder in vanilla_folders:
        try:
            preview = _process_vanilla_map_folder(map_folder, module_root)
            if preview:
                definitions.append(preview)
        except Exception as e:
            logger.error(f"Failed to process vanilla map folder {map_folder}: {e}")
            
    return definitions

def generate_vanilla_registry(target: str | None = None, module: str = "DynamicTradingCommon") -> dict[str, object]:
    previews = build_vanilla_map_definitions(target=target, module=module)
    generated_files: list[str] = []
    
    for preview in previews:
        output_path = Path(preview["output_file"])
        definition = preview["definition"]
        metadata = preview.get("generation_metadata")
        
        print(f"Generating vanilla {output_path}")
        write_definition_file(output_path, definition, metadata=metadata if isinstance(metadata, dict) else None)
        generated_files.append(str(output_path))
        
    return {
        "generated_files": generated_files,
        "total_generated": len(generated_files),
    }

def _process_vanilla_map_folder(map_folder: Path, module_root: Path) -> dict[str, object] | None:
    map_name = map_folder.name
    spawnregions_path = map_folder / "spawnregions.lua"
    annotations_path = map_folder / "worldmap-annotations.lua"
    objects_path = map_folder / "objects.lua"
    worldmap_path = map_folder / "worldmap.xml"

    spawnregions = parse_spawnregions(spawnregions_path) if spawnregions_path.exists() else []
    
    # Vanilla specific: collect spawnpoints from map folder
    spawnpoints_path = map_folder / "spawnpoints.lua"
    spawnpoints = parse_spawnpoints(spawnpoints_path) if spawnpoints_path.exists() else []
    
    annotations = parse_worldmap_annotations(annotations_path) if annotations_path.exists() else []
    object_entries = parse_objects_lua(objects_path) if objects_path.exists() else []
    world_features = parse_worldmap_features(worldmap_path) if worldmap_path.exists() else []
    lotheader_cells = parse_lotheader_cells(map_folder)

    if not lotheader_cells and not spawnpoints:
        return None

    bounds, _ = build_map_bounds(lotheader_cells, spawnpoints, annotations)
    
    short_name = strip_version_tokens(map_name) or map_name
    long_name = _determine_long_name(short_name, spawnregions)
    file_base_name = sanitize_pascal_case(short_name)
    county_name = short_name
    
    pois, poi_buckets, poi_warnings = build_map_pois(
        map_name=map_name,
        town_name=short_name,
        county_name=county_name,
        annotations=annotations,
        object_entries=object_entries,
        world_features=world_features,
    )
    
    map_folders = [map_name]
    world_maps = [map_name] + [entry["name"] for entry in spawnregions if entry.get("name")]
    
    definition = {
        "id": file_base_name,
        "mod": "Vanilla",
        "isVanilla": True,
        "activation": {
            "modIDs": ["Vanilla"],
            "mapFolders": map_folders,
            "worldMaps": world_maps,
        },
        "locations": [
            {
                "id": normalize_registry_key(short_name),
                "longName": long_name,
                "shortName": short_name,
                "startX": bounds["minX"],
                "endX": bounds["maxX"],
                "startY": bounds["minY"],
                "endY": bounds["maxY"],
            }
        ],
        "towns": [
            {
                "name": short_name,
                "minX": bounds["minX"],
                "maxX": bounds["maxX"],
                "minY": bounds["minY"],
                "maxY": bounds["maxY"],
            }
        ],
        "counties": [],
        "pois": pois,
    }

    output_file = module_root / GEOLOCATOR_DEFINITIONS_SUBPATH / "Vanilla" / f"DT_{file_base_name}.lua"
    source_fingerprint = _compute_source_fingerprint(definition)
    
    generation_metadata = {
        "GeneratedAt": _utc_now_iso(),
        "SourceVersion": "Vanilla",
        "SourceFingerprint": source_fingerprint,
        "SourcePath": str(map_folder),
        "MapFolder": map_name,
    }

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
        "poiCount": len(pois),
        "pois": pois,
        "poiBuckets": poi_buckets,
        "output_file": str(output_file),
        "definition": definition,
        "generation_metadata": generation_metadata,
        "registry_status": _build_registry_status(output_file, definition, "Vanilla", source_fingerprint),
    }

def _resolve_module_root(project: dict[str, object], module: str) -> Path:
    normalized_module = str(module or "DynamicTradingCommon").strip()
    for mod in project.get("sub_mods", []):
        if str(mod.get("id", "")).lower() == normalized_module.lower():
            return Path(mod["path"])
    raise FileNotFoundError(f"Module '{normalized_module}' was not found in project '{project['name']}'.")

def _determine_long_name(short_name: str, spawnregions: list[dict[str, str]]) -> str:
    spawn_name = next((entry["name"] for entry in spawnregions if entry.get("name")), None)
    if spawn_name:
        return str(spawn_name)
    return f"{short_name}, KY"

def _compute_source_fingerprint(definition: dict[str, object]) -> str:
    rendered = render_definition_file(definition)
    normalized = normalize_generated_content_for_compare(rendered)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def _build_registry_status(
    output_file: Path,
    definition: dict[str, object],
    source_version: str,
    source_fingerprint: str,
) -> dict[str, object]:
    if not output_file.exists():
        return {
            "state": "not_added",
            "is_added": False,
            "is_outdated": False,
            "added_at": None,
            "source_version": source_version,
            "generated_version": None,
            "output_exists": False,
        }

    metadata = parse_generated_metadata(output_file)
    existing_text = output_file.read_text(encoding="utf-8", errors="replace")
    current_rendered = render_definition_file(definition)
    content_changed = normalize_generated_content_for_compare(existing_text) != normalize_generated_content_for_compare(current_rendered)
    stored_fingerprint = metadata.get("SourceFingerprint", "")
    fingerprint_changed = bool(stored_fingerprint) and stored_fingerprint != source_fingerprint
    generated_version = metadata.get("SourceVersion") or None
    version_changed = bool(source_version) and bool(generated_version) and source_version != generated_version
    
    is_outdated = content_changed or fingerprint_changed or version_changed

    return {
        "state": "outdated" if is_outdated else "added",
        "is_added": True,
        "is_outdated": is_outdated,
        "added_at": metadata.get("GeneratedAt"),
        "source_version": source_version,
        "generated_version": generated_version,
        "output_exists": True,
    }

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
