# PHASE24_REPORT.md - فاز ۲۴: بهبود کامل Fork

## 📋 خلاصه
بهبود کامل قابلیت Fork: فیلد test_type در نسخه‌ها، مودال Fork پیشرفته، فیلتر نوع آزمون، بج‌های نمایشی، و تست end-to-end موفق.

## ✅ تغییرات انجام‌شده

### ۱. Migration
- `backend/migrations/versions/e5f6a7b8c9d0_add_test_type_to_strategy_version.py` (جدید)
- ستون `test_type` (VARCHAR, nullable) به `strategy_versions` اضافه شد.
- زنجیره اصلاح شد: `down_revision = a3f7c21b9d84` (head قبلی).
- اجرا شد: `alembic upgrade head` → `e5f6a7b8c9d0 (head)` ✅

### ۲. مدل
- `StrategyVersion.test_type = Column(String, nullable=True)`

### ۳. بک‌اند — `strategies.py`
- **`VersionCreate`**: `test_type` + `status`
- **`ForkRequest`** (جدید): `version_name`, `rules_note`, `test_type`, `status`
- **`POST /{strategy_id}/versions`**: ذخیره test_type/status
- **`POST /versions/{version_id}/fork`**: body اختیاری + پیش‌فرض هوشمند از نسخه اصلی
- **نرمال‌سازی `test_type` به lowercase** (create_version + fork_version) — رفع باگ E2E
- Responseها شامل `test_type` و `forked_from_version_id`

### ۴. فرانت‌اند
- **`client.ts`**: `forkVersion(id, data?)`, `createVersion`/`updateVersion` با test_type
- **`StrategyPage.tsx`**:
  - Version interface: `test_type`, `forked_from_version_id`
  - مودال Fork کامل (نام، نوع آزمون، وضعیت، قوانین)
  - فرم نسخه: dropdown نوع آزمون + وضعیت
  - بج نوع آزمون + نشان 🔱 Fork
  - تب‌های فیلتر (همه/بک تست/فوروارد/ریل)
  - **مقایسه case-insensitive** test_type (رفع باگ E2E)

## 🧪 تست end-to-end (Fork واقعی)

محیط: FastAPI TestClient (چرخه کامل HTTP → endpoint → DB)

| بررسی | نتیجه |
|---|---|
| Fork نسخه `SP2L_TP1` → `SP2L_TP1_FWD` | ✅ HTTP 200 |
| `forked_from_version_id` ثبت شد | ✅ = 1 |
| معاملات کپی نشدند | ✅ fork=0 / source=3 |
| `test_type` در DB ذخیره شد | ✅ = `forward` (lowercase) |
| `status` ذخیره شد | ✅ = `StrategyStatus.FORWARD` |
| `rules_note` کپی شد | ✅ از نسخه اصلی |
| Tab «فوروارد» نسخه را نشان می‌دهد | ✅ `['SP2L_TP1_FWD']` |
| بج FORWARD (🔭 فوروارد) نمایش | ✅ |
| بج Fork (🔱) نمایش | ✅ |

### 🐛 باگ کشف‌شده و رفع‌شده:
**مشکل:** API مقدار `test_type` را `FORWARD` (بزرگ) ذخیره/برمی‌گرداند، اما فرانت‌اند با `forward` (کوچک) مقایسه می‌کرد → تب فوروارد خالی بود.
**رفع:** نرمال‌سازی lowercase در بک‌اند + مقایسه `.toLowerCase()` در فرانت‌اند.

## ✅ تست‌های خودکار
- `pnpm exec tsc --noEmit` → EXIT 0
- `python -m py_compile` → EXIT 0
- `alembic heads` → تک head `e5f6a7b8c9d0`
- ستون `test_type` در DB تأیید شد

## 📁 فایل‌های تغییر یافته
- `backend/migrations/versions/e5f6a7b8c9d0_*.py` (جدید)
- `backend/app/models/strategy.py`
- `backend/app/api/strategies.py`
- `frontend/src/api/client.ts`
- `frontend/src/pages/StrategyPage.tsx`

## 📌 نکته باقی‌مانده
نسخه قدیمی `SP2L_TP1` دارای `test_type = NULL` است (داده legacy). لذا در تب «بک تست» نمایش داده نمی‌شود و فقط در تب «همه» و بج «نامشخص» دیده می‌شود. در صورت نیاز می‌توان test_type آن را به `backtest` تنظیم کرد.
