import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from api.routers.common import get_debug_parser

logger = logging.getLogger(__name__)
router = APIRouter(tags=["debug"])


@router.get("/api/debug/logs")
async def get_debug_logs(
    limit: int = 500,
    only_dt: bool = False,
    offset: Optional[int] = None,
    levels: Optional[str] = None,
    systems: Optional[str] = None,
):
    try:
        parser = get_debug_parser()
        level_list = levels.split(",") if levels else None
        system_list = systems.split(",") if systems else None

        if offset is not None:
            return parser.get_new_lines(offset, only_dt=only_dt, levels=level_list, systems=system_list)
        return parser.get_last_n_lines(lines=limit, only_dt=only_dt, levels=level_list, systems=system_list)
    except Exception as exc:
        logger.error("Error fetching debug logs: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
