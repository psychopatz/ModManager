from __future__ import annotations

import math


CELL_SIZE = 300
DEFAULT_PADDING = CELL_SIZE


def build_map_bounds(
    lotheader_cells: list[tuple[int, int]],
    spawn_points: list[dict[str, int]],
    labels: list[dict[str, object]],
) -> tuple[dict[str, int], list[str]]:
    warnings: list[str] = []
    raw_bounds = _bounds_from_cells(lotheader_cells)
    feature_bounds = _bounds_from_points(
        [(point["x"], point["y"]) for point in spawn_points]
        + [(int(label["x"]), int(label["y"])) for label in labels]
    )

    if raw_bounds is None and feature_bounds is None:
        raise ValueError("No lotheader cells, spawn points, or map labels were found to compute bounds.")

    if raw_bounds is None:
        warnings.append("No .lotheader files were found; bounds were derived from spawn points and map labels only.")
        combined = feature_bounds
    elif feature_bounds is None:
        warnings.append("No spawn points or map labels were found; bounds were derived from .lotheader coverage only.")
        combined = raw_bounds
    else:
        combined = {
            "minX": min(raw_bounds["minX"], feature_bounds["minX"]),
            "maxX": max(raw_bounds["maxX"], feature_bounds["maxX"]),
            "minY": min(raw_bounds["minY"], feature_bounds["minY"]),
            "maxY": max(raw_bounds["maxY"], feature_bounds["maxY"]),
        }

    if combined is None:
        raise ValueError("Unable to compute map bounds.")

    return _expand_and_align_bounds(combined), warnings


def _bounds_from_cells(cells: list[tuple[int, int]]) -> dict[str, int] | None:
    if not cells:
        return None
    min_cell_x = min(cell_x for cell_x, _ in cells)
    max_cell_x = max(cell_x for cell_x, _ in cells)
    min_cell_y = min(cell_y for _, cell_y in cells)
    max_cell_y = max(cell_y for _, cell_y in cells)
    return {
        "minX": min_cell_x * CELL_SIZE,
        "maxX": (max_cell_x + 1) * CELL_SIZE,
        "minY": min_cell_y * CELL_SIZE,
        "maxY": (max_cell_y + 1) * CELL_SIZE,
    }


def _bounds_from_points(points: list[tuple[int, int]]) -> dict[str, int] | None:
    if not points:
        return None
    return {
        "minX": min(x for x, _ in points),
        "maxX": max(x for x, _ in points),
        "minY": min(y for _, y in points),
        "maxY": max(y for _, y in points),
    }


def _expand_and_align_bounds(bounds: dict[str, int], padding: int = DEFAULT_PADDING) -> dict[str, int]:
    min_x = _align_down(bounds["minX"] - padding)
    max_x = _align_up(bounds["maxX"] + padding)
    min_y = _align_down(bounds["minY"] - padding)
    max_y = _align_up(bounds["maxY"] + padding)
    return {
        "minX": min_x,
        "maxX": max_x,
        "minY": min_y,
        "maxY": max_y,
    }


def _align_down(value: int) -> int:
    return int(math.floor(value / CELL_SIZE) * CELL_SIZE)


def _align_up(value: int) -> int:
    return int(math.ceil(value / CELL_SIZE) * CELL_SIZE)
