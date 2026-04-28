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


def default_paths(mod_id: str = "DynamicTradingCommon") -> Paths:
    from config.paths import get_mod_root, get_archetypes_root
    
    # Resolve roots dynamically
    mod_root = get_mod_root(mod_id)
    project_root = mod_root.parent.parent.parent if mod_root.parts else Path()
    
    # Resolve mod_common: we need the directory that CONTAINS 'ArchetypeDefinitions' and 'Items'
    # get_archetypes_root returns the ArchetypeDefinitions dir itself, so we need its parent
    archetypes_dir = get_archetypes_root(mod_id)
    if archetypes_dir and archetypes_dir.exists():
        mod_common = archetypes_dir.parent
    else:
        from config.paths import get_items_root
        items_dir = get_items_root(mod_id)
        if items_dir and items_dir.exists():
            mod_common = items_dir.parent
        else:
            # Final fallback
            mod_common = mod_root / "common" / "media" / "lua" / "shared" / "DT" / "Common"
    
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
RiversidePaths = {
    "DynamicTradingCommon": "media/lua/shared/DT/Common",
    "DynamicTradingV1": "media/lua/shared/DT/V1",
    "DynamicTradingV2": "media/lua/shared/DT/V2",
    "DynamicColonies": "media/lua/shared/DC/Common",
    "CurrencyExpanded": "media/lua/shared/CE/Common",
}
