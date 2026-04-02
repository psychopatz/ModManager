from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class StatsResponse(BaseModel):
    total_vanilla: int
    registered: int
    unregistered: int
    coverage: float
    notifications: List[str]


class AddRequest(BaseModel):
    batch_size: Union[int, str] = 50


class FindPropertyRequest(BaseModel):
    property_name: str
    value_filter: Optional[str] = None
    chunk_limit: Optional[int] = 20


class ListPropertiesRequest(BaseModel):
    min_usage: int = 1
    chunk_limit: Optional[int] = 20


class PricingConfigRequest(BaseModel):
    config: Dict[str, Any]


class PricingPreviewRequest(BaseModel):
    item_id: str
    props: Optional[str] = None
    tags: Optional[List[str]] = None


class PricingTagPreviewRequest(BaseModel):
    tag: str
    addition: float = 0.0
    limit: int = 40


class BlacklistItemRequest(BaseModel):
    item_id: str


class ItemOverrideRequest(BaseModel):
    item_id: str
    base_price: Optional[float] = None
    tags: Optional[List[str]] = None
    stock_min: Optional[int] = None
    stock_max: Optional[int] = None
    description: Optional[str] = None


class ArchetypeAllocationEntryRequest(BaseModel):
    kind: str
    count: int
    tags: Optional[List[str]] = None
    item_id: Optional[str] = None


class ArchetypeWantEntryRequest(BaseModel):
    tag: str
    multiplier: float


class ArchetypeSaveRequest(BaseModel):
    name: str
    allocations: List[ArchetypeAllocationEntryRequest]
    expert_tags: List[str] = []
    wants: List[ArchetypeWantEntryRequest] = []
    forbid: List[str] = []


class ManualSaveRequest(BaseModel):
    manual_id: str
    title: str
    description: Optional[str] = ""
    start_page_id: Optional[str] = ""
    audiences: List[str] = ["common"]
    sort_order: Optional[int] = None
    release_version: Optional[str] = ""
    popup_version: Optional[str] = ""
    auto_open_on_update: bool = False
    is_whats_new: bool = False
    manual_type: Optional[str] = ""
    show_in_library: bool = True
    support_url: Optional[str] = ""
    banner_title: Optional[str] = ""
    banner_text: Optional[str] = ""
    banner_action_label: Optional[str] = ""
    source_folder: Optional[str] = None
    chapters: List[Dict[str, Any]] = []
    pages: List[Dict[str, Any]] = []


class WorkshopPushRequest(BaseModel):
    target: Optional[str] = None
    workshop_id: Optional[str] = None
    username: str
    password: Optional[str] = None
    changenote: Optional[str] = "Update pushed via SteamCMD"
    title: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[int] = None
    tags: Optional[str] = None
    update_files: bool = True
    update_metadata: bool = False
    update_preview: bool = False
