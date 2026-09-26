# 📋 گزارش فاز ۲۳ — استقلال تحلیل (Backtest / Forward / مرحله پراپ / بروکر)

> **تاریخ:** ۱۴۰۵/۰۷/۰۴ (2026-09-26) · **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ کامل — ✅ ۷۱ تست پاس · ✅ tsc -b --force (exit 0) · ✅ npm run build (exit 0)

---

## ۱. بررسی وضعیت فعلی (قبل از تغییر)

**تب‌ها (`AnalysisPage.tsx`):** `backtest | forward | prop_stage_1 | prop_stage_2 | prop_stage_3 | broker`
هر تب انتخاب‌گر مخصوص خودش را دارد (نسخه / مرحله پراپ / حساب بروکر).

**مسیر فراخوانی تحلیل (`handleReanalyze`):**
- بک‌تست/فوروارد → `analyzeVersionScoped(versionId, 'BACKTEST'|'FORWARD')` → `POST /api/analytics/analyze/version/{id}?test_type=...`
- مرحله → `analyzePropStage(id)` → `POST /api/analytics/analyze/prop/{id}`
- بروکر → `analyzeBroker(id)` → `POST /api/analytics/analyze/broker/{id}`

**محل فیلتر `test_type`:** فقط در `AnalysisService.analyze_version` و `analysis_trades_filter()`.

### 🐞 ریشهٔ خطاها (۵ باگ)
| # | باگ | اثر |
|---|---|---|
| ۱ | `TT(test_type)` در `analytics.py` — مقادیر enum **lowercase** هستند (`TestType("BACKTEST")` → **ValueError**)، و این خط **بیرون از try** بود | خطای ۵۰۰ در تب‌های بک‌تست **و** فوروارد |
| ۲ | `_guard_analyzable` و `get_analysis_version` پارامتر `test_type` را در شمارش نادیده می‌گرفتند | بعد از تحلیل Backtest، اگر Forward هم بود → ۴۰۴ «تحلیل کهنه» |
| ۳ | `scope_key = str(version_id)` برای همهٔ VERSIONها + `UniqueConstraint(scope, scope_key)` | تحلیل Backtest و Forward هم را **بازنویسی** می‌کردند |
| ۴ | تب‌های مرحله ۱/۲/۳ همان **لیست کامل** مراحل را نشان می‌دادند (بدون فیلتر `stage_type`) | «مرحله ۲» و «مرحله ۳» هم مرحله ۱ را تحلیل می‌کردند |
| ۵ | جدول معاملات همیشه `getVersionTrades(selectedId)` را صدا می‌زد | برای پراپ/بروکر لیست غلط یا خالی |

---

## ۲. تغییرات Backend

### `app/utils/trade_scope.py`
تابع جدید `version_scope_key(version_id, test_type)`:
- `test_type is None` → `str(version_id)` (سازگار با رکوردهای legacy و تست‌های قبلی)
- وگرنه → `f"{version_id}:{test_type.name}"` (مثلاً `12:BACKTEST` و `12:FORWARD`)

### `app/services/analysis_service.py`
- `analyze_version` حالا `scope_key=version_scope_key(...)` می‌سازد ⇒ بک‌تست و فوروارد **مستقل** ذخیره می‌شوند.
- پیام خطا هنگام نبود معامله: **«این استراتژی معاملات فوروارد/بک‌تست ندارد»**.

### `app/api/analytics.py`
- `analyze_version_scoped`: پارس مقاوم `TT(test_type.lower())` **داخل try**؛ `400` برای نوع نامعتبر؛ رد `REAL`.
- `get_analysis_version`: جست‌وجو با `version_scope_key` + پاس‌دادن `test_type` به گارد.
- `_guard_analyzable(..., test_type=...)`: هنگام scope=VERSION، شمارش **همان test_type** را فیلتر می‌کند (رفع ۴۰۴ کاذب) و پیام گویا می‌دهد.

---

## ۳. تغییرات Frontend

### `api/client.ts`
- افزودن `finance_account_id` به پارامترهای `getTrades`.

### `pages/AnalysisPage.tsx`
- ثبت `STAGE_TYPE_BY_SCOPE` (`prop_stage_1→stage_1`، `prop_stage_2→stage_2`، `prop_stage_3→funded_real`).
- **انتخاب خودکار** اولین مرحلهٔ همان نوع هنگام ورود به هر تب مرحله.
- dropdown مرحله‌ها فقط مراحل **همان نوع** را نشان می‌دهد.
- جدول معاملات بر اساس scope:
  - بک‌تست/فوروارد → `getTrades({ version_id, test_type })`
  - مرحله → `getTrades({ prop_stage_id })`
  - بروکر → `getTrades({ finance_account_id })`
- دکمهٔ PDF فقط در تب‌های بک‌تست/فوروارد (چون export فعلاً نسخه‌محور است).

---

## ۴. نتیجهٔ رفع هر باگ (خواسته‌های ۲ تا ۶)

| خواسته | نتیجه |
|---|---|
| **۲. Backtest** | تب بک‌تست → `POST .../analyze/version/{id}?test_type=BACKTEST` → فیلتر `version_id + test_type=BACKTEST` → فقط معاملات بک‌تست |
| **۳. Forward** | تب فوروارد → `test_type=FORWARD` → فقط فوروارد؛ اگر نبود: پیام «این استراتژی معاملات فوروارد ندارد» (۴۰۴) |
| **۴. مرحله ۱/۲/۳** | dropdown فیلترشده + `POST .../analyze/prop/{prop_stage_id}` → فقط `Trade.prop_stage_id == id` |
| **۵. بروکر** | `POST .../analyze/broker/{finance_account_id}` → فقط `Trade.finance_account_id == id` |
| **۶. مرحله ۲/۳** | حالا `prop_stage_id` **درست** بر اساس نوع تب پاس داده می‌شود |

---

## ۵. تست

### تست واحد (pytest)
| مورد | نتیجه |
|---|---|
| کل تست‌ها | ✅ **۷۱ passed** (۶۲ قبلی + ۹ جدید) |
| `tests/test_analysis_phase23.py` | ✅ ۹ تست |
| `tests/test_analysis_scope.py` | ✅ ۱۴ تست (رگرسیون فاز ۱۹/۲۰ حفظ شد) |
| `py_compile` فایل‌های تغییریافته | ✅ exit=0 |
| `npx tsc -b --force` | ✅ exit=0 |
| `npm run build` | ✅ exit=0 (built in 3.22s) |

**۹ تست جدید:** استقلال بک‌تست/فوروارد · پذیرش `backtest` کوچک · پیام نبود فوروارد · رد نوع نامعتبر/REAL · فیلتر `test_type` در `/api/trades/` · استقلال مراحل پراپ · فیلتر معاملات مرحله · فقط معاملات همان بروکر · فیلتر معاملات بروکر.

### تست یکپارچه روی **کپی** دیتابیس واقعی
(برای دست‌نخوردن داده اصلی، از کپی موقت استفاده شد)
| سناریو | نتیجه |
|---|---|
| `POST analyze/version/1?test_type=BACKTEST` | ✅ ۲۰۰ — `total_trades = 153` (فقط بک‌تست) |
| `GET analysis/version/1?test_type=BACKTEST` | ✅ ۲۰۰ — `net_pnl = 1746.44` |
| `POST analyze/version/1?test_type=FORWARD` | ✅ ۴۰۴ — «این استراتژی معاملات فوروارد ندارد» |
| `POST analyze/prop/1` | ✅ ۲۰۰ — `total_trades = 21` |
| `GET /api/trades/?version_id=1&test_type=BACKTEST` | ✅ `total = 153` |
| `GET /api/trades/?version_id=1&test_type=REAL` | ✅ `total = 21` |

---

## ۶. فایل‌های تغییریافته

| فایل | وضعیت | توضیح |
|---|---|---|
| `backend/app/utils/trade_scope.py` | ✏️ | تابع مشترک `version_scope_key` |
| `backend/app/services/analysis_service.py` | ✏️ | کلید مستقل نسخه + پیام دقیق نبود نوع |
| `backend/app/api/analytics.py` | ✏️ | پارس مقاوم `test_type` + گارد آزمون‌شده |
| `backend/tests/test_analysis_phase23.py` | 🆕 | ۹ تست فاز ۲۳ |
| `frontend/src/api/client.ts` | ✏️ | `finance_account_id` در `getTrades` |
| `frontend/src/pages/AnalysisPage.tsx` | ✏️ | انتخاب‌گر مرحله + جدول معاملات scope-aware |
| **جدید** | `PHASE23_REPORT.md` | این فایل |

---

## ۷. یادداشت‌ها / فاز آینده
1. **سازگاری:** برای نسخه‌ای که فقط با تب بک‌تست تحلیل شده، کلید آن `"{id}:BACKTEST"` است؛ endpoint قدیمی `GET /api/analytics/{version_id}` (کلید `str(id)`) آن را سرو نمی‌کند—اما این endpoint در فرانت‌اند استفاده نمی‌شود و دست‌نخورده ماندنش تست‌های فاز ۱۹ را حفظ می‌کند.
2. **گزارش PDF تحلیل** (`/api/export/analysis/pdf`) هنوز همهٔ معاملات غیر-REAL نسخه را می‌گیرد؛ افزودن پارامتر `test_type` پیشنهاد فاز بعدی است.
3. **تحلیل بروکر/پراپ** پیش‌فرض بدون فیلتر `test_type` است (درست است، چون آن دامنه‌ها اساساً REAL هستند).

---

*گزارش فاز ۲۳ — تهیه‌شده در ۱۴۰۵/۰۷/۰۴.*

