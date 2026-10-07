# گزارش ممیزی MokTradeDesk (نسخهٔ ۲) — پاس ۱: مهندسی (پیش‌نویس ناقص)

> وضعیت: **پیش‌نویس ناقص**. فقط یافته‌هایی ثبت شده‌اند که در این نشست با خواندن کد یا اجرای دستور دیده شده‌اند. پاس ۲ (معاملاتی) و امتیاز ۱۲ حوزه هنوز انجام نشده‌اند.
> نام `audit_report.md` به‌خاطر وجود `AUDIT_REPORT.md` (ویندوز به حروف حساس نیست) استفاده نشد.

## محیط و ایمنی اجرای تست
- VERIFIED: `backend/tests/conftest.py` پیش از import مسیر `DATABASE_URL` را به فایل موقت (`mkstemp`) می‌برد و هوک‌های startup/shutdown را پاک می‌کند. تست‌ها روی DB درون‌حافظه کار می‌کنند.
- VERIFIED: تست‌های backup (`test_phase42_backup.py`، `test_phase53_backup_settings.py`) با `monkeypatch` پوشهٔ backup و screenshots را به `tmp_path` می‌برند.
- محدودیت: شمارش فایل‌های `backend/backups` (۹ فایل) و `backend/storage` (۰ فایل) فقط **بعد از** اجرای pytest گرفته شد. شمارش «قبل از اجرا» ثبت نشده است، پس نمی‌توان ادعا کرد تست‌ها به داده‌های واقعی دست نزده‌اند. این مورد فقط از روی کد و `monkeypatch`ها استنباط می‌شود (SUSPECTED-SAFE).
- هنگام import `app.main` پوشهٔ `backend/logs` و فایل `app.log` ساخته/باز می‌شود و `storage/screenshots` ساخته می‌شود (نسبت به cwd). این عوارض جانبی هنگام تست رخ می‌دهند.
- `pytest` یک‌بار روی کل `backend/tests` اجرا شد و بار دیگر فقط روی تست‌های انتخابی. از خروجی کل فقط ۳۰ خط آخر دیده شد؛ تعداد کل passed/failed نامشخص است و ممکن است شکست‌های بیشتری وجود داشته باشند.

## نتیجهٔ اجرای تست
در ۳۰ خط آخر خروجی این شکست‌ها دیده شد (VERIFIED فقط برای وجود این موارد):
1. `test_phase36_performance.py::test_phase36_indexes_exist` — با اجرای جداگانه هم شکست خورد. ایندکس `ix_trades_is_deleted` انتظار می‌رود ولی در جدول `trades` مدل فعلی نیست. علت احتمالی (SUSPECTED): مایگریشن `61b2c3d4e5f6_hard_delete_trades` وضعیت soft-delete را حذف کرده و تست قدیمی مانده است.
2. `test_phase4_initial_sl.py` — سه تست (`test_patch_sl_does_not_change_r_when_initial_sl_exists`، `test_patch_open_price_without_initial_sl_warns`، `test_patch_open_price_with_initial_sl_no_warn`). علت بررسی نشد؛ اجرای دوباره خروجی قابل‌استفاده نداد.
3. `test_phase58_prop_migration.py::test_phase58_migration_adds_modes_and_preserves_legacy_total_mode` — در فهرست شکست‌ها است. در تریس دیده‌شده `NoSuchTableError: trades` همراه لاگ آلمبیک تا `e4f5a6b7c8d9` آمده بود، اما نام تست صاحب آن تریس در خروجی دیده نشد؛ پس نمی‌توان آن را قطعاً به این تست نسبت داد. علت: بررسی نشده.

## یافته‌ها

### E-01 — شکست Backup پیش‌مهاجرت، مایگریشن را متوقف نمی‌کند (P1، VERIFIED)
- مکان: `backend/app/main.py` (بلوک `try/except Exception` اطراف `svc.create_backup(prefix=PREMIGRATE_PREFIX)`، حدود خطوط 124–129).
- مشکل: در صورت شکست Backup فقط لاگ می‌شود و `alembic upgrade head` ادامه می‌یابد.
- راه‌حل: وقتی مایگریشن لازم است، شکست Backup باید startup را متوقف کند. تلاش: کم.

### E-02 — `restore_backup` فایل زنده را با `shutil.copy2` بازنویسی می‌کند (P2، VERIFIED)
- مکان: `backend/app/services/backup_service.py` خطوط 190–209.
- مشکل: فایل DB بدون قفل انحصاری و بدون نوشتن در فایل موقت + `os.replace` جایگزین می‌شود. اگر کپی وسط کار قطع شود، DB خراب می‌ماند. thread پس‌زمینهٔ backup هم همزمان فعال است. Backup ایمنی ساخته می‌شود که ریسک را کم می‌کند.
- راه‌حل: کپی به فایل موقت کنار DB و سپس `os.replace`. تلاش: کم.

### E-03 — `restore_backup_archive` ابتدا screenshots را بازنویسی می‌کند و بعد DB را (P2، VERIFIED)
- مکان: `backup_service.py` خطوط 418–429.
- مشکل: فایل‌های screenshots پیش از موفقیت `restore_backup` (که integrity_check دارد) استخراج می‌شوند. اگر DB سالم نباشد، تصاویر قبلاً بازنویسی شده‌اند. همچنین `zf.extract` بدون سقف حجم/تعداد است.
- راه‌حل: ابتدا DB را اعتبارسنجی و جایگزین کن، سپس تصاویر را استخراج کن. تلاش: کم.

### E-04 — خطاهای داخلی در پاسخ HTTP نمایش داده می‌شوند (P3 محلی / P2 شبکه‌ای، VERIFIED)
- مکان: `backend/app/api/backup.py` (`detail=str(e)` در `create_backup`، `create_backup_archive`، `restore_backup_archive`، `restore_backup`).
- راه‌حل: پیام عمومی در پاسخ، جزئیات فقط در لاگ. تلاش: کم.

### E-05 — مسیر screenshots به cwd وابسته است و بین ماژول‌ها یکسان نیست (P2، VERIFIED)
- مکان: `backend/app/api/trades.py` خط 29 (`SCREENSHOTS_DIR = "storage/screenshots"` نسبی)، `backend/app/main.py` خط 175 (`os.path.abspath("storage")`)، `backend/app/services/backup_service.py` خطوط 27–28 (نسبت به فایل).
- مشکل: اگر سرور از پوشه‌ای غیر از `backend/` اجرا شود، تصاویر در جای دیگری ذخیره می‌شوند و backup آن‌ها را نمی‌بیند. این ماژول‌ها هنگام import پوشه می‌سازند.
- راه‌حل: یک ثابت مطلق در `core/config.py`. تلاش: کم.

### E-06 — `/storage` بدون احراز هویت سرو می‌شود (P2، VERIFIED از کد؛ مدل تهدید: برنامهٔ محلی)
- مکان: `backend/app/main.py` خط 177 (`app.mount("/storage", StaticFiles(...))`).
- راه‌حل: نام فایل تصادفی (UUID) یا endpoint کنترل‌شده. تلاش: کم.

### E-07 — حذف فایل screenshot با `except:` خالی (P3، VERIFIED)
- مکان: `backend/app/api/personal.py` خطوط 121–125 و 175–179؛ همچنین `backend/app/api/trades.py` خطوط 865–867 (`except Exception: pass`). (مسیر مشابه در `trades.py` خط 603 درست `OSError` می‌گیرد.)
- مشکل: هر خطا بلعیده می‌شود (حتی `KeyboardInterrupt`) و ردیف DB حذف می‌شود، پس فایل یتیم می‌ماند.
- راه‌حل: `except OSError` با لاگ. تلاش: خیلی کم.

### E-08 — تست‌های مایگریشن ناقص یا قدیمی (P2، VERIFIED)
- `test_migrations_match_models` (`test_migrations.py` خطوط 48–53) فقط گزارش می‌دهد؛ `assert` غیرفعال است، پس اختلاف مدل و مایگریشن شکست نمی‌دهد.
- سه گروه تست شکست‌خوردهٔ بالا نشان می‌دهند مجموعهٔ تست با کد فعلی هم‌خوان نیست؛ پس «همه سبز» ملاک اعتماد نیست.
- راه‌حل: فعال‌کردن assert، اصلاح یا حذف تست‌های قدیمی. تلاش: متوسط.

### E-09 — ساختار مایگریشن
- VERIFIED: مسیر واقعی `backend/migrations/versions` است (۲۹ فایل). `python -m alembic heads` فقط یک head را نشان داد: `5691cf13a881`.
- ساخت از صفر تا head در `test_migrations_match_models` اجرا می‌شود (در تست‌های اجراشده خطای آن در ۳۰ خط آخر دیده نشد)، ولی نتیجهٔ تفصیلی آن را ندیدم. وضعیت: تأییدنشده.

### E-10 — `on_event` منسوخ است (P3، VERIFIED)
- اخطار FastAPI هنگام تست؛ مکان: `backend/app/main.py` (startup و خط 167 shutdown). راه‌حل: `lifespan`.

## پوشش (تا این لحظه)
- **کامل خوانده‌شده:** فهرست «Done» در خلاصهٔ قبلی (هستهٔ محاسبات، دامنهٔ ریسک، Import، config/database/conftest) + `backup_service.py`، `api/backup.py`، `utils/uploads.py`، `main.py`.
- **ناقص:** `api/trades.py` (فقط خطوط 1–330)، `test_migrations.py` (1–60)، `test_phase39_screenshot.py` (1–60)، `test_phase42_backup.py` (1–40).
- **اصلاً خوانده نشده:** parserها/`import_engine` API، `api/analytics.py`، `api/prop.py`، `api/finance.py`، `wallet_service`، `payout_service`، `export.py`، فرانت‌اند (stores/formatters/pages)، بیشتر مدل‌ها.
- **تست:** `pytest` یک‌بار روی کل `backend/tests` اجرا شد (۵ شکست دیده‌شده). تست‌های فرانت‌اند اجرا نشدند.
- **اجرانشده:** پاس ۲، تأیید دستی A1–A6، امتیاز ۱۲ حوزه، `alembic heads`.
