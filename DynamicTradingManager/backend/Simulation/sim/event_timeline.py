from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List

from ..config import BuildConfig
from ..models import EventDef


SEASONS = ("Spring", "Summer", "Autumn", "Winter")


@dataclass
class TimelineState:
    day: int = 0
    last_flash_day: int = -10
    active_flash: Dict[str, int] = field(default_factory=dict)


@dataclass
class ActiveEventSet:
    ids: List[str]
    season: str


def season_for_day(day: int) -> str:
    idx = (day // 90) % 4
    return SEASONS[idx]


def can_spawn_event(event_def: EventDef, allow_hardcore: bool = True) -> bool:
    if not event_def.can_spawn_source:
        return True
    src = event_def.can_spawn_source
    if "AllowHardcoreEvents" in src and not allow_hardcore:
        return False
    return True


def is_condition_true(event_def: EventDef, day: int, season_name: str) -> bool:
    if event_def.condition_kind == "none":
        return True
    if event_def.condition_kind == "season":
        return season_name == event_def.condition_value
    if event_def.condition_kind == "nights_gt":
        return day > int(event_def.condition_value)
    if event_def.condition_kind == "days_gt":
        return day > int(event_def.condition_value)
    return False


def compute_active_events(
    events: Dict[str, EventDef],
    config: BuildConfig,
    state: TimelineState,
    rng: random.Random,
    allow_hardcore: bool = True,
) -> ActiveEventSet:
    season_name = season_for_day(state.day)

    # Remove expired flash events.
    expired = [event_id for event_id, expires in state.active_flash.items() if state.day >= expires]
    for event_id in expired:
        state.active_flash.pop(event_id, None)

    # Maintain always-on meta and seasonal events.
    active_ids = set(state.active_flash.keys())
    flash_candidates: list[str] = []

    for event_id, event_def in events.items():
        if event_def.event_type in ("meta", "seasonal"):
            if is_condition_true(event_def, state.day, season_name):
                active_ids.add(event_id)
        elif event_def.event_type == "flash":
            if can_spawn_event(event_def, allow_hardcore=allow_hardcore):
                flash_candidates.append(event_id)

    # Simplified parity for flash lottery.
    active_flash_count = len(state.active_flash)
    if (
        active_flash_count < config.max_flash_events
        and (state.day - state.last_flash_day) >= config.event_frequency_days
        and flash_candidates
    ):
        roll = rng.randint(1, 100)
        if roll <= config.event_chance_percent:
            pick = rng.choice(flash_candidates)
            state.active_flash[pick] = state.day + config.flash_duration_days
            active_ids.add(pick)
            state.last_flash_day = state.day
        else:
            state.last_flash_day = state.day - (config.event_frequency_days - 1)

    return ActiveEventSet(ids=sorted(active_ids), season=season_name)
