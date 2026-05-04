from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = BACKEND_ROOT / ".env"
load_dotenv(dotenv_path=DOTENV_PATH)


def _read_settings_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _first_non_empty(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser().resolve()


@dataclass(frozen=True)
class ServerSettings:
    backend_root: Path
    settings_file: Path
    dynamic_trading_path: Path
    market_sense_path: Path
    dynamic_colonies_path: Path
    dynamic_currency_path: Path
    console_path: Path
    dt_items_dir: Path
    runtime_rules_file: Path
    steamcmd_path: str | None
    allowed_origins: list[str]


@lru_cache(maxsize=1)
def get_server_settings() -> ServerSettings:
    settings_path_raw = os.getenv("DT_SERVER_SETTINGS_FILE")
    settings_file = (
        Path(settings_path_raw).expanduser().resolve()
        if settings_path_raw
        else (BACKEND_ROOT / "server_settings.json").resolve()
    )

    file_settings = _read_settings_file(settings_file)

    dt_raw = _first_non_empty(
        os.getenv("DYNAMIC_TRADING_PATH"),
        file_settings.get("dynamic_trading_path"),
    )
    dynamic_trading_path = _resolve_path(dt_raw)
    if dynamic_trading_path is None:
        raise RuntimeError(
            "Dynamic Trading path is not configured. Set DYNAMIC_TRADING_PATH or add dynamic_trading_path to server settings."
        )

    dynamic_colonies_path = _resolve_path(
        _first_non_empty(
            os.getenv("DYNAMIC_COLONIES_PATH"),
            file_settings.get("dynamic_colonies_path"),
            str(dynamic_trading_path.parent / "DynamicColonies"),
        )
    )
    market_sense_path = _resolve_path(
        _first_non_empty(
            os.getenv("MARKET_SENSE_PATH"),
            file_settings.get("market_sense_path"),
            str(dynamic_trading_path.parent / "MarketSense"),
        )
    )
    if market_sense_path is None:
        raise RuntimeError(
            "Market Sense path is not configured. Set MARKET_SENSE_PATH or add market_sense_path to server settings."
        )
    dynamic_currency_path = _resolve_path(
        _first_non_empty(
            os.getenv("DYNAMIC_CURRENCY_PATH"),
            file_settings.get("dynamic_currency_path"),
            str(dynamic_trading_path.parent / "CurrencyExpanded"),
        )
    )

    console_path = _resolve_path(
        _first_non_empty(
            os.getenv("CONSOLE_PATH"),
            file_settings.get("console_path"),
            str(dynamic_trading_path.parent / "console.txt"),
        )
    )
    if console_path is None:
        raise RuntimeError("Console path could not be resolved from settings.")

    dt_items_dir = _resolve_path(
        _first_non_empty(
            os.getenv("DT_ITEMS_DIR"),
            os.getenv("DT_RUNTIME_DUMP_FILE"),
            file_settings.get("dt_items_dir"),
            file_settings.get("runtime_dump_file"),
            str(Path.home() / "Zomboid" / "Lua" / "DT_Items"),
        )
    )
    if dt_items_dir is None:
        raise RuntimeError("DT_Items directory path could not be resolved from settings.")

    runtime_rules_file = _resolve_path(
        _first_non_empty(
            os.getenv("DT_RUNTIME_RULES_FILE"),
            file_settings.get("runtime_rules_file"),
            str(
                market_sense_path
                / "Contents"
                / "mods"
                / "MarketSense"
                / "common"
                / "media"
                / "lua"
                / "shared"
                / "DT"
                / "MarketSense"
                / "Items"
                / "MS_RuntimeRules_Data.lua"
            ),
        )
    )
    if runtime_rules_file is None:
        raise RuntimeError("Runtime rules file path could not be resolved from settings.")

    steamcmd_path = _first_non_empty(
        os.getenv("STEAM_CMD_PATH"),
        os.getenv("STEAMCMD_PATH"),
        file_settings.get("steamcmd_path"),
        file_settings.get("steam_cmd_path"),
    )

    allowed_origins_raw = _first_non_empty(
        os.getenv("ALLOWED_ORIGINS"),
        file_settings.get("allowed_origins"),
    )
    allowed_origins = [o.strip() for o in allowed_origins_raw.split(",")] if allowed_origins_raw else []

    return ServerSettings(
        backend_root=BACKEND_ROOT,
        settings_file=settings_file,
        dynamic_trading_path=dynamic_trading_path,
        market_sense_path=market_sense_path,
        dynamic_colonies_path=dynamic_colonies_path,
        dynamic_currency_path=dynamic_currency_path,
        console_path=console_path,
        dt_items_dir=dt_items_dir,
        runtime_rules_file=runtime_rules_file,
        steamcmd_path=steamcmd_path,
        allowed_origins=allowed_origins,
    )


def reload_server_settings() -> ServerSettings:
    get_server_settings.cache_clear()
    return get_server_settings()
