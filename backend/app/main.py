from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .core.database import engine, Base
from .api import strategies, prop, personal, imports, analytics, trades, symbol_mappings
from .api import settings as settings_api

# ⚠️ Migration باید تنها راه ساخت جدول‌ها باشه
# Base.metadata.create_all(bind=engine)   ← غیرفعال شد

# ═════════════════════════════════════════════
# App
# ═════════════════════════════════════════════
app = FastAPI(title="MokTradeDesk API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
app.include_router(symbol_mappings.router, prefix="/api/symbol-mappings", tags=["symbol-mappings"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])

@app.get("/")
def root():
    return {"message": "MokTradeDesk API is running"}