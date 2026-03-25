from __future__ import annotations

from statistics import mean
from typing import Any, Dict, Iterable

from ..commons.vanilla_loader import get_translated_name
from ..tag.tagging import generate_tags
from .pricing import calculate_price_details


DEFAULT_AUDIT_BASKETS: dict[str, list[str]] = {
    "Medical": [
        "Bandage",
        "AlcoholBandage",
        "Disinfectant",
        "PillsBeta",
        "AntibioticsBox",
        "CigarettePack",
    ],
    "Food": [
        "CannedSardines",
        "TunaTin",
        "Pop",
        "Whiskey",
        "Macaroni",
        "PeanutButter",
    ],
    "Misc": [
        "WaterPurificationTablets",
        "Matches",
        "MagnesiumFirestarter",
        "BoxOfJars",
        "Soap2",
    ],
    "Tool": [
        "Hammer",
        "Crowbar",
        "Saw",
        "Axe",
    ],
    "Combat": [
        "Bullets9mmBox",
        "ShotgunShellsBox",
        "Pistol",
        "Shotgun",
        "Bag_BigHikingBag",
        "Generator",
    ],
}


def _quartile(sorted_values: list[int], ratio: float) -> int:
    if not sorted_values:
        return 0
    index = int((len(sorted_values) - 1) * ratio)
    return sorted_values[index]


def _compute_category_stats(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[int]] = {}
    for row in rows:
        buckets.setdefault(row["category"], []).append(int(row["price"]))

    stats: list[dict[str, Any]] = []
    for category, prices in sorted(buckets.items()):
        values = sorted(prices)
        stats.append(
            {
                "category": category,
                "count": len(values),
                "min": values[0],
                "q1": _quartile(values, 0.25),
                "median": _quartile(values, 0.5),
                "q3": _quartile(values, 0.75),
                "max": values[-1],
                "avg": round(mean(values), 2),
            }
        )
    return stats


def build_pricing_audit(
    items: Dict[str, str],
    baskets: dict[str, list[str]] | None = None,
    outlier_limit: int = 20,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item_id, props in items.items():
        tags = generate_tags(item_id, props)
        details = calculate_price_details(item_id, props, tags)
        rows.append(
            {
                "item_id": item_id,
                "name": get_translated_name(item_id, props),
                "price": int(details["price"]),
                "category": details["category"],
                "primary_tag": details["primary_tag"],
            }
        )

    basket_rows: dict[str, list[dict[str, Any]]] = {}
    for label, item_ids in (baskets or DEFAULT_AUDIT_BASKETS).items():
        basket_rows[label] = [row for row in rows if row["item_id"] in item_ids]
        basket_rows[label].sort(key=lambda row: item_ids.index(row["item_id"]))

    sorted_rows = sorted(rows, key=lambda row: row["price"], reverse=True)
    return {
        "summary": {
            "total_items": len(rows),
            "categories": len({row["category"] for row in rows}),
        },
        "category_stats": _compute_category_stats(rows),
        "anchors": basket_rows,
        "outliers": sorted_rows[: max(1, outlier_limit)],
    }
