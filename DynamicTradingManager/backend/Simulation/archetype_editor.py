from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from .config import default_paths
from .models import ItemDef
from .parse.lua_utils import (
    extract_balanced_block,
    find_lua_files,
    parse_lua_map_numbers,
    parse_quoted_list,
    read_text,
    table_field_block,
)
from .parse.items_parser import parse_items
from .sim.tag_logic import matches_all_tags, tag_matches

try:
    from ItemManagement.commons.vanilla_loader import get_translated_name, load_vanilla_items
except ImportError:
    load_vanilla_items = None
    get_translated_name = None


REGISTER_ARCH_RE = re.compile(r'DynamicTrading\.RegisterArchetype\(\s*"([^"]+)"\s*,\s*\{', re.DOTALL)
ALLOC_ENTRY_RE = re.compile(
    r'\{\s*(?:tags\s*=\s*\{([^}]*)\}|item\s*=\s*"([^"]+)")\s*,\s*count\s*=\s*(\d+)\s*\}',
    re.DOTALL,
)
ITEM_FIELD_RE = re.compile(r'\bitem\s*=\s*"([^"]+)"')
COUNT_FIELD_RE = re.compile(r'\bcount\s*=\s*(\d+)')

ALLOWED_ARCHETYPE_FIELDS = {"name", "allocations", "expertTags", "wants", "forbid"}
REQUIRED_ARCHETYPE_FIELDS = {"name", "allocations"}
ALLOWED_ALLOCATION_FIELDS = {"tags", "item", "count"}


def load_archetype_editor_data(mod_id: str = "DynamicTradingCommon") -> dict:
    paths = default_paths(mod_id=mod_id)
    items = _get_cached_items(mod_id)
    taxonomy_tags = _get_cached_taxonomy_tags(mod_id)
    archetypes = _load_archetypes(paths.mod_common / "ArchetypeDefinitions", items, taxonomy_tags, _get_cached_vanilla_items())
    all_tags = _collect_all_tags(items, archetypes)
    portrait_catalog = _get_cached_portrait_catalog(mod_id)

    archetype_item_coverage: dict[str, set[str]] = {}
    served_item_ids: set[str] = set()

    for archetype in archetypes:
        covered: set[str] = set()
        for allocation in archetype["allocations"]:
            match_ids = _match_entry_items(allocation, items)
            covered.update(match_ids)
        archetype_item_coverage[archetype["archetype_id"]] = covered
        served_item_ids.update(covered)

    item_catalog = [
        {
            "item_id": item_id,
            "name": _get_item_name_cached(item_id),
            "tags": item_def.tags,
        }
        for item_id, item_def in sorted(items.items())
    ]

    available_tags = []
    for tag in sorted(all_tags):
        matching_items = _find_matching_items_for_tag(tag, items)
        served_matches = [item_id for item_id in matching_items if item_id in served_item_ids]
        covered_by = [
            archetype["archetype_id"]
            for archetype in archetypes
            if any(item_id in archetype_item_coverage[archetype["archetype_id"]] for item_id in matching_items)
        ]

        available_tags.append(
            {
                "tag": tag,
                "item_count": len(matching_items),
                "covered_item_count": len(served_matches),
                "covered_by_count": len(covered_by),
                "covered_by": covered_by,
                "sample_items": [
                    {
                        "item_id": item_id,
                    "name": _get_item_name_cached(item_id),
                    }
                    for item_id in matching_items[:5]
                ],
            }
        )

    uncovered_tags = [
        row
        for row in available_tags
        if row["item_count"] > 0 and row["covered_item_count"] == 0
    ]
    uncovered_tags.sort(key=lambda row: (-row["item_count"], row["tag"]))

    archetypes.sort(key=lambda row: row["name"].lower())

    return {
        "meta": {
            "archetype_count": len(archetypes),
            "item_count": len(items),
            "tag_count": len(available_tags),
            "uncovered_tag_count": len(uncovered_tags),
            "invalid_archetype_count": len([row for row in archetypes if row["validation"]["issue_count"] > 0]),
            "portrait_archetype_count": len([row for row in archetypes if row.get("portraits")]),
        },
        "archetypes": archetypes,
        "available_tags": available_tags,
        "uncovered_tags": uncovered_tags,
        "item_catalog": item_catalog,
        "portrait_base_url": "/static/portraits",
    }


def save_archetype_definition(archetype_id: str, payload: dict, mod_id: str = "DynamicTradingCommon") -> dict:
    paths = default_paths(mod_id=mod_id)
    items = _get_cached_items(mod_id)
    taxonomy_tags = _get_cached_taxonomy_tags(mod_id)
    archetypes = _load_archetypes(paths.mod_common / "ArchetypeDefinitions", items, taxonomy_tags, _get_cached_vanilla_items())
    archetype = next((row for row in archetypes if row["archetype_id"] == archetype_id), None)
    if archetype is None:
        raise ValueError(f"Unknown archetype: {archetype_id}")

    normalized = _normalize_archetype_payload(payload, items, archetype_id)
    file_path = Path(archetype["source_file"])
    _write_archetype(file_path, archetype_id, normalized)
    return _load_single_archetype(file_path, items, taxonomy_tags, _get_cached_vanilla_items())


def _collect_all_tags(items: Dict[str, ItemDef], archetypes: list[dict] | None = None) -> set[str]:
    tags: set[str] = set()

    def add_tag_family(tag_name: str) -> None:
        parts = [part for part in tag_name.split(".") if part]
        for index in range(len(parts)):
            tags.add(".".join(parts[: index + 1]))

    for item_def in items.values():
        for tag in item_def.tags:
            add_tag_family(tag)

    for archetype in archetypes or []:
        for allocation in archetype.get("allocations", []):
            for tag in allocation.get("tags") or []:
                add_tag_family(tag)

    return tags


@lru_cache(maxsize=8)
def _get_cached_items(mod_id: str = "DynamicTradingCommon") -> Dict[str, ItemDef]:
    paths = default_paths(mod_id=mod_id)
    return parse_items(paths.mod_common / "Items")


@lru_cache(maxsize=8)
def _get_cached_taxonomy_tags(mod_id: str = "DynamicTradingCommon") -> set[str]:
    return _collect_all_tags(_get_cached_items(mod_id))


@lru_cache(maxsize=1)
def _get_cached_vanilla_items() -> dict:
    return load_vanilla_items() if load_vanilla_items else {}


@lru_cache(maxsize=None)
def _get_item_name_cached(item_id: str) -> str:
    return _get_item_name(item_id, _get_cached_vanilla_items())


def _load_archetypes(archetypes_root: Path, items: Dict[str, ItemDef], taxonomy_tags: set[str], vanilla_items: dict) -> list[dict]:
    archetypes: list[dict] = []
    portrait_catalog = _get_cached_portrait_catalog()

    for lua_file in find_lua_files(archetypes_root):
        normalized = str(lua_file).replace("\\", "/")
        # Removed hardcoded "/Items/" filter if possible, or made it more inclusive
        archetypes.extend(_parse_archetype_file(lua_file, items, taxonomy_tags, vanilla_items, portrait_catalog))

    return archetypes


def _load_single_archetype(file_path: Path, items: Dict[str, ItemDef], taxonomy_tags: set[str], vanilla_items: dict) -> dict:
    portrait_catalog = _get_cached_portrait_catalog()
    parsed = _parse_archetype_file(file_path, items, taxonomy_tags, vanilla_items, portrait_catalog)
    if not parsed:
        raise ValueError(f"Unable to reparse archetype file {file_path.name} after save.")
    return parsed[0]


def _parse_archetype_file(
    lua_file: Path,
    items: Dict[str, ItemDef],
    taxonomy_tags: set[str],
    vanilla_items: dict,
    portrait_catalog: dict[str, list[dict]],
) -> list[dict]:
    archetypes: list[dict] = []
    content = read_text(lua_file)
    for match in REGISTER_ARCH_RE.finditer(content):
        archetype_id = match.group(1).strip()
        open_idx = match.end() - 1
        block = extract_balanced_block(content, open_idx)
        if not block:
            continue

        name_match = re.search(r'name\s*=\s*"([^"]+)"', block)
        name = name_match.group(1).strip() if name_match else archetype_id
        
        module_match = re.search(r'module\s*=\s*"([^"]+)"', block)
        module_id = module_match.group(1).strip() if module_match else None
        expert_tags = parse_quoted_list(table_field_block(block, "expertTags"))
        forbid = parse_quoted_list(table_field_block(block, "forbid"))
        wants = [
            {
                "tag": tag,
                "multiplier": multiplier,
            }
            for tag, multiplier in parse_lua_map_numbers(table_field_block(block, "wants")).items()
        ]

        allocations: list[dict] = []
        alloc_block = ""
        alloc_match = re.search(r"allocations\s*=\s*\{", block)
        if alloc_match:
            alloc_open_idx = alloc_match.end() - 1
            alloc_block = extract_balanced_block(block, alloc_open_idx)
            for source_order, entry_match in enumerate(ALLOC_ENTRY_RE.finditer(alloc_block)):
                if entry_match.group(1) is not None:
                    entry = {
                        "kind": "tag",
                        "tags": parse_quoted_list(entry_match.group(1)),
                        "count": int(entry_match.group(3)),
                        "source_order": source_order,
                    }
                else:
                    entry = {
                        "kind": "item",
                        "item_id": entry_match.group(2).strip(),
                        "count": int(entry_match.group(3)),
                        "source_order": source_order,
                    }

                allocations.append(_entry_to_payload(entry, items, vanilla_items))

            for index, allocation in enumerate(allocations):
                allocation["position"] = index
                allocation.pop("source_order", None)

        validation = _validate_archetype_block(
            archetype_id,
            block,
            alloc_block,
            items,
            taxonomy_tags,
        )

        archetypes.append(
            {
                "position": index,
                "archetype_id": archetype_id,
                "name": name,
                "module": module_id,
                "expert_tags": expert_tags,
                "forbid": forbid,
                "wants": wants,
                "source_file": str(lua_file),
                "allocations": allocations,
                "allocation_count": len(allocations),
                "tag_allocation_count": len([row for row in allocations if row["kind"] == "tag"]),
                "item_allocation_count": len([row for row in allocations if row["kind"] == "item"]),
                "validation": validation,
                "portraits": portrait_catalog.get(archetype_id, []),
            }
        )

    return archetypes


@lru_cache(maxsize=8)
def _get_cached_portrait_catalog(mod_id: str = "DynamicTradingCommon") -> dict[str, list[dict]]:
    portraits_root = _get_portraits_root(mod_id)
    catalog: dict[str, list[dict]] = {}
    if not portraits_root or not portraits_root.exists():
        return catalog

    for archetype_dir in sorted([path for path in portraits_root.iterdir() if path.is_dir()]):
        groups: list[dict] = []
        for variant_dir in sorted([path for path in archetype_dir.iterdir() if path.is_dir()], key=lambda path: path.name.lower()):
            images = sorted([path for path in variant_dir.iterdir() if path.is_file()])
            if not images:
                continue
            groups.append(
                {
                    "label": variant_dir.name,
                    "images": [f'/static/portraits/{image.relative_to(portraits_root).as_posix()}' for image in images],
                }
            )
        if groups:
            catalog[archetype_dir.name] = groups
    return catalog


def _get_portraits_root(mod_id: str = "DynamicTradingCommon") -> Path:
    from config.paths import get_portraits_root
    return get_portraits_root(mod_id)


def _validate_archetype_block(
    archetype_id: str,
    block: str,
    alloc_block: str,
    items: Dict[str, ItemDef],
    taxonomy_tags: set[str],
) -> dict:
    issues: list[dict] = []
    field_names = _extract_top_level_field_names(block)

    unknown_fields = sorted({field for field in field_names if field not in ALLOWED_ARCHETYPE_FIELDS})
    for field in unknown_fields:
        issues.append(_issue("error", "unknown_field", f'Unknown archetype variable "{field}" in {archetype_id}.', field=field))

    for field in sorted(REQUIRED_ARCHETYPE_FIELDS):
        if field not in field_names:
            issues.append(_issue("error", "missing_field", f'Missing required archetype field "{field}" in {archetype_id}.', field=field))

    for field_name in ("expertTags", "forbid"):
        for index, tag in enumerate(parse_quoted_list(table_field_block(block, field_name))):
            if tag not in taxonomy_tags:
                issues.append(
                    _issue(
                        "warning",
                        "unknown_tag",
                        f'Unknown tag "{tag}" found in {field_name}.',
                        field=field_name,
                        value=tag,
                        replaceable=True,
                        path={
                            "section": "expert_tags" if field_name == "expertTags" else "forbid",
                            "index": index,
                        },
                    )
                )

    for index, (tag, multiplier) in enumerate(parse_lua_map_numbers(table_field_block(block, "wants")).items()):
        if tag not in taxonomy_tags:
            issues.append(
                _issue(
                    "warning",
                    "unknown_tag",
                    f'Unknown tag "{tag}" found in wants.',
                    field="wants",
                    value=tag,
                    replaceable=True,
                    path={
                        "section": "wants",
                        "index": index,
                        "tag": tag,
                        "multiplier": multiplier,
                    },
                )
            )

    for index, entry in enumerate(_split_top_level_table_entries(alloc_block), start=1):
        entry_fields = _extract_top_level_field_names(entry)
        unknown_alloc_fields = sorted({field for field in entry_fields if field not in ALLOWED_ALLOCATION_FIELDS})
        for field in unknown_alloc_fields:
            issues.append(
                _issue(
                    "error",
                    "unknown_allocation_field",
                    f'Allocation row #{index} uses invalid variable "{field}".',
                    field=field,
                )
            )

        has_tags = "tags" in entry_fields
        has_item = "item" in entry_fields
        if not has_tags and not has_item:
            issues.append(
                _issue(
                    "error",
                    "allocation_missing_source",
                    f'Allocation row #{index} needs either tags or item.',
                    field="allocations",
                )
            )
        if has_tags and has_item:
            issues.append(
                _issue(
                    "error",
                    "allocation_conflict",
                    f'Allocation row #{index} cannot contain both tags and item.',
                    field="allocations",
                )
            )

        if "count" not in entry_fields:
            issues.append(
                _issue(
                    "error",
                    "allocation_missing_count",
                    f'Allocation row #{index} is missing a count value.',
                    field="count",
                )
            )
        else:
            count_match = COUNT_FIELD_RE.search(entry)
            if count_match and int(count_match.group(1)) < 1:
                issues.append(
                    _issue(
                        "error",
                        "allocation_invalid_count",
                        f'Allocation row #{index} must use a count of at least 1.',
                        field="count",
                        value=count_match.group(1),
                    )
                )

        if has_tags:
            tags = parse_quoted_list(table_field_block(entry, "tags"))
            if not tags:
                issues.append(
                    _issue(
                        "error",
                        "allocation_empty_tags",
                        f'Allocation row #{index} has an empty tags list.',
                        field="tags",
                    )
                )
            for tag_index, tag in enumerate(tags):
                if tag not in taxonomy_tags:
                    issues.append(
                        _issue(
                        "error",
                        "unknown_tag",
                        f'Allocation row #{index} uses unknown tag "{tag}".',
                        field="tags",
                        value=tag,
                        replaceable=True,
                        path={
                            "section": "allocations",
                            "entry_index": index - 1,
                            "tag_index": tag_index,
                        },
                    )
                )

        if has_item:
            item_match = ITEM_FIELD_RE.search(entry)
            item_id = item_match.group(1).strip() if item_match else ""
            if not item_id:
                issues.append(
                    _issue(
                        "error",
                        "allocation_missing_item_id",
                        f'Allocation row #{index} is missing an item ID.',
                        field="item",
                    )
                )
            elif item_id not in items:
                issues.append(
                    _issue(
                        "error",
                        "unknown_item",
                        f'Allocation row #{index} uses unknown item ID "{item_id}".',
                        field="item",
                        value=item_id,
                    )
                )

    return {
        "issue_count": len(issues),
        "error_count": len([issue for issue in issues if issue["level"] == "error"]),
        "warning_count": len([issue for issue in issues if issue["level"] == "warning"]),
        "issues": issues,
    }


def _issue(
    level: str,
    code: str,
    message: str,
    field: str | None = None,
    value: str | None = None,
    replaceable: bool = False,
    path: dict | None = None,
) -> dict:
    return {
        "level": level,
        "code": code,
        "message": message,
        "field": field,
        "value": value,
        "replaceable": replaceable,
        "path": path,
    }


def _extract_top_level_field_names(table_text: str) -> list[str]:
    if not table_text or not table_text.strip().startswith("{"):
        return []

    fields: list[str] = []
    depth = 0
    in_string = False
    string_char = ""
    escape = False
    index = 0

    while index < len(table_text):
        char = table_text[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == string_char:
                in_string = False
            index += 1
            continue

        if char in ('"', "'"):
            in_string = True
            string_char = char
            index += 1
            continue

        if char == "{":
            depth += 1
            index += 1
            continue

        if char == "}":
            depth -= 1
            index += 1
            continue

        if depth == 1 and (char.isalpha() or char == "_"):
            start = index
            index += 1
            while index < len(table_text) and (table_text[index].isalnum() or table_text[index] == "_"):
                index += 1
            field_name = table_text[start:index]
            probe = index
            while probe < len(table_text) and table_text[probe].isspace():
                probe += 1
            if probe < len(table_text) and table_text[probe] == "=":
                fields.append(field_name)
            continue

        index += 1

    return fields


def _split_top_level_table_entries(table_text: str) -> list[str]:
    if not table_text or not table_text.strip().startswith("{"):
        return []

    entries: list[str] = []
    depth = 0
    in_string = False
    string_char = ""
    escape = False
    entry_start = -1

    for index, char in enumerate(table_text):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == string_char:
                in_string = False
            continue

        if char in ('"', "'"):
            in_string = True
            string_char = char
            continue

        if char == "{":
            if depth == 1:
                entry_start = index
            depth += 1
            continue

        if char == "}":
            depth -= 1
            if depth == 1 and entry_start >= 0:
                entries.append(table_text[entry_start:index + 1])
                entry_start = -1

    return entries


def _entry_to_payload(entry: dict, items: Dict[str, ItemDef], vanilla_items: dict) -> dict:
    matching_items = _match_entry_items(entry, items)
    payload = {
        "kind": entry["kind"],
        "count": int(entry["count"]),
        "matched_item_count": len(matching_items),
        "sample_items": [
            {
                "item_id": item_id,
                "name": _get_item_name(item_id, vanilla_items),
            }
            for item_id in matching_items[:5]
        ],
        "source_order": entry.get("source_order", 0),
    }

    if entry["kind"] == "tag":
        payload["tags"] = list(entry["tags"])
        payload["label"] = " + ".join(entry["tags"])
    else:
        item_id = entry["item_id"]
        payload["item_id"] = item_id
        payload["label"] = item_id
        payload["item_name"] = _get_item_name(item_id, vanilla_items)

    return payload


def _match_entry_items(entry: dict, items: Dict[str, ItemDef]) -> list[str]:
    if entry["kind"] == "item":
        item_id = entry["item_id"]
        return [item_id] if item_id in items else []

    tags = entry.get("tags") or []
    if not tags:
        return []

    return [
        item_id
        for item_id, item_def in items.items()
        if matches_all_tags(item_def.tags, tags)
    ]


def _find_matching_items_for_tag(tag: str, items: Dict[str, ItemDef]) -> list[str]:
    matches = []
    for item_id, item_def in items.items():
        if any(tag_matches(item_tag, tag) for item_tag in item_def.tags):
            matches.append(item_id)
    return matches


def _get_item_name(item_id: str, vanilla_items: dict) -> str:
    bare_id = item_id.split(".", 1)[1] if "." in item_id else item_id
    props = vanilla_items.get(bare_id) if isinstance(vanilla_items, dict) else None
    if props and get_translated_name:
        return get_translated_name(bare_id, props)
    return bare_id


def _normalize_entries(entries: List[dict], items: Dict[str, ItemDef]) -> list[dict]:
    normalized: list[dict] = []
    for index, entry in enumerate(entries):
        kind = str(entry.get("kind", "")).strip().lower()
        try:
            count = int(entry.get("count", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Allocation #{index + 1} has an invalid count.") from exc

        if count < 1:
            raise ValueError(f"Allocation #{index + 1} must have a count of at least 1.")

        if kind == "tag":
            tags = [str(tag).strip() for tag in (entry.get("tags") or []) if str(tag).strip()]
            if not tags:
                raise ValueError(f"Allocation #{index + 1} is missing tag values.")
            normalized.append({"kind": "tag", "tags": tags, "count": count})
            continue

        if kind == "item":
            item_id = str(entry.get("item_id", "")).strip()
            if not item_id:
                raise ValueError(f"Allocation #{index + 1} is missing an item ID.")
            if item_id not in items:
                raise ValueError(f"Allocation #{index + 1} uses an unknown item ID: {item_id}")
            normalized.append({"kind": "item", "item_id": item_id, "count": count})
            continue

        raise ValueError(f"Allocation #{index + 1} has an unsupported kind: {kind}")

    return normalized


def _normalize_tag_list(values: List[str] | None) -> list[str]:
    return [str(value).strip() for value in (values or []) if str(value).strip()]


def _normalize_wants(values: List[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for index, row in enumerate(values or []):
        tag = str(row.get("tag", "")).strip()
        if not tag:
            raise ValueError(f'Want entry #{index + 1} is missing a tag.')
        try:
            multiplier = float(row.get("multiplier", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f'Want entry #{index + 1} has an invalid multiplier.') from exc
        if multiplier <= 0:
            raise ValueError(f'Want entry #{index + 1} must use a multiplier above 0.')
        normalized.append({
            "tag": tag,
            "multiplier": multiplier,
        })
    return normalized


def _normalize_archetype_payload(payload: dict, items: Dict[str, ItemDef], archetype_id: str) -> dict:
    name = str(payload.get("name", "")).strip() or archetype_id
    module = str(payload.get("module", "")).strip() or None
    return {
        "name": name,
        "module": module,
        "allocations": _normalize_entries(payload.get("allocations") or [], items),
        "expert_tags": _normalize_tag_list(payload.get("expert_tags")),
        "forbid": _normalize_tag_list(payload.get("forbid")),
        "wants": _normalize_wants(payload.get("wants")),
    }


def _write_archetype(file_path: Path, archetype_id: str, payload: dict) -> None:
    content = read_text(file_path)

    for match in REGISTER_ARCH_RE.finditer(content):
        if match.group(1).strip() != archetype_id:
            continue

        block_start = match.end() - 1
        block = extract_balanced_block(content, block_start)
        if not block:
            break
        updated_block = _render_archetype_block(archetype_id, payload)

        updated_content = (
            content[:block_start]
            + updated_block
            + content[block_start + len(block):]
        )
        file_path.write_text(updated_content, encoding="utf-8")
        return

    raise ValueError(f"Unable to locate archetype definition for {archetype_id} in {file_path.name}.")


def _render_allocations(entries: list[dict]) -> str:
    if not entries:
        return "{\n    }"

    lines = ["{"]
    for index, entry in enumerate(entries):
        suffix = "," if index < len(entries) - 1 else ""
        if entry["kind"] == "tag":
            tags = ", ".join(f'"{tag}"' for tag in entry["tags"])
            lines.append(f'        {{ tags={{{tags}}}, count = {entry["count"]} }}{suffix}')
        else:
            lines.append(f'        {{ item = "{entry["item_id"]}", count = {entry["count"]} }}{suffix}')
    lines.append("    }")
    return "\n".join(lines)


def _render_quoted_list(values: list[str], indent: str = "    ") -> str:
    if not values:
        return "{}"
    joined = ", ".join(f'"{_escape_lua_string(value)}"' for value in values)
    return f"{{ {joined} }}"


def _render_wants(entries: list[dict]) -> str:
    if not entries:
        return "{}"

    lines = ["{"]
    for index, row in enumerate(entries):
        suffix = "," if index < len(entries) - 1 else ""
        lines.append(f'        ["{_escape_lua_string(row["tag"])}"] = {row["multiplier"]}{suffix}')
    lines.append("    }")
    return "\n".join(lines)


def _escape_lua_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _render_archetype_block(archetype_id: str, payload: dict) -> str:
    lines = ["{"]
    lines.append(f'    name = "{_escape_lua_string(payload["name"])}",')
    if payload.get("module"):
        lines.append(f'    module = "{_escape_lua_string(payload["module"])}",')
    
    lines.append(f'    allocations = {_render_allocations(payload["allocations"])}' + ("," if payload["expert_tags"] or payload["wants"] or payload["forbid"] is not None else ""))

    if payload["expert_tags"]:
        lines.append(f'    expertTags = {_render_quoted_list(payload["expert_tags"])},')

    lines.append(f'    wants = {_render_wants(payload["wants"])},')
    lines.append(f'    forbid = {_render_quoted_list(payload["forbid"])}')
    lines.append("}")
    return "\n".join(lines)
