from __future__ import annotations

from pathlib import Path
import re


def _normalize_rel_path(path_str: str) -> str:
    return str(path_str or "").replace("\\", "/").strip().lower().lstrip("/")


def _normalize_submod_id(mod_id: str) -> str:
    return str(mod_id or "").strip()


def _is_prefix(path_value: str, prefix: str) -> bool:
    if not path_value or not prefix:
        return False
    return path_value == prefix or path_value.startswith(prefix + "/")


def _is_variant_folder_name(name: str) -> bool:
    lowered = str(name or "").strip().lower()
    if lowered in {"common", "shared"}:
        return True
    return bool(re.match(r"^\d+(?:\.\d+)+$", lowered))


def get_repo_submod_prefixes(repo_path: Path) -> dict[str, list[str]]:
    """
    Build a dynamic route map: submod id -> list of repo-relative path prefixes.
    Prefixes are derived from discovered sub_mod paths in project metadata.
    """
    try:
        from ProjectManagement.projects import list_workshop_projects
    except Exception:
        return {}

    repo_resolved = Path(repo_path).resolve()
    prefixes_by_submod: dict[str, set[str]] = {}

    for project in list_workshop_projects():
        project_path = Path(project.get("path") or "")
        if not project_path.exists():
            continue
        if project_path.resolve() != repo_resolved:
            continue

        for sub_mod in project.get("sub_mods", []):
            submod_id = _normalize_submod_id(sub_mod.get("id") or "")
            sub_path_raw = sub_mod.get("path") or ""
            if not submod_id or not sub_path_raw:
                continue

            sub_path = Path(sub_path_raw)
            try:
                rel = sub_path.resolve().relative_to(repo_resolved)
            except Exception:
                continue

            rel_str = _normalize_rel_path(rel.as_posix())
            if not rel_str:
                continue

            bucket = prefixes_by_submod.setdefault(submod_id, set())
            bucket.add(rel_str)

            # If discovery points to a variant folder (e.g. common or 42.16),
            # include its parent sub-mod root as an additional stable prefix.
            if rel.parent != rel and _is_variant_folder_name(rel.name):
                parent_str = _normalize_rel_path(rel.parent.as_posix())
                if parent_str:
                    bucket.add(parent_str)

    return {
        submod_id: sorted(values, key=lambda p: len(p), reverse=True)
        for submod_id, values in prefixes_by_submod.items()
        if values
    }


def route_commit_paths(changed_files: list[str], submod_prefixes: dict[str, list[str]]) -> dict:
    """
    Route commit file paths to submods.
    Returns:
      {
        "primary_submod": str | None,
        "resolved_submods": list[str],
        "scores": dict[str, int],
        "unmatched_files": list[str],
      }
    """
    scores: dict[str, int] = {submod_id: 0 for submod_id in submod_prefixes.keys()}
    unmatched: list[str] = []

    for file_path in changed_files:
        normalized_file = _normalize_rel_path(file_path)
        if not normalized_file:
            continue

        matched = False
        for submod_id, prefixes in submod_prefixes.items():
            for prefix in prefixes:
                if _is_prefix(normalized_file, prefix):
                    scores[submod_id] += 1
                    matched = True
                    break
        if not matched:
            unmatched.append(file_path)

    resolved = [submod_id for submod_id, score in scores.items() if score > 0]
    resolved.sort(key=lambda submod_id: (-scores[submod_id], submod_id.lower()))

    primary_submod = resolved[0] if resolved else None
    return {
        "primary_submod": primary_submod,
        "resolved_submods": resolved,
        "scores": {k: v for k, v in scores.items() if v > 0},
        "unmatched_files": unmatched,
    }