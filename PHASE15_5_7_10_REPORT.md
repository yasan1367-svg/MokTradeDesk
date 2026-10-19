# 📋 گزارش فازهای ۱۵.۵ + ۱۵.۷ + ۱۵.۸ + ۱۵.۹ + ۱۵.۱۰

> **تاریخ:** ۱۴۰۵/۰۷/۰۳ (2026-09-25)
> **مدل:** `deepseek/deepseek-v4.1-flash`
> **ترتیب اجرا:** ۱۵.۵ ← ۱۵.۷ ← ۱۵.۸ ← ۱۵.۹ ← ۱۵.۱۰
> **وضعیت کلی:** ✅ همهٔ ۵ فاز انجام شد — ✅ Frontend (`tsc` + `build`) و Backend (`py_compile` + `pytest` ۳۳ تست) پاس

| فاز | عنوان | وضعیت |
|---|---|---|
| ۱۵.۵ | Dark Mode ناسازگار | ✅ انجام شد (+ یافتهٔ مهم: ایرادهای واقعی در جای دیگری بودند) |
| ۱۵.۷ | ثبت وابستگی‌های گم‌شده | ✅ از قبل در فاز ۱۵.۳ انجام شده بود — تأیید شد |
| ۱۵.۸ | رفع Duplicate در `client.ts` | ✅ انجام شد |
| ۱۵.۹ | رفع `StrategyStatus` enum | ✅ انجام شد (helper مشترک) |
| ۱۵.۱۰ | رفع `_to_currency` بی‌صدا | ✅ انجام شد (لاگ اضافه شد) |

**فایل‌های تغییر‌یافته:**
- Backend: `api/prop.py` · `api/strategies.py` · **جدید:** `utils/enums.py`
- Frontend: `api/client.ts` · `index.css` · `pages/{DashboardPage,ComparisonPage,CalendarPage,JournalPage,ImportPage}.tsx`

---

## 🎯 فاز ۱۵.۵ — Dark Mode ناسازگار

### 🔍 یافتهٔ مهم (واقع‌بینی)
قبل از تغییر، هر ۴ صفحهٔ فهرست‌شده با الگوهای light-only اسکن شدند:

```
=== JournalPage.tsx ===        (no light-only patterns)
=== CalendarPage.tsx ===       (no light-only patterns)
=== RiskManagementPage.tsx === (no light-only patterns)
=== ImportPage.tsx ===         (no light-only patterns)
```

**نتیجه:** این ۴ صفحه **از قبل سازگار با Dark Mode بودند** و همهٔ سطوح/متن/بوردرهایشان از `var(--*)` استفاده می‌کرد. (`RiskManagementPage` حتی یک رنگ hardcoded هم نداشت.)

رنگ‌های باقی‌مانده در آن‌ها، **گرادیان‌های برند** (آبی/سبز/بنفش) بودند که در هر دو تم یکسان رندر می‌شوند.

**اما** اسکن تکمیلی، **۶ ایراد واقعی Dark Mode** در دو صفحهٔ دیگر پیدا کرد (که در `COMPREHENSIVE_REVIEW.md` هم علامت‌گذاری شده بودند). این‌ها رفع شدند:

### ۱۵.۵.۱ رفع‌های واقعی (صفحاتی که در Dark Mode خراب می‌شدند)

| # | فایل:خط | قبل | بعد |
|---|---|---|---|
| ۱ | `DashboardPage.tsx:378` | `linear-gradient(135deg, #FFFFFF 0%, #F0F6FF 100%)` | `linear-gradient(135deg, var(--bg-card) 0%, var(--accent-soft) 100%)` |
| ۲ | `DashboardPage.tsx:413,419,425` | `bg-white/70 backdrop-blur` (×۳) | `bg-[var(--bg-card-translucent)] backdrop-blur` |
| ۳ | `ComparisonPage.tsx:496` | `linear-gradient(135deg, #EDF3FF 0%, #F0F6FF 100%)` | `linear-gradient(135deg, var(--accent-soft) 0%, var(--accent-light) 100%)` |
| ۴ | `ComparisonPage.tsx:568,572` | `bg-white/60` (×۲) | `bg-[var(--bg-card-translucent)]` |
| ۵ | `ComparisonPage.tsx:397` | `bg-[#EDF3FF]/50` | `bg-[var(--accent-soft)]` |

> **قبل:** این کارت‌ها/سطرها در حالت تاریک **سفید/آبیِ روشن** می‌ماندند (ناخوانا).
> **بعد:** در تم تاریک به `#1A2736` / `#1A2E4D` / `#1E3A6B` تغییر می‌کنند ✅

### ۱۵.۵.۲ متغیر جدید CSS
برای حفظ شفافیت (`/70`) بدون شکستن Tailwind، یک متغیر جدید اضافه شد:

```css
/* index.css — :root */
--bg-card-translucent: rgba(255, 255, 255, 0.7);

/* index.css — .dark */
--bg-card-translucent: rgba(26, 39, 54, 0.7);
```

### ۱۵.۵.۳ نگاشت برند-hex به CSS Variables (در ۴ صفحهٔ فهرست‌شده)
طبق درخواست، رنگ‌های hardcoded برند به معادل متغیری خودشان تبدیل شدند (مقدار **یکسان** ⇒ بدون تغییر بصری، اما theme-driven):

| hex | متغیر | مقدار |
|---|---|---|
| `#3F7CFF` | `var(--accent)` | `#3F7CFF` (یکسان در هر دو تم) |
| `#13AE81` | `var(--profit)` | `#13AE81` (یکسان) |
| `#7959D6` | `var(--purple)` | `#7959D6` (یکسان) |

- `JournalPage.tsx` — ۳ گرادیان (خطوط ۱۶۸، ۱۷۹، ۲۶۳)
- `ImportPage.tsx` — ۱۰ گرادیان (خطوط ۲۰۴، ۲۲۴، ۲۳۵، ۲۵۶، ۲۷۰، ۳۱۲، ۳۸۷، ۴۵۴، ۴۸۶، ۵۴۲، ۶۰۵)
- `CalendarPage.tsx` — `bg-[#3F7CFF]` → `bg-[var(--accent)]` (خط ۱۳۶) + حذف `dark:text-white` تکراری (خطوط ۱۳۲، ۱۶۵)
- `DashboardPage.tsx` / `ComparisonPage.tsx` — گرادیان‌های برند باقی‌مانده

### ۱۵.۵.۴ مواردی که عمداً تغییر نکردند (با دلیل فنی)
رنگ‌های hex که **با opacity modifier** استفاده شده‌اند، دست‌نخورده ماندند:

```
bg-[#13AE81]/15     bg-[#E45D72]/15     bg-[#1E2F4D]/30
hover:bg-[#1E2F4D]/80     bg-[#1A2B47]/75
```

**دلیل:** Tailwind v3 برای `bg-[var(--x)]/15` کد `rgb(var(--x) / 0.15)` تولید می‌کند که با متغیرِ **hex** (`#13AE81`) **می‌شکند**. این مقادیر در هر دو تم به‌درستی رندر می‌شوند (رنگ برند با شفافیت)، پس حفظ شدند.

### ۱۵.۵.۵ تست
- `npx tsc -b --force` → ✅ `TSC_EXIT=0`
- `npm run build` → ✅ `BUILD_EXIT=0` · built in 3.20s · entry chunk **240.85 kB** (بدون تغییر نسبت به ۱۵.۴)
- اسکن نهایی ۶ فایل → ✅ **صفر** الگوی light-only (`bg-white` / `#FFFFFF` / `#F0F6FF` / `#EDF3FF` / `dark:text-white`)

---

## 🎯 فاز ۱۵.۷ — ثبت وابستگی‌های گم‌شده

### وضعیت: ✅ از قبل انجام شده بود (در فاز ۱۵.۳)
این فاز **نیازی به تغییر نداشت** — در فاز ۱۵.۳ این ۴ پکیج به `requirements.txt` اضافه شده بودند.

**محتوای فعلی `backend/requirements.txt`:**
```
fastapi
uvicorn[standard]
sqlalchemy
alembic
python-multipart
openpyxl
beautifulsoup4
pydantic-settings
slowapi

# Export / PDF (فاز ۱۵.۳ — وابستگی‌های گم‌شده که export.py استفاده می‌کند)
reportlab
jdatetime
arabic-reshaper
python-bidi

# Testing (فاز ۱۲)
pytest
pytest-cov
httpx
```

### تست
```
python -c "import reportlab, jdatetime, arabic_reshaper, bidi"
→ all 4 imports OK ✅
```
نسخه‌های نصب‌شده: `reportlab 5.0.1` · `jdatetime 6.1.0` · `arabic-reshaper 3.0.1` · `python-bidi 0.6.11`

---

## 🎯 فاز ۱۵.۸ — رفع Duplicate در `client.ts`

### قبل
```typescript
export const compareVersions = (versionIds: number[], minTrades: number = 0) =>
  api.post('/api/analytics/compare', { version_ids: versionIds, min_trades: minTrades });
export const getIntervals = (symbol?: string) => ...
export const compareVersionsWithDetails = (versionIds: number[], minTrades: number = 0) =>
  api.post('/api/analytics/compare', { version_ids: versionIds, min_trades: minTrades });   // ← کپی دقیق
```

### بررسی استفاده‌ها (جست‌وجوی بازگشتی در کل `src`)
```
src\api\client.ts:29        export const compareVersions = ...          ← فقط تعریف
src\api\client.ts:33        export const compareVersionsWithDetails = ... ← فقط تعریف
src\pages\ComparisonPage.tsx:8    compareVersionsWithDetails,            ← import
src\pages\ComparisonPage.tsx:75   const res = await compareVersionsWithDetails(...)  ← استفاده
```
⇒ **`compareVersions` هیچ‌جا استفاده نمی‌شد.**

### بعد
```typescript
export const getIntervals = (symbol?: string) =>
  api.get('/api/analytics/intervals/', { params: symbol ? { symbol } : {} });
// فاز ۱۵.۸: تابع تکراری compareVersions حذف شد — این نسخهٔ واحد استفاده می‌شود
export const compareVersionsWithDetails = (versionIds: number[], minTrades: number = 0) =>
  api.post('/api/analytics/compare', { version_ids: versionIds, min_trades: minTrades });
```
**نتیجه:** تابع تکراری و بی‌استفاده حذف شد؛ تنها **یک** تابع باقی ماند و همان جایی که استفاده می‌شود (`ComparisonPage`) بدون تغییر کار می‌کند. ✅

---

## 🎯 فاز ۱۵.۹ — رفع `StrategyStatus` enum

### مشکل
الگوی تکراری `x.value if hasattr(x, 'value') else str(x)` در **۴ نقطه** تکرار می‌شد، در حالی که بعضی جاها مستقیماً `.value` استفاده می‌کردند (خروجی ناهمگون).

### راه‌حل: helper مشترک جدید
فایل **جدید** `backend/app/utils/enums.py`:
```python
"""
کمک‌تابع مشترک استخراج مقدار Enum (فاز ۱۵.۹)
"""
from typing import Any


def enum_value(value: Any) -> Any:
    """مقدار رشته‌ای یک Enum را برمی‌گرداند.

    - اگر مقدار Enum باشد → `.value` آن (رشته)
    - در غیر این صورت → `str(value)` (رفتار fallback قبلی، بدون تغییر)
    """
    return value.value if hasattr(value, "value") else str(value)
```

### اعمال در ۴ نقطه
| فایل:خط (قبل) | قبل | بعد |
|---|---|---|
| `strategies.py:143` | `v.status.value if hasattr(...) else str(v.status)` | `enum_value(v.status)` |
| `strategies.py:171` | (همان) | `enum_value(v.status)` |
| `strategies.py:259` | `forked.status.value if hasattr(...) else str(...)` | `enum_value(forked.status)` |
| `prop.py:184` | `r.stage_type.value if hasattr(...) else str(...)` | `enum_value(r.stage_type)` |

+ import: `from ..utils.enums import enum_value` در هر دو فایل.

**نتیجه:** الگوی تکراری `hasattr(...'value')` در کل `app/` **صفر** شد (فقط در docstring خود helper باقی است) و خروجی Enum در همهٔ endpointها یکسان شد. ✅

### تست
```
enum_value(StageType.STAGE_1) = 'stage_1'   ✅
enum_value('x')               = 'x'          ✅
```


---

## 🎯 فاز ۱۵.۱۰ — رفع `_to_currency` بی‌صدا

### قبل (`prop.py:23-28`)
```python
def _to_currency(value: Optional[str]) -> Currency:
    """تبدیل ارز رشته‌ای پراپ به Enum مالی (IRR|USD) با fallback امن"""
    try:
        return Currency((value or "USD").upper())
    except ValueError:
        return Currency.USD          # ← بی‌صدا (silent fallback)
```

> **نکتهٔ دقت:** در کد واقعی `pass` وجود نداشت؛ `return Currency.USD` بود. مشکل اصلی همان **بی‌صدا بودن** fallback بود (بدون لاگ) که در بررسی جامع هم علامت‌گذاری شده بود (`BE-17`).

### بعد
```python
import logging
...
logger = logging.getLogger("moktrade")
...
def _to_currency(value: Optional[str]) -> Currency:
    """تبدیل ارز رشته‌ای پراپ به Enum مالی (IRR|USD) با fallback امن + لاگ (فاز ۱۵.۱۰)"""
    raw = (value or "USD").upper()
    try:
        return Currency(raw)
    except ValueError:
        # پیش‌تر این fallback بی‌صدا بود؛ حالا هشدار لاگ می‌شود تا تبدیل ناخواسته دیده شود.
        logger.warning("Invalid currency %r — falling back to USD", value)
        return Currency.USD
```
> `logger = logging.getLogger("moktrade")` همان logger سراسری `main.py` است ⇒ لاگ در `backend/logs/app.log` و کنسول ثبت می‌شود.

### تست
```
to_currency('IRR')   = Currency.IRR          ✅
to_currency('USD')   = Currency.USD          ✅
to_currency(None)    = Currency.USD          ✅
to_currency('BOGUS') = Currency.USD          ✅ + لاگ:
   WARNING: Invalid currency 'BOGUS' — falling back to USD
```

---

## 🧪 نتایج تست (نهایی)

### Frontend
| دستور | نتیجه |
|---|---|
| `npx tsc -b --force` | ✅ `TSC_EXIT=0` |
| `npm run build` | ✅ `BUILD_EXIT=0` · built in 3.20s |
| entry chunk (بارگذاری اولیه) | ✅ **240.85 kB** (gzip 75.25) — بدون رگرسیون نسبت به فاز ۱۵.۴ |
| اسکن light-only در ۶ فایل | ✅ **صفر** مورد |

### Backend
| دستور | نتیجه |
|---|---|
| `python -m py_compile prop.py strategies.py utils/enums.py` | ✅ `py_compile=0` |
| `pytest -q` | ✅ **۳۳ passed** |
| smoke test ۵ endpoint | ✅ همه `200` (`/api/prop/firms`, `/api/prop/accounts`, `/api/strategies/`, `/api/strategies/versions/all`, `/api/strategies/1/stats`) |
| `enum_value` helper | ✅ `'stage_1'` / `'x'` |
| `_to_currency` + لاگ | ✅ fallback + WARNING ثبت شد |

---

## ✅ نتیجه‌گیری

| فاز | خروجی |
|---|---|
| **۱۵.۵** | ۶ ایراد واقعی Dark Mode رفع شد (DashboardPage ×۴، ComparisonPage ×۳) + متغیر جدید `--bg-card-translucent` + نگاشت برند-hex به `var()` در ۵ فایل. ۴ صفحهٔ فهرست‌شده از قبل سازگار بودند (تأیید شد). |
| **۱۵.۷** | تأیید شد که ۴ وابستگی از فاز ۱۵.۳ در `requirements.txt` ثبت شده‌اند و import می‌شوند. |
| **۱۵.۸** | تابع تکراری/بی‌استفادهٔ `compareVersions` حذف شد؛ یک تابع واحد باقی ماند. |
| **۱۵.۹** | helper مشترک `utils/enums.py:enum_value()` ساخته شد و در ۴ نقطه اعمال شد ⇒ صفر شدن الگوی `hasattr(...,'value')`. |
| **۱۵.۱۰** | fallback ارز حالا **لاگ** می‌شود (WARNING) و بی‌صدا نیست. |

### 📌 یادداشت‌ها
- **مشکلی رخ نداد که نیاز به توقف باشد.** همهٔ مراحل با موفقیت انجام شد.
- **تست بصری Dark Mode در مرورگر ممکن نبود** (محیط headless). اعتبارسنجی با `tsc` + `build` + اسکن استاتیک انجام شد؛ چون همهٔ تغییرات به متغیرهای CSS معتبر map شده‌اند، ریسک پایین است.
- **موارد باقی‌ماندهٔ اختیاری:** رنگ‌های برند با `opacity modifier` (`bg-[#13AE81]/15`, `bg-[#1E2F4D]/30`, ...) به‌دلیل محدودیت Tailwind v3 با `var()` تغییر نکردند؛ در صورت نیاز می‌توان با `color-mix()` یا تعریف متغیرهای `-soft` اختصاصی در فاز بعد رفع کرد.
- **فایل‌های موقت:** همهٔ اسکریپت‌های کمکی (`.ps1`، `.py`، `.txt`) پس از استفاده پاک شدند.

*گزارش فازهای ۱۵.۵ + ۱۵.۷ + ۱۵.۸ + ۱۵.۹ + ۱۵.۱۰ — تهیه‌شده در ۱۴۰۵/۰۷/۰۳.*

