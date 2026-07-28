"""NetAI Manager – FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app import __version__
from app.api.routes import accounts, ai, bots, chats, health, inbox, messages, platforms, settings
from app.config import get_settings
from app.core.account_manager import account_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{__version__}")
    yield
    logger.info("Shutting down – disconnecting all accounts")
    await account_manager.disconnect_all()


cfg = get_settings()

app = FastAPI(
    title=cfg.app_name,
    version=__version__,
    description=(
        "Professional multi-platform AI social network manager. "
        "Unified inbox for Telegram, Bale, Rubika, Rubino, Soroush, Email, YouTube."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(platforms.router, prefix="/api/platforms", tags=["Platforms"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["Accounts"])
app.include_router(chats.router, prefix="/api/chats", tags=["Chats"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(inbox.router, prefix="/api/inbox", tags=["Inbox"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(bots.router, prefix="/api/bots", tags=["Bots"])

static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", include_in_schema=False)
async def root_page():
    index = static_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return HTMLResponse("<p>static/index.html missing</p>")
