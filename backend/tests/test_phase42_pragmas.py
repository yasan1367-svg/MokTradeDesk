"""تست‌های فاز ۴۲.۲ — PRAGMAهای SQLite روی engine اصلی.

engine اصلی به DATABASE_URL تستی (فایل موقت) اشاره می‌کند، پس این PRAGMAها
روی دیتابیس واقعی اثر نمی‌گذارند.
"""
from sqlalchemy import text

from app.core.database import engine


def _pragma(name: str):
    with engine.connect() as conn:
        return conn.execute(text(f"PRAGMA {name}")).scalar()


def test_foreign_keys_enabled():
    assert int(_pragma("foreign_keys")) == 1


def test_wal_mode_enabled():
    assert str(_pragma("journal_mode")).lower() == "wal"


def test_busy_timeout():
    assert int(_pragma("busy_timeout")) == 5000
