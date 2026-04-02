from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
from config.server_settings import get_server_settings

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DT_PATH_ENV = os.getenv("DYNAMIC_TRADING_PATH")
SCRIPT_DIR = Path(DT_PATH_ENV) if DT_PATH_ENV else get_server_settings().dynamic_trading_path


@dataclass(frozen=True)
class Paths:
    root: Path
    mod_common: Path
    output_root: Path
    output_web: Path
    output_data: Path


@dataclass(frozen=True)
class BuildConfig:
    seed: int = 1337
    stock_mult: float = 1.0
    rarity_bonus: float = 0.0
    buy_mult: float = 1.0
    sell_mult: float = 0.5
    event_frequency_days: int = 5
    event_chance_percent: int = 50
    max_flash_events: int = 3
    flash_duration_days: int = 3


def default_paths() -> Paths:
    project_root = SCRIPT_DIR
    mod_common = project_root / "Contents/mods/DynamicTradingCommon/42.13/media/lua/shared/DT/Common"
    output_root = project_root / "Scripts/SimulateGame/Output"
    output_web = output_root / "web"
    output_data = output_web / "assets/data"
    return Paths(
        root=project_root,
        mod_common=mod_common,
        output_root=output_root,
        output_web=output_web,
        output_data=output_data,
    )
