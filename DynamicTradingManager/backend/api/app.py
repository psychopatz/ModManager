import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routers.archetypes import router as archetypes_router
from api.routers.blacklist_overrides import router as blacklist_overrides_router
from api.routers.catalog import router as catalog_router
from api.routers.common import configure_environment
from api.routers.debug_logs import router as debug_logs_router
from api.routers.git import router as git_router
from api.routers.manuals import router as manuals_router
from api.routers.pricing import router as pricing_router
from api.routers.simulation import router as simulation_router
from api.routers.tasks_actions import router as tasks_actions_router
from api.routers.workshop import router as workshop_router
from config.server_settings import get_server_settings


def create_app() -> FastAPI:
    load_dotenv()
    settings = get_server_settings()

    app = FastAPI(title="Dynamic Trading Manager API")

    portraits_root = settings.dynamic_trading_path / "Contents/mods/DynamicTradingCommon/42.13/media/ui/Portraits"
    if portraits_root.exists():
        app.mount("/static/portraits", StaticFiles(directory=str(portraits_root)), name="dt-portraits")

    mod_root = settings.dynamic_trading_path
    colonies_root = settings.dynamic_colonies_path
    currency_root = settings.dynamic_currency_path

    if mod_root.exists():
        app.mount("/static/workshop", StaticFiles(directory=str(mod_root)), name="workshop-static")
        manuals_static_root = mod_root / "Contents/mods/DynamicTradingCommon/42.13/media/ui/Manuals"
        manuals_static_root.mkdir(parents=True, exist_ok=True)
        app.mount("/static/manuals", StaticFiles(directory=str(manuals_static_root)), name="manuals-static")

    if colonies_root.exists():
        manuals_colony_static_root = colonies_root / "Contents/mods/DynamicColonies/42.13/media/ui/Manuals"
        manuals_colony_static_root.mkdir(parents=True, exist_ok=True)
        app.mount(
            "/static/manuals-colony",
            StaticFiles(directory=str(manuals_colony_static_root)),
            name="manuals-colony-static",
        )

    if currency_root.exists():
        manuals_currency_static_root = currency_root / "Contents/mods/CurrencyExpanded/42.13/media/ui/Manuals"
        manuals_currency_static_root.mkdir(parents=True, exist_ok=True)
        app.mount(
            "/static/manuals-currency",
            StaticFiles(directory=str(manuals_currency_static_root)),
            name="manuals-currency-static",
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_origin_regex=r"^(https?://(localhost|127\.0\.0\.1)(:\d+)?|vscode-webview://.*|https://.*\.puter\.com)$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    configure_environment(
        console_path=str(settings.console_path),
        mod_root=mod_root,
        colonies_root=colonies_root,
        currency_root=currency_root,
    )

    app.include_router(catalog_router)
    app.include_router(pricing_router)
    app.include_router(tasks_actions_router)
    app.include_router(blacklist_overrides_router)
    app.include_router(archetypes_router)
    app.include_router(manuals_router)
    app.include_router(debug_logs_router)
    app.include_router(workshop_router)
    app.include_router(git_router)
    app.include_router(simulation_router)

    return app


app = create_app()
