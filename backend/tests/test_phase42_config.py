"""تست‌های فاز ۴۲.۱ — مسیر مطلق دیتابیس.

هدف: `DATABASE_URL` پیش‌فرض نباید نسبی و وابسته به CWD باشد؛ باید از روی
`__file__` ساخته شود تا اجرای uvicorn از هر پوشه‌ای به همان فایل
`backend/trading_desk.db` اشاره کند.
"""
from pathlib import Path

from app.core import config


def test_db_path_is_absolute():
    """DB_PATH باید مطلق باشد (نه وابسته به CWD)."""
    assert config.DB_PATH.is_absolute()
    assert ".." not in str(config.DB_PATH)


def test_db_path_exists_in_backend_dir():
    """DB_PATH باید دقیقاً `backend/trading_desk.db` باشد."""
    assert config.DB_PATH == config.BACKEND_DIR / "trading_desk.db"
    assert config.DB_PATH.name == "trading_desk.db"


def test_default_database_url_is_absolute():
    """URL پیش‌فرض باید مطلق باشد و به مسیر backend اشاره کند."""
    url = config._default_database_url()
    assert url.startswith("sqlite:///")
    # مسیر استخراج‌شده باید مطلق باشد
    extracted = Path(url.replace("sqlite:///", "", 1))
    assert extracted.is_absolute()
    assert extracted == config.DB_PATH


def test_backend_dir_contains_alembic_ini():
    """BACKEND_DIR باید ریشهٔ backend باشد (اعتبارسنجی مسیر parent.parent.parent)."""
    assert (config.BACKEND_DIR / "alembic.ini").exists()
    assert (config.BACKEND_DIR / "app").is_dir()
