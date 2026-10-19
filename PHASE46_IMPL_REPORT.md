# PHASE 46 — Time & Date — گزارش پیاده‌سازی

> هدف فاز: **زمان‌ها و تاریخ‌ها درست**.
> مبنا: آنالیز خارجی باگ #۱۴ و #۱۵ — فرض بی‌قید UTC، مبنای UTC برای «امروز»/تقویم شمسی/
> Daily DD، حذف آخرین روز در `date_to`، و `DateTime` ناهمگون (naive vs aware).
> تصمیم D3 کاربر: ساعت MT4 = GMT+0 (فعلاً تبدیل لازم نیست ⇒ offset پیش‌فرض 0).
> وضعیت: ✅ همهٔ تسک‌ها انجام شد · **۳۴۷ تست بک‌اند** · `ruff` سبز · migration روی DB واقعی · commit **زده نشده**.

---

## ۱) خلاصهٔ اجرایی

| # | مشکل | وضعیت | راه‌حل |
|---|---|---|---|
| ۴۶.۱ | نبود آگاهی از ساعت سرور بروکر/پراپ | ✅ | ستون `server_utc_offset_minutes` روی ۳ جدول + migration |
| ۴۶.۲ | naive ⇒ بی‌قید UTC فرض می‌شد | ✅ | `utils/time_utils.to_utc/from_utc` + اعمال offset در ایمپورت و ثبت دستی |
| ۴۶.۳ | کپی الگوریتم شمسی در دو فایل | ✅ | `utils/jalali.py` منبع واحد + جایگزینی |
| ۴۶.۴ | تقویم/روز/ماه بر پایهٔ UTC | ✅ | مبنای **Asia/Tehran** در calendar/financial-calendar/payout monthly |
| ۴۶.۵ | `date_to` آخرین روز را حذف می‌کرد | ✅ | `utils/date_range.py` (بازهٔ نیمه‌باز شامل آخرین روز) |
| ۴۶.۶ | `DateTime` ناهمگون | ✅ | قرارداد aware در مرزهای ورود/خروج + تست؛ migration بازسازی skip شد (allowance پلن) |

**پایه:** ۳۳۱ (پایان فاز ۴۵) → **۳۴۷ تست** (+۱۶).

---

## ۲) تسک‌ها

### ۴۶.۰ — بکاپ اولیه ✅
`C:\Backup\trading_desk.db.before_phase46` (۴۱۷٬۷۹۲ بایت).

### ۴۶.۱ — ستون `server_utc_offset_minutes` ✅
- `Broker` · `PersonalTradingAccount` (`models/trading.py`) · `PropAccount` (`models/prop.py`)
  با `Integer, default=0, nullable=False, server_default="0"`.
- Migration جدید `b46d1e2f3a4b` (idempotent) — روی DB واقعی اعمال شد
  (`a45c0de1f2a3 → b46d1e2f3a4b` = head).

### ۴۶.۲ — `utils/time_utils.py` + اعمال در ورود ✅
- `to_utc(dt, offset_minutes)` · `from_utc` · `now_utc`.
- `import_identity.normalize_utc(value, offset_minutes=0)`.
- `ImportContext.server_utc_offset_minutes` + `_resolve_server_offset()` (از مرحله پراپ→PropAccount، حساب شخصی→Broker)
  و استفاده در `normalize_trade` برای `open_time`/`close_time`.
- `trades._parse_iso_datetime(..., offset_minutes)` + `_resolve_trade_server_offset()` در ثبت دستی.

### ۴۶.۳ — `utils/jalali.py` واحد ✅
- توابع `gregorian_to_jalali_parts` · `jalali_to_gregorian_parts` · `gregorian_to_jalali(str)` · `jalali_to_gregorian(date)` · `JALALI_MONTHS`.
- `finance.py` و `analytics.py` حالا delegate می‌کنند (نام‌های قدیمی برای سازگاری تست‌ها حفظ شد).

### ۴۶.۴ — مبنای Asia/Tehran ✅
- `utils/time_utils.py`: `TEHRAN` (با fallback ثابت +03:30 اگر `tzdata` نبود) + `to_tehran`.
- `tzdata` به `requirements.txt` اضافه و نصب شد (ویندوز zoneinfo نیازمند آن است).
- `analytics.get_calendar_data`: کلید روز = تاریخ تهران؛ مرزهای ماه شمسی = نیمه‌شب تهران.
- `finance._jalali_date_str` + `_jalali_range`: بر پایهٔ تهران.
- `prop.get_payout_stats`: گروه‌بندی ماهانه در پایتون با `to_tehran` (قبلاً `strftime` UTC در SQL).

### ۴۶.۵ — `utils/date_range.py` ✅
- `date_range(from, to)` ⇒ `to_dt = نیمه‌شب روز بعدِ date_to` (پس `date_to` شامل است).
- `filter_by_range(query, column, from, to)`.
- اعمال در: `/finance/transactions`، `/finance/financial-calendar`، `/finance/asset-trend`،
  `_payout_filter_query` (پراپ) و لیست معاملات.

### ۴۶.۶ — یکدست‌سازی DateTime ✅
- SQLite از `ALTER COLUMN` پشتیبانی نمی‌کند و `DateTime(timezone=True)` روی SQLite عملاً
  ذخیره‌سازی را تغییر نمی‌دهد؛ طبق allowance پلن، **بازسازی جدول انجام نشد**.
- به‌جایش قرارداد «aware در مرزهای ورود/خروج» تثبیت و تست شد
  (`to_utc`/`normalize_utc`/`_parse_iso_datetime` همیشه aware برمی‌گردانند).

### ۴۶.۷ — تست نهایی ✅
`tests/test_phase46_time.py` — ۱۶ تست (فهرست در بخش بعد).

### ۴۶.۸ — گزارش نهایی ✅
همین فایل.

---

## ۳) تست‌ها

| تست | پوشش |
|---|---|
| `test_server_utc_offset_default_zero` | پیش‌فرض ۰ روی سه مدل |
| `test_server_utc_offset_persists` | ذخیره/خواندن offset |
| `test_to_utc_naive_with_offset` | naive + offset ⇒ UTC |
| `test_to_utc_aware` | aware ⇒ UTC |
| `test_from_utc` | UTC ⇒ local |
| `test_import_applies_offset` | `normalize_utc` با/بدون offset |
| `test_build_context_resolves_server_offset` | استخراج offset از مرحله پراپ |
| `test_jalali_conversion_roundtrip` | رفت‌وبرگشت میلادی↔شمسی |
| `test_jalali_nowruz_1403` | مرز سال (۲۰ مارس ۲۰۲۴) |
| `test_jalali_leap_year` | کبیسه ۱۴۰۳ (اسفند ۳۰) |
| `test_calendar_uses_tehran_timezone` | گروه‌بندی روز با وقت تهران |
| `test_transaction_23_30_utc_is_next_day_in_tehran` | ۲۳:۳۰ UTC ⇒ روز بعد تهران |
| `test_date_range_includes_last_day` | بازهٔ نیمه‌باز شامل آخرین روز |
| `test_transaction_at_10am_included` | تراکنش ۱۰صبح با date_to همان روز |
| `test_datetime_helpers_return_aware_utc` | قرارداد aware |
| `test_api_stored_datetime_is_normalized_on_read` | خروجی ISO قابل parse |

**کل بک‌اند: ۳۴۷ passed** (۱۹٫۸s) · `ruff check .` → All checks passed.

---

## ۴) فایل‌های تغییر‌یافته

**کد جدید:** `backend/app/utils/time_utils.py` · `backend/app/utils/jalali.py` ·
`backend/app/utils/date_range.py` · `backend/migrations/versions/b46d1e2f3a4b_phase46_server_utc_offset.py`
**کد ویرایش‌شده:** `backend/app/models/trading.py` · `backend/app/models/prop.py` ·
`backend/app/services/import_engine.py` · `backend/app/utils/import_identity.py` ·
`backend/app/api/trades.py` · `backend/app/api/finance.py` · `backend/app/api/analytics.py` ·
`backend/app/api/prop.py` · `backend/requirements.txt`
**تست جدید:** `backend/tests/test_phase46_time.py`
**مستند:** `PHASE46_IMPL_REPORT.md` · اعمال migration روی DB واقعی (`b46d1e2f3a4b` = head)

---

## ۵) کشف‌ها

- **ویندوز + zoneinfo:** `ZoneInfo("Asia/Tehran")` بدون پکیج `tzdata` شکست می‌خورد؛
  `tzdata` اضافه شد و یک fallback ثابت (+03:30) هم گذاشته شد تا محیط بدون tzdata هم کار کند.
- **`date_to` در چند endpoint به‌صورت رشته مستقیم فیلتر می‌شد** (`FinancialTransaction.date <= "2025-03-15"`)
  که کل روز پایانی را حذف می‌کرد — دقیقاً باگ #۱۴. همه به `filter_by_range` منتقل شدند.
- **`strftime` در SQL** برای گروه‌بندی ماهانه اجازهٔ منطقهٔ زمانی نمی‌دهد ⇒ در `payouts/stats`
  گروه‌بندی به پایتون منتقل شد.
- **SQLite و tz-aware:** ذخیره‌سازی aware را «فراموش» می‌کند؛ لذا نرمال‌سازی باید در مرز انجام شود
  (که اکنون می‌شود) — بازسازی جدول ارزش ریسک نداشت.

---

## ۶) آماده برای Phase 47

- ورود زمان‌ها (ایمپورت + دستی) اکنون بر اساس ساعت سرور مقصد تفسیر و به UTC تبدیل می‌شود.
- تقویم/گزارش‌های شمسی بر پایهٔ وقت تهران ⇒ «امروز» و مرزهای ماه درست.
- بازه‌های تاریخی شامل آخرین روز ⇒ گزارش‌ها دادهٔ روز پایانی را از دست نمی‌دهند.
- تبدیل شمسی و زمان، هرکدام یک منبع واحد دارند (`utils/jalali.py`، `utils/time_utils.py`).

## ۷) گام Git

```
git status        → 9 فایل تغییر‌یافته + 4 فایل جدید (time_utils/jalali/date_range/migration) + تست + PHASE46_IMPL_REPORT.md
git log --oneline -3 → df21b1d (HEAD) Phase 45 ...
```

⛔ **commit زده نشده — منتظر تأیید کاربر.**

