# 📋 گزارش فاز ۱۷ — Backup خودکار و دستی دیتابیس

> **تاریخ:** ۱۴۰۵/۰۷/۰۳ (2026-09-25) · **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ کامل — ✅ `pytest` ۳۳ پاس · ✅ `tsc` + `build` موفق · ✅ startup واقعی تست شد

**فایل‌های تغییر‌یافته:**
- **جدید:** `backend/app/services/backup_service.py` · `backend/app/api/backup.py` · `frontend/src/components/BackupManager.tsx`
- `backend/app/main.py` · `frontend/src/api/client.ts` · `frontend/src/pages/SettingsPage.tsx` · `frontend/src/pages/DashboardPage.tsx` · `.gitignore`

---

## ۱. بررسی وضعیت قبل

| مورد | یافته |
|---|---|
| سیستم Backup | ❌ **وجود نداشت** (جست‌وجوی `backup` در کل کدبیس: صفر نتیجه) |
| محل دیتابیس | `backend/trading_desk.db` (SQLite، ۶۷۱ KB) — `DATABASE_URL = sqlite:///./trading_desk.db` |
| پکیج‌های Backup | ❌ هیچ‌کدام نصب نبود (no `apscheduler` / `celery` / `schedule`) |

⇒ تصمیم: **بدون افزودن وابستگی خارجی**، با `sqlite3` + `threading` استاندارد پیاده شد.

---

## ۲. Backend

### ۲.۱ سرویس جدید `services/backup_service.py`
| تابع | توضیح |
|---|---|
| `create_backup()` | Backup **آنلاین** با `sqlite3.Connection.backup()` (ایمن حتی با DB در حال استفاده) — نام: `trading_desk_YYYYMMDD_HHMMSS.db` |
| `list_backups()` | لیست مرتب (جدیدترین اول) با نام/حجم/تاریخ |
| `restore_backup(filename)` | **Backup ایمنی خودکار** از وضعیت فعلی → `engine.dispose()` → جایگزینی فایل |
| `delete_backup(filename)` | حذف یک Backup |
| `cleanup_old_backups(keep=30)` | نگه‌داشتن فقط `keep` جدید و حذف بقیه |
| `should_auto_backup()` / `run_auto_backup()` | منطق Backup خودکار بر اساس تنظیمات و سن آخرین Backup |

- **مسیر ذخیره:** `backend/backups/` (خودکار ساخته می‌شود)
- **امنیت:** `safe_name()` جلوی Path Traversal را می‌گیرد (فقط نام پایه با پیشوند/پسوند مجاز)
- **تنظیمات** در `backend/backups/.backup_config.json` (بدون نیاز به migration دیتابیس): `auto_enabled`, `interval_hours`, `keep`

### ۲.۲ APIهای جدید (`api/backup.py` — prefix `/api/backup`)
| متد | مسیر | کار |
|---|---|---|
| `POST` | `/create` | ساخت Backup دستی |
| `GET` | `/list` | لیست Backupها |
| `GET` | `/download/{filename}` | دانلود (FileResponse) |
| `POST` | `/restore/{filename}` | بازیابی |
| `DELETE` | `/{filename}` | حذف |
| `GET`/`PUT` | `/settings` | خواندن/ذخیرهٔ تنظیمات Backup خودکار |

**تعداد مسیرهای OpenAPI: ۸۵ → ۹۱** ✅

### ۲.۳ Backup خودکار (`main.py`)
```python
@app.on_event("startup")
def startup():
    # 💾 Backup اولیه + cleanup
    svc.create_backup(); svc.cleanup_old_backups(keep=...)
    # ⏱️ راهاندازی حلقهٔ پسزمینه (thread daemon)
    _backup_thread = threading.Thread(target=_backup_loop, daemon=True)
```
- حلقه هر **۳۰ دقیقه** بررسی می‌کند و اگر `interval_hours` (پیش‌فرض ۲۴) از آخرین Backup گذشته باشد، یکی می‌سازد.
- `shutdown` با `_backup_stop.set()` thread را متوقف می‌کند.
- **بدون APScheduler/Celery** ⇒ صفر وابستگی جدید.

---

## ۳. Frontend

### ۳.۱ تب «Backup» در `SettingsPage.tsx`
- نوار تب: «⚙️ تنظیمات عمومی» / «💾 Backup» (بقیهٔ صفحه بدون تغییر)
- محتوا در کامپوننت جدید **`components/BackupManager.tsx`**:
  - دکمه **«➕ ساخت Backup جدید»**
  - **تنظیمات Backup خودکار:** چک‌باکس فعال/غیرفعال، بازهٔ زمانی (ساعت)، تعداد نگهداری
  - **جدول Backupها:** نام فایل · تاریخ **شمسی** · حجم · دکمه‌های **دانلود / بازیابی / حذف**
  - **Skeleton** هنگام بارگذاری · **EmptyState** برای حالت خالی · **Toast** برای پیام‌ها
  - **ConfirmDialog** برای «بازیابی» (خطرناک) و «حذف»
  - کاملاً Dark Mode (توکن‌های `var(--*)`) و RTL

### ۳.۲ کارت داشبورد (اختیاری)
کارت **«💾 آخرین Backup»** با نمایش نام/تاریخ شمسی/حجم + دکمهٔ «➕ ساخت Backup» و لینک «مدیریت →» (به Settings).

### ۳.۳ `client.ts`
۷ تابع جدید: `createBackup` · `listBackups` · `downloadBackup` · `restoreBackup` · `deleteBackup` · `getBackupSettings` · `updateBackupSettings`

### ۳.۴ `.gitignore`
`backend/backups/` اضافه شد تا فایل‌های Backup در git ثبت نشوند.

---

## ۴. تست

| مورد | نتیجه |
|---|---|
| `py_compile` (main.py, backup.py, backup_service.py) | ✅ `0` |
| `app.openapi()` | ✅ **۹۱ مسیر** (۶ مسیر backup) |
| `POST /api/backup/create` | ✅ `200` + فایل ساخته شد (۶۷۱٬۷۴۴ بایت) |
| `GET /api/backup/list` | ✅ `200` |
| `GET /api/backup/download/{f}` | ✅ `200` + ۶۷۱٬۷۴۴ بایت + Content-Disposition درست |
| `GET`/`PUT /api/backup/settings` | ✅ `200` |
| `POST /api/backup/restore/{f}` | ✅ `200` · **Backup ایمنی ساخته شد** · تعداد trades قبل/بعد: **۱۸ = ۱۸** |
| `DELETE /api/backup/{f}` | ✅ `200` |
| محافظت Path Traversal (`../`) | ✅ مسدود |
| نام نامعتبر (`*.bak`) | ✅ `400` · فایل ناموجود ✅ `404` |
| `cleanup_old_backups(keep=3)` | ✅ ۱۳ → ۳ |
| **startup واقعی (uvicorn)** | ✅ «💾 initial backup created» + «⏱️ auto-backup loop started» |
| `pytest -q` | ✅ **۳۳ passed** |
| `npx tsc -b --force` | ✅ `TSC_EXIT=0` |
| `npm run build` | ✅ `BUILD_EXIT=0` · entry = 241.34 kB |

### 📌 یادداشت‌ها
- **بدون وابستگی جدید:** از `sqlite3` + `threading` استاندارد استفاده شد (نیازی به APScheduler/Celery نبود).
- **بازیابی ایمن:** قبل از هر restore یک Backup خودکار گرفته می‌شود و اتصال‌های engine آزاد می‌شوند.
- **تست چشمی مرورگر در محیط headless ممکن نبود** — اعتبارسنجی با `tsc` + `build` + تست کامل API + startup واقعی.
- فایل‌های Backup تولیدشده در تست‌ها به ۳ نسخهٔ آخر کاهش یافتند.

*گزارش فاز ۱۷ — تهیه‌شده در ۱۴۰۵/۰۷/۰۳.*
