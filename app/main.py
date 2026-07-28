"""NetAI Manager – FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app import __version__
from app.api.routes import accounts, ai, chats, health, messages, platforms
from app.config import get_settings
from app.core.account_manager import account_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{__version__}")
    yield
    logger.info("Shutting down – disconnecting all accounts")
    await account_manager.disconnect_all()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "Professional multi-platform AI social network manager. "
        "Connect Telegram, Bale, Rubika, Rubino, Soroush, Email and YouTube."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(health.router, tags=["Health"])
app.include_router(platforms.router, prefix="/api/platforms", tags=["Platforms"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["Accounts"])
app.include_router(chats.router, prefix="/api/chats", tags=["Chats"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])

# Static dashboard (minimal)
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root_page() -> str:
    return f"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{settings.app_name}</title>
  <style>
    :root {{
      --bg: #0f1419;
      --card: #1a2332;
      --accent: #3b82f6;
      --text: #e7ecf3;
      --muted: #94a3b8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: system-ui, Tahoma, sans-serif;
      background: var(--bg); color: var(--text);
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
    }}
    .card {{
      background: var(--card); border-radius: 16px; padding: 2.5rem;
      max-width: 640px; width: 92%; box-shadow: 0 20px 50px rgba(0,0,0,.4);
      border: 1px solid #243044;
    }}
    h1 {{ margin: 0 0 .5rem; font-size: 1.75rem; }}
    p {{ color: var(--muted); line-height: 1.7; }}
    a {{
      color: var(--accent); text-decoration: none; font-weight: 600;
    }}
    a:hover {{ text-decoration: underline; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: .5rem; margin: 1.25rem 0; }}
    .badge {{
      background: #243044; color: var(--text); padding: .35rem .7rem;
      border-radius: 999px; font-size: .8rem;
    }}
    .links {{ margin-top: 1.5rem; display: flex; gap: 1rem; flex-wrap: wrap; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{settings.app_name}</h1>
    <p>نسخه {__version__} — مدیریت یکپارچه شبکه‌های مجازی با هوش مصنوعی</p>
    <div class="badges">
      <span class="badge">Telegram</span>
      <span class="badge">Bale</span>
      <span class="badge">Rubika</span>
      <span class="badge">Rubino</span>
      <span class="badge">Soroush</span>
      <span class="badge">Email</span>
      <span class="badge">YouTube</span>
    </div>
    <p>
      این نسخه اسکلت حرفه‌ای و قابل گسترش است.
      سروش از طریق <strong>SoroPy</strong> متصل می‌شود.
      مستندات کامل API را از لینک زیر باز کنید.
    </p>
    <div class="links">
      <a href="/docs">مستندات Swagger</a>
      <a href="/redoc">ReDoc</a>
      <a href="/api/health">Health Check</a>
    </div>
  </div>
</body>
</html>
"""
