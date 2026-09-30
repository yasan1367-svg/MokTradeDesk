# PHASE 42 — Data Infrastructure — گزارش پیاده‌سازی

> هدف فاز: **جلوگیری از از دست دادن DB**.
> مبنا: آنالیز خارجی باگ #۷ (مسیر DB نسبی · Migration خطاخور · Backup هر startup ·
> FK خاموش · بدون WAL).
> وضعیت: ✅ همهٔ تسک‌ها انجام شد · **۲۷۲ تست سبز** · commit **زده نشده** (منتظر تأیید).

---

## ۱) خلاصهٔ اجرایی

| # | مشکل (باگ #۷) | وضعیت | راه‌حل |
|---|---|---|---|
| ۴۲.۱ | مسیر DB نسبی (`sqlite:///./trading_desk.db`) و وابسته به CWD | ✅ رفع | مسیر مطلق از روی `__file__` در `config.py` |
| ۴۲.۲ | FK خاموش · بدون WAL · قفل‌شکنی فوری | ✅ رفع | PRAGMA روی هر اتصال (`foreign_keys=ON` · `journal_mode=WAL` · `busy_timeout=5000`) |
| ۴۲.۳ | خطای migration فقط log می‌شد | ✅ رفع | `raise` ⇒ برنامه روی schema قدیمی بالا نمی‌آید |
| ۴۲.۴ | Backup **بعد** از migration | ✅ رفع | Snapshot `premigrate_*` **قبل از** `upgrade` |
| ۴۲.۵ | Backup در **هر** startup | ✅ رفع | `should_backup(interval_hours)` — فقط اگر آخرین Backup قدیمی‌تر از بازه باشد |
| ۴۲.۶ | Retention خطی (`keep=30`) | ✅ رفع | Rotation طبقه‌ای: ساعتی/روزانه/هفتگی + حفظ دائمی `premigrate_*` |
| ۴۲.۷ | Restore بدون بررسی سلامت | ✅ رفع | `integrity_check` + حذف `-wal`/`-shm` + پیام ری‌استارت |

**پایهٔ اولیه:** از ۲۵۰ تست (Phase 41) به **۲۷۲ تست** رسید (۲۲ تست جدید فاز ۴۲).

---

## ۲) تسک‌ها

### ۴۲.۰ — بکاپ اولیه ✅
- `C:\Backup\trading_desk.db.before_phase42` (۴۱۳٬۶۹۶ بایت).
- در زمان بکاپ هیچ فایل `-wal`/`-shm` وجود نداشت (DB هنوز در WAL نبود).

### ۴۲.۱ — مسیر DB مطلق ✅
فایل: `backend/app/core/config.py`
```python
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BACKEND_DIR / "trading_desk.db"
DATABASE_URL: str = f"sqlite:///{DB_PATH.as_posix()}"
```
- اجرا از `C:\` همان مسیر `C:/MokTradeDesk/backend/trading_desk.db` را می‌دهد (تأیید شد).
- متغیر محیطی `DATABASE_URL` (مثل conftest) همچنان اولویت دارد ⇒ تست‌ها DB واقعی را لمس نمی‌کنند.
- تست: `tests/test_phase42_config.py` (۴ تست).

### ۴۲.۲ — PRAGMAها ✅
فایل: `backend/app/core/database.py`
```python
def _apply_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()

event.listen(engine, "connect", _apply_sqlite_pragmas)
```
- تابع `enable_sqlite_pragmas(engine)` برای engineهای موقت/تستی استخراج شد.
- تست: `tests/test_phase42_pragmas.py` (FK=1 · WAL · busy_timeout=5000).

### ۴۲.۳ — خطای migration = توقف ✅
فایل: `backend/app/main.py`
```python
except Exception:
    logger.exception("❌ migration failed — startup aborted")
    raise
```
- تست: `test_startup_raises_on_migration_failure` (monkeypatch روی `alembic.command.upgrade`).

### ۴۲.۴ — Backup قبل از migration ✅
فایل: `backend/app/main.py`
- تابع کمکی `_needs_migration(alembic_cfg, db_url)` (revision فعلی ≠ head).
- اگر migration جدید باشد: `svc.create_backup(prefix="premigrate_")` **قبل از** `upgrade`.
- نام فایل: `trading_desk_premigrate_YYYYMMDD_HHMMSS.db`.

### ۴۲.۵ — Backup هوشمند ✅
فایل: `backend/app/services/backup_service.py`
- `should_backup(interval_hours=24)`: اگر سن آخرین Backup **غیر-premigrate** کمتر از بازه باشد ⇒ `False`.
- `should_auto_backup()` روی همان بنا شده + چک `auto_enabled`.
- `startup` فقط وقتی Backup می‌سازد که بازه سپری شده باشد.

### ۴۲.۶ — Rotation طبقه‌ای ✅
فایل: `backend/app/services/backup_service.py`
- `cleanup_old_backups(keep=None)`:
  - `age < 24h` → یک Backup در هر **ساعت**
  - `24h ≤ age < 7d` → یک Backup در هر **روز**
  - `7d ≤ age < 28d` → یک Backup در هر **هفته**
  - `age ≥ 28d` → حذف
  - `premigrate_*` هرگز خودکار حذف نمی‌شود
- سازگاری عقب‌رو: اگر `keep` صریح داده شود، رفتار قدیمی (نگه‌داشتن `keep` مورد آخر) اعمال می‌شود.

### ۴۲.۷ — restore ایمن ✅
فایل: `backend/app/services/backup_service.py`
- `verify_backup(path)` با `PRAGMA integrity_check` (مقدار `ok`).
- در `restore_backup`: ابتدا بررسی سلامت → Backup ایمنی → `engine.dispose()` →
  حذف `-wal`/`-shm` → جایگزینی فایل.
- خروجی شامل `restart_required: True` و پیام «بازیابی با موفقیت انجام شد — برنامه را ری‌استارت کن».

### ۴۲.۸ — تست با FK روشن ✅
- `conftest.py` اکنون PRAGMAها را روی engine تستی هم اعمال می‌کند (`enable_sqlite_pragmas`).
- اجرا: `venv\Scripts\python.exe -m pytest -q -p no:warnings` → **۲۷۲ passed**.
- **نتیجهٔ اول (با FK روشن):** ۲ تست fail شد که دو مسئلهٔ واقعی را آشکار کرد:

| تست | خطا | تحلیل | رفع |
|---|---|---|---|
| `test_profile_crud_and_default_context` | `IntegrityError: FOREIGN KEY constraint failed` روی `DELETE FROM import_profiles` | **باگ واقعی:** حذف پروفایل وقتی `import_batches.profile_id` به آن ارجاع داشت شکست می‌خورد (FK خاموش این را مخفی کرده بود) | در `delete_import_profile`، ارجاع `ImportBatch.profile_id` ابتدا `NULL` می‌شود (تاریخچهٔ ایمپورت حفظ می‌گردد) |
| `test_analysis_result_allows_same_key_across_scopes` | `IntegrityError` روی `INSERT INTO analysis_results (... prop_stage_id=1)` | **دادهٔ تست ناسازگار:** تست `prop_stage_id=1` جعلی می‌ساخت بدون رکورد `PropStage` | تست اصلاح شد تا یک `PropStage` واقعی بسازد |

- پس از رفع: **۲۷۲ passed** · `ruff check app tests` → **All checks passed**.

### ۴۲.۹ — README / CHECKLIST ✅
- `README.md`: افزودن بخش «ایمنی داده (فاز ۴۲)» + به‌روزرسانی وضعیت به فاز ۲۵–۴۲ و شمار تست‌ها
  (۲۴۵ → ۲۷۲) + توضیح واقعی WAL و مسیر مطلق.
- `CHECKLIST.md`: افزودن دستور **کپی ماهانه به دیسک/Drive دیگر** + هشدار WAL
  (در حالت اجرا فقط `.db` را کپی نکن).

---

## ۳) تست‌ها

| فایل | تعداد | پوشش |
|---|---|---|
| `tests/test_phase42_config.py` | ۴ | مطلق بودن مسیر · قرارگیری در backend · URL مطلق |
| `tests/test_phase42_pragmas.py` | ۳ | `foreign_keys` · `journal_mode=WAL` · `busy_timeout` |
| `tests/test_phase42_backup.py` | ۱۵ | نام‌گذاری premigrate · should_backup · Rotation طبقه‌ای · integrity_check · restore · توقف startup |
| **جمع جدید** | **۲۲** | |
| **کل مجموعه** | **۲۷۲ passed** | در ۱۳ ثانیه |

---

## ۴) فایل‌های تغییر‌یافته

**کد:**
- `backend/app/core/config.py`
- `backend/app/core/database.py`
- `backend/app/main.py`
- `backend/app/services/backup_service.py`
- `backend/app/api/import_engine.py` (رفع باگ FK در حذف پروفایل)

**تست:**
- `backend/tests/conftest.py`
- `backend/tests/test_analysis_scope.py`
- `backend/tests/test_phase42_config.py` (جدید)
- `backend/tests/test_phase42_pragmas.py` (جدید)
- `backend/tests/test_phase42_backup.py` (جدید)

**مستندات:**
- `README.md` · `CHECKLIST.md` · `PHASE42_IMPL_REPORT.md`

---

## ۵) یافته‌های باقی‌مانده (برای فازهای بعد)

- **`import_batches.profile_id` بدون `ondelete`:** رفع فعلی در سطح endpoint است. برای
  استحکام کامل (حذف مستقیم SQL) بهتر است `ON DELETE SET NULL` + migration اضافه شود.
- **`test_migrations.py` هنوز assert ندارد:** در فاز ۴۱ قرار بود در ۴۲ فعال شود؛ در
  این فاز انجام نشد (مستقل از اهداف Data Infrastructure). پیشنهاد برای فاز ۴۳.
- **`Settings.Config.env_file = ".env"` نسبی است** (وابسته به CWD). مسیر DB اکنون مطلق
  است، ولی خواندن `.env` همچنان از CWD است — کاندید بهبود در فاز بعد.

---

## ۶) آماده برای Phase 43

- DB مسیر مطلق و WAL فعال ⇒ امن در برابر خطای CWD و crash.
- خطای migration برنامه را متوقف می‌کند و Snapshot پیش از تغییر گرفته می‌شود.
- Rotation خودکار حجم Backup را کنترل می‌کند؛ `premigrate_*` حفظ می‌شود.
- ۲۷۲ تست سبز با FK روشن ⇒ سازگاری کد/داده با قیدهای خارجی تأیید شد.

## ۷) گام Git

```
git status           → 9 فایل تغییر‌یافته + 3 فایل تست جدید + PHASE42_IMPL_REPORT.md
git diff --stat      → 9 files changed, 340 insertions(+), 69 deletions(-)
git log --oneline -3 → 902a389 (HEAD) Phase 41 ...
```

⛔ **commit زده نشده — منتظر تأیید کاربر.**

