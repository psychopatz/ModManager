from __future__ import annotations

import re
from pathlib import Path
import xml.etree.ElementTree as ET


def parse_mod_info(path: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = value.strip()
    return payload


def parse_spawnregions(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(r'name\s*=\s*"([^"]+)"\s*,\s*file\s*=\s*"([^"]+)"')
    return [{"name": match.group(1), "file": match.group(2)} for match in pattern.finditer(text)]


def parse_spawnpoints(path: Path) -> list[dict[str, int]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    
    # Match the entire block between { and } for each spawn point entry
    # This allows us to find key-value pairs independently of their order
    entry_pattern = re.compile(r"\{([^\}]+)\}")
    
    points: list[dict[str, int]] = []
    for match in entry_pattern.finditer(text):
        entry_text = match.group(1)
        
        # Extract values using specific key-based searches
        def get_val(key: str) -> int | None:
            m = re.search(rf"\b{key}\s*=\s*(-?\d+)", entry_text)
            return int(m.group(1)) if m else None
        
        world_x = get_val("worldX")
        world_y = get_val("worldY")
        pos_x = get_val("posX")
        pos_y = get_val("posY")
        pos_z = get_val("posZ") or 0
        
        if pos_x is None or pos_y is None:
            continue
            
        # If worldX/Y are provided, x/y are relative to the cell
        if world_x is not None and world_y is not None:
            abs_x = world_x * 300 + pos_x
            abs_y = world_y * 300 + pos_y
        else:
            # If worldX/Y are missing, posX/posY are treated as absolute coordinates
            abs_x = pos_x
            abs_y = pos_y
            world_x = abs_x // 300
            world_y = abs_y // 300
            
        points.append(
            {
                "worldX": world_x,
                "worldY": world_y,
                "posX": pos_x,
                "posY": pos_y,
                "posZ": pos_z,
                "x": abs_x,
                "y": abs_y,
            }
        )
    return points


def parse_worldmap_annotations(path: Path) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(
        r'addUntranslatedText\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)'
    )
    labels: list[dict[str, object]] = []
    for match in pattern.finditer(text):
        labels.append(
            {
                "name": _normalize_display_label(match.group(1)),
                "symbolType": match.group(2),
                "x": int(float(match.group(3))),
                "y": int(float(match.group(4))),
            }
        )
    return labels


def parse_lotheader_cells(map_folder: Path) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    pattern = re.compile(r"^(\d+)_(\d+)\.lotheader$", re.IGNORECASE)
    for child in map_folder.iterdir():
        if not child.is_file():
            continue
        match = pattern.match(child.name)
        if not match:
            continue
        cells.append((int(match.group(1)), int(match.group(2))))
    return cells


def parse_objects_lua(path: Path) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = _extract_top_level_lua_table_blocks(text, "objects")
    objects: list[dict[str, object]] = []
    for block in blocks:
        entry = {
            "name": _extract_lua_string(block, "name"),
            "type": _extract_lua_string(block, "type"),
            "geometry": _extract_lua_string(block, "geometry"),
            "x": _extract_lua_int(block, "x"),
            "y": _extract_lua_int(block, "y"),
            "z": _extract_lua_int(block, "z"),
            "width": _extract_lua_int(block, "width"),
            "height": _extract_lua_int(block, "height"),
            "points": _extract_lua_number_list(block, "points"),
            "properties": _extract_lua_properties(block),
        }
        if not entry["type"]:
            continue
        objects.append(entry)
    return objects


def parse_worldmap_features(path: Path) -> list[dict[str, object]]:
    root = ET.parse(path).getroot()
    features: list[dict[str, object]] = []
    for cell in root.findall("./cell"):
        cell_x = int(cell.attrib.get("x", "0"))
        cell_y = int(cell.attrib.get("y", "0"))
        for feature in cell.findall("./feature"):
            geometry = feature.find("./geometry")
            properties_node = feature.find("./properties")
            points: list[tuple[float, float]] = []
            if geometry is not None:
                coordinates = geometry.find("./coordinates")
                if coordinates is not None:
                    for point in coordinates.findall("./point"):
                        local_x = float(point.attrib.get("x", "0"))
                        local_y = float(point.attrib.get("y", "0"))
                        points.append((cell_x * 300 + local_x, cell_y * 300 + local_y))

            properties: dict[str, str] = {}
            if properties_node is not None:
                for prop in properties_node.findall("./property"):
                    name = prop.attrib.get("name", "").strip()
                    value = prop.attrib.get("value", "").strip()
                    if name:
                        properties[name] = value

            features.append(
                {
                    "cellX": cell_x,
                    "cellY": cell_y,
                    "geometryType": geometry.attrib.get("type", "") if geometry is not None else "",
                    "points": points,
                    "properties": properties,
                }
            )
    return features


def _normalize_display_label(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    letters = [char for char in text if char.isalpha()]
    if letters and all(char.isupper() for char in letters):
        return text.title()
    return text


def _extract_top_level_lua_table_blocks(text: str, table_name: str) -> list[str]:
    anchor = text.find(f"{table_name} =")
    if anchor < 0:
        return []

    start = text.find("{", anchor)
    if start < 0:
        return []

    blocks: list[str] = []
    depth = 0
    entry_start: int | None = None
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":
            depth += 1
            if depth == 2:
                entry_start = index
        elif char == "}":
            if depth == 2 and entry_start is not None:
                blocks.append(text[entry_start : index + 1])
                entry_start = None
            depth -= 1
            if depth <= 0:
                break

    return blocks


def _extract_lua_string(block: str, key: str) -> str:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*\"([^\"]*)\"", block)
    return match.group(1) if match else ""


def _extract_lua_int(block: str, key: str) -> int | None:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*(-?\d+)", block)
    return int(match.group(1)) if match else None


def _extract_lua_number_list(block: str, key: str) -> list[float]:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*\{{([^}}]*)\}}", block, flags=re.S)
    if not match:
        return []
    return [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", match.group(1))]


def _extract_lua_properties(block: str) -> dict[str, str]:
    match = re.search(r"\bproperties\s*=\s*\{(.*?)\}", block, flags=re.S)
    if not match:
        return {}
    payload = match.group(1)
    properties: dict[str, str] = {}
    for key, value in re.findall(r"([A-Za-z0-9_]+)\s*=\s*\"([^\"]*)\"", payload):
        properties[key] = value
    return properties
