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
import zipfile
from datetime import datetime, timezone
from typing import Optional

from ..core.config import settings

# مسیر پوشهٔ Backup: backend/backups/
BACKUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backups"))
CONFIG_PATH = os.path.join(BACKUP_DIR, ".backup_config.json")
PREFIX = "trading_desk_"
PREMIGRATE_PREFIX = "premigrate_"
SUFFIX = ".db"

# فاز ۵۳.۶.۴ — Backup کامل (DB + تصاویر)
ARCHIVE_SUFFIX = ".zip"
STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage"))
SCREENSHOTS_DIR = os.path.join(STORAGE_DIR, "screenshots")

DEFAULT_CONFIG = {
    "auto_enabled": True,
    "interval_hours": 24,
    "keep": 30,
}


def is_premigrate(name: str) -> bool:
    """آیا این Backup پیش از migration است؟ (هرگز خودکار حذف نمی‌شود)"""
    return os.path.basename(name).startswith(f"{PREFIX}{PREMIGRATE_PREFIX}")



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


def create_backup(prefix: str = "") -> dict:
    """ساخت Backup جدید (آنلاین و ایمن) — نام: trading_desk_[<prefix>]YYYYMMDD_HHMMSS.db

    ``prefix`` برای Backupهای خاص مثل ``premigrate_`` استفاده می‌شود.
    """
    ensure_backup_dir()
    src = _db_path()
    if not os.path.exists(src):
        raise FileNotFoundError("فایل دیتابیس پیدا نشد")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{PREFIX}{prefix}{ts}"
    dest = os.path.join(BACKUP_DIR, f"{base}{SUFFIX}")
    # جلوگیری از بازنویسی Backup قبلی در همان ثانیه
    counter = 1
    while os.path.exists(dest):
        dest = os.path.join(BACKUP_DIR, f"{base}_{counter}{SUFFIX}")
        counter += 1

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
        "filename": os.path.basename(dest),
        "size": st.st_size,
        "created_at": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(sep=" "),
    }


def verify_backup(path: str, filename: str = "") -> bool:
    """بررسی سلامت فایل Backup با ``PRAGMA integrity_check``.

    فایل باید SQLite معتبر باشد و integrity_check مقدار ``ok`` برگرداند.
    """
    if not os.path.exists(path):
        return False
    conn = None
    try:
        conn = sqlite3.connect(path)
        row = conn.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.Error:
        return False
    finally:
        if conn is not None:
            conn.close()
    return bool(row) and str(row[0]).strip().lower() == "ok"



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

    مراحل ایمنی:
    (۰) ``PRAGMA integrity_check`` روی فایل Backup — در صورت خرابی ValueError.
    (۱) یک Backup خودکار از وضعیت فعلی گرفته می‌شود.
    (۲) اتصال‌های SQLAlchemy بسته می‌شوند (``engine.dispose()``).
    (۳) فایل‌های جانبی ``-wal``/``-shm`` حذف می‌شوند تا فایل جایگزین معتبر بماند.
    (۴) فایل دیتابیس جایگزین می‌شود.
    """
    ensure_backup_dir()
    name = safe_name(filename)
    path = os.path.join(BACKUP_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError("فایل Backup پیدا نشد")

    # ۰) بررسی سلامت فایل Backup پیش از هر تغییری
    if not verify_backup(path, name):
        raise ValueError("فایل Backup سالم نیست (integrity_check ناموفق)")

    db_path = _db_path()

    # ۱) Backup ایمنی از وضعیت فعلی (قبل از بازنویسی)
    safety = create_backup()

    # ۲) آزادسازی اتصال‌های engine تا فایل قفل نماند
    from ..core.database import engine
    engine.dispose()

    # ۳) حذف فایل‌های جانبی WAL/SHM نسخهٔ فعلی
    for side_suffix in ("-wal", "-shm"):
        side = db_path + side_suffix
        if os.path.exists(side):
            try:
                os.remove(side)
            except OSError:
                pass

    # ۴) جایگزینی فایل دیتابیس
    shutil.copy2(path, db_path)

    return {
        "message": "بازیابی با موفقیت انجام شد — برنامه را ری‌استارت کن",
        "restored_from": name,
        "safety_backup": safety["filename"],
        "restart_required": True,
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


def cleanup_old_backups(keep: Optional[int] = None) -> dict:
    """Rotation طبقه‌بندی‌شدهٔ Backupها (فاز ۴۲.۶).

    - ۲۴ ساعت آخر  → یک Backup در هر ساعت (ساعتی)
    - ۱ تا ۷ روز   → یک Backup در هر روز (روزانه)
    - ۷ تا ۲۸ روز  → یک Backup در هر هفته (هفتگی)
    - قدیمی‌تر از ۲۸ روز → حذف
    - ``premigrate_*`` هرگز خودکار حذف نمی‌شود

    اگر ``keep`` به‌صراحت داده شود، رفتار قدیمی (نگه‌داشتن فقط ``keep`` مورد
    جدید) برای سازگاری عقب‌رو اعمال می‌شود.
    """
    ensure_backup_dir()

    if keep is not None:
        # رفتار قدیمی (سازگاری عقب‌رو): نگه‌داشتن فقط `keep` مورد جدید
        items = list_backups()
        removed = []
        for item in items[keep:]:
            if is_premigrate(item["filename"]):
                continue
            try:
                os.remove(os.path.join(BACKUP_DIR, item["filename"]))
                removed.append(item["filename"])
            except OSError:
                pass
        return {"removed": removed, "removed_count": len(removed), "kept": min(len(items), keep)}

    now = datetime.now(timezone.utc)
    seen_buckets = set()
    removed = []
    kept = 0

    for item in list_backups():  # جدیدترین اول
        name = item["filename"]
        if is_premigrate(name):
            kept += 1
            continue

        try:
            created = datetime.fromisoformat(item["created_at"])
        except ValueError:
            kept += 1
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        age = (now - created).total_seconds()
        if age < 86400:  # ۲۴ ساعت
            key = ("hour", created.strftime("%Y%m%d%H"))
        elif age < 7 * 86400:  # ۷ روز
            key = ("day", created.strftime("%Y%m%d"))
        elif age < 28 * 86400:  # ۴ هفته
            key = ("week", created.strftime("%Y%W"))
        else:
            key = None  # خیلی قدیمی → حذف

        if key is not None and key not in seen_buckets:
            seen_buckets.add(key)
            kept += 1
            continue

        try:
            os.remove(os.path.join(BACKUP_DIR, name))
            removed.append(name)
        except OSError:
            kept += 1

    return {"removed": removed, "removed_count": len(removed), "kept": kept}



# ═════════════════════════════════════════════
# Backup خودکار
# ═════════════════════════════════════════════
def _last_backup_age_hours() -> Optional[float]:
    """سن آخرین Backup غیر-premigrate به ساعت (None اگر Backupی نباشد)."""
    items = [i for i in list_backups() if not is_premigrate(i["filename"])]
    if not items:
        return None
    try:
        last = datetime.fromisoformat(items[0]["created_at"])
    except ValueError:
        return None
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last).total_seconds() / 3600


def should_backup(interval_hours: Optional[float] = None) -> bool:
    """آیا با توجه به سن آخرین Backup باید Backup جدید ساخته شود؟ (فاز ۴۲.۵)

    اگر آخرین Backup کمتر از ``interval_hours`` ساعت پیش ساخته شده باشد → False.
    اگر هیچ Backupی وجود نداشته باشد → True.
    """
    if interval_hours is None:
        interval_hours = float(load_config().get("interval_hours", 24))
    age = _last_backup_age_hours()
    if age is None:
        return True
    return age >= float(interval_hours)


def should_auto_backup() -> bool:
    """آیا با توجه به تنظیمات و آخرین Backup، الان باید Backup خودکار ساخته شود؟"""
    cfg = load_config()
    if not cfg.get("auto_enabled"):
        return False
    return should_backup(float(cfg.get("interval_hours", 24)))


def run_auto_backup() -> Optional[dict]:
    """اگر بازه سپری شده باشد، Backup می‌سازد و Rotation طبقه‌بندی‌شده اعمال می‌کند."""
    if not should_auto_backup():
        return None
    info = create_backup()
    cleanup_old_backups()
    return info


# ═════════════════════════════════════════════
# فاز ۵۳.۶.۴ — Backup کامل (DB + تصاویر) در یک فایل zip
# ═════════════════════════════════════════════
def safe_archive_name(filename: str) -> str:
    """اعتبارسنجی نام فایل zip (جلوگیری از Path Traversal)."""
    name = os.path.basename(filename or "")
    if not name.startswith(PREFIX) or not name.endswith(ARCHIVE_SUFFIX):
        raise ValueError("نام فایل Backup نامعتبر است")
    return name


def create_backup_archive(prefix: str = "") -> dict:
    """ساخت Backup کامل: دیتابیس + پوشهٔ screenshots در یک فایل ``.zip``.

    سازگاری: یک نسخهٔ خام ``.db`` هم ساخته می‌شود (خارجی و قابل بازیابی با
    مسیر موجود)؛ نام آن در ``db_filename`` برگردانده می‌شود.
    """
    ensure_backup_dir()
    info = create_backup(prefix=prefix)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{PREFIX}{prefix}{ts}"
    archive_path = os.path.join(BACKUP_DIR, f"{base}{ARCHIVE_SUFFIX}")
    counter = 1
    while os.path.exists(archive_path):
        archive_path = os.path.join(BACKUP_DIR, f"{base}_{counter}{ARCHIVE_SUFFIX}")
        counter += 1

    screenshots_count = 0
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(os.path.join(BACKUP_DIR, info["filename"]), arcname=info["filename"])
        if os.path.isdir(SCREENSHOTS_DIR):
            for root, _dirs, files in os.walk(SCREENSHOTS_DIR):
                for fn in sorted(files):
                    full = os.path.join(root, fn)
                    arc = os.path.join("screenshots", os.path.relpath(full, SCREENSHOTS_DIR))
                    zf.write(full, arcname=arc.replace(os.sep, "/"))
                    screenshots_count += 1

    st = os.stat(archive_path)
    return {
        "filename": os.path.basename(archive_path),
        "db_filename": info["filename"],
        "screenshots_count": screenshots_count,
        "size": st.st_size,
        "created_at": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(sep=" "),
    }


def restore_backup_archive(filename: str) -> dict:
    """بازیابی کامل از فایل zip: ابتدا دیتابیس، سپس screenshots."""
    ensure_backup_dir()
    name = safe_archive_name(filename)
    path = os.path.join(BACKUP_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError("فایل Backup پیدا نشد")

    with zipfile.ZipFile(path) as zf:
        members = zf.namelist()
        # امنیت: هیچ مسیر خارج از مقصد مجاز نیست
        for m in members:
            if m.startswith("/") or ".." in m.replace("\\", "/").split("/"):
                raise ValueError("مسیر نامعتبر داخل فایل Backup")
        db_members = [m for m in members if os.path.basename(m).startswith(PREFIX) and m.endswith(SUFFIX)]
        if not db_members:
            raise ValueError("دیتابیس داخل فایل Backup پیدا نشد")

        db_member = db_members[0]
        zf.extract(db_member, BACKUP_DIR)
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        restored_shots = 0
        for m in members:
            if m.replace("\\", "/").startswith("screenshots/") and not m.endswith("/"):
                zf.extract(m, STORAGE_DIR)
                restored_shots += 1

    result = restore_backup(os.path.basename(db_member))
    result["restored_screenshots"] = restored_shots
    return result


