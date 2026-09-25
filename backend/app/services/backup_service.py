"""
سرویس Backup دیتابیس (فاز ۱۷)

- ساخت / لیست / بازیابی / حذف / پاک‌سازی Backupهای قدیمی
- Backup آنلاین با sqlite3 backup API (ایمن حتی وقتی دیتابیس در حال استفاده است)
- تنظیمات Backup خودکار در فایل JSON کنار پوشهٔ Backup (بدون نیاز به migration)
"""
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from ..core.config import settings

# مسیر پوشهٔ Backup: backend/backups/
BACKUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backups"))
CONFIG_PATH = os.path.join(BACKUP_DIR, ".backup_config.json")
PREFIX = "trading_desk_"
SUFFIX = ".db"

DEFAULT_CONFIG = {
    "auto_enabled": True,
    "interval_hours": 24,
    "keep": 30,
}


def _db_path() -> str:
    """مسیر فایل دیتابیس از DATABASE_URL (فقط SQLite)"""
    url = settings.DATABASE_URL or ""
    if not url.startswith("sqlite"):
        raise RuntimeError("Backup فقط برای دیتابیس SQLite پشتیبانی می‌شود")
    return os.path.abspath(url.replace("sqlite:///", "", 1))


def ensure_backup_dir() -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    return BACKUP_DIR


def load_config() -> dict:
    ensure_backup_dir()
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            if isinstance(data, dict):
                cfg.update(data)
        except Exception:
            pass
    return cfg


def save_config(cfg: dict) -> dict:
    merged = load_config()
    if cfg.get("auto_enabled") is not None:
        merged["auto_enabled"] = bool(cfg["auto_enabled"])
    if cfg.get("interval_hours"):
        merged["interval_hours"] = max(1, int(cfg["interval_hours"]))
    if cfg.get("keep"):
        merged["keep"] = max(1, int(cfg["keep"]))
    ensure_backup_dir()
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged


def safe_name(filename: str) -> str:
    """جلوگیری از Path Traversal — فقط نام فایل پایه با پیشوند/پسوند مجاز"""
    name = os.path.basename(filename or "")
    if not name.startswith(PREFIX) or not name.endswith(SUFFIX):
        raise ValueError("نام فایل Backup نامعتبر است")
    return name


def create_backup() -> dict:
    """ساخت Backup جدید (آنلاین و ایمن) — نام: trading_desk_YYYYMMDD_HHMMSS.db"""
    ensure_backup_dir()
    src = _db_path()
    if not os.path.exists(src):
        raise FileNotFoundError("فایل دیتابیس پیدا نشد")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{PREFIX}{ts}{SUFFIX}"
    dest = os.path.join(BACKUP_DIR, name)

    src_conn = sqlite3.connect(src)
    try:
        dst_conn = sqlite3.connect(dest)
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()

    st = os.stat(dest)
    return {
        "filename": name,
        "size": st.st_size,
        "created_at": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(sep=" "),
    }


def list_backups() -> list:
    """لیست Backupها (جدیدترین اول)"""
    ensure_backup_dir()
    items = []
    for fn in os.listdir(BACKUP_DIR):
        if not (fn.startswith(PREFIX) and fn.endswith(SUFFIX)):
            continue
        p = os.path.join(BACKUP_DIR, fn)
        try:
            st = os.stat(p)
        except OSError:
            continue
        items.append({
            "filename": fn,
            "size": st.st_size,
            "created_at": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(sep=" "),
        })
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items


def restore_backup(filename: str) -> dict:
    """بازیابی از یک Backup.

    مراحل ایمنی: (۱) یک Backup خودکار از وضعیت فعلی گرفته می‌شود،
    (۲) اتصال‌های SQLAlchemy بسته می‌شوند، (۳) فایل دیتابیس جایگزین می‌شود.
    """
    ensure_backup_dir()
    name = safe_name(filename)
    path = os.path.join(BACKUP_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError("فایل Backup پیدا نشد")

    db_path = _db_path()

    # ۱) Backup ایمنی از وضعیت فعلی (قبل از بازنویسی)
    safety = create_backup()

    # ۲) آزادسازی اتصال‌های engine تا فایل قفل نماند
    from ..core.database import engine
    engine.dispose()

    # ۳) جایگزینی فایل دیتابیس
    shutil.copy2(path, db_path)

    return {
        "message": "بازیابی با موفقیت انجام شد",
        "restored_from": name,
        "safety_backup": safety["filename"],
    }


def delete_backup(filename: str) -> dict:
    """حذف یک Backup"""
    ensure_backup_dir()
    name = safe_name(filename)
    path = os.path.join(BACKUP_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError("فایل Backup پیدا نشد")
    os.remove(path)
    return {"message": "Backup حذف شد", "filename": name}


def cleanup_old_backups(keep: int = 30) -> dict:
    """نگه‌داشتن فقط `keep` Backup جدید و حذف بقیه"""
    items = list_backups()
    removed = []
    for item in items[keep:]:
        try:
            os.remove(os.path.join(BACKUP_DIR, item["filename"]))
            removed.append(item["filename"])
        except OSError:
            pass
    return {"removed": removed, "removed_count": len(removed), "kept": min(len(items), keep)}


# ═════════════════════════════════════════════
# Backup خودکار
# ═════════════════════════════════════════════
def should_auto_backup() -> bool:
    """آیا با توجه به تنظیمات و آخرین Backup، الان باید Backup خودکار ساخته شود؟"""
    cfg = load_config()
    if not cfg.get("auto_enabled"):
        return False

    items = list_backups()
    if not items:
        return True

    try:
        last = datetime.fromisoformat(items[0]["created_at"])
    except ValueError:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)

    age_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600
    return age_hours >= float(cfg.get("interval_hours", 24))


def run_auto_backup() -> Optional[dict]:
    """اگر بازه سپری شده باشد، Backup می‌سازد و قدیمی‌ها را پاک می‌کند. در غیر این صورت None."""
    if not should_auto_backup():
        return None
    info = create_backup()
    cleanup_old_backups(keep=int(load_config().get("keep", 30)))
    return info

