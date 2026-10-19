# 🔁 PHASE 31 — Duplicate & Import Integrity

> **وضعیت:** ✅ کامل (پیاده‌سازی + تست)
> **تاریخ:** ۱۴۰۵/۰۷/۰۶
> **پیش‌نیاز:** PHASE 30 (Import Engine) — همان revision: `d4e5f6a7b8c9`

---

## 🎯 ImportIdentity — هویت معامله

```python
class ImportIdentity(Base):
    __tablename__ = "import_identities"

    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False, index=True)
    source = Column(String, nullable=False)
    external_ticket = Column(String, nullable=True)
    trading_account_id = Column(Integer, ForeignKey("personal_trading_accounts.id"), nullable=True)
    prop_stage_id = Column(Integer, ForeignKey("prop_stages.id"), nullable=True)
    symbol = Column(String, nullable=False)
    open_time = Column(DateTime(timezone=True), nullable=False)
    close_time = Column(DateTime(timezone=True), nullable=True)
    identity_hash = Column(String, unique=True, nullable=False, index=True)

    # توسعه‌های فاز ۳۰/۳۱:
    batch_id   -> import_batches.id      # همان اجرایی که این رکورد را آورد
    version_id -> strategy_versions.id
    test_type  Enum(TestType)
    trade_hash String(32)                # همان hash قدیمی معاملات
```

### فرمول `identity_hash`
```
SHA-256( source | external_ticket | trading_account_id | prop_stage_id
         | version_id | test_type | symbol | open_time(UTC) | close_time(UTC) )
```

| بخش | منبع |
|:---|:---|
| `source + external_ticket + trading_account_id + symbol + open_time + close_time` | قرارداد فاز ۳۱ (طبق درخواست) |
| `prop_stage_id + version_id + test_type` | **افزودهٔ لازم فاز ۳۰** |

> ⚠️ **دلیل افزوده‌ها:** برای `BACKTEST` / `FORWARD` / `REAL_PROP` هیچ
> `trading_account_id` وجود ندارد. اگر دامنه در هویت نبود، همان فایل بک‌تست که
> برای دو نسخهٔ استراتژی ایمپورت می‌شود، در نسخهٔ دوم اشتباهاً «تکراری» رد می‌شد.
> تست `test_scope_isolation_between_versions` همین را تضمین می‌کند.

Timestampها همیشه به **UTC** نرمال می‌شوند (`normalize_utc`) تا یک رکورد در دو اجرا
هش یکسان بگیرد — همین تابع در Backfill مهاجرت هم (به‌صورت کپی) استفاده می‌شود و
برابری هش‌ها در اعتبارسنجی مهاجرت تأیید شده است.

---

## 🔍 الگوریتم Duplicate Detection — سه حالت

```
            ┌── تکرار در همان فایل (seen) ─────────────────────────→ DUPLICATE
ورودی ردیف ─┼── identity_hash در import_identities (شامل Soft-Deleted) → DUPLICATE
            ├── Trade.trade_hash قدیمی ───────────────────────────→ DUPLICATE
            ├── همان ticket در همان دامنه با مشخصات دیگر ─────────→ POSSIBLE_DUPLICATE
            ├── همان symbol + همان open_time در همان دامنه ───────→ POSSIBLE_DUPLICATE
            └── هیچ‌کدام ────────────────────────────────────────→ NEW
```

| حالت | معنی | اثر روی Commit |
|:---|:---|:---|
| `NEW` | رکورد جدید | وارد می‌شود |
| `DUPLICATE` | همان هویت قبلاً وارد شده | **نادیده گرفته می‌شود** (`duplicate`++) — خطا نیست |
| `POSSIBLE_DUPLICATE` | شباهت قوی ولی هویت کامل نیست | پیش‌فرض **۴۰۹** (نیاز به تأیید صریح) |
| `INVALID` | نقض قرارداد معامله | همیشه مانع Commit (۴۰۰) — قانون اتمیک بودن |

### جزئیات مهم
1. **دامنه** (`version_id` + `prop_stage_id` + `trading_account_id` + `test_type`) در همهٔ
   جست‌وجوهای «تکراری» و «شباهت» شرط است ⇒ دو نسخهٔ متفاوت همدیگر را رد نمی‌کنند.
2. **Soft Delete دیده می‌شود:** هیچ شرطی روی `is_deleted` گذاشته نمی‌شود؛ هویت معاملهٔ
   حذف‌شده‌ی نرم در `import_identities` می‌ماند و در پیام ردیف هم صریحاً
   «— این معامله حذف نرم شده است» می‌آید.
3. **Hard Delete ⇒ پاک‌شدن هویت:** رابطهٔ `Trade.import_identities` با
   `cascade="all, delete-orphan"` تعریف شده تا حذف کامل معامله هویتش را هم پاک کند؛
   در غیر این صورت re-import بعدی بی‌دلیل «تکراری» می‌شد.
4. **تکرار داخل یک فایل:** ردیف‌های تکراری همان batch با `seen` تشخیص داده می‌شوند
   (پیام: «تکراری در همان فایل (ردیف N)») — بدون شکستن تراکنش و بدون `IntegrityError`.
5. **`trade_hash` قدیمی** همچنان پر می‌شود (فرمول MD5 فاز ۵، از مقادیر خام پارسر) تا با
   رکوردهای قدیمی دیتابیس بایت‌به‌بایت سازگار بماند و به‌عنوان لایهٔ دوم تشخیص تکرار کار کند.

---

## 🧾 سرشماری و وضعیت‌های ImportBatch

```
PENDING ──(commit موفق)──► COMMITTED
   │
   ├──(خطای غیرمنتظره در commit)──► FAILED
   └──(لغو کاربر)──────────────────► CANCELLED
```

شمارنده‌ها (فاز ۳۱):
- `total`     : تعداد ردیف‌های فایل
- `imported`  : معاملات واقعاً ذخیره‌شده
- `duplicate` : «تکراری قطعی» + «مشکوک به تکرار» (تفکیک دقیق در `counts`)
- `failed`    : ردیف‌های نامعتبر (پس از Commit موفق صفر می‌شود)

`GET /api/imports/batches/{id}` علاوه بر این‌ها، `counts` تفکیکی و ردیف‌ها را برمی‌گرداند:
```json
"counts": {"new": 4, "duplicate": 1, "possible_duplicate": 1, "invalid": 0},
"blocking": true
```

### حالت‌های خطا (API)
| سناریو | پاسخ |
|:---|:---|
| Commit دوبارهٔ batch تأییدشده | `409` — «قبلاً تأیید و ذخیره شده است» |
| Commit بعد از لغو | `409` — «لغو شده است؛ Preview جدید بگیرید» |
| ردیف نامعتبر | `400` + لیست ردیف‌های مانع؛ هیچ رکوردی ذخیره نمی‌شود |
| ردیف مشکوک بدون تأیید | `409` + لیست ردیف‌های مشکوک |
| خطای غیرمنتظرهٔ دیتابیس | `500` + `status=FAILED` روی batch و **صفر رکورد ذخیره‌شده** |

---

## 🧪 تست‌ها (۱۰ تست جدید — `tests/test_duplicate_integrity.py`)

```
cd backend; .\venv\Scripts\python.exe -m pytest tests/test_duplicate_integrity.py -q
..........  [100%]
```

| تست | تضمین |
|:---|:---|
| `test_identity_hash_is_stable_and_scope_aware` | هش پایدار + حساس به version/test_type/ticket |
| `test_identity_hash_is_unique_in_database` | ایندکس یکتا در سطح DB |
| `test_duplicate_after_import` | NEW ⇒ import ⇒ DUPLICATE (idempotent) |
| `test_soft_deleted_trade_is_still_detected` | قانون Soft Delete فاز ۳۱ |
| `test_possible_duplicate_requires_explicit_confirmation` | ۴۰۹ بدون تأیید / import با تأیید |
| `test_same_external_ticket_with_other_details_is_possible_duplicate` | تطبیق با شمارهٔ سفارش |
| `test_duplicate_rows_inside_same_file` | تکرار داخل یک فایل |
| `test_scope_isolation_between_versions` | دو نسخه، یک فایل ⇒ هر دو NEW |
| `test_hard_delete_removes_identity_so_reimport_is_new` | cascade هویت با Hard Delete |
| `test_batch_counters_and_completed_at` | شمارنده‌ها + `completed_at` |

### وضعیت کل تست‌ها
```
Backend : 127 passed  (107 قبلی + 20 فاز ۳۰ + 10 فاز ۳۱ — بدون Regression)
Frontend: 9 passed    (vitest)
TypeScript: tsc -b --force ⇒ 0 خطا
```

---

## 🔗 ارتباط با فازهای دیگر

| فاز | ارتباط |
|:---|:---|
| ۲۵ (Soft Delete) | معاملات حذف‌شده در تشخیص تکرار **دیده می‌شوند**؛ در محاسبهٔ سود مرحلهٔ پراپ لحاظ نمی‌شوند. |
| ۲۷/۲۸ (Trade Contract) | اعتبارسنجی هر دو سطح (دسته/رکورد) از همان `TradeValidator` و `CheckConstraint` استفاده می‌کند. |
| ۳۰ (Import Engine) | `ImportIdentity` فقط از مسیر `ImportEngine.commit` ساخته می‌شود (هیچ مسیر موازی). |
| FINANCE | هیچ ارتباطی — Import نه `FinancialAccount` می‌سازد و نه به آن وابسته است. |

---

## ✅ چک‌لیست نهایی فاز ۳۱

- [x] `ImportBatch` با تمام فیلدهای خواسته‌شده (source, file_name, started_at, completed_at, total, imported, duplicate, failed, status, user_id)
- [x] `ImportIdentity` با تمام فیلدهای خواسته‌شده (+ توسعه‌های مستند)
- [x] هویت: `source + external_ticket + trading_account_id + symbol + open_time + close_time` (+ دامنه)
- [x] سه حالت NEW / DUPLICATE / POSSIBLE_DUPLICATE
- [x] Soft Deleted در Duplicate Detection دیده می‌شود
- [x] یکتایی `identity_hash` در سطح دیتابیس (ایندکس unique)
- [x] Backfill هویت برای داده‌های موجود (شامل Soft-Deleted) با تأیید برابری هش
- [x] Commit اتمیک + شمارنده‌ها + وضعیت‌ها
- [x] تست‌های خودکار (۱۰ تست) + بدون Regression در ۱۰۷ تست قبلی

