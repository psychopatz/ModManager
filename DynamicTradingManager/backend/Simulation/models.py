from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ItemDef:
    item_id: str
    base_price: float
    tags: List[str]
    stock_min: int
    stock_max: int
    chance: Optional[float] = None
    source_file: str = ""


@dataclass
class Allocation:
    count: int
    item: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class ArchetypeDef:
    archetype_id: str
    name: str
    allocations: List[Allocation] = field(default_factory=list)
    expert_tags: List[str] = field(default_factory=list)
    wants: Dict[str, float] = field(default_factory=dict)
    forbid: List[str] = field(default_factory=list)


@dataclass
class EventEffect:
    price: Optional[float] = None
    vol: Optional[float] = None


@dataclass
class EventDef:
    event_id: str
    name: str
    event_type: str
    sentiment: str
    description: str
    effects: Dict[str, EventEffect] = field(default_factory=dict)
    inject: Dict[str, float] = field(default_factory=dict)
    stock_volume_mult: Optional[float] = None
    stock_injections: Dict[str, float] = field(default_factory=dict)
    stock_expert_tags: List[str] = field(default_factory=list)
    stock_forbid_tags: List[str] = field(default_factory=list)
    can_spawn_source: str = ""
    condition_source: str = ""
    condition_kind: str = "none"
    condition_value: str = ""


@dataclass
class TagDef:
    tag: str
    price_mult: float = 1.0
    weight: float = 50.0
