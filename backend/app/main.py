from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
import os
import logging
import threading
from datetime import datetime, timezone

from .core.rate_limit import limiter
from .api import strategies, prop, personal, imports, analytics, trades, symbol_mappings, export, finance, broker, trading
from .api import import_engine as import_engine_api
from .api import settings as settings_api
from .api import backup as backup_api

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
# فاز ۱۷: زمان‌بند Backup خودکار (thread پس‌زمینه، بدون وابستگی خارجی)
# ═════════════════════════════════════════════
_backup_stop = threading.Event()
_backup_thread = None
_BACKUP_CHECK_SECONDS = 1800  # هر ۳۰ دقیقه وضعیت بررسی می‌شود


def _backup_loop():
    """در هر بازه بررسی می‌کند و در صورت رسیدن زمان (طبق تنظیمات) Backup می‌سازد."""
    from .services import backup_service as svc
    while not _backup_stop.wait(_BACKUP_CHECK_SECONDS):
        try:
            info = svc.run_auto_backup()
            if info:
                logger.info("💾 auto backup created: %s", info["filename"])
        except Exception:
            logger.exception("auto-backup failed")

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

    # ── فاز ۱۸: اطمینان از ساخت/به‌روزرسانی جداول دیتابیس ──
    # اگر فایل DB حذف/خالی شود، جداول به‌صورت خودکار ساخته می‌شوند تا داشبورد ۵۰۰ ندهد.
    try:
        from alembic.config import Config as AlembicConfig
        from alembic import command as alembic_command
        from .core.config import settings

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_cfg = AlembicConfig(os.path.join(base_dir, "alembic.ini"))
        alembic_cfg.set_main_option(
            "script_location", os.path.join(base_dir, "migrations")
        )
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

        # alembic در env.py با fileConfig تنظیمات لاگ را بازنویسی می‌کند؛
        # برای حفظ لاگ اپلیکیشن (فایل + کنسول)، هندلرها و سطح لاگ ذخیره/بازگردانی می‌شوند.
        root = logging.getLogger()
        saved_handlers = root.handlers[:]
        saved_level = root.level
        try:
            alembic_command.upgrade(alembic_cfg, "head")
        finally:
            root.handlers[:] = saved_handlers
            root.setLevel(saved_level)

        logger.info("✅ Database migrations applied")
    except Exception:
        logger.exception("migration check failed")

    # ── فاز ۱۷: Backup اولیه + شروع حلقهٔ Backup خودکار ──
    try:
        from .services import backup_service as svc
        svc.create_backup()
        svc.cleanup_old_backups(keep=int(svc.load_config().get("keep", 30)))
        logger.info("💾 initial backup created")
    except Exception:
        logger.exception("initial backup failed")

    global _backup_thread
    if _backup_thread is None or not _backup_thread.is_alive():
        _backup_thread = threading.Thread(target=_backup_loop, name="auto-backup", daemon=True)
        _backup_thread.start()
        logger.info("⏱️ auto-backup loop started")

@app.on_event("shutdown")
def shutdown():
    _backup_stop.set()
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
# فاز ۳۰/۳۱: موتور ایمپورت (preview / commit / batches / profiles)
app.include_router(import_engine_api.router, prefix="/api/imports", tags=["imports"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
app.include_router(symbol_mappings.router, prefix="/api/symbol-mappings", tags=["symbol-mappings"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])
app.include_router(finance.router, prefix="/api/finance", tags=["finance"])
app.include_router(broker.router, prefix="/api/broker", tags=["broker"])
app.include_router(trading.router, prefix="/api/trading", tags=["trading"])
app.include_router(backup_api.router, prefix="/api/backup", tags=["backup"])

@app.get("/")
def root():
    return {"message": "MokTradeDesk API is running"}