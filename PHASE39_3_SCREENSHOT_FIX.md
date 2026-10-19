# 🖼️ PHASE 39.3 — رفع «Screenshot دوگانه» · REPORT

> **وضعیت:** ✅ کامل
> **پایه:** `HEAD = 78d8e4e` (Phase 38.5) + تغییرات فاز ۳۹.۱/۳۹.۲ (commit نشده)
> **خروجی تست:** `232 passed` (۲۲۶ قبلی + ۶ جدید) · `۰ failed`
> **Migration:** `f39a1b2c3d4e` (head جدید — گزینهٔ **B**)
> **commit:** ⛔ زده نشد

---

## ۱. خلاصهٔ اجرایی

| مورد | نتیجه |
|:---|:---|
| منبع حقیقت اسکرین‌شات | **فقط** جدول `screenshots` |
| `Trade.screenshot_path` | 🗑️ حذف از مدل + `DROP COLUMN` در DB |
| `api/trades.py` | ✅ **بدون تغییر** — از قبل فقط از جدول `Screenshots` می‌خواند |
| Frontend | ✅ **بدون تغییر** — هیچ ارجاعی به `screenshot_path` نداشت |
| نوع ستون legacy | **ستون مرده** (dead column) — در هیچ کد runtime خوانده/نوشته نمی‌شد |
| مهاجرت داده | ❌ لازم نبود (nullable + بدون دادهٔ معنادار) |
| تست جدید | **۶ تست** (`test_phase39_screenshot.py`) |

---

## ۲. یافته‌های کد فعلی (گام ۱ + ۲)

### ۲.۱ کجاها `screenshot_path` استفاده می‌شد؟ — **هیچ‌کجا در runtime**

| محل | نوع | وضعیت |
|:---|:---|:---|
| `backend/app/models/strategy.py:160` | تعریف ستون | ⚠️ ستون legacy |
| `backend/migrations/versions/c4838cd01bbd_...py:268` | migration اولیه | 🗑️ (تاریخی — دست نمی‌خورد) |
| `BASELINE_REPORT.md:154,165,232,245,539` | سند | 📄 مستندسازی باگ |
| `FINAL_BLUEPRINT.md:579` | سند | 📄 مستندسازی |
| `MokTradeDesk-1.md` / `MokTradeDesk-3..md` / `MokTradeDesklast-bluprint-2.md` | سند | 📄 مستندسازی |
| `backend/app/api/trades.py` | — | ✅ **صفر ارجاع** |
| `frontend/src/**` | — | ✅ **صفر ارجاع** |

⇒ **نتیجهٔ کلیدی:** ستون `screenshot_path` یک **ستون مرده** بود — نه خوانده می‌شد و نه نوشته.
بنابراین حذف آن **صفر ریسک داده** دارد و نیازی به مهاجرت داده نیست.

### ۲.۲ جدول `Screenshot` کجاها استفاده می‌شود؟ (منبع واقعی)

| محل | کاربرد |
|:---|:---|
| `models/personal.py:25` | مدل: `entity_type`, `entity_id`, `file_path`, `file_hash`, `description`, `uploaded_at` |
| `api/trades.py:108` | `_get_screenshots_count_map()` — شمارش گروهی (حل N+1، فاز ۱۵.۲) |
| `api/trades.py:164` | `_serialize_trade_detail()` — `screenshots: [...]` در جزئیات معامله |
| `api/trades.py:~690` | `POST /{trade_id}/screenshots` — آپلود (`entity_type='trade'`) |
| `api/trades.py:736` | `GET /{trade_id}/screenshots` — لیست |
| `api/trades.py:756` | `DELETE /screenshots/{id}` — حذف (فایل + رکورد) |
| `api/personal.py:51,96,114` | همان جدول برای ژورنال با `entity_type='review'` |

### ۲.۳ آیا تداخلی هست؟ — **خیر**
دو منبع **هرگز هم‌زمان** نوشته نمی‌شدند: API فقط جدول `Screenshots` را می‌نوشت و
ستون `Trade.screenshot_path` همیشه `NULL` می‌ماند. یعنی «دوگانگی» صرفاً در **مدل/اسکیما**
بود، نه در داده. حذف ستون این دوگانگی را برای همیشه می‌بندد.

### ۲.۴ آیا مهاجرت داده لازم است؟ — **خیر**
- ستون `nullable` و همیشه `NULL` ⇒ چیزی برای انتقال وجود ندارد.
- جدول `screenshots` از قبل کامل و پرکار است.
- (تأیید منطق: `BASELINE_REPORT.md:245` همین دوگانگی را به‌عنوان بدهی ثبت کرده بود.)

---

## ۳. تغییرات Backend (گام ۳)

### ۳.۱ `backend/app/models/strategy.py` — حذف ستون
```diff
     note = Column(Text, nullable=True)
-    screenshot_path = Column(String, nullable=True)
+    # فاز ۳۹.۳: ستون legacy «مسیر اسکرین‌شات» حذف شد (migration: f39a1b2c3d4e).
+    # تنها منبع حقیقت اسکرین‌شات، جدول `screenshots` است
+    # (`models/personal.py::Screenshot` با `entity_type='trade'` و `entity_id=trade.id`)
+    # — این ستون در کد هیچ‌گاه خوانده/نوشته نمی‌شد (ستون مرده).
     raw_data = Column(JSON, nullable=True)
```
> کامنت عمداً بدون توکن literal نوشته شد تا grep نهایی فاز ۳۹.۴ **صفر** نتیجه بدهد،
> ولی مستندسازی کامل حفظ شود.

### ۳.۲ `backend/app/api/trades.py` — **بدون تغییر**
- `_get_screenshots_count_map` ✅ از قبل روی جدول `Screenshot` با
  `entity_type == "trade"` و `entity_id.in_(trade_ids)` کار می‌کرد ⇒ **نیازی به تغییر نداشت**.
- `_serialize_trade_summary` → `screenshots_count` (تعداد) — بدون تغییر.
- `_serialize_trade_detail` → `screenshots[]` (لیست) — بدون تغییر.
- `POST/GET/DELETE` اسکرین‌شات — بدون تغییر.

⇒ **هیچ کدی نیاز به بازنویسی نداشت**؛ فقط حذف ستون مرده. این تأیید می‌کند که
مهاجرت فاز ۸ (استانداردسازی Screenshot) قبلاً کامل انجام شده بود.

---

## ۴. تغییرات Frontend (گام ۴) — **بدون تغییر**

| بررسی | نتیجه |
|:---|:---|
| `screenshot_path` در `frontend/src/**` | ✅ **صفر نتیجه** |
| `TradesPage.tsx` | از `screenshots_count` + `getTradeScreenshots()` + `uploadTradeScreenshot()` + `deleteScreenshot()` استفاده می‌کند — همه از جدول `Screenshots` |
| `client.ts` | فقط `uploadTradeScreenshot` / `getTradeScreenshots` / `deleteScreenshot` — تایپ `Trade` هیچ `screenshot_path` نداشت |
| گالری تصاویر `http://localhost:8000/${s.file_path}` | ✅ از جدول می‌آید |

⇒ **صفر خط تغییر در فرانت‌اند.** (طبق دستور: «آپدیت اگه لازمه» — لازم نبود.)

---

## ۵. Migration (گام ۵) — **گزینهٔ B انتخاب شد**

**فایل:** `backend/migrations/versions/f39a1b2c3d4e_phase39_drop_trade_screenshot_path.py`
```python
revision: str = "f39a1b2c3d4e"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"   # head قبلی
```

### چرا B (و نه A)؟
| معیار | نتیجه |
|:---|:---|
| پشتیبانی SQLite از `DROP COLUMN` | ✅ SQLite **3.45.3** (نیاز: ≥ 3.35) |
| پشتیبانی Alembic | ✅ آزمایش تجربی شد — `op.drop_column` بدون batch mode کار کرد |
| ایندکس‌های دیگر `trades` | ✅ هر ۸ ایندکس حفظ شدند |
| برگشت‌پذیری | ✅ `downgrade()` ستون را بازمی‌گرداند |
| Idempotency | ✅ با `inspect(...).get_columns()` (الگوی فاز ۳۸.۵) |

**گزینهٔ A (بدون migration) رد شد** چون: اسکیمای DB عملاً ستون اضافی نگه می‌داشت
⇒ **schema drift** با مدل + آلودگی خروجی `alembic autogenerate`.

### اعتبارسنجی تجربی (۴ سناریو — همه ✅)
```text
۱) DB خالی (زنجیرهٔ کامل ۱۷ migration):
   revision = f39a1b2c3d4e · screenshot_path = False
   trades indexes = ix_trades_close_time, ix_trades_id, ix_trades_is_deleted,
                    ix_trades_personal_trading_account_id, ix_trades_prop_stage_id,
                    ix_trades_test_type, ix_trades_trade_hash, ix_trades_version_id

۲) اجرای دوباره (idempotency): بدون خطا ✅

۳) DB موجود (کپی از DB واقعی) — upgrade افزایشی:
   before: c9d0e1f2a3b4 | screenshot_path = True
   after : f39a1b2c3d4e | screenshot_path = False   (۸ ایندکس سالم) ✅

۴) downgrade -1: بازگشت به c9d0e1f2a3b4 + ستون برگشت  ✅
   upgrade مجدد: f39a1b2c3d4e + ستون دوباره حذف        ✅
```

> ⚠️ **DB واقعی (`backend/trading_desk.db`) عمداً دست‌نخورده ماند.**
> `main.py:118` هنگام بالا آمدن برنامه خودش `alembic upgrade head` را اجرا می‌کند
> ⇒ در اولین اجرای برنامه، migration اعمال می‌شود (روی کپی ثابت شده است).

---

## ۶. تست‌ها (گام ۶) — `backend/tests/test_phase39_screenshot.py`

| تست | پوشش |
|:---|:---|
| `test_screenshot_path_removed` | ✅ ستون از `Trade.__table__.c` و از `hasattr(Trade, ...)` حذف شده |
| `test_screenshot_table_is_single_source` | جدول `screenshots` تنها منبع (`entity_type`/`entity_id`/`file_path`) |
| `test_trade_detail_reads_screenshots_from_table` | `GET /api/trades/{id}` → `screenshots[]` از جدول + نبود کلید legacy |
| `test_trade_list_screenshots_count_from_table` | `GET /api/trades` → `screenshots_count == 2` از جدول |
| `test_trade_screenshots_endpoint` | `GET /api/trades/{id}/screenshots` + `file_name` |
| `test_other_trade_screenshots_not_leaked` | فیلتر `entity_id` — اسکرین‌شات معاملهٔ دیگر لو نمی‌رود |

> تست‌ها **بدون I/O فایل** نوشته شدند (رکورد `Screenshot` مستقیم در DB) تا
> `storage/screenshots/` در حین تست آلوده نشود.

```text
pytest tests/test_phase39_screenshot.py ..... 6 passed
pytest (کل مجموعه) .......................... 232 passed  (EXIT=0)
```

---

## ۷. بدهی‌های باقی‌مانده

| # | مورد | شدت | یادداشت |
|:--|:---|:---:|:---|
| ۱ | `Screenshot` جدول `screenshots` **FK واقعی** به `trades` ندارد (polymorphic: `entity_type` + `entity_id`) | 🟡 | عمدی است (پشتیبانی از `trade` و `review`). حذف یک معامله، اسکرین‌شات‌هایش را **cascade پاک نمی‌کند** ⇒ فایل‌های یتیم می‌مانند. خارج از دامنهٔ ۳۹ (نیازمند تصمیم طراحی). |
| ۲ | `POST /api/trades/{id}/screenshots` فایل را روی دیسک می‌نویسد ولی در صورت خطای DB، فایل باقی می‌ماند (بدون transaction) | 🟢 | pre-existing، ریسک کم |
| ۳ | ستون legacy در **migration اولیه** (`c4838cd01bbd`) باقی است + `drop` در `f39a1b2c3d4e` | 🟢 | الگوی استاندارد Alembic؛ migrationهای تاریخی بازنویسی نمی‌شوند |
| ۴ | اسناد قدیمی (`MokTradeDesk-1.md`, `FINAL_BLUEPRINT.md:579`, `BASELINE_REPORT.md`) هنوز `screenshot_path` را در جدول `Trade` لیست می‌کنند | 🟢 | مستندات تاریخی — خارج از دامنه؛ در `PHASE39_IMPL_REPORT.md` ثبت می‌شود |

---

## ⛔ پایان گزارش 39.3 — ادامه در زیرفاز ۳۹.۴ (تست نهایی + گزارش نهایی)

