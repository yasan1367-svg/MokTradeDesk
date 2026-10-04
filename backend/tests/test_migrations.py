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
from sqlalchemy import create_engine, inspect, text

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


def test_hard_delete_migration_purges_legacy_deleted_trade_dependents():
    """Upgrade removes legacy soft-deleted rows/dependents and the state column."""
    fd, db_path = tempfile.mkstemp(prefix="moktrade_hard_delete_migration_", suffix=".db")
    os.close(fd)
    url = "sqlite:///" + db_path.replace(os.sep, "/")
    alembic_cfg = Config(str(ALEMBIC_INI))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", url)

    try:
        command.upgrade(alembic_cfg, "58a1b2c3d4e5")
        engine = create_engine(url)
        try:
            with engine.begin() as connection:
                tables = set(inspect(connection).get_table_names())
                assert {"trades", "journal_reviews", "screenshots", "import_identities"} <= tables
                assert {"trades", "import_batch_rows", "transactions"} <= tables
                if {"trades", "journal_reviews", "screenshots", "import_identities"} <= tables:
                    # Minimal valid rows for the legacy deleted record graph.
                    strategy_id = connection.execute(text(
                        "INSERT INTO strategies (name) VALUES ('migration-test') RETURNING id"
                    )).scalar_one()
                    version_id = connection.execute(text(
                        "INSERT INTO strategy_versions (strategy_id, version_name) "
                        "VALUES (:sid, 'v1') RETURNING id"
                    ), {"sid": strategy_id}).scalar_one()
                    trade_id = connection.execute(text(
                        "INSERT INTO trades (version_id, symbol, direction, open_time, open_price, size, "
                        "source, test_type, is_deleted) VALUES (:vid, 'XAUUSD', 'buy', "
                        "'2025-01-01 10:00:00', 2000, 1, 'MANUAL', 'BACKTEST', 1) RETURNING id"
                    ), {"vid": version_id}).scalar_one()
                    review_id = connection.execute(text(
                        "INSERT INTO journal_reviews (trade_id) VALUES (:tid) RETURNING id"
                    ), {"tid": trade_id}).scalar_one()
                    connection.execute(text(
                        "INSERT INTO screenshots (entity_type, entity_id, review_id, file_path) "
                        "VALUES ('review', :rid, :rid, 'legacy-shot.png')"
                    ), {"rid": review_id})
                    connection.execute(text(
                        "INSERT INTO import_identities "
                        "(trade_id, source, symbol, open_time, identity_hash) "
                        "VALUES (:tid, 'MT4_IMPORT', 'XAUUSD', '2025-01-01 10:00:00', 'legacy-id')"
                    ), {"tid": trade_id})
                    connection.execute(text(
                        "INSERT INTO import_batch_rows "
                        "(batch_id, row_number, status, identity_hash, payload) "
                        "VALUES (1, 1, 'RESTORED', 'legacy-row', '{}')"
                    ))

            command.upgrade(alembic_cfg, "head")
            with engine.connect() as connection:
                inspector = inspect(connection)
                assert "is_deleted" not in {column["name"] for column in inspector.get_columns("trades")}
                assert "ix_trades_is_deleted" not in {index["name"] for index in inspector.get_indexes("trades")}
                for table in ("trades", "journal_reviews", "screenshots", "import_identities"):
                    assert connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one() == 0
                assert connection.execute(text(
                    "SELECT status FROM import_batch_rows WHERE identity_hash='legacy-row'"
                )).scalar_one() == "NEW"
        finally:
            engine.dispose()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
