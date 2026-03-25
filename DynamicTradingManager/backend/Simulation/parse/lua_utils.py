from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List


QUOTED_STR_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def find_lua_files(root: Path) -> List[Path]:
    return sorted([p for p in root.rglob("*.lua") if p.is_file()])


def parse_quoted_list(table_expr: str) -> List[str]:
    out: List[str] = []
    for match in QUOTED_STR_RE.finditer(table_expr):
        out.append(match.group(1) or match.group(2) or "")
    return [s.strip() for s in out if s.strip()]


def parse_lua_map_numbers(table_expr: str) -> dict[str, float]:
    pairs = re.findall(r'\[\s*["\']([^"\']+)["\']\s*\]\s*=\s*([-]?\d+(?:\.\d+)?)', table_expr)
    return {k: float(v) for k, v in pairs}


def extract_balanced_block(text: str, open_idx: int) -> str:
    if open_idx < 0 or open_idx >= len(text) or text[open_idx] != "{":
        return ""

    depth = 0
    in_string = False
    string_char = ""
    escape = False

    for i in range(open_idx, len(text)):
        ch = text[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == string_char:
                in_string = False
            continue

        if ch in ('"', "'"):
            in_string = True
            string_char = ch
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx : i + 1]

    return ""


def table_field_block(table_text: str, field_name: str) -> str:
    m = re.search(rf"{re.escape(field_name)}\s*=\s*\{{", table_text)
    if not m:
        return ""
    open_idx = m.end() - 1
    return extract_balanced_block(table_text, open_idx)


def normalize_path(path: Path, roots: Iterable[Path]) -> str:
    for root in roots:
        try:
            return str(path.relative_to(root)).replace("\\", "/")
        except ValueError:
            continue
    return str(path).replace("\\", "/")
