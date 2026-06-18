from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.deps import verify_api_key
from api.models import StatusOut
from api.routes import auth, groups, rules, scheduler, messages, settings as settings_routes, telegram_auth
from bot.client import userbot
from bot import scheduler as sched_service
from config import BASE_DIR
from database.engine import async_session
from database import crud

DIST_DIR = BASE_DIR / "web" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Telegram Userbot API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(groups.router, prefix="/api")
    app.include_router(rules.router, prefix="/api")
    app.include_router(scheduler.router, prefix="/api")
    app.include_router(messages.router, prefix="/api")
    app.include_router(settings_routes.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(telegram_auth.router, prefix="/api")

    @app.get("/api/status", response_model=StatusOut, tags=["System"])
    async def get_status(api_key: str = Depends(verify_api_key)):
        authorized = userbot.is_connected and await userbot.client.is_user_authorized()
        me = await userbot.get_me() if authorized else None
        async with async_session() as session:
            grps = await crud.get_active_groups(session)
            rls = await crud.get_all_rules(session)
            schs = await crud.get_all_schedules(session)
        return StatusOut(
            user_id=me.id if me else None,
            username=me.username if me else None,
            first_name=me.first_name if me else None,
            monitored_groups=len(grps),
            keyword_rules=len(rls),
            scheduled_tasks=len(schs),
            scheduler_running=sched_service.scheduler.running,
            telegram_authorized=authorized,
        )

    @app.get("/health", tags=["System"])
    async def health():
        return {"status": "ok", "connected": userbot.is_connected}

    if DIST_DIR.exists():
        app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            file = DIST_DIR / full_path
            if file.is_file():
                return FileResponse(file)
            return FileResponse(DIST_DIR / "index.html")

    return app
