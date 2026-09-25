from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
import os
import logging
from datetime import datetime, timezone

from .core.database import engine, Base
from .core.rate_limit import limiter
from .api import strategies, prop, personal, imports, analytics, trades, symbol_mappings, export, finance
from .api import settings as settings_api

# ═════════════════════════════════════════════
# Logging
# ═════════════════════════════════════════════
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "app.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("moktrade")

# ═════════════════════════════════════════════
# App
# ═════════════════════════════════════════════
app = FastAPI(title="MokTradeDesk API", version="1.0")

# ═════════════════════════════════════════════
# CORS
# ═════════════════════════════════════════════
# توجه: در production دامنهٔ واقعی فرانت‌اند را این‌جا اضافه کنید.
# (پیش‌تر "*" بود که با allow_credentials=True ترکیب ناامن/نامعتبری می‌ساخت.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═════════════════════════════════════════════
# Rate Limiting (فاز ۱۵.۲)
# ═════════════════════════════════════════════
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ═════════════════════════════════════════════
# Middleware — Request Logging
# ═════════════════════════════════════════════
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = datetime.now(timezone.utc)
    response = await call_next(request)
    duration = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration:.3f}s)")
    return response


@app.on_event("startup")
def startup():
    logger.info("🚀 MokTradeDesk API started")

@app.on_event("shutdown")
def shutdown():
    logger.info("👋 MokTradeDesk API stopped")

# ═════════════════════════════════════════════
# Mount static files برای اسکرین‌شات‌ها
# ═════════════════════════════════════════════
STORAGE_DIR = os.path.abspath("storage")
os.makedirs(os.path.join(STORAGE_DIR, "screenshots"), exist_ok=True)
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")

# ═════════════════════════════════════════════
# Routers
# ═════════════════════════════════════════════
app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(prop.router, prefix="/api/prop", tags=["prop"])
app.include_router(personal.router, prefix="/api/personal", tags=["personal"])
app.include_router(imports.router, prefix="/api/imports", tags=["imports"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
app.include_router(symbol_mappings.router, prefix="/api/symbol-mappings", tags=["symbol-mappings"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])
app.include_router(finance.router, prefix="/api/finance", tags=["finance"])

@app.get("/")
def root():
    return {"message": "MokTradeDesk API is running"}