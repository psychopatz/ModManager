from fastapi import FastAPI, BackgroundTasks, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import sys
import os
import threading
from pathlib import Path
import logging
import shutil
import re
from uuid import uuid4
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import from local ItemManagement package
try:
    from ItemManagement import (
        load_vanilla_items,
        VANILLA_SCRIPTS_DIR,
        DISTRIBUTIONS_DIR,
        generate_tags,
        calculate_price,
        calculate_price_details,
        build_pricing_audit,
        build_pricing_tag_catalog,
        preview_pricing_tag,
        warm_pricing_tag_cache,
        load_pricing_config,
        save_pricing_config,
        get_stat,
        add_item_to_blacklist,
        reload_blacklist,
    )
    from ItemManagement.commons.vanilla_loader import get_property_value, get_translated_name
    from ItemManagement.commons.lua_handler.records import tags_list_to_dict
    from ItemManagement.parse.overrides import load_overrides, save_overrides, validate_override
    from ItemManagement.ui.commands import (
        update as run_update, 
        add as run_add,
        delete_all_items,
        list_properties,
        find_property,
        analyze_properties,
        analyze_spawns,
        rarity_stats,
        get_registered_items
    )
    from ItemManagement.ui.stats import count_registered_items, find_invalid_blacklist_ids
    from ItemManagement.parse import load_blacklist, is_item_blacklisted
    from ItemManagement.task_manager import manager
    from DebugManagement import LogParser
    from WorkshopManagement.workshop import prepare_staging, generate_vdf, run_steamcmd_upload, parse_workshop_txt, fetch_steam_metadata, run_full_workshop_push
    from GitManagement.diff_handler import get_git_changes, get_git_branches
    from ProjectManagement import list_workshop_projects, resolve_project_target
except ImportError as e:
    logger.error(f"Error importing ItemManagement or DebugManagement modules: {e}")
    sys.exit(1)

# Initialize Debug Parser
CONSOLE_PATH = os.getenv("CONSOLE_PATH", "/home/psychopatz/Zomboid/console.txt")
debug_parser = LogParser(CONSOLE_PATH)

app = FastAPI(title="Dynamic Trading Manager API")

PORTRAITS_ROOT = Path(__file__).resolve().parents[2] / "Contents/mods/DynamicTradingCommon/42.13/media/ui/Portraits"
if PORTRAITS_ROOT.exists():
    app.mount("/static/portraits", StaticFiles(directory=str(PORTRAITS_ROOT)), name="dt-portraits")

MOD_ROOT = Path(os.getenv("DYNAMIC_TRADING_PATH", "/home/psychopatz/Zomboid/Workshop/DynamicTrading/"))
COLONIES_ROOT = Path(os.getenv("DYNAMIC_COLONIES_PATH", str(MOD_ROOT.parent / "DynamicColonies")))
CURRENCY_ROOT = Path(os.getenv("DYNAMIC_CURRENCY_PATH", str(MOD_ROOT.parent / "CurrencyExpanded")))
if MOD_ROOT.exists():
    app.mount("/static/workshop", StaticFiles(directory=str(MOD_ROOT)), name="workshop-static")
    MANUALS_STATIC_ROOT = MOD_ROOT / "Contents/mods/DynamicTradingCommon/42.13/media/ui/Manuals"
    MANUALS_STATIC_ROOT.mkdir(parents=True, exist_ok=True)
    app.mount("/static/manuals", StaticFiles(directory=str(MANUALS_STATIC_ROOT)), name="manuals-static")
if COLONIES_ROOT.exists():
    MANUALS_COLONY_STATIC_ROOT = COLONIES_ROOT / "Contents/mods/DynamicColonies/42.13/media/ui/Manuals"
    MANUALS_COLONY_STATIC_ROOT.mkdir(parents=True, exist_ok=True)
    app.mount("/static/manuals-colony", StaticFiles(directory=str(MANUALS_COLONY_STATIC_ROOT)), name="manuals-colony-static")
if CURRENCY_ROOT.exists():
    MANUALS_CURRENCY_STATIC_ROOT = CURRENCY_ROOT / "Contents/mods/CurrencyExpanded/42.13/media/ui/Manuals"
    MANUALS_CURRENCY_STATIC_ROOT.mkdir(parents=True, exist_ok=True)
    app.mount("/static/manuals-currency", StaticFiles(directory=str(MANUALS_CURRENCY_STATIC_ROOT)), name="manuals-currency-static")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _finish_pricing_page_warm():
    try:
        warmed = warm_pricing_tag_cache(get_items())
        logger.info(
            "Warmed tag pricing cache for %s items across %s tags",
            warmed["items"],
            warmed["tags"],
        )
    except Exception as exc:
        logger.warning("Unable to warm tag pricing cache on startup: %s", exc)


@app.on_event("startup")
async def warm_pricing_page_cache():
    try:
        catalog = build_pricing_tag_catalog(get_items())
        logger.info("Warmed tag pricing catalog for %s tags", len(catalog.get("tags", [])))
    except Exception as exc:
        logger.warning("Unable to warm tag pricing catalog on startup: %s", exc)
        return

    threading.Thread(target=_finish_pricing_page_warm, daemon=True).start()

# Models
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

# Global state (cache items)
cached_vanilla_items = None


def _get_workshop_project_or_404(target: Optional[str] = None):
    try:
        return resolve_project_target(target)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def _serialize_workshop_projects():
    projects = list_workshop_projects()
    default_target = next((project["key"] for project in projects if project["is_default"]), None)
    return {"targets": projects, "default_target": default_target}

def get_items():
    global cached_vanilla_items
    if cached_vanilla_items is None:
        cached_vanilla_items = load_vanilla_items()
    return cached_vanilla_items

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    items = get_items()
    total_vanilla = len(items)
    registered = count_registered_items()
    unregistered = total_vanilla - registered
    coverage = (registered / total_vanilla * 100) if total_vanilla > 0 else 0
    
    notifications = []
    invalid_blacklist = find_invalid_blacklist_ids()
    if invalid_blacklist:
        notifications.append(f"{len(invalid_blacklist)} invalid item ID(s) in blacklist")
    
    return {
        "total_vanilla": total_vanilla,
        "registered": registered,
        "unregistered": unregistered,
        "coverage": round(coverage, 2),
        "notifications": notifications
    }

@app.get("/api/items")
async def list_items(
    search: Optional[str] = None, 
    status: Optional[str] = None,
    tag: Optional[str] = None,
    min_weight: Optional[float] = None,
    max_weight: Optional[float] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    limit: int = 100, 
    offset: int = 0
):
    try:
        items = get_items()
        registered_ids = get_registered_items() # Full set from Lua files
        
        filtered_results = []
        item_keys = list(items.keys())
        
        for item_id in item_keys:
            props = items[item_id]
            is_bl, _ = is_item_blacklisted(item_id, {})
            
            # Extract metadata
            tags_list = generate_tags(item_id, props)
            tags_dict = tags_list_to_dict(tags_list)
            price = calculate_price(item_id, props, tags_dict)
            weight = get_stat(props, "Weight", 0.5)
            
            item_name = get_translated_name(item_id, props)
            
            # Application of filters
            if search and search.lower() not in item_name.lower() and search.lower() not in item_id.lower():
                continue
                
            if status:
                if status == "registered" and item_id not in registered_ids:
                    continue
                elif status == "unregistered" and (item_id in registered_ids or is_bl):
                    continue
                elif status == "blacklisted" and not is_bl:
                    continue
                    
            if tag:
                # Match if tag exists within any tag string in the array
                if not any(tag.lower() in t.lower() for t in tags_list):
                    continue
                    
            if min_weight is not None and weight < min_weight:
                continue
            if max_weight is not None and weight > max_weight:
                continue
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
            
            filtered_results.append({
                "id": item_id,
                "name": item_name,
                "is_blacklisted": bool(is_bl),
                "is_registered": item_id in registered_ids,
                "price": int(price),
                "tags": tags_list,
                "weight": float(weight)
            })
            
        total = len(filtered_results)
        
        # Paginate correctly after slicing
        paginated_results = filtered_results[offset:offset+limit]
        
        return {
            "total": total,
            "items": paginated_results
        }
    except Exception as e:
        logger.error(f"Error in list_items: {e}")
        return {"total": 0, "items": [], "error": str(e)}

@app.get("/api/tags")
async def list_unique_tags():
    try:
        items = get_items()
        unique_tags = set()
        
        for item_id, props in items.items():
            tags_list = generate_tags(item_id, props)
            for tag in tags_list:
                unique_tags.add(tag)
                
        return {"tags": sorted(list(unique_tags))}
    except Exception as e:
        logger.error(f"Error fetching tags: {e}")
        return {"tags": [], "error": str(e)}


@app.get("/api/pricing/config")
async def get_pricing_config():
    try:
        return load_pricing_config()
    except Exception as e:
        logger.error(f"Error loading pricing config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/pricing/config")
async def update_pricing_config(request: PricingConfigRequest):
    try:
        return save_pricing_config(request.config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving pricing config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pricing/preview")
async def preview_pricing(request: PricingPreviewRequest):
    try:
        items = get_items()
        props = request.props or items.get(request.item_id)
        if not props:
            raise HTTPException(status_code=404, detail=f"Unknown item: {request.item_id}")

        tags_list = request.tags or generate_tags(request.item_id, props)
        tags_dict = tags_list_to_dict(tags_list)
        details = calculate_price_details(request.item_id, props, tags_dict)

        return {
            "item_id": request.item_id,
            "name": get_translated_name(request.item_id, props),
            "tags": tags_list,
            "price": details["price"],
            "details": details,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing pricing for {request.item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pricing/audit")
async def get_pricing_audit(limit: int = 20):
    try:
        return build_pricing_audit(get_items(), outlier_limit=limit)
    except Exception as e:
        logger.error(f"Error building pricing audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pricing/tags")
async def get_pricing_tags():
    try:
        return build_pricing_tag_catalog(get_items())
    except Exception as e:
        logger.error(f"Error building pricing tag catalog: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pricing/tags/preview")
async def preview_pricing_tags(request: PricingTagPreviewRequest):
    try:
        return preview_pricing_tag(
            get_items(),
            request.tag,
            addition=request.addition,
            limit=request.limit,
        )
    except Exception as e:
        logger.error(f"Error previewing pricing tag {request.tag}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Task Routes ---

@app.get("/api/tasks")
async def list_tasks():
    return manager.list_tasks()

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/api/tasks/{task_id}/logs")
async def get_task_logs(task_id: str, since: int = 0):
    return manager.get_logs(task_id, since)

# --- Action Routes (now using TaskManager) ---

@app.post("/api/actions/update")
async def trigger_update():
    items = get_items()
    task_id = manager.create_task("Update Items", run_update, items)
    return {"task_id": task_id}

@app.post("/api/actions/add")
async def trigger_add(request: AddRequest):
    items = get_items()
    task_id = manager.create_task(f"Add Items (Batch: {request.batch_size})", run_add, items, request.batch_size)
    return {"task_id": task_id}

@app.post("/api/actions/reset")
async def trigger_reset():
    task_id = manager.create_task("Reset Item Registry", delete_all_items, force=True)
    return {"task_id": task_id}

@app.post("/api/actions/list-properties")
async def trigger_list_properties(request: ListPropertiesRequest):
    task_id = manager.create_task(
        "List Properties", 
        list_properties, 
        VANILLA_SCRIPTS_DIR, 
        request.min_usage, 
        request.chunk_limit
    )
    return {"task_id": task_id}

@app.post("/api/actions/find-property")
async def trigger_find_property(request: FindPropertyRequest):
    task_id = manager.create_task(
        f"Find Property: {request.property_name}", 
        find_property, 
        VANILLA_SCRIPTS_DIR, 
        request.property_name, 
        request.value_filter, 
        request.chunk_limit
    )
    return {"task_id": task_id}

@app.post("/api/actions/analyze-spawns")
async def trigger_analyze_spawns():
    task_id = manager.create_task("Analyze Spawns", analyze_spawns, DISTRIBUTIONS_DIR, full_output=True)
    return {"task_id": task_id}

@app.post("/api/actions/rarity-stats")
async def trigger_rarity_stats():
    task_id = manager.create_task("Rarity Statistics", rarity_stats, DISTRIBUTIONS_DIR)
    return {"task_id": task_id}

@app.post("/api/actions/generate-docs")
async def trigger_generate_docs():
    task_id = manager.create_task("Generate Property Docs", analyze_properties, VANILLA_SCRIPTS_DIR)
    return {"task_id": task_id}

# --- Blacklist ---

@app.get("/api/blacklist")
async def get_blacklist():
    return load_blacklist()


@app.post("/api/blacklist/item")
async def add_blacklist_item(request: BlacklistItemRequest):
    global cached_vanilla_items

    try:
        blacklist = add_item_to_blacklist(request.item_id)
        reload_blacklist()
        cached_vanilla_items = None
        return {
            "success": True,
            "item_id": request.item_id,
            "blacklist": blacklist,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding {request.item_id} to blacklist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/overrides")
async def get_overrides():
    try:
        overrides = load_overrides()
        return {
            "overrides": overrides,
            "by_item": {
                override.get("item"): override
                for override in overrides
                if override.get("item")
            },
        }
    except Exception as e:
        logger.error(f"Error loading overrides: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/overrides/item")
async def save_item_override(request: ItemOverrideRequest):
    try:
        override = {"item": request.item_id}
        if request.base_price is not None:
            override["basePrice"] = request.base_price
        if request.tags:
            override["tags"] = request.tags
        if request.stock_min is not None or request.stock_max is not None:
            override["stockRange"] = {}
            if request.stock_min is not None:
                override["stockRange"]["min"] = request.stock_min
            if request.stock_max is not None:
                override["stockRange"]["max"] = request.stock_max
        if request.description:
            override["description"] = request.description

        if len(override) == 1:
            raise HTTPException(status_code=400, detail="Override must include at least one field to save.")

        is_valid, error = validate_override(override)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error or "Invalid override")

        overrides = [entry for entry in load_overrides() if entry.get("item") != request.item_id]
        overrides.append(override)
        save_overrides(overrides)
        return {
            "success": True,
            "override": override,
            "overrides": overrides,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving override for {request.item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/overrides/item/{item_id}")
async def delete_item_override(item_id: str):
    try:
        overrides = load_overrides()
        next_overrides = [entry for entry in overrides if entry.get("item") != item_id]
        if len(next_overrides) == len(overrides):
            raise HTTPException(status_code=404, detail="Override not found")

        save_overrides(next_overrides)
        return {
            "success": True,
            "item_id": item_id,
            "overrides": next_overrides,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting override for {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Archetype Editor ---

@app.get("/api/archetypes/editor")
async def get_archetype_editor_data():
    try:
        return load_archetype_editor_data()
    except Exception as e:
        logger.error(f"Error loading archetype editor data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/archetypes/{archetype_id}/allocations")
async def update_archetype_allocations(archetype_id: str, request: ArchetypeSaveRequest):
    try:
        payload = save_archetype_definition(
            archetype_id,
            request.model_dump(),
        )
        return {
            "success": True,
            "archetype_id": archetype_id,
            "archetype": payload,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving allocations for {archetype_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _normalize_manual_module(module: Optional[str]) -> str:
    normalized = str(module or "common").strip().lower()
    if normalized in {"v1", "v2", "colony", "currency", "common"}:
        return normalized
    return "common"


@app.get("/api/manuals/editor")
async def get_manual_editor_data(scope: str = "manuals", module: str = "common"):
    try:
        return load_manual_editor_data(scope=scope, module=_normalize_manual_module(module))
    except Exception as e:
        logger.error(f"Error loading manual editor data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/manuals")
async def create_manual(request: ManualSaveRequest, scope: str = "manuals", module: str = "common"):
    try:
        payload = create_manual_definition(request.model_dump(), scope=scope, module=_normalize_manual_module(module))
        return {
            "success": True,
            "manual": payload,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating manual: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/manuals/{manual_id}")
async def update_manual(manual_id: str, request: ManualSaveRequest, scope: str = "manuals", module: str = "common"):
    try:
        payload = save_manual_definition(manual_id, request.model_dump(), scope=scope, module=_normalize_manual_module(module))
        return {
            "success": True,
            "manual": payload,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving manual {manual_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/manuals/{manual_id}")
async def remove_manual(manual_id: str, scope: str = "manuals", module: str = "common"):
    try:
        delete_manual_definition(manual_id, scope=scope, module=_normalize_manual_module(module))
        return {
            "success": True,
            "manual_id": manual_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting manual {manual_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/manuals/images")
async def upload_manual_image(
    manual_id: str = Form(...),
    module: str = Form("common"),
    file: UploadFile = File(...),
):
    def _resolve_extension(upload: UploadFile, original_name: str) -> str:
        suffix = Path(original_name).suffix.lower()
        if suffix:
            return suffix

        content_type = (upload.content_type or "").lower()
        if content_type in {"image/jpeg", "image/jpg"}:
            return ".jpg"
        if content_type == "image/png":
            return ".png"
        if content_type == "image/webp":
            return ".webp"
        if content_type == "image/gif":
            return ".gif"
        return ".png"

    def _build_unique_name(assets_dir: Path, upload: UploadFile) -> str:
        original_name = Path(upload.filename or "manual-image").name
        stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(original_name).stem).strip("-").lower() or "manual-image"
        extension = _resolve_extension(upload, original_name)

        while True:
            candidate = f"{stem}_{uuid4().hex[:10]}{extension}"
            if not (assets_dir / candidate).exists():
                return candidate

    normalized_module = _normalize_manual_module(module)
    if normalized_module == "colony":
        base_root = COLONIES_ROOT
        base_url = "/static/manuals-colony"
        mod_folder = "DynamicColonies"
    elif normalized_module == "currency":
        base_root = CURRENCY_ROOT
        base_url = "/static/manuals-currency"
        mod_folder = "CurrencyExpanded"
    else:
        base_root = MOD_ROOT
        base_url = "/static/manuals"
        mod_folder = "DynamicTradingCommon"
    assets_root = base_root / f"Contents/mods/{mod_folder}/42.13/media/ui/Manuals" / manual_id
    assets_root.mkdir(parents=True, exist_ok=True)
    filename = _build_unique_name(assets_root, file)
    file_path = assets_root / filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {
            "success": True,
            "path": f"media/ui/Manuals/{manual_id}/{filename}",
            "url": f"{base_url}/{manual_id}/{filename}",
        }
    except Exception as e:
        logger.error(f"Error uploading manual image for {manual_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Debug / Logs ---

@app.get("/api/debug/logs")
async def get_debug_logs(
    limit: int = 500, 
    only_dt: bool = False, 
    offset: Optional[int] = None,
    levels: Optional[str] = None,
    systems: Optional[str] = None
):
    try:
        level_list = levels.split(",") if levels else None
        system_list = systems.split(",") if systems else None
        
        if offset is not None:
            return debug_parser.get_new_lines(offset, only_dt=only_dt, levels=level_list, systems=system_list)
        return debug_parser.get_last_n_lines(lines=limit, only_dt=only_dt, levels=level_list, systems=system_list)
    except Exception as e:
        logger.error(f"Error fetching debug logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Workshop Management ---

@app.post("/api/workshop/prepare")
async def trigger_workshop_prepare(target: Optional[str] = None):
    project = _get_workshop_project_or_404(target)
    mod_root = project["path"]
    staging_dir = mod_root / "upload_staging"
    
    # Run synchronously since it's just local file copy
    success = prepare_staging(mod_root, staging_dir)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to prepare staging directory")
    
    return {"success": True, "staging_dir": str(staging_dir)}

@app.get("/api/workshop/targets")
async def get_workshop_targets():
    return _serialize_workshop_projects()

@app.get("/api/workshop/metadata")
async def get_workshop_metadata(target: Optional[str] = None):
    project = _get_workshop_project_or_404(target)
    mod_root = project["path"]
    workshop_txt_path = mod_root / "workshop.txt"
    return {
        **parse_workshop_txt(workshop_txt_path),
        "target": project["key"],
        "project_name": project["name"],
        "project_title": project["title"],
    }

@app.get("/api/workshop/sync")
async def sync_workshop_metadata(target: Optional[str] = None, item_id: Optional[str] = None):
    project = _get_workshop_project_or_404(target)
    mod_root = project["path"]
    local_meta = parse_workshop_txt(mod_root / "workshop.txt")
    resolved_item_id = item_id or local_meta.get("id", "")
    if not resolved_item_id:
        raise HTTPException(status_code=400, detail="This project has no workshop ID yet.")
    
    steam_meta = fetch_steam_metadata(resolved_item_id)
    if not steam_meta:
        raise HTTPException(status_code=500, detail="Failed to fetch data from Steam Web API")
    return {**steam_meta, "target": project["key"], "project_name": project["name"]}

@app.get("/api/workshop/preview")
async def get_workshop_preview(target: Optional[str] = None):
    project = _get_workshop_project_or_404(target)
    preview_path = project["path"] / "preview.png"
    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="Preview image not found for this project.")
    return FileResponse(preview_path)

@app.post("/api/workshop/image")
async def upload_workshop_image(file: UploadFile = File(...), target: Optional[str] = None):
    project = _get_workshop_project_or_404(target)
    mod_root = project["path"]
    preview_path = mod_root / "preview.png"
    
    try:
        with open(preview_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"success": True, "filename": "preview.png", "target": project["key"]}
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workshop/push")
async def trigger_workshop_push(request: WorkshopPushRequest):
    project = _get_workshop_project_or_404(request.target)
    mod_root = project["path"]
    staging_dir = mod_root / "upload_staging"
    vdf_path = mod_root / "workshop_update.vdf"
    steamcmd_path = os.getenv("STEAM_CMD_PATH", os.getenv("STEAMCMD_PATH", "/home/psychopatz/Desktop/Apps/SteamCMD/steamcmd.sh"))

    # Run full push workflow in background task
    task_id = manager.create_task(
        "Internal Workshop Sync & Push", 
        run_full_workshop_push, 
        mod_root,
        staging_dir,
        vdf_path,
        steamcmd_path, 
        request.username, 
        request.password,
        request.dict()
    )
    
    return {"task_id": task_id, "target": project["key"], "project_name": project["name"]}

@app.get("/api/git/changes")
async def get_project_changes(branch: Optional[str] = None, target: Optional[str] = None):
    project = _get_workshop_project_or_404(target)
    return get_git_changes(branch, project["path"])

@app.get("/api/git/branches")
async def get_project_branches(target: Optional[str] = None):
    project = _get_workshop_project_or_404(target)
    return get_git_branches(project["path"])

# --- Simulation ---

try:
    from Simulation.config import BuildConfig, default_paths
    from Simulation.archetype_editor import load_archetype_editor_data, save_archetype_definition
    from Simulation.manual_editor import (
        create_manual_definition,
        delete_manual_definition,
        load_manual_editor_data,
        save_manual_definition,
    )
    from Simulation.export.database_builder import build_database
except ImportError as e:
    logger.error(f"Error importing Simulation modules: {e}")

@app.get("/api/simulation/data")
async def get_simulation_data():
    try:
        paths = default_paths()
        config = BuildConfig()
        payload = build_database(paths, config)
        return payload
    except Exception as e:
        logger.error(f"Error generating simulation data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
