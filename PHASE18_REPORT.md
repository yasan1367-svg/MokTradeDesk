# 📋 گزارش فاز ۱۸ — محافظت خودکار دیتابیس (Auto-Migrate)

> **تاریخ:** ۱۴۰۵/۰۷/۰۳ (2026-09-25) · **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ کامل — ✅ اجرای هر دو گزینه (start.cmd + main.py) · ✅ startup واقعی تست شد · ✅ endpointها ۲۰۰

**فایل‌های تغییر‌یافته:**
- `start.cmd` — افزودن مرحلهٔ `[0/3] Running database migrations...`
- `backend/app/main.py` — افزودن Migration درون‌برنامه‌ای در `startup()`
- `backend/migrations/env.py` — `disable_existing_loggers=False` (حفظ لاگر برنامه هنگام Migration درون‌برنامه‌ای)
- **جدید:** `PHASE18_REPORT.md`

---

## ۱. بررسی وضعیت قبل (ریشهٔ مشکل)

| مورد | یافته |
|---|---|
| فایل `backend/trading_desk.db` | ❌ وجود داشت اما **۰ بایت (خالی)** |
| جداول دیتابیس | ❌ **صفر جدول** |
| `alembic current` | ❌ خالی (هیچ نسخه‌ای اعمال نشده) |
| `GET /api/analytics/dashboard` | ❌ **۵۰۰** |
| `main.py:88` → `startup()` | ❌ فقط لاگ می‌کرد؛ **هیچ Migration/create_all اجرا نمی‌کرد** (همان `BE-14` در `COMPREHENSIVE_REVIEW.md`) |

⇒ اگر فایل DB حذف/خالی شود، هیچ‌جا جداول بازسازی نمی‌شوند و داشبورد ۵۰۰ می‌دهد.

---

## ۲. تغییرات

### ۲.۱ `start.cmd` (گزینهٔ ۱ — ساده)

مرحلهٔ صفر **قبل از** بالا آمدن سرور اضافه شد:

```batch
echo [0/3] Running database migrations...
pushd "%~dp0backend"
if exist "venv\Scripts\alembic.exe" (
    venv\Scripts\alembic.exe upgrade head
    if errorlevel 1 (
        echo [WARN] Migration reported an error - see output above.
    ) else (
        echo [OK] Database migrations are up to date.
    )
) else (
    echo [WARN] venv\Scripts\alembic.exe not found - skipping migration.
)
popd
```

- از `pushd/popd` استفاده شد تا **محیط خود Launcher تغییر نکند** و DLL مسیرها درست بمانند.
- از `alembic.exe` مستقیم استفاده شد (بدون `activate`) تا side-effect روی محیط Launcher نداشته باشد.
- بررسی وجود فایل + مدیریت خطا (`errorlevel`) تا اجرای Launcher قطع نشود.

### ۲.۲ `backend/app/main.py` (گزینهٔ ۲ — حرفه‌ای)

در `startup()` و **قبل از** Backup، Migration اجرا می‌شود:

```python
# ── فاز ۱۸: اطمینان از ساخت/به‌روزرسانی جداول دیتابیس ──
try:
    from alembic.config import Config as AlembicConfig
    from alembic import command as alembic_command
    from .core.config import settings

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_cfg = AlembicConfig(os.path.join(base_dir, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    try:
        alembic_command.upgrade(alembic_cfg, "head")
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)

    logger.info("✅ Database migrations applied")
except Exception:
    logger.exception("migration check failed")
```

**نکات پیاده‌سازی:**
- مسیر `alembic.ini` و `migrations/` **مطلق** محاسبه می‌شود (مستقل از CWD).
- URL از `settings.DATABASE_URL` گرفته می‌شود (هماهنگ با `.env`).
- Migration **قبل از Backup** اجرا می‌شود تا Backup روی DB سالم گرفته شود (قبلاً روی DB خالی خطا می‌داد).
- خطا فقط Exception-log می‌شود ⇒ اگر Migration مشکل داشت، برنامه باز هم بالا می‌آید.

### ۲.۳ `backend/migrations/env.py` (لازم برای گزینهٔ ۲)

```python
fileConfig(config.config_file_name, disable_existing_loggers=False)
```

**چرا لازم بود؟** `env.py` هنگام اجرا با `fileConfig` تنظیمات لاگ را بازنویسی می‌کند. به‌صورت پیش‌فرض (`disable_existing_loggers=True`) لاگر `moktrade` **غیرفعال** می‌شد و هندلر فایل از root حذف می‌شد ⇒ لاگ برنامه قطع می‌شد. با این تغییر + ذخیره/بازگردانی هندلرها در `main.py`، لاگ سالم ماند.

---

## ۳. اعتبارسنجی

| مورد | نتیجه |
|---|---|
| `python -m py_compile app/main.py migrations/env.py` | ✅ `PY_COMPILE OK` |
| `from app.main import app` | ✅ `IMPORT OK` |
| **تست Migration روی DB خالی** (DB موقت `_phase18_test.db`) | ✅ **۲۲ جدول** ساخته شد · نسخه = `9f1a2b3c4d5e (head)` |
| فایل DB اصلی | ✅ ۲۲۹٬۳۷۶ بایت · ۲۲ جدول · `categories` = ۱۳ |
| startup واقعی (uvicorn) | ✅ لاگ **`✅ Database migrations applied`** سپس `💾 initial backup created` |
| لاگ درخواست‌ها پس از Migration | ✅ هنوز در `logs/app.log` ثبت می‌شود (restore لاگ موفق) |
| `GET /` | ✅ ۲۰۰ |
| `GET /api/analytics/dashboard` | ✅ **۲۰۰** |
| `GET /api/finance/categories` | ✅ ۲۰۰ |
| `GET /api/finance/summary` | ✅ ۲۰۰ |
| `start.cmd` (بازبینی منطق) | ✅ مرحلهٔ `[0/3]` قبل از `[1/3]` · `pushd/popd` متوازن · مدیریت خطا دارد |

---

## ۴. یادداشت‌ها و محدودیت‌ها

- **دو لایهٔ محافظ:** `start.cmd` (برای اجرای دستی Launcher) + `main.py` (برای هر روش اجرای سرور). اگر سرور بدون `start.cmd` هم اجرا شود (مثلاً IDE)، لایهٔ دوم DB را می‌سازد.
- **بدون وابستگی جدید:** `alembic` از قبل در `requirements.txt` و venv نصب است.
- **مدل و Auto-approve** تنظیمات کلاینت/ابزار هستند، نه کدبیس؛ قابل تغییر از داخل کد نیستند.
- **پیشنهاد آینده (خارج از دامنهٔ این فاز):** افزودن `seed` خودکار برای دسته‌بندی‌های `finance` هنگام راه‌اندازی (فعلاً دستی: `POST /api/finance/seed`).

*گزارش فاز ۱۸ — تهیه‌شده در ۱۴۰۵/۰۷/۰۳.*
