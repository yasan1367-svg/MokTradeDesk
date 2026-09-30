"""تست هم‌خوانی مدل‌ها با migrationها (فاز ۴۱.۴ — Safety Net).

روی یک DB موقت: `alembic upgrade head` زده می‌شود، سپس `compare_metadata`
اختلاف بین مدل‌ها (`Base.metadata`) و اسکیمای واقعی را گزارش می‌کند.

⚠️ فعلاً **فقط گزارش** (بدون assert) — طبق برنامهٔ فاز ۴۱.۴، فعال‌سازی assert
در فاز ۴۲ انجام می‌شود. دیتابیس واقعی (`trading_desk.db`) هرگز لمس نمی‌شود.
"""
import os
import tempfile
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

import app.main  # noqa: F401  (ثبت همهٔ مدل‌ها در Base.metadata)
from app.core.database import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def test_migrations_match_models():
    """alembic upgrade head روی DB خالی + compare_metadata (فقط گزارش)."""
    fd, db_path = tempfile.mkstemp(prefix="moktrade_migration_test_", suffix=".db")
    os.close(fd)
    url = "sqlite:///" + db_path.replace(os.sep, "/")

    try:
        alembic_cfg = Config(str(ALEMBIC_INI))
        alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", url)

        # اجرای همهٔ migrationها روی DB خالی
        command.upgrade(alembic_cfg, "head")

        engine = create_engine(url)
        try:
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                diff = compare_metadata(context, Base.metadata)
        finally:
            engine.dispose()

        print(f"\n[migrations] alembic head اعمال شد · اختلافات مدل vs migration: {len(diff)}")
        for item in diff:
            print(f"  - {item}")

        # فاز ۴۱.۴: فعلاً فقط گزارش — assert در فاز ۴۲ فعال می‌شود.
        # assert len(diff) == 0, f"{len(diff)} اختلاف بین مدل‌ها و migrationها پیدا شد"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
