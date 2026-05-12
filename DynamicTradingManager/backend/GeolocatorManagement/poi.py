from __future__ import annotations

import asyncio
import json
import logging
import math
import re
from collections import Counter, defaultdict
from typing import Any

from LLMManagement.client import chat_completion

logger = logging.getLogger(__name__)

OBJECT_TYPE_BLACKLIST = {
    "ParkingStall",
    "SpawnPoint",
    "Nav",
    "TownZone",
    "Vegitation",
    "Forest",
    "DeepForest",
    "Animal",
}

OBJECT_NAME_BLACKLIST = {
    "",
    "good",
    "bad",
    "medium",
    "trafficjams",
    "trafficjamn",
    "trafficjame",
    "trafficjamw",
    "rtrafficjams",
    "forest",
}

ROOM_TONE_LABELS = {
    "bank": "Bank Plaza",
    "church": "Church Grounds",
    "firestation": "Fire Services",
    "garage": "Auto Garage",
    "gas": "Gas Station",
    "grocery": "Grocery Center",
    "medical": "Medical Complex",
    "pharmacy": "Pharmacy",
    "police": "Police Compound",
}

CATEGORY_LABELS = {
    "residential": "Residential Block",
    "retail": "Retail Strip",
    "restaurant": "Restaurant Row",
    "medical": "Medical Complex",
    "industrial": "Industrial Yard",
    "hospitality": "Hotel Complex",
    "civic": "Civic Center",
    "mixed": "Mixed Urban Block",
    "building": "Building Cluster",
}

CATEGORY_TYPE_LABELS = {
    "residential": "Residential",
    "retail": "Retail",
    "restaurant": "Restaurant",
    "medical": "Medical",
    "industrial": "Industrial",
    "hospitality": "Hospitality",
    "civic": "CommunityServices",
    "mixed": "MixedUse",
    "building": "Building",
}


def build_map_pois(
    *,
    map_name: str,
    town_name: str,
    county_name: str,
    annotations: list[dict[str, object]],
    object_entries: list[dict[str, object]],
    world_features: list[dict[str, object]],
    llm_config: dict[str, object] | None = None,
) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]], list[str]]:
    warnings: list[str] = []
    buckets: dict[str, list[dict[str, object]]] = {
        "annotation": [],
        "objects": [],
        "generic": [],
    }
    merged: list[dict[str, object]] = []

    for poi in _build_annotation_pois(town_name, county_name, annotations):
        if _append_if_unique(merged, poi):
            buckets["annotation"].append(poi)

    for poi in _build_object_pois(town_name, county_name, object_entries):
        if _append_if_unique(merged, poi):
            buckets["objects"].append(poi)

    generic_clusters = _cluster_generic_features(world_features)
    generic_pois = _build_generic_cluster_pois(
        map_name=map_name,
        town_name=town_name,
        county_name=county_name,
        clusters=generic_clusters,
        higher_priority_pois=merged,
        llm_config=llm_config,
    )
    for poi in generic_pois:
        if _append_if_unique(merged, poi):
            buckets["generic"].append(poi)

    if not buckets["annotation"]:
        warnings.append(f"{map_name}: no worldmap annotation POIs were found.")
    if not buckets["objects"]:
        warnings.append(f"{map_name}: no named object-derived POIs were found.")
    if not buckets["generic"]:
        warnings.append(f"{map_name}: no generic clustered POIs were generated from worldmap.xml.")

    return merged, buckets, warnings


def _build_annotation_pois(
    town_name: str,
    county_name: str,
    annotations: list[dict[str, object]],
) -> list[dict[str, object]]:
    pois: list[dict[str, object]] = []
    seen: set[tuple[str, int, int]] = set()
    for label in annotations:
        name = str(label.get("name", "")).strip()
        x = int(label.get("x", 0))
        y = int(label.get("y", 0))
        if not name:
            continue
        key = (_normalize_key(name), x, y)
        if key in seen:
            continue
        seen.add(key)
        pois.append(
            {
                "id": _normalize_key(name),
                "name": name,
                "type": "Label",
                "x": x,
                "y": y,
                "town": town_name,
                "county": county_name,
                "metadata": {
                    "source": "worldmap-annotations",
                    "symbolType": label.get("symbolType"),
                    "label_method": "annotation",
                },
            }
        )
    return pois


def _build_object_pois(
    town_name: str,
    county_name: str,
    object_entries: list[dict[str, object]],
) -> list[dict[str, object]]:
    pois: list[dict[str, object]] = []
    seen: set[tuple[str, int, int]] = set()
    for entry in object_entries:
        object_type = str(entry.get("type", "") or "").strip()
        raw_name = str(entry.get("name", "") or "").strip()
        if object_type in OBJECT_TYPE_BLACKLIST:
            continue
        if _normalize_key(raw_name) in OBJECT_NAME_BLACKLIST:
            continue
        center = _entry_center(entry)
        if center is None:
            continue
        label = _humanize_identifier(raw_name)
        key = (_normalize_key(label), int(center["x"] // 15), int(center["y"] // 15))
        if key in seen:
            continue
        seen.add(key)
        pois.append(
            {
                "id": _normalize_key(f"{object_type}_{label}_{int(center['x'])}_{int(center['y'])}"),
                "name": label,
                "type": "Landmark",
                "x": int(center["x"]),
                "y": int(center["y"]),
                "town": town_name,
                "county": county_name,
                "metadata": {
                    "source": "objects-lua",
                    "objectType": object_type,
                    "originalName": raw_name,
                    "label_method": "object-name",
                },
            }
        )
    return pois


def _cluster_generic_features(world_features: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for feature in world_features:
        summary = _summarize_world_feature(feature)
        if summary is None:
            continue
        grouped[summary["bucket"]].append(summary)

    clusters: list[dict[str, object]] = []
    for bucket, features in grouped.items():
        clusters.extend(_cluster_bucket_features(bucket, features))
    return clusters


def _build_generic_cluster_pois(
    *,
    map_name: str,
    town_name: str,
    county_name: str,
    clusters: list[dict[str, object]],
    higher_priority_pois: list[dict[str, object]],
    llm_config: dict[str, object] | None,
) -> list[dict[str, object]]:
    eligible_clusters = [cluster for cluster in clusters if _cluster_should_emit(cluster)]
    llm_labels = _label_generic_clusters(map_name, eligible_clusters, higher_priority_pois, llm_config)

    pois: list[dict[str, object]] = []
    for index, cluster in enumerate(eligible_clusters, start=1):
        if _cluster_conflicts_with_named_poi(cluster, higher_priority_pois):
            continue
        label = llm_labels.get(cluster["id"]) or _deterministic_cluster_label(cluster)
        label_method = "llm" if cluster["id"] in llm_labels else "deterministic"
        pois.append(
            {
                "id": _normalize_key(f"{cluster['bucket']}_{index}_{cluster['centerX']}_{cluster['centerY']}"),
                "name": label,
                "type": CATEGORY_TYPE_LABELS.get(cluster["bucket"], "Building"),
                "x": int(cluster["centerX"]),
                "y": int(cluster["centerY"]),
                "town": town_name,
                "county": county_name,
                "metadata": {
                    "source": "worldmap-xml-cluster",
                    "bucket": cluster["bucket"],
                    "featureCount": cluster["featureCount"],
                    "area": int(cluster["area"]),
                    "clusterSize": _cluster_size_bucket(cluster),
                    "label_method": label_method,
                    "dominantBuilding": cluster["dominantBuilding"],
                    "dominantRoomTone": cluster["dominantRoomTone"],
                },
            }
        )
    return pois


def _summarize_world_feature(feature: dict[str, object]) -> dict[str, object] | None:
    points = feature.get("points") or []
    if not isinstance(points, list) or len(points) < 3:
        return None

    properties = feature.get("properties") or {}
    building_value = str(properties.get("building", "") or "").strip()
    room_tone = str(properties.get("RoomTone", "") or "").strip()
    if not building_value and not room_tone:
        return None

    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    area = max(1.0, (max_x - min_x) * (max_y - min_y))
    bucket = _building_bucket(building_value, room_tone)

    return {
        "bucket": bucket,
        "building": building_value,
        "roomTone": room_tone,
        "minX": min_x,
        "maxX": max_x,
        "minY": min_y,
        "maxY": max_y,
        "centerX": (min_x + max_x) / 2.0,
        "centerY": (min_y + max_y) / 2.0,
        "area": area,
    }


def _cluster_bucket_features(bucket: str, features: list[dict[str, object]]) -> list[dict[str, object]]:
    if not features:
        return []
    margin = 22.0 if bucket == "residential" else 28.0
    parent = list(range(len(features)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for left in range(len(features)):
        for right in range(left + 1, len(features)):
            if _bbox_distance(features[left], features[right]) <= margin:
                union(left, right)

    grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
    for index, feature in enumerate(features):
        grouped[find(index)].append(feature)

    clusters: list[dict[str, object]] = []
    for index, group in grouped.items():
        min_x = min(item["minX"] for item in group)
        max_x = max(item["maxX"] for item in group)
        min_y = min(item["minY"] for item in group)
        max_y = max(item["maxY"] for item in group)
        building_counts = Counter(str(item.get("building", "") or "") for item in group if item.get("building"))
        room_tone_counts = Counter(str(item.get("roomTone", "") or "") for item in group if item.get("roomTone"))
        clusters.append(
            {
                "id": f"{bucket}_{index}",
                "bucket": bucket,
                "minX": min_x,
                "maxX": max_x,
                "minY": min_y,
                "maxY": max_y,
                "centerX": (min_x + max_x) / 2.0,
                "centerY": (min_y + max_y) / 2.0,
                "area": max(1.0, (max_x - min_x) * (max_y - min_y)),
                "featureCount": len(group),
                "buildingCounts": dict(building_counts),
                "roomToneCounts": dict(room_tone_counts),
                "dominantBuilding": building_counts.most_common(1)[0][0] if building_counts else "",
                "dominantRoomTone": room_tone_counts.most_common(1)[0][0] if room_tone_counts else "",
            }
        )
    return clusters


def _cluster_should_emit(cluster: dict[str, object]) -> bool:
    bucket = str(cluster.get("bucket", ""))
    count = int(cluster.get("featureCount", 0))
    area = float(cluster.get("area", 0))
    if bucket == "residential":
        return count >= 3 or area >= 2200
    if bucket in {"mixed", "building"}:
        return count >= 2 or area >= 1800
    return count >= 1


def _cluster_conflicts_with_named_poi(cluster: dict[str, object], higher_priority_pois: list[dict[str, object]]) -> bool:
    expanded_min_x = float(cluster["minX"]) - 40.0
    expanded_max_x = float(cluster["maxX"]) + 40.0
    expanded_min_y = float(cluster["minY"]) - 40.0
    expanded_max_y = float(cluster["maxY"]) + 40.0
    for poi in higher_priority_pois:
        x = float(poi.get("x", 0))
        y = float(poi.get("y", 0))
        if expanded_min_x <= x <= expanded_max_x and expanded_min_y <= y <= expanded_max_y:
            return True
    return False


def _label_generic_clusters(
    map_name: str,
    clusters: list[dict[str, object]],
    higher_priority_pois: list[dict[str, object]],
    llm_config: dict[str, object] | None,
) -> dict[str, str]:
    usable_config = _normalize_llm_config(llm_config)
    if not usable_config or not clusters:
        return {}

    grouped_batches: list[list[dict[str, object]]] = []
    batch_size = 20
    for index in range(0, len(clusters), batch_size):
        grouped_batches.append(clusters[index : index + batch_size])

    output: dict[str, str] = {}
    for batch in grouped_batches:
        try:
            output.update(asyncio.run(_label_generic_clusters_batch(map_name, batch, higher_priority_pois, usable_config)))
        except Exception as exc:
            logger.warning("Generic POI LLM labeling failed for %s: %s", map_name, exc)
    return output


async def _label_generic_clusters_batch(
    map_name: str,
    clusters: list[dict[str, object]],
    higher_priority_pois: list[dict[str, object]],
    llm_config: dict[str, object],
) -> dict[str, str]:
    nearby_named = [
        {
            "name": poi.get("name"),
            "x": poi.get("x"),
            "y": poi.get("y"),
        }
        for poi in higher_priority_pois[:30]
    ]
    cluster_payload = []
    for cluster in clusters:
        cluster_payload.append(
            {
                "id": cluster["id"],
                "bucket": cluster["bucket"],
                "feature_count": cluster["featureCount"],
                "bbox": [int(cluster["minX"]), int(cluster["minY"]), int(cluster["maxX"]), int(cluster["maxY"])],
                "center": [int(cluster["centerX"]), int(cluster["centerY"])],
                "dominant_building": cluster["dominantBuilding"],
                "dominant_room_tone": cluster["dominantRoomTone"],
                "building_mix": cluster["buildingCounts"],
                "room_tone_mix": cluster["roomToneCounts"],
            }
        )

    messages = [
        {
            "role": "system",
            "content": (
                "You label Project Zomboid map landmark clusters. "
                "Return only a JSON object mapping each cluster id to a short plain English label of 2 to 4 words. "
                "Do not include markdown, explanations, punctuation-heavy names, or coordinates."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "map_name": map_name,
                    "nearby_named_pois": nearby_named,
                    "clusters": cluster_payload,
                },
                ensure_ascii=False,
            ),
        },
    ]
    result = await chat_completion(
        base_url=str(llm_config["base_url"]),
        api_key=str(llm_config.get("api_key", "")),
        model=str(llm_config["model"]),
        messages=messages,
        thinking=bool(llm_config.get("thinking", False)),
        max_tokens=int(llm_config.get("max_tokens", 500)),
        stream=False,
        reasoning_effort=str(llm_config.get("reasoning_effort", "medium")),
    )
    return _parse_llm_label_map(result.content)


def _parse_llm_label_map(text: str) -> dict[str, str]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    json_match = re.search(r"\{.*\}", raw, flags=re.S)
    payload = json_match.group(0) if json_match else raw
    try:
        data = json.loads(payload)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}

    output: dict[str, str] = {}
    for key, value in data.items():
        label = str(value or "").strip()
        if not label:
            continue
        output[str(key)] = _sanitize_llm_label(label)
    return output


def _sanitize_llm_label(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip().strip('"')
    text = text.replace("_", " ")
    words = text.split()
    if len(words) > 5:
        words = words[:5]
    return " ".join(word[:1].upper() + word[1:] if word else word for word in words)


def _normalize_llm_config(llm_config: dict[str, object] | None) -> dict[str, object] | None:
    if not isinstance(llm_config, dict):
        return None
    if llm_config.get("is_browser_only"):
        return None
    base_url = str(llm_config.get("base_url", "") or "").strip()
    model = str(llm_config.get("model", "") or "").strip()
    if not base_url or not model:
        return None
    return {
        "base_url": base_url,
        "api_key": str(llm_config.get("api_key", "") or ""),
        "model": model,
        "thinking": bool(llm_config.get("thinking", False)),
        "reasoning_effort": str(llm_config.get("reasoning_effort", "medium") or "medium"),
        "max_tokens": int(llm_config.get("max_tokens", 500) or 500),
    }


def _deterministic_cluster_label(cluster: dict[str, object]) -> str:
    dominant_room_tone = str(cluster.get("dominantRoomTone", "") or "").strip().lower()
    if dominant_room_tone in ROOM_TONE_LABELS:
        return ROOM_TONE_LABELS[dominant_room_tone]

    bucket = str(cluster.get("bucket", "building"))
    return CATEGORY_LABELS.get(bucket, "Building Cluster")


def _cluster_size_bucket(cluster: dict[str, object]) -> str:
    area = float(cluster.get("area", 0))
    count = int(cluster.get("featureCount", 0))
    if count >= 12 or area >= 12000:
        return "large"
    if count >= 5 or area >= 4000:
        return "medium"
    return "small"


def _building_bucket(building_value: str, room_tone: str) -> str:
    building_key = str(building_value or "").strip().lower()
    room_tone_key = str(room_tone or "").strip().lower()

    if room_tone_key in {"bank", "church", "firestation", "garage", "gas", "grocery", "pharmacist", "police", "post", "policestation"}:
        return "civic" if room_tone_key in {"church", "firestation", "police", "policestation", "post"} else "retail"

    mapping = {
        "residential": "residential",
        "retailandcommercial": "retail",
        "restaurantsandentertainment": "restaurant",
        "medical": "medical",
        "industrial": "industrial",
        "hospitality": "hospitality",
        "communityservices": "civic",
        "yes": "building",
        "no": "building",
    }
    normalized = re.sub(r"[^a-z]+", "", building_key)
    return mapping.get(normalized, "mixed" if normalized else "building")


def _append_if_unique(existing: list[dict[str, object]], candidate: dict[str, object]) -> bool:
    candidate_key = _normalize_key(candidate.get("name", ""))
    candidate_x = float(candidate.get("x", 0))
    candidate_y = float(candidate.get("y", 0))
    for poi in existing:
        other_key = _normalize_key(poi.get("name", ""))
        if candidate_key != other_key:
            continue
        distance = math.dist((candidate_x, candidate_y), (float(poi.get("x", 0)), float(poi.get("y", 0))))
        if distance <= 40:
            return False
    existing.append(candidate)
    return True


def _entry_center(entry: dict[str, object]) -> dict[str, float] | None:
    x = entry.get("x")
    y = entry.get("y")
    width = entry.get("width")
    height = entry.get("height")
    points = entry.get("points") or []

    if isinstance(x, int) and isinstance(y, int) and isinstance(width, int) and isinstance(height, int):
        return {
            "x": x + (width / 2.0),
            "y": y + (height / 2.0),
        }
    if isinstance(points, list) and len(points) >= 4:
        xs = [float(points[index]) for index in range(0, len(points), 2)]
        ys = [float(points[index]) for index in range(1, len(points), 2)]
        return {
            "x": sum(xs) / len(xs),
            "y": sum(ys) / len(ys),
        }
    if isinstance(x, int) and isinstance(y, int):
        return {"x": float(x), "y": float(y)}
    return None


def _humanize_identifier(value: str) -> str:
    text = str(value or "").strip().replace("_", " ")
    if not text:
        return text
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    text = re.sub(r"(\d)([A-Za-z])", r"\1 \2", text)
    text = re.sub(r"([A-Za-z])(\d)", r"\1 \2", text)
    text = re.sub(r"\s+", " ", text).strip()
    return " ".join(word[:1].upper() + word[1:] if word else word for word in text.split())


def _normalize_key(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _bbox_distance(left: dict[str, object], right: dict[str, object]) -> float:
    dx = max(float(left["minX"]) - float(right["maxX"]), float(right["minX"]) - float(left["maxX"]), 0.0)
    dy = max(float(left["minY"]) - float(right["maxY"]), float(right["minY"]) - float(left["maxY"]), 0.0)
    return math.hypot(dx, dy)
