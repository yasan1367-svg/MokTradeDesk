"""تست‌های فاز ۴۲.۳ تا ۴۲.۷ — Backup / Migration safety.

تمام تست‌ها روی پوشهٔ Backup موقت اجرا می‌شوند تا به `backend/backups/` واقعی
دست نزنند.
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from app.services import backup_service as svc


@pytest.fixture()
def backup_env(tmp_path, monkeypatch):
    """پوشهٔ Backup را به tmp_path منتقل می‌کند (بدون لمس دادهٔ واقعی)."""
    bdir = tmp_path / "backups"
    bdir.mkdir()
    monkeypatch.setattr(svc, "BACKUP_DIR", str(bdir))
    monkeypatch.setattr(svc, "CONFIG_PATH", str(bdir / ".backup_config.json"))
    return bdir


def _make_backup_file(bdir, name, age_hours):
    """یک فایل SQLite معتبر با mtime دلخواه می‌سازد."""
    p = bdir / name
    conn = sqlite3.connect(str(p))
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    ts = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).timestamp()
    os.utime(str(p), (ts, ts))
    return p


# ═════════════════════════════════════════════
# ۴۲.۴ — Backup پیش از migration
# ═════════════════════════════════════════════
def test_premigrate_backup_naming(backup_env):
    info = svc.create_backup(prefix=svc.PREMIGRATE_PREFIX)
    assert info["filename"].startswith("trading_desk_premigrate_")
    assert svc.is_premigrate(info["filename"]) is True
    assert os.path.exists(os.path.join(svc.BACKUP_DIR, info["filename"]))


# ═════════════════════════════════════════════
# ۴۲.۵ — Backup هوشمند
# ═════════════════════════════════════════════
def test_should_backup_true_when_no_backups(backup_env):
    assert svc.should_backup(24) is True


def test_should_backup_false_when_recent(backup_env):
    svc.create_backup()
    assert svc.should_backup(24) is False


def test_should_backup_true_when_old(backup_env):
    info = svc.create_backup()
    old = (datetime.now(timezone.utc) - timedelta(hours=25)).timestamp()
    os.utime(os.path.join(svc.BACKUP_DIR, info["filename"]), (old, old))
    assert svc.should_backup(24) is True


def test_premigrate_not_counted_for_interval(backup_env):
    svc.create_backup(prefix=svc.PREMIGRATE_PREFIX)
    assert svc.should_backup(24) is True


# ═════════════════════════════════════════════
# ۴۲.۶ — Rotation طبقه‌بندی‌شده
# ═════════════════════════════════════════════
def test_rotation_same_hour_keeps_newest(backup_env):
    base = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    for i, sec in enumerate((1, 2)):
        p = _make_backup_file(backup_env, f"trading_desk_20260101_00000{i}.db", 0)
        ts = (base + timedelta(seconds=sec)).timestamp()
        os.utime(str(p), (ts, ts))
    res = svc.cleanup_old_backups()
    assert res["removed_count"] == 1
    assert len(svc.list_backups()) == 1


def test_rotation_keeps_different_hours_within_24h(backup_env):
    _make_backup_file(backup_env, "trading_desk_20260101_000001.db", 1)
    _make_backup_file(backup_env, "trading_desk_20260101_000002.db", 3)
    res = svc.cleanup_old_backups()
    assert res["removed_count"] == 0
    assert len(svc.list_backups()) == 2


def test_rotation_daily_bucket(backup_env):
    _make_backup_file(backup_env, "trading_desk_20260101_000001.db", 30)
    _make_backup_file(backup_env, "trading_desk_20260101_000002.db", 80)
    res = svc.cleanup_old_backups()
    assert res["removed_count"] == 0
    assert len(svc.list_backups()) == 2


def test_rotation_removes_older_than_4_weeks(backup_env):
    _make_backup_file(backup_env, "trading_desk_20250101_000000.db", 24 * 30)
    res = svc.cleanup_old_backups()
    assert res["removed_count"] == 1
    assert svc.list_backups() == []


def test_rotation_never_removes_premigrate(backup_env):
    _make_backup_file(backup_env, "trading_desk_premigrate_20200101_000000.db", 24 * 400)
    res = svc.cleanup_old_backups()
    assert res["removed_count"] == 0
    names = [b["filename"] for b in svc.list_backups()]
    assert "trading_desk_premigrate_20200101_000000.db" in names


# ═════════════════════════════════════════════
# ۴۲.۷ — restore ایمن
# ═════════════════════════════════════════════
def test_verify_backup_ok(backup_env):
    info = svc.create_backup()
    path = os.path.join(svc.BACKUP_DIR, info["filename"])
    assert svc.verify_backup(path) is True


def test_verify_backup_corrupt(backup_env):
    p = backup_env / "trading_desk_corrupt.db"
    p.write_bytes(b"this is definitely not a sqlite database")
    assert svc.verify_backup(str(p)) is False


def test_restore_backup_rejects_corrupt(backup_env):
    p = backup_env / "trading_desk_corrupt.db"
    p.write_bytes(b"garbage not sqlite")
    with pytest.raises(ValueError):
        svc.restore_backup("trading_desk_corrupt.db")


def test_restore_backup_removes_wal_and_reports_restart(backup_env):
    info = svc.create_backup()
    db_path = svc._db_path()
    for side in ("-wal", "-shm"):
        with open(db_path + side, "w", encoding="utf-8") as f:
            f.write("stale")

    res = svc.restore_backup(info["filename"])

    assert res["restart_required"] is True
    assert "ری‌استارت" in res["message"]
    for side in ("-wal", "-shm"):
        assert not os.path.exists(db_path + side)


# ═════════════════════════════════════════════
# ۴۲.۳ — خطای migration = توقف startup
# ═════════════════════════════════════════════
def test_startup_raises_on_migration_failure(monkeypatch, backup_env):
    from alembic import command as alembic_command

    from app import main

    def boom(*args, **kwargs):
        raise RuntimeError("migration boom")

    monkeypatch.setattr(alembic_command, "upgrade", boom)
    with pytest.raises(RuntimeError, match="migration boom"):
        main.startup()
