# 📥 PHASE 30 — Import Engine

> **وضعیت:** ✅ کامل (پیاده‌سازی + تست + مهاجرت + فرانت‌اند)
> **تاریخ:** ۱۴۰۵/۰۷/۰۶
> **Revision جدید:** `d4e5f6a7b8c9` (Phase 30/31)

---

## 🎯 Pipeline اجراشده

```
File ← Parse ← Normalize ← Validate ← Duplicate Detection ← Preview
     ← User Confirm ← Atomic Commit
```

| مرحله | پیاده‌سازی | محل |
|:---|:---|:---|
| **File** | سقف ۱۰MB (`read_upload_limited`) + بررسی پسوند در `/preview` و مسیرهای قدیمی | `api/import_engine.py` |
| **Parse** | همان پارسرهای فاز ۵ (`Soft4XImporter` / `MT4Importer`) + پشتیبانی **Column Mapping** | `services/import_service.py` |
| **Normalize** | زمان UTC، Symbol Mapping، جهت، اعداد، محاسبهٔ R-Multiple | `services/import_engine.py` |
| **Validate** | Trade Contract (فاز ۲۷) در دو سطح: دسته‌ای و رکوردی | `validate_contract` / `validate_trade` |
| **Duplicate Detection** | سه حالت NEW / DUPLICATE / POSSIBLE_DUPLICATE (فاز ۳۱) | `classify_duplicate` |
| **Preview** | staging ردیف‌ها در `import_batch_rows` — **هیچ معامله‌ای ساخته نمی‌شود** | `ImportEngine.create_preview` |
| **User Confirm** | `POST /api/imports/commit/{batch_id}` | `api/import_engine.py` |
| **Atomic Commit** | یک تراکنش برای همهٔ ردیف‌ها؛ خطا ⇒ rollback کامل + `status=FAILED` | `ImportEngine.commit` |

---

## 🧱 مدل‌های جدید — `backend/app/models/imports.py`

دامنهٔ جدید **IMPORT** (کاملاً جدا از FINANCE):

| مدل | جدول | نقش |
|:---|:---|:---|
| `ImportProfile` | `import_profiles` | پروفایل ایمپورت (قانون ۵) |
| `ImportBatch` | `import_batches` | سرشماری هر اجرا + وضعیت |
| `ImportBatchRow` | `import_batch_rows` | ردیف‌های staging (Preview → Commit) |
| `ImportIdentity` | `import_identities` | هویت معامله (Duplicate Detection) |

### ImportProfile — قانون ۵
```python
class ImportProfile(Base):
    __tablename__ = "import_profiles"
    id, name (unique)
    broker_id        -> brokers.id              # Broker
    source_format     Enum(ImportSourceFormat)  # SOFT4X_XLSX / MT4_HTML
    symbol_mapping    JSON                      # {"GOLD": "XAUUSD"}
    column_mapping    JSON                      # {"open_time": "Time Open", ...}
    default_context   JSON                      # {"test_type","version_id","prop_stage_id",...}
    notes, is_active, created_at
```

### ImportBatch (مطابق قرارداد فاز ۳۱ + توسعه‌های لازم)
```python
id, source, file_name, started_at, completed_at,
total, imported, duplicate, failed,
status Enum(ImportStatus) = PENDING,      # PENDING / COMMITTED / FAILED / CANCELLED
user_id
# توسعه‌های فاز ۳۰:
profile_id -> import_profiles.id
context    JSON    # اسنپ‌شات قرارداد معاملهٔ همان اجرا (test_type/version/scope/symbol)
message    Text
```

### ImportBatchRow — چرا لازم بود؟
`Preview` باید نتیجه‌اش را جایی نگه دارد تا `Confirm` نیاز به آپلود دوبارهٔ فایل نداشته باشد
و شمارنده‌های `total/imported/duplicate/failed` واقعی باشند:

```python
id, batch_id -> import_batches.id, row_number,
status Enum(ImportRowStatus),   # NEW / DUPLICATE / POSSIBLE_DUPLICATE / INVALID
message, external_ticket, identity_hash, matched_trade_id (ارجاع نرم), payload JSON
```

---

## 🔌 APIهای جدید

| متد | مسیر | کار |
|:---|:---|:---|
| `POST` | `/api/imports/preview` | آپلود + Parse + Normalize + Validate + Duplicate + **staging** |
| `POST` | `/api/imports/commit/{batch_id}` | تأیید کاربر ⇒ Commit اتمیک |
| `POST` | `/api/imports/batches/{batch_id}/cancel` | لغو Preview |
| `GET` | `/api/imports/batches` | تاریخچهٔ ایمپورت‌ها |
| `GET` | `/api/imports/batches/{batch_id}` | جزئیات + ردیف‌ها |
| `GET/POST/PATCH/DELETE` | `/api/imports/profiles[/{id}]` | CRUD پروفایل ایمپورت |

### نمونهٔ خروجی Preview
```json
{
  "batch_id": 3,
  "source": "MT4_IMPORT",
  "status": "pending",
  "total": 12, "imported": 0, "duplicate": 2, "failed": 0,
  "counts": {"new": 9, "duplicate": 1, "possible_duplicate": 1, "invalid": 0},
  "blocking": true,
  "context": {"test_type": "BACKTEST", "version_id": 4, "prop_stage_id": null, "symbol": "XAUUSD"},
  "rows": [{"row_number": 1, "status": "new", "symbol": "XAUUSD", "open_time": "...", "message": null}]
}
```

### نمونهٔ خروجی Commit
```json
{
  "batch_id": 3, "status": "committed",
  "total": 12, "imported": 9, "duplicate": 3, "failed": 0,
  "message": "9 معامله ذخیره شد — 3 ردیف تکراری نادیده گرفته شد",
  "trade_ids": [101, 102], "skipped_rows": [4, 7, 11]
}
```

### سبک‌های Commit
- `allow_possible_duplicates=false` (پیش‌فرض): ردیف مشکوک به تکرار ⇒ **۴۰۹** و هیچ تغییری در داده‌ها.
- `allow_possible_duplicates=true`: ردیف مشکوک هم وارد می‌شود (کاربر صریحاً تأیید کرده).
- ردیف `DUPLICATE` همیشه فقط **نادیده گرفته می‌شود** (شمارش در `duplicate`) — نه خطا.
- ردیف `INVALID` همیشه مانع Commit است (۴۰۰) و batch در وضعیت `PENDING` می‌ماند.

---

## ✅ انطباق با قوانین فاز ۳۰

| قانون | وضعیت | نحوهٔ اجرا |
|:---|:---:|:---|
| **۱. Validation بر اساس Trade Contract** | ✅ | `TradeValidator.validate_classification` ⇒ `REAL_PERSONAL` حساب شخصی اجباری، `REAL_PROP` مرحلهٔ پراپ اجباری، `BACKTEST/FORWARD` بدون آن‌ها و **`version_id` برای همه اجباری**. وجود مقصدها هم بررسی می‌شود (۴۰۴). مقدار قدیمی `real` در UI به `REAL_PROP`/`REAL_PERSONAL` نگاشت می‌شود. |
| **۲. Atomic Commit** | ✅ | همهٔ درج‌ها در یک تراکنش؛ هر خطا ⇒ `rollback` + `status=FAILED` + پیام خطا. ردیف نامعتبر مانع Commit است (Import ناقص ممنوع). |
| **۳. Preview قبل از Commit** | ✅ | ردیف‌ها فقط staging می‌شوند؛ تا `/commit` هیچ `Trade` و هیچ `ImportIdentity` ساخته نمی‌شود. |
| **۴. Import نباید FinancialAccount بسازد** | ✅ | دامنهٔ IMPORT هیچ وابستگی‌ای به `models.finance` ندارد (در تست فقط `Account` شمرده می‌شود تا ثابت شود صفر می‌ماند). |
| **۵. ImportProfile** | ✅ | مدل + CRUD + اعمال در `build_context` (اولویت: پارامتر درخواست ⟶ پیش‌فرض پروفایل). |

---

## 📂 فایل‌های تغییر یافته

| فایل | نوع | توضیح |
|:---|:---:|:---|
| `backend/app/models/imports.py` | 🆕 | ۴ مدل + ۳ Enum دامنهٔ IMPORT |
| `backend/app/services/import_engine.py` | 🆕 | موتور ایمپورت |
| `backend/app/utils/import_identity.py` | 🆕 | `compute_trade_hash`, `build_identity_hash`, `normalize_utc` |
| `backend/app/api/import_engine.py` | 🆕 | Preview/Commit/Batches/Profiles |
| `backend/migrations/versions/d4e5f6a7b8c9_phase30_import_engine.py` | 🆕 | ۴ جدول + ایندکس‌ها + Backfill هویت |
| `backend/app/api/imports.py` | ♻️ | مسیرهای قدیمی روی همان موتور (Preview خودکار + Commit اتمیک) |
| `backend/app/services/import_service.py` | ♻️ | `parse_file(column_mapping=...)` + حذف مسیر ذخیرهٔ قدیمی (تک‌مسیره‌سازی) |
| `backend/app/models/strategy.py` | ✏️ | رابطهٔ `Trade.import_identities` (cascade برای Hard Delete) |
| `backend/app/main.py`, `migrations/env.py` | ✏️ | ثبت روتر/مدل‌های جدید |
| `backend/tests/test_import_engine.py` | 🆕 | ۲۰ تست |
| `frontend/src/api/client.ts` | ✏️ | `previewImport`, `commitImport`, `cancelImportBatch`, Batches/Profiles |
| `frontend/src/pages/ImportPage.tsx` | ♻️ | جریان «پیش‌نمایش ⇒ تأیید» + جدول ردیف‌ها + تیک «مشکوک به تکرار» |

---

## 🧪 تست‌ها (۲۰ تست جدید)

```
cd backend; .\venv\Scripts\python.exe -m pytest tests/test_import_engine.py -q
....................  [100%]
```

| تست | چه‌چیزی را ثابت می‌کند |
|:---|:---|
| `test_preview_requires_version_id` | `version_id` اجباری (قانون ۱) |
| `test_preview_real_personal_requires_account` | REAL_PERSONAL ⇒ حساب شخصی اجباری |
| `test_preview_real_prop_requires_stage` | REAL_PROP ⇒ مرحلهٔ پراپ اجباری |
| `test_preview_stages_rows_without_touching_trades` | Preview هیچ معامله/هویتی نمی‌سازد (قانون ۳) |
| `test_commit_imports_trades_and_is_idempotent` | Import + ImportIdentity + اجرای دوباره بدون تکرار |
| `test_invalid_row_blocks_whole_import` | Atomic (قانون ۲) |
| `test_commit_rollback_marks_batch_failed` | rollback کامل + `FAILED` در خطای غیرمنتظره |
| `test_import_never_creates_financial_account` | قانون ۴ + به‌روزرسانی سود مرحلهٔ پراپ |
| `test_profile_crud_and_default_context` | پروفایل با Column Mapping/Symbol Mapping/Default Context |
| `test_legacy_*` | مسیرهای قدیمی هم روی همان موتور و همان Batch/Identity کار می‌کنند |

---

## 🗄️ مهاجرت `d4e5f6a7b8c9_phase30_import_engine`

- ساخت `import_profiles` / `import_batches` / `import_batch_rows` / `import_identities`
  (+ همهٔ ایندکس‌ها؛ `identity_hash` با ایندکس **unique**)
- **Backfill**: برای همهٔ معاملات موجود (شامل Soft-Deleted) یک `ImportIdentity` ساخته می‌شود
  تا re-import فایل قدیمی هم تکراری تشخیص داده شود. هویت‌های تکراری داده‌ی قدیمی skip می‌شوند
  تا ایندکس یکتا نشکند.
- منطق هویت به‌صورت کپیِ تثبیت‌شده داخل همان فایل migration است (Migration نباید به کد اپ وابسته باشد).

**اعتبارسنجی انجام‌شده روی دیتابیس موقت:**
```
STEP1 head(pre-phase30) OK
STEP2 seed trades OK (1 normal + 1 soft-deleted)
[phase30] backfilled import_identities: 2 rows
STEP3 upgrade head OK            → revision: d4e5f6a7b8c9
STEP4 backfill hash == engine hash OK
STEP5 downgrade OK
MIGRATION VALIDATION: PASSED
```

---

## 🛠️ رفع یک مشکل از قبل موجود در دیتابیس محلی

`backend/trading_desk.db` مقدار `alembic_version = a2b3c4d5e6f7` داشت؛ این revision
در کامیت `56d9cfc` (فاز ۲۶-۲۸) **حذف** شده و دیگر در `migrations/versions` وجود ندارد.
نتیجه: `alembic current/upgrade` خطای «Can't locate revision identified by 'a2b3c4d5e6f7'»
می‌داد و مهاجرت خودکار در `startup` هیچ‌وقت اجرا نمی‌شد ⇒ جداول فاز ۳۰ ساخته نمی‌شدند.

اقدام انجام‌شده (دیتابیس **خالی** بود — همهٔ جداول ۰ رکورد):
1. Backup سازگار: `backend/trading_desk.db.bak_phase30_pre` (با SQLite backup API)
2. فایل کهنه کنار گذاشته شد: `backend/trading_desk.db.stale_phase26`
3. ساخت دیتابیس تازه با `alembic upgrade head` ⇒ revision: **d4e5f6a7b8c9** و ۲۸ جدول

> ⚠️ اگر می‌خواهید دیتابیس کهنه را بازگردانید: فایل `.stale_phase26` را به `trading_desk.db`
> تغییر نام دهید (و برای ساخت جداول فاز ۳۰ روی آن، ابتدا `alembic stamp c3d4e5f6a7b8` و
> سپس `alembic upgrade head` را اجرا کنید).

---

## 📝 نکات و تصمیم‌های طراحی

1. **`ImportBatch.source`** نام enum منبع است (`SOFT4X_IMPORT` / `MT4_IMPORT`) — هم‌نام با
   `Trade.source` و `ImportIdentity.source` تا فیلترها یکسان بمانند؛ قالب فایل در
   `context.source_format` نگه داشته می‌شود.
2. **`ImportBatch.duplicate`** مجموع «تکراری + مشکوک به تکرار» است؛ تفکیک دقیق در
   `GET /batches/{id}` با `counts` ارائه می‌شود.
3. **مسیرهای قدیمی** (`/soft4x` و `/mt4`) عمداً `allow_possible_duplicates=True` می‌فرستند
   تا رفتار قبلی (و تست‌های regression موجود) نشکند؛ مسیر جدید `preview/commit` سخت‌گیرانه است.
4. **`column_mapping`** الان به پارسر Soft4X اعمال می‌شود (نام هدر یا شمارهٔ ستون صفر-مبنا).
   برای MT4 ستون‌ها موقعیتی‌اند و نگاشت لازم نیست (شمارهٔ سفارش از `raw_data.position` برداشته می‌شود).
5. **`FAILED` در Preview رخ نمی‌دهد**؛ Preview همیشه `PENDING` می‌سازد. `FAILED` فقط
   نتیجهٔ خطای غیرمنتظره در Commit است.


