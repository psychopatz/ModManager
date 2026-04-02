from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from Simulation.config import BuildConfig, default_paths
from Simulation.export.database_builder import build_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/simulation", tags=["simulation"])


@router.get("/data")
async def get_simulation_data():
    try:
        paths = default_paths()
        config = BuildConfig()
        payload = build_database(paths, config)
        return payload
    except Exception as exc:
        logger.error("Error generating simulation data: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
