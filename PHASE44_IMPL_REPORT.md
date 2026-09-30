# PHASE 44 — Dashboard & Finance Numbers — گزارش پیاده‌سازی

> هدف فاز: **اعداد داشبورد و مالی درست**.
> مبنا: آنالیز خارجی ۳ باگ — #۳ (داشبورد بک‌تست و واقعی را قاطی می‌کرد)،
> #۴ (سود بروکر دو بار)، #۶ (IRR + USD = عدد بی‌معنی).
> وضعیت: ✅ همهٔ تسک‌ها انجام شد · **۳۰۹ تست بک‌اند** · `ruff` سبز ·
> frontend (`tsc` + `vitest` + `build`) سبز · commit **زده نشده**.

---

## ۱) خلاصهٔ اجرایی

| # | باگ | وضعیت | راه‌حل |
|---|---|---|---|
| ۴۴.۱ | داشبورد Backtest + Real قاطی | ✅ | پارامتر `scope` (real/backtest/forward/all) روی dashboard/risk/calendar/yesterday — پیش‌فرض `real` |
| ۴۴.۲ | سود بروکر دو بار در `total_balance` | ✅ | `total_balance = broker_balance + funded_pnl` (دیگر `+broker_pnl`) |
| ۴۴.۳ | Payout دریافت‌شده دوباره «قابل خرج» می‌شد | ✅ | `prop_stage_3 = Σ max(0, net×share − total_withdrawn)` |
| ۴۴.۴ | محاسبات تکراری پول | ✅ | ماژول مشترک `services/finance_metrics.py` |
| ۴۴.۵ | IRR و USD با هم جمع می‌شدند | ✅ | پارامتر `currency` + `by_currency` در گزارش‌های مالی |
| ۴۴.۶ | فرانت با مدل جدید | ✅ | تایپ‌ها + انتخابگر دامنه (داشبورد) و ارز (مالی) |

**پایهٔ اولیه:** ۳۰۱ → **۳۰۹ تست** (در انتهای فاز ۴۳: ۲۸۹؛ +۲۰ تست فاز ۴۴).

---

## ۲) تسک‌ها

### ۴۴.۰ — بکاپ اولیه ✅
`C:\Backup\trading_desk.db.before_phase44` (۴۱۳٬۶۹۶ بایت).

### ۴۴.۱ — Scope روی Dashboard (باگ #۳) ✅
`backend/app/api/analytics.py`:
- `normalize_scope()` + `_apply_scope()` + `_scope_filter(..., scope)`.
- پارامتر `scope` (Query، پیش‌فرض `"real"`) روی: `/dashboard` · `/risk-metrics` ·
  `/risk-advanced` · `/calendar` · `/yesterday`. مقدار نامعتبر ⇒ `400`.
- `real` = REAL_PERSONAL + REAL_PROP · `backtest` · `forward` · `all`.
- شمارش معاملات باز (`open_trades`) هم تابع scope شد.
- تست‌های موجود soft-delete/regression به `?scope=all` به‌روزرسانی شدند (هدفشان فیلتر حذف نرم است، نه دامنه).

### ۴۴.۲ — رفع Double Counting در dashboard (باگ #۴) ✅
- `funded_pnl` فقط معاملات REAL_PROP روی مراحل **FUNDED_REAL** (join با PropStage).
- `total_balance = broker_balance + funded_pnl` (broker_balance خودش شامل سود است).
  پیش‌تر `broker_balance + broker_pnl + funded_pnl` بود ⇒ سود بروکر دو بار.

### ۴۴.۳ + ۴۴.۴ — finance_metrics.py مشترک ✅
فایل جدید `backend/app/services/finance_metrics.py`:
`broker_balance` · `broker_pnl` · `initial_capital` · `funded_pnl` · `total_balance` · `prop_stage_3`.
- `prop_stage_3` = Σ روی مراحل FUNDED_REAL از `max(0, net_pnl×profit_share − total_withdrawn)`.
- مصرف در `analytics.py::spendable_money` و `finance.py::spendable-assets`.
- تابع مردهٔ `_prop_stage3_tx_net` حذف شد.
- `spendable-assets`: `prop_stage_3` اکنون ۵۰۰×۸۰٪ = ۴۰۰ (پیش‌تر ۵۰۰) — تست به‌روزرسانی شد.

### ۴۴.۵ — GROUP BY currency (باگ #۶) ✅
`backend/app/api/finance.py` — پارامتر `currency` (پیش‌فرض USD) + `by_currency`:
`/summary` · `/charts/cashflow` · `/reports/monthly` · `/reports/category-breakdown` ·
`/reports/profit-loss` · `/expenses` · `/money-cycle` · `/net-profit` · `/withdrawals/stats`.
- اعداد سطح-بالا حالا فقط یک ارز هستند (دیگر ریال در عدد دلاری نمی‌آید) و تفکیک کامل در `by_currency`.
- `/charts/cashflow` شکل لیستی خود را برای سازگاری فرانت حفظ کرد (فیلترشده با `currency`).

### ۴۴.۶ — فرانت‌اند ✅
- `client.ts`: تایپ `TradeScope` + `CurrencyCode`؛ پارامترهای `scope`/`currency` روی توابع API؛
  تایپ `by_currency` در `ExpensesBreakdown`/`getNetProfit`/`getMoneyCycle`.
- `DashboardPage.tsx`: انتخابگر **دامنه** (واقعی/بک‌تست/فوروارد/همه) + ذخیره در localStorage + پاس‌دادن به داشبورد/ریسک/دیروز.
- `FinancePage.tsx`: انتخابگر **ارز** (USD/IRR) روی تب‌های گزارش/پیشرفته/Real/هزینه‌ها/چرخه.
- `PayoutHistoryPage.tsx`: نیازی به تغییر نداشت (از این endpointها استفاده نمی‌کند).
- اعتبارسنجی: `npx tsc -b --force` ✅ · `npx vitest run` ۹ passed ✅ · `npm run build` ✅

### ۴۴.۷ — تست سناریو ✅
`test_scenario_no_double_counting` و `test_dashboard_scope_real_ignores_backtest` (هر دو سبز).

---

## ۳) تست‌ها

| فایل | تعداد | پوشش |
|---|---|---|
| `tests/test_phase44_scope.py` | ۸ | scope روی dashboard/risk/calendar/yesterday + ۴۰۰ نامعتبر |
| `tests/test_phase44_money.py` | ۴ | Double Counting · فقط FUNDED_REAL · payout · یکسان‌بودن منابع |
| `tests/test_phase44_currency.py` | ۶ | summary/cashflow/money-cycle/expenses/net-profit/withdrawals |
| `tests/test_phase44_scenario.py` | ۲ | سناریوی سرتاسری «قابل خرج» + scope=real با ۱۰۰ بک‌تست |
| **جمع جدید** | **۲۰** | |
| **کل بک‌اند** | **۳۰۹ passed** (۱۴.۳s) | `ruff check app tests` → All checks passed |
| **فرانت‌اند** | ۹ vitest · tsc/build ✅ | |

---

## ۴) فایل‌های تغییر‌یافته

**کد جدید:** `backend/app/services/finance_metrics.py`
**کد ویرایش‌شده:** `backend/app/api/analytics.py` · `backend/app/api/finance.py`
**تست جدید:** `test_phase44_scope.py` · `test_phase44_money.py` · `test_phase44_currency.py` · `test_phase44_scenario.py`
**تست ویرایش‌شده:** `test_finance.py` · `test_phase40_full_regression.py` · `test_soft_delete_filters.py`
**فرانت‌اند:** `src/api/client.ts` · `src/pages/DashboardPage.tsx` · `src/pages/FinancePage.tsx`
**مستند:** `PHASE44_IMPL_REPORT.md`

---

## ۵) کشف‌ها

- **دامنهٔ باگ #۴ بزرگ‌تر بود:** علاوه بر `analytics.spendable_money`، محاسبهٔ `prop_stage_3`
  در `finance.spendable-assets` هم پس از هر payout همان پول را دوباره «قابل خرج» نشان می‌داد.
- **باگ #۶ واقعی بود:** `/summary` و `/money-cycle` و گزارش‌ها همهٔ ارزها را با هم SUM می‌کردند؛
  با اولین تراکنش ریالی، اعداد دلاری بی‌معنی می‌شدند. اکنون جداست.
- **پیش‌فرض scope=real یک تغییر رفتار عامدانه است:** چند تست قدیمی (soft-delete/regression) به
  `?scope=all` منتقل شدند تا هدفشان (فیلتر حذف نرم) دست‌نخورده بماند.

---

## ۶) باقی‌مانده / پیشنهاد برای Phase 45

- `/charts/cashflow` هنوز «لیست» برمی‌گرداند (نه `{USD:…, IRR:…}`) — برای سازگاری فرانت.
  در صورت نیاز، افزودن خروجی دوبعدی (سری زمانی × ارز) به‌عنوان گام بعدی.
- `spendable-assets.total.usd` فقط بسته‌های USD را جمع می‌کند (IRR جدا در `total.irr`) — مطابق رفتار فعلی.
- محاسبهٔ نرخ تبدیل IRR↔USD همچنان در `/exchange-rates` جداگانه است (خارج از دامنهٔ این فاز).

---

## ۷) آماده برای Phase 45

- داشبورد/ریسک/تقویم اکنون **دامنه‌محور** است ⇒ تحلیل واقعی از بک‌تست جدا.
- «قابل خرج» بروکر و Funded دقیق و بدون شمارش دوگانه، با کسر payoutهای دریافت‌شده.
- گزارش‌های مالی ارز-محور ⇒ حذف کلاس کاملی از نتایج بی‌معنی پس از افزودن تراکنش ریالی.
- پوشش تست سناریویی ازاین‌پس از بازگشت این سه باگ جلوگیری می‌کند.

## ۸) گام Git

```
git status        → 8 فایل تغییر‌یافته + 1 ماژول جدید + 4 تست جدید + PHASE44_IMPL_REPORT.md
git log --oneline -3 → 03c2847 (HEAD) Phase 43 ...
```

⛔ **commit زده نشده — منتظر تأیید کاربر.**

