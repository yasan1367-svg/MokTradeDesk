# گزارش پاکسازی پروژه (CLEANUP_REPORT.md)

**تاریخ:** 1405/07/03 | **ابزار:** `cleanup.ps1` (PowerShell، تأیید مرحله‌ای)
**حالت:** هر مرحله جداگانه با تأیید اجرا می‌شود (`-Stage 1|2|3`، `-DryRun`، `-Yes`)

---

## ✅ مرحله ۱ — فایل‌های بی‌خطر (انجام شد)

ابتدا با **Dry Run** پیش‌نمایش گرفته شد. یک باگ بحرانی در فیلتر `-Include` (با `-LiteralPath`) کشف و رفع شد که در غیر این صورت فایل‌های واقعی سورس را حذف می‌کرد. سپس اجرای واقعی انجام شد.

### حذف‌شده‌ها (۵۶ آیتم — ≈ ۳٫۲۴ MB)

| دسته | تعداد | توضیح |
|---|---|---|
| `backend/.coverage` | ۱ | خروجی pytest-cov |
| `frontend/dist/` | ۱ | خروجی بیلد |
| `frontend/temp_build*.log` | ۲ | لاگ موقت بیلد |
| `__pycache__/` (در backend) | ۱۰ | کش پایتون |
| فایل‌های `.pre61/.pre7/.pre71/.pre8/.bak` | ۳۶ | بکاپ‌های کد در `frontend/src` |
| بکاپ‌های دیتابیس | ۳ | `trading_desk.db.backup`، `trading_desk.db.backup-20260923-090101`، `trading_desk.backup_phase9_20260925_020348.db` |
| `cmd.exe` (ریشه) | ۱ | فایل اجرایی بیگانه (بدون ارجاع در سورس) |
| `storage/` (ریشه) | ۱ | پوشه خالی |
| `launch.py` | ۱ | فایل ۰ بایتی خالی |

### نگه‌داشته‌شده
- `backend/logs/` — **خالی نبود** (شامل `app.log`) → نگه داشته شد.
- بررسی شد که همه فایل‌های سورس کلیدی (`FinancePage.tsx`، `main.tsx`، `utils/jalali.ts`، تست‌ها) و `backend/trading_desk.db` سالم مانده‌اند.

---

## ✅ مرحله ۲ — فایل‌های بزرگ (انجام شد)

با `-Yes` اجرا شد.

### حذف‌شده‌ها (۴ آیتم — ≈ ۲۳۴٫۷ MB)

| مسیر | حجم |
|---|---|
| `backend/.venv/` | 184.8 MB |
| `backend/node_modules/` | 49.9 MB |
| `backend/package.json` | 356 B |
| `backend/pnpm-lock.yaml` | 27 KB |

### وضعیت `backend/` پس از مرحله ۲
```
.git  app/  logs/  migrations/  storage/  tests/  venv/
alembic.ini  pytest.ini  requirements.txt  trading_desk.db
```
- `backend/venv/` (ضروری) ✅ سالم
- `backend/app/` و `backend/trading_desk.db` ✅ سالم

---

## ⏭️ مرحله ۳ — رد شد (به درخواست کاربر)

`backend/.git` (ریپوی تودرتوی بدون commit) **نگه داشته شد**.

**دلایل کاربر:** کم‌ریسک‌تر بودن نگه‌داشتن، حجم کم، و اولویت پایین‌تر از تست نهایی پروژه. این ریپو هیچ commit ندارد؛ در صورت نیاز بعداً می‌توان با `cleanup.ps1 -Stage 3` حذف کرد.

---

## 📄 اسکریپت `cleanup.ps1`

```powershell
# اجرای مرحله‌ای (با تأیید تعاملی)
powershell -NoProfile -ExecutionPolicy Bypass -File cleanup.ps1 -Stage 1
powershell -NoProfile -ExecutionPolicy Bypass -File cleanup.ps1 -Stage 2
powershell -NoProfile -ExecutionPolicy Bypass -File cleanup.ps1 -Stage 3

# پیش‌نمایش بدون حذف
powershell -NoProfile -ExecutionPolicy Bypass -File cleanup.ps1 -Stage all -DryRun

# تأیید خودکار (بدون پرسش)
powershell -NoProfile -ExecutionPolicy Bypass -File cleanup.ps1 -Stage 1 -Yes
```

**محافظت‌ها:** عدم حذف ریشه پروژه، محدود بودن حذف به داخل پروژه، بررسی قبل از حذف (existence/emptiness)، نگه‌داشتن `trading_desk.db`، بررسی ارجاع `cmd.exe` در سورس.

---

## 🧪 تست نهایی پروژه (پس از پاکسازی)

| بررسی | نتیجه |
|---|---|
| Backend pytest | ✅ **33 passed** |
| Frontend vitest | ✅ **9 passed** (2 files) |
| Frontend build (`npm run build`) | ✅ موفق (built in 2.68s) |

> اجرای تست‌ها و بیلد، چند آرتیفکت **قابل‌بازتولید** را دوباره ساختند:
> - `backend/**/__pycache__/` (توسط pytest)
> - `frontend/dist/` (توسط build)
>
> این‌ها بی‌خطر و در `.gitignore` هستند و در صورت تمایل با `cleanup.ps1 -Stage 1` دوباره پاک می‌شوند.

---

## 📊 جمع‌بندی نهایی

| مورد | مقدار |
|---|---|
| آزادشده در مرحله ۱ | ≈ ۳٫۲۴ MB |
| آزادشده در مرحله ۲ | ≈ ۲۳۴٫۷ MB |
| **مجموع آزادشده** | **≈ ۲۳۸ MB** |
| آیتم‌های حذف‌شده | ۶۰ (۵۶ + ۴) |
| مرحله ۳ | ⏭️ رد شد |

**نگه‌داشته‌شده (ضروری):** `backend/venv/`، `backend/trading_desk.db`، `backend/storage/screenshots/` (داده کاربر)، `backend/.git`، و کل سورس `backend/app` و `frontend/`.

**توصیه آینده:** افزودن `*.pre*` به `.gitignore` (پسوند `.pre61/.pre7/.pre71/.pre8` فعلاً در ignore نیست).

---

## وضعیت کلی
- مرحله ۱: ✅ کامل (≈ ۳٫۲۴ MB آزاد شد)
- مرحله ۲: ✅ کامل (≈ ۲۳۴٫۷ MB آزاد شد)
- مرحله ۳: ⏭️ رد شد (backend/.git نگه داشته شد)
