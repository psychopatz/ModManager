from __future__ import annotations

import re
from pathlib import Path


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
    pattern = re.compile(
        r"worldX\s*=\s*(-?\d+)\s*,\s*worldY\s*=\s*(-?\d+)\s*,\s*posX\s*=\s*(-?\d+)\s*,\s*posY\s*=\s*(-?\d+)(?:\s*,\s*posZ\s*=\s*(-?\d+))?"
    )
    points: list[dict[str, int]] = []
    for match in pattern.finditer(text):
        world_x = int(match.group(1))
        world_y = int(match.group(2))
        pos_x = int(match.group(3))
        pos_y = int(match.group(4))
        pos_z = int(match.group(5) or 0)
        points.append(
            {
                "worldX": world_x,
                "worldY": world_y,
                "posX": pos_x,
                "posY": pos_y,
                "posZ": pos_z,
                "x": world_x * 300 + pos_x,
                "y": world_y * 300 + pos_y,
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


def _normalize_display_label(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    letters = [char for char in text if char.isalpha()]
    if letters and all(char.isupper() for char in letters):
        return text.title()
    return text
