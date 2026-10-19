# PHASE 43 — Unified Metrics ⭐ — گزارش پیاده‌سازی

> هدف فاز: **یک تعریف واحد `net_pnl = pnl + commission + swap` در همه‌جا**.
> مبنا: آنالیز خارجی باگ #۱ (PropRuleEngine از `pnl` خام استفاده می‌کرد ولی تحلیل/داشبورد/
> pass_stage از `pnl+commission+swap` ⇒ تصمیم پاس/DD/برداشت‌پذیری روی عدد اشتباه — **خطر پولی**).
> وضعیت: ✅ همهٔ تسک‌ها انجام شد · **۲۸۹ تست سبز** · `ruff` سبز · commit **زده نشده**.

---

## ۱) خلاصهٔ اجرایی

| # | مشکل | وضعیت | راه‌حل |
|---|---|---|---|
| ۴۳.۱ | نبود منبع واحد متریک | ✅ | ماژول جدید `app/services/metrics.py` |
| ۴۳.۲ | نبود تست مستقل | ✅ | `tests/test_metrics.py` (۱۳ تست) |
| ۴۳.۳ | **PropRuleEngine روی `pnl` خام** (خطر پولی) | ✅ | `current_profit/equity/daily/DD/withdrawable` همه روی `net_pnl` |
| ۴۳.۴ | دو نسخهٔ `_net_pnl` + `_calculate_max_drawdown` در تحلیل | ✅ | حذف شدند؛ استفاده از `metrics` |
| ۴۳.۵ | فرمول‌های تکراری در analytics/finance | ✅ | `_net_expr`/`_trade_net_expr` → `metrics.net_pnl_sql()` |
| ۴۳.۶ | نبود تست «یک عدد» | ✅ | `tests/test_phase43_unified_metrics.py` (۴ تست) |

**پایهٔ اولیه:** از ۲۷۲ تست (Phase 42) به **۲۸۹ تست** رسید (**+۱۷**).

---

## ۲) تسک‌ها

### ۴۳.۰ — بکاپ اولیه ✅
- `C:\Backup\trading_desk.db.before_phase43` (۴۱۳٬۶۹۶ بایت).

### ۴۳.۱ — `services/metrics.py` ✅
توابع: `net_pnl` · `net_pnl_sql` · `equity_curve` · `max_drawdown` · `streaks` ·
`profit_factor` · `calculate_basic_metrics` · `calculate_max_drawdown`.
- طبق پلن، در `calculate_basic_metrics` مقدار `largest_loss` = `min(losses)` (عدد منفی خام) است
  (این تابع مصرف‌کنندهٔ فعلی ندارد؛ `AnalysisService` نسخهٔ خودش با `abs()` را نگه داشته).

### ۴۳.۲ — تست‌های مستقل metrics ✅
`tests/test_metrics.py` — ۱۳ تست: `net_pnl` (basic/none/SQL-eq) · `equity_curve` ·
`max_drawdown` · `streaks` (+empty) · `profit_factor` (+no-loss) ·
`calculate_basic_metrics` (+commission) · `calculate_max_drawdown` · empty.

### ۴۳.۳ — PropRuleEngine روی metrics ✅
`app/services/prop_rule_engine.py`:
- `total_pnl = sum(metrics.net_pnl(t) for t in trades)` (خط ۱۰۲)
- `floating_pnl` روی `net_pnl`
- `_group_daily_pnl` → `metrics.net_pnl`
- `_calculate_max_drawdown` → wrapper نازک روی `metrics.calculate_max_drawdown`
  (برای سازگاری عقب‌رو با `test_prop.py`، با ترتیب زمانی معاملات).
- دیگر هیچ `.pnl` خامی در فایل نیست.

### ۴۳.۴ — analysis_service.py روی metrics ✅
- حذف **دو نسخهٔ** `_net_pnl` (تابع تودرتو + متد static).
- حذف متد `_calculate_max_drawdown`.
- افزودن helper `_chronological(trades)` برای ترتیب زمانی.
- همه‌جا `metrics.net_pnl` / `metrics.calculate_max_drawdown` (شامل
  `_calculate_basic_metrics`، `_calculate_max_consecutive_losses`، `_calculate_consistency`، `_summarize`).

### ۴۳.۵ — analytics.py + finance.py (+ export/chart_helpers) ✅
- `analytics.py`: `_net_expr()` → `metrics.net_pnl_sql()`؛ `funded_pnl` روی net؛
  `net_pnl` تودرتو در `/yesterday` حذف و `metrics.net_pnl`؛ `open exposure` روی net.
- `finance.py`: `_trade_net_expr()` → `metrics.net_pnl_sql()`؛ تقویم مالی روی `metrics.net_pnl`.
- **افزودنی (برای تحقق «همه‌جا»):** `export.py` (خلاصهٔ آماری PDF → net) و
  `chart_helpers.py` (Equity/Win-Loss chart → net) و `prop.py::pass_stage` (موجودی نهایی → net)
  و `strategies.py::_net_expr` → `metrics`.
- باقی‌ماندهٔ `commission` فقط دسترسی خام به فیلد داده است (خروجی CSV/API/مدل/Import/Validator) — نه محاسبهٔ net_pnl.
  جستجوی الگوی `pnl+commission+swap` فقط در `metrics.py` نتیجه می‌دهد.

### ۴۳.۶ — تست «یک عدد» ✅
`tests/test_phase43_unified_metrics.py` — ۴ تست روی یک سناریوی مشترک:

| تست | چه چیزی را اثبات می‌کند |
|---|---|
| `test_prop_engine_uses_net_pnl` | `current_profit == 1195` (net) و **نه** `1300` (pnl خام) |
| `test_all_services_return_same_net_pnl` | `PropRuleEngine == AnalysisService == dashboard(prop) == finance.real-pnl` |
| `test_commission_affects_prop_decision` ⭐ | با هدف ۱۲۰۰: pnl خام (۱۳۰۰) پاس می‌شد، net (۱۱۹۵) → `ready_to_pass=False` |
| `test_max_drawdown_consistent` | `max_dd` موتور == `metrics.calculate_max_drawdown` == تحلیل |

**اثبات رگرسیون:** روی کد Phase 42 (`total_pnl = sum(t.pnl or 0 ...)`) این تست‌ها fail می‌شدند
(۱۱۹۵ ≠ ۱۳۰۰).

---

## ۳) تست‌ها

| فایل | تعداد | پوشش |
|---|---|---|
| `tests/test_metrics.py` | ۱۳ | توابع خالص متریک + برابری SQL/Python |
| `tests/test_phase43_unified_metrics.py` | ۴ | PropRuleEngine · یکسان‌بودن همهٔ سرویس‌ها · اثر کمیسیون · DD |
| **جمع جدید** | **۱۷** | |
| **کل مجموعه** | **۲۸۹ passed** (۱۴.۵s) | `ruff check .` → All checks passed |

---

## ۴) فایل‌های تغییر‌یافته

**جدید:**
- `backend/app/services/metrics.py`
- `backend/tests/test_metrics.py`
- `backend/tests/test_phase43_unified_metrics.py`
- `PHASE43_IMPL_REPORT.md`

**تغییر‌یافته:**
- `backend/app/services/prop_rule_engine.py`
- `backend/app/services/analysis_service.py`
- `backend/app/api/analytics.py`
- `backend/app/api/finance.py`
- `backend/app/api/prop.py` (pass_stage)
- `backend/app/api/strategies.py`
- `backend/app/api/export.py`
- `backend/app/utils/chart_helpers.py`

---

## ۵) کشف‌ها

- **دامنهٔ باگ #۱ بزرگ‌تر از سه فایل اعلامی بود:** علاوه بر prop_rule_engine/analysis/finance،
  محاسبات net_pnl تکراری در `prop.py::pass_stage` (موجودی نهایی هنگام پاس!)، `strategies.py`،
  `export.py` (PDF) و `chart_helpers.py` (نمودار) هم وجود داشت — همه یکسان‌سازی شدند.
- **تناقض مستندات:** `ANALYSIS.md` ادعا می‌کرد «net_pnl در PropRuleEngine ✅» ولی کد واقعی
  از `pnl` خام استفاده می‌کرد (یعنی مستندات/رگرسیون نادرست بود). اکنون کد و ادعا هماهنگ‌اند.
- در `metrics.calculate_basic_metrics` (طبق پلن) `largest_loss` منفی است؛ چون مصرف‌کننده ندارد
  فعلاً بی‌اثر است ولی در صورت استفادهٔ آینده باید آگاهانه تصمیم گرفته شود.

---

## ۶) آماده برای Phase 44

- یک منبع حقیقت (`metrics.py`) برای همهٔ محاسبات سود ⇒ حذف کلاس کاملی از باگ‌های ناسازگاری عددی.
- تصمیم پاس/DD/برداشت‌پذیری پراپ اکنون روی **عدد خالص واقعی** (با کمیسیون/swap) گرفته می‌شود.
- پوشش تست رگرسیون برای «یک عدد» تضمین می‌کند بازگشت باگ #۱ در آینده فوراً fail شود.
- `net_pnl_sql()` آمادهٔ استفاده در هر aggregation جدید SQL است.

## ۷) گام Git

```
git status        → 8 فایل تغییر‌یافته + 3 فایل جدید (metrics.py + 2 تست) + PHASE43_IMPL_REPORT.md
git log --oneline -3 → 448d95f (HEAD) Phase 42 ...
```

⛔ **commit زده نشده — منتظر تأیید کاربر.**

