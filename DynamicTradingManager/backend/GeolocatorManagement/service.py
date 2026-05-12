from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from ProjectManagement.projects import resolve_project_target
from config.server_settings import get_server_settings

from .bounds import build_map_bounds
from .discovery import (
    DiscoveredMod,
    discover_mods_from_source,
    get_workshop_item_id_for_mod_root,
    normalize_registry_key,
    sanitize_pascal_case,
    strip_version_tokens,
)
from .poi import build_map_pois
from .lua_writer import (
    normalize_generated_content_for_compare,
    parse_generated_metadata,
    render_definition_file,
    write_definition_file,
)
from .parsers import (
    parse_lotheader_cells,
    parse_mod_info,
    parse_objects_lua,
    parse_spawnpoints,
    parse_spawnregions,
    parse_worldmap_annotations,
    parse_worldmap_features,
)


GEOLOCATOR_DEFINITIONS_SUBPATH = Path(
    "common/media/lua/shared/DT/Common/GeolocatorDefinitions"
)


def inspect_source_path(source_path: str, target: str | None = None, module: str = "DynamicTradingCommon", llm_config: dict[str, object] | None = None) -> dict[str, object]:
    project = resolve_project_target(target)
    module_root = _resolve_module_root(project, module)
    source_mods = discover_mods_from_source(source_path)

    mod_previews: list[dict[str, object]] = []
    total_maps = 0
    for source_mod in source_mods:
        preview = _build_mod_preview(source_mod, module_root, llm_config=llm_config)
        mod_previews.append(preview)
        total_maps += len(preview["maps"])

    return {
        "source_path": str(Path(source_path).expanduser()),
        "resolved_source_path": str(Path(source_path).expanduser().resolve()),
        "target": project["key"],
        "project_name": project["name"],
        "module": module,
        "module_root": str(module_root),
        "output_root": str(module_root / GEOLOCATOR_DEFINITIONS_SUBPATH),
        "mods": mod_previews,
        "total_mods": len(mod_previews),
        "total_maps": total_maps,
    }


def list_workshop_sources(
    root_path: str | None = None,
    target: str | None = None,
    module: str = "DynamicTradingCommon",
    llm_config: dict[str, object] | None = None,
) -> dict[str, object]:
    settings = get_server_settings()
    resolved_root = Path(root_path).expanduser().resolve() if root_path else settings.workshop_content_path
    if not resolved_root.exists():
        raise FileNotFoundError(f"Workshop content path does not exist: {resolved_root}")

    module_root: Path | None = None
    if target is not None or module:
        project = resolve_project_target(target)
        module_root = _resolve_module_root(project, module)

    source_mods = discover_mods_from_source(resolved_root)
    sources: list[dict[str, object]] = []
    for source_mod in source_mods:
        mod_preview = _build_mod_preview(source_mod, module_root, llm_config=llm_config) if module_root is not None else _build_mod_preview_without_target(source_mod)
        sources.append(_build_workshop_source_summary(mod_preview))

    sources.sort(key=lambda item: ((item["mod_name"] or "").lower(), str(item["workshop_item_id"] or "")))
    return {
        "root_path": str(resolved_root),
        "sources": sources,
        "total_sources": len(sources),
    }


def generate_registry_files(source_path: str, target: str | None = None, module: str = "DynamicTradingCommon", llm_config: dict[str, object] | None = None) -> dict[str, object]:
    print(f"[Geolocator] Starting registry generation for source: {source_path}")
    preview = inspect_source_path(source_path, target=target, module=module, llm_config=llm_config)
    generated_files: list[str] = []
    skipped_maps: list[dict[str, str]] = []

    for mod_preview in preview["mods"]:
        mod_name = mod_preview["mod_name"]
        print(f"Inspecting mod: {mod_name}")
        for map_preview in mod_preview["maps"]:
            output_path = Path(map_preview["output_file"])
            definition = map_preview["definition"]
            if not isinstance(definition, dict):
                skipped_maps.append(
                    {
                        "mod": mod_name,
                        "map": str(map_preview.get("map_folder_name", "")),
                        "reason": "No generated definition payload was available.",
                    }
                )
                continue
            print(f"Generating {output_path}")
            metadata = map_preview.get("generation_metadata")
            write_definition_file(output_path, definition, metadata=metadata if isinstance(metadata, dict) else None)
            generated_files.append(str(output_path))

    print(
        f"[Geolocator] Generation complete: generated={len(generated_files)} skipped={len(skipped_maps)} "
        f"target={preview['target']} module={preview['module']}"
    )
    return {
        "target": preview["target"],
        "project_name": preview["project_name"],
        "module": preview["module"],
        "resolved_source_path": preview["resolved_source_path"],
        "generated_files": generated_files,
        "skipped_maps": skipped_maps,
        "mods": preview["mods"],
        "total_generated": len(generated_files),
    }


def _resolve_module_root(project: dict[str, object], module: str) -> Path:
    normalized_module = str(module or "DynamicTradingCommon").strip()
    for mod in project.get("sub_mods", []):
        if str(mod.get("id", "")).lower() == normalized_module.lower():
            return Path(mod["path"])
    raise FileNotFoundError(f"Module '{normalized_module}' was not found in project '{project['name']}'.")


def _build_mod_preview(source_mod: DiscoveredMod, module_root: Path, llm_config: dict[str, object] | None = None) -> dict[str, object]:
    mod_metadata = _collect_mod_metadata(source_mod)
    output_folder = _determine_output_folder_name(mod_metadata)
    map_previews = [_build_map_preview(source_mod, map_folder, module_root, output_folder, mod_metadata, llm_config=llm_config) for map_folder in source_mod.map_folders]

    warnings = list(mod_metadata["warnings"])
    for map_preview in map_previews:
        warnings.extend(map_preview["warnings"])

    return {
        "mod_root": str(source_mod.mod_root),
        "source_path": str(_preferred_source_path(source_mod)),
        "mod_name": mod_metadata["name"],
        "mod_id": mod_metadata["id"],
        "mod_version": mod_metadata["version"],
        "mod_ids": mod_metadata["mod_ids"],
        "workshop_item_id": get_workshop_item_id_for_mod_root(source_mod.mod_root),
        "output_folder": output_folder,
        "warnings": _unique_strings(warnings),
        "maps": map_previews,
        "registry_status": _summarize_mod_registry_status(map_previews, mod_metadata["version"]),
    }


def _collect_mod_metadata(source_mod: DiscoveredMod) -> dict[str, object]:
    parsed_infos = [parse_mod_info(path) for path in source_mod.mod_info_files]
    primary = parsed_infos[0] if parsed_infos else {}
    mod_ids = _unique_strings([payload.get("id", "") for payload in parsed_infos if payload.get("id")])
    name = primary.get("name") or source_mod.mod_root.name
    mod_id = primary.get("id") or sanitize_pascal_case(strip_version_tokens(name)) or sanitize_pascal_case(source_mod.mod_root.name)
    version = (
        primary.get("version")
        or primary.get("modversion")
        or primary.get("versionMin")
        or ""
    )
    warnings: list[str] = []
    if not mod_ids:
        warnings.append(f"No mod ID was found in mod.info under {source_mod.mod_root}.")
    return {
        "name": name,
        "id": mod_id,
        "version": version,
        "mod_ids": mod_ids or [mod_id],
        "warnings": warnings,
    }


def _build_map_preview(
    source_mod: DiscoveredMod,
    map_folder: Path,
    module_root: Path,
    output_folder: str,
    mod_metadata: dict[str, object],
    llm_config: dict[str, object] | None = None,
) -> dict[str, object]:
    map_name = map_folder.name
    spawnregions_path = map_folder / "spawnregions.lua"
    annotations_path = map_folder / "worldmap-annotations.lua"
    objects_path = map_folder / "objects.lua"
    worldmap_path = map_folder / "worldmap.xml"

    spawnregions = parse_spawnregions(spawnregions_path) if spawnregions_path.exists() else []
    spawnpoints = _collect_spawnpoints(source_mod, map_folder, spawnregions)
    annotations = parse_worldmap_annotations(annotations_path) if annotations_path.exists() else []
    object_entries = parse_objects_lua(objects_path) if objects_path.exists() else []
    world_features = parse_worldmap_features(worldmap_path) if worldmap_path.exists() else []
    lotheader_cells = parse_lotheader_cells(map_folder)

    bounds, bound_warnings = build_map_bounds(lotheader_cells, spawnpoints, annotations)
    warnings = list(bound_warnings)
    if not spawnpoints:
        warnings.append(f"{map_name}: no spawnpoints.lua was found.")
    if not world_features:
        warnings.append(f"{map_name}: no worldmap.xml features were found for generic POI clustering.")

    short_name = _determine_short_name(map_name, spawnregions, annotations)
    long_name = _determine_long_name(short_name, spawnregions)
    file_base_name = sanitize_pascal_case(strip_version_tokens(short_name or map_name)) or sanitize_pascal_case(map_name)
    county_name = short_name
    map_folders = _unique_strings([map_name])
    world_maps = _unique_strings([map_name] + [entry["name"] for entry in spawnregions if entry.get("name")])
    pois, poi_buckets, poi_warnings = build_map_pois(
        map_name=map_name,
        town_name=short_name,
        county_name=county_name,
        annotations=annotations,
        object_entries=object_entries,
        world_features=world_features,
        llm_config=llm_config,
    )
    warnings.extend(poi_warnings)

    definition = {
        "id": file_base_name,
        "mod": mod_metadata["name"],
        "isVanilla": False,
        "activation": {
            "modIDs": mod_metadata["mod_ids"],
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
        "counties": [
            {
                "name": county_name,
                "bounds": {
                    "minX": bounds["minX"],
                    "maxX": bounds["maxX"],
                    "minY": bounds["minY"],
                    "maxY": bounds["maxY"],
                },
                "towns": [short_name],
            }
        ],
        "pois": pois,
    }

    output_file = module_root / GEOLOCATOR_DEFINITIONS_SUBPATH / output_folder / f"DT_{file_base_name}.lua"
    source_fingerprint = _compute_source_fingerprint(definition)
    generation_metadata = {
        "GeneratedAt": _utc_now_iso(),
        "SourceVersion": str(mod_metadata.get("version", "") or ""),
        "SourceFingerprint": source_fingerprint,
        "WorkshopItemID": get_workshop_item_id_for_mod_root(source_mod.mod_root) or "",
        "SourcePath": str(_preferred_source_path(source_mod)),
        "MapFolder": map_name,
    }
    registry_status = _build_registry_status(output_file, definition, str(mod_metadata.get("version", "") or ""), source_fingerprint)

    return {
        "map_folder": str(map_folder),
        "map_folder_name": map_name,
        "display_name": short_name,
        "long_name": long_name,
        "bounds": bounds,
        "warnings": warnings,
        "spawnregion_names": [entry["name"] for entry in spawnregions if entry.get("name")],
        "spawnpoint_count": len(spawnpoints),
        "poi_count": len(pois),
        "pois": pois,
        "poi_buckets": poi_buckets,
        "output_file": str(output_file),
        "definition": definition,
        "generation_metadata": generation_metadata,
        "registry_status": registry_status,
        "lua_preview": render_definition_file(definition, metadata=generation_metadata),
    }


def _determine_output_folder_name(mod_metadata: dict[str, object]) -> str:
    primary_name = strip_version_tokens(str(mod_metadata["name"]))
    sanitized = sanitize_pascal_case(primary_name)
    if sanitized:
        return sanitized
    return sanitize_pascal_case(str(mod_metadata["id"])) or "GeneratedMaps"


def _determine_short_name(map_name: str, spawnregions: list[dict[str, str]], annotations: list[dict[str, object]]) -> str:
    town_label = next((label["name"] for label in annotations if str(label.get("symbolType", "")).lower() == "text-town"), None)
    if town_label:
        return str(town_label)

    spawn_name = next((entry["name"] for entry in spawnregions if entry.get("name")), None)
    if spawn_name:
        return _strip_region_suffix(str(spawn_name))

    return strip_version_tokens(map_name) or map_name


def _determine_long_name(short_name: str, spawnregions: list[dict[str, str]]) -> str:
    spawn_name = next((entry["name"] for entry in spawnregions if entry.get("name")), None)
    if spawn_name:
        return str(spawn_name)
    return f"{short_name}, KY"


def _strip_region_suffix(value: str) -> str:
    text = str(value or "").strip()
    if "," in text:
        text = text.split(",", 1)[0].strip()
    return strip_version_tokens(text) or text


def _collect_spawnpoints(
    source_mod: DiscoveredMod,
    map_folder: Path,
    spawnregions: list[dict[str, str]],
) -> list[dict[str, int]]:
    candidates: list[Path] = []
    default_path = map_folder / "spawnpoints.lua"
    if default_path.exists():
        candidates.append(default_path)

    for entry in spawnregions:
        raw_file = str(entry.get("file", "")).strip()
        if not raw_file:
            continue
        normalized = raw_file.replace("\\", "/").lstrip("/")
        for content_root in source_mod.content_roots:
            candidate = content_root / normalized
            if candidate.exists():
                candidates.append(candidate)
                break

    points: list[dict[str, int]] = []
    seen: set[tuple[int, int, int]] = set()
    for candidate in candidates:
        for point in parse_spawnpoints(candidate):
            key = (point["x"], point["y"], point.get("posZ", 0))
            if key in seen:
                continue
            seen.add(key)
            points.append(point)
    return points


def _unique_strings(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _preferred_source_path(source_mod: DiscoveredMod) -> Path:
    common_root = next((root for root in source_mod.content_roots if root.name.lower() == "common"), None)
    if common_root is not None:
        return common_root
    if source_mod.content_roots:
        return source_mod.content_roots[0]
    return source_mod.mod_root


def _build_mod_preview_without_target(source_mod: DiscoveredMod) -> dict[str, object]:
    mod_metadata = _collect_mod_metadata(source_mod)
    output_folder = _determine_output_folder_name(mod_metadata)
    return {
        "mod_root": str(source_mod.mod_root),
        "source_path": str(_preferred_source_path(source_mod)),
        "mod_name": mod_metadata["name"],
        "mod_id": mod_metadata["id"],
        "mod_version": mod_metadata["version"],
        "mod_ids": mod_metadata["mod_ids"],
        "workshop_item_id": get_workshop_item_id_for_mod_root(source_mod.mod_root),
        "output_folder": output_folder,
        "warnings": _unique_strings(list(mod_metadata["warnings"])),
        "maps": [
            {
                "map_folder_name": map_folder.name,
                "display_name": strip_version_tokens(map_folder.name) or map_folder.name,
                "registry_status": {"state": "unknown", "is_added": False},
            }
            for map_folder in source_mod.map_folders
        ],
        "registry_status": {
            "state": "unknown",
            "is_added": False,
            "added_at": None,
            "source_version": mod_metadata["version"],
        },
    }


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
            "source_version": source_version or None,
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
    added_at = metadata.get("GeneratedAt") or _file_mtime_iso(output_file)
    is_outdated = content_changed or fingerprint_changed or version_changed

    return {
        "state": "outdated" if is_outdated else "added",
        "is_added": True,
        "is_outdated": is_outdated,
        "added_at": added_at,
        "source_version": source_version or None,
        "generated_version": generated_version,
        "output_exists": True,
    }


def _summarize_mod_registry_status(map_previews: list[dict[str, object]], source_version: str) -> dict[str, object]:
    statuses = [preview.get("registry_status") for preview in map_previews if isinstance(preview.get("registry_status"), dict)]
    added_count = sum(1 for status in statuses if status.get("is_added"))
    outdated_count = sum(1 for status in statuses if status.get("is_outdated"))
    total = len(statuses)
    added_dates = [status.get("added_at") for status in statuses if status.get("added_at")]
    generated_versions = _unique_strings([status.get("generated_version") or "" for status in statuses if status.get("generated_version")])

    if total == 0:
        state = "unknown"
    elif added_count == 0:
        state = "not_added"
    elif added_count < total:
        state = "partial"
    elif outdated_count > 0:
        state = "outdated"
    else:
        state = "added"

    return {
        "state": state,
        "is_added": added_count > 0,
        "is_outdated": outdated_count > 0,
        "added_at": min(added_dates) if added_dates else None,
        "source_version": source_version or None,
        "generated_version": generated_versions[0] if len(generated_versions) == 1 else (generated_versions[0] if generated_versions else None),
        "added_maps": added_count,
        "total_maps": total,
    }


def _build_workshop_source_summary(mod_preview: dict[str, object]) -> dict[str, object]:
    return {
        "id": f"{mod_preview.get('workshop_item_id') or 'local'}:{Path(str(mod_preview.get('mod_root', ''))).name}",
        "workshop_item_id": mod_preview.get("workshop_item_id"),
        "mod_root": mod_preview.get("mod_root"),
        "source_path": mod_preview.get("source_path"),
        "mod_name": mod_preview.get("mod_name"),
        "mod_id": mod_preview.get("mod_id"),
        "mod_version": mod_preview.get("mod_version"),
        "output_folder": mod_preview.get("output_folder"),
        "map_count": len(mod_preview.get("maps", [])),
        "map_names": [map_item.get("map_folder_name") for map_item in mod_preview.get("maps", []) if map_item.get("map_folder_name")],
        "registry_status": mod_preview.get("registry_status"),
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _file_mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat()
