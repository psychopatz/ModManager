from __future__ import annotations

from typing import Iterable, Sequence


def _tag_candidates(item_tag: str) -> list[str]:
    if not item_tag:
        return []

    out: list[str] = []
    seen: set[str] = set()

    probe = item_tag
    while probe:
        if probe not in seen:
            out.append(probe)
            seen.add(probe)
        if "." not in probe:
            break
        probe = probe.rsplit(".", 1)[0]

    parts = [part for part in item_tag.split(".") if part]
    for part in reversed(parts):
        if part not in seen:
            out.append(part)
            seen.add(part)

    return out


def tag_matches(item_tag: str, query_tag: str) -> bool:
    if not item_tag or not query_tag:
        return False
    if item_tag == query_tag or item_tag.startswith(query_tag + "."):
        return True
    return query_tag in _tag_candidates(item_tag)


def matches_all_tags(item_tags: Sequence[str], required_tags: Sequence[str]) -> bool:
    if not required_tags:
        return False
    for req in required_tags:
        matched = False
        for item_tag in item_tags:
            if tag_matches(item_tag, req):
                matched = True
                break
        if not matched:
            return False
    return True


def has_forbidden_tag(item_tags: Sequence[str], forbidden_tags: Iterable[str]) -> bool:
    for forbid in forbidden_tags:
        for tag in item_tags:
            if tag_matches(tag, forbid):
                return True
    return False


def tag_price_mult(item_tags: Sequence[str], tag_price_map: dict[str, float]) -> float:
    max_mult = 1.0
    for tag in item_tags:
        for candidate in _tag_candidates(tag):
            mult = tag_price_map.get(candidate)
            if mult is not None and mult > max_mult:
                max_mult = mult
    return max_mult


def find_first_want_bonus(item_tags: Sequence[str], wants: dict[str, float]) -> float:
    for item_tag in item_tags:
        for want_tag, bonus in wants.items():
            if tag_matches(item_tag, want_tag):
                return float(bonus)
    return 1.0
