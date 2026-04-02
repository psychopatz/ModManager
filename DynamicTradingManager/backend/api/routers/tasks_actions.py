from fastapi import APIRouter, HTTPException

from api.routers.common import get_items
from api.schemas import AddRequest, FindPropertyRequest, ListPropertiesRequest
from ItemManagement import DISTRIBUTIONS_DIR, VANILLA_SCRIPTS_DIR
from ItemManagement.task_manager import manager
from ItemManagement.ui.commands import (
    add as run_add,
    analyze_properties,
    analyze_spawns,
    delete_all_items,
    find_property,
    list_properties,
    rarity_stats,
    update as run_update,
)

router = APIRouter(tags=["tasks-actions"])


@router.get("/api/tasks")
async def list_tasks():
    return manager.list_tasks()


@router.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/api/tasks/{task_id}/logs")
async def get_task_logs(task_id: str, since: int = 0):
    return manager.get_logs(task_id, since)


@router.post("/api/actions/update")
async def trigger_update():
    items = get_items()
    task_id = manager.create_task("Update Items", run_update, items)
    return {"task_id": task_id}


@router.post("/api/actions/add")
async def trigger_add(request: AddRequest):
    items = get_items()
    task_id = manager.create_task(f"Add Items (Batch: {request.batch_size})", run_add, items, request.batch_size)
    return {"task_id": task_id}


@router.post("/api/actions/reset")
async def trigger_reset():
    task_id = manager.create_task("Reset Item Registry", delete_all_items, force=True)
    return {"task_id": task_id}


@router.post("/api/actions/list-properties")
async def trigger_list_properties(request: ListPropertiesRequest):
    task_id = manager.create_task(
        "List Properties",
        list_properties,
        VANILLA_SCRIPTS_DIR,
        request.min_usage,
        request.chunk_limit,
    )
    return {"task_id": task_id}


@router.post("/api/actions/find-property")
async def trigger_find_property(request: FindPropertyRequest):
    task_id = manager.create_task(
        f"Find Property: {request.property_name}",
        find_property,
        VANILLA_SCRIPTS_DIR,
        request.property_name,
        request.value_filter,
        request.chunk_limit,
    )
    return {"task_id": task_id}


@router.post("/api/actions/analyze-spawns")
async def trigger_analyze_spawns():
    task_id = manager.create_task("Analyze Spawns", analyze_spawns, DISTRIBUTIONS_DIR, full_output=True)
    return {"task_id": task_id}


@router.post("/api/actions/rarity-stats")
async def trigger_rarity_stats():
    task_id = manager.create_task("Rarity Statistics", rarity_stats, DISTRIBUTIONS_DIR)
    return {"task_id": task_id}


@router.post("/api/actions/generate-docs")
async def trigger_generate_docs():
    task_id = manager.create_task("Generate Property Docs", analyze_properties, VANILLA_SCRIPTS_DIR)
    return {"task_id": task_id}
