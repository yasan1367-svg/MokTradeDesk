from pathlib import Path

from pydantic_settings import BaseSettings

# ═════════════════════════════════════════════
# فاز ۴۲.۱: مسیر مطلق دیتابیس
# ═════════════════════════════════════════════
# `backend/app/core/config.py` → parents: core → app → backend
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BACKEND_DIR / "trading_desk.db"


def _default_database_url() -> str:
    """URL مطلق SQLite بر اساس محل فایل (مستقل از CWD)."""
    return f"sqlite:///{DB_PATH.as_posix()}"


class Settings(BaseSettings):
    # پیش‌فرض مطلق است؛ ولی متغیر محیطی DATABASE_URL (مثلاً در تست‌ها) اولویت دارد.
    DATABASE_URL: str = _default_database_url()
    APP_NAME: str = "MokTradeDesk"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
