# 📋 گزارش فاز ۲۲ — گزارش‌های مالی (۲۲.۱، ۲۲.۲، ۲۲.۳)

> **تاریخ:** ۱۴۰۵/۰۷/۰۴ (2026-09-26) · **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ کامل — ✅ ۶۲ تست پاس · ✅ tsc -b --force (exit 0) · ✅ npm run build (exit 0)
> **قوانین:** ✅ Auto-approve غیرفعال · ✅ ترتیب ۲۲.۱ ← ۲۲.۲ ← ۲۲.۳

---

## ۰. بررسی وضعیت قبل از تغییر

### گزارش‌هایی که **از قبل** وجود داشت
| Endpoint | توضیح |
|---|---|
| `GET /api/finance/summary` | مجموع دارایی به تفکیک ارز، درآمد/هزینه/انتقال، تعداد تراکنش |
| `GET /api/finance/accounts/{id}/stats` | آمار یک حساب (موجودی، درآمد، هزینه، آخرین تراکنش) |
| `GET /api/finance/withdrawals/stats` | آمار برداشت‌ها (پراپ/بروکر) + تاریخچه |
| `GET /api/finance/charts/cashflow` | نمودار جریان نقدی ماهانه (درآمد vs هزینه) |
| `GET /api/finance/charts/distribution` | توزیع تراکنش‌ها بر اساس نوع |
| `GET /api/finance/reports/monthly` | گزارش ماهانه شمسی (۱۲ ماه) |
| `GET /api/finance/reports/category-breakdown` | تفکیک دسته‌بندی + درصد |
| `GET /api/finance/reports/account-comparison` | مقایسه حساب‌ها |
| `GET /api/finance/reports/profit-loss` | سود/زیان ماهانه/سالانه + روند تجمعی |
| `GET /api/analytics/dashboard` → `spendable_money` | `{ net_pnl, total_balance, initial_capital }` (فاز ۲۰/۲۱) |

### گزارش‌هایی که **کم بود** (فاز ۲۲)
- تفکیک «دارایی قابل برداشت» بر اساس منبع (پراپ ۳ / بروکر / صرافی / Trust Wallet / بانک)
- سود/زیان **Real** به تفکیک منبع + تعداد معاملات
- **سود خالص** (سود Real − هزینه‌ها)
- **جریان پول** بین حساب‌ها
- تفکیک **هزینه‌ها** (خرید پراپ، اشتراک، کارمزد صرافی، کارمزد برداشت، سایر)
- **چرخهٔ پول** (واریز/برداشت/تبدیل/انتقال + موجودی)
- **تقویم مالی** شمسی
- **روند دارایی** (تجمعی USD/IRR)
- **نرخ تبدیل** IRR→USD

---

## ۱. فاز ۲۲.۱ — گزارش‌های مالی ضروری

### Backend (`backend/app/api/finance.py`)

| Endpoint | خروجی |
|---|---|
| `GET /api/finance/spendable-assets` | `prop_stage_3 / broker / exchange / trust_wallet / bank` + `total{usd,irr}` |
| `GET /api/finance/real-pnl` | `prop_stage_3{pnl,trades} / broker{pnl,trades} / total{pnl,trades}` |
| `GET /api/finance/net-profit` | `{ real_pnl, expenses, net_profit }` |

**محاسبه:**
- `prop_stage_3` (دارایی): `SUM(PROFIT) − SUM(LOSS)` تراکنش‌های حساب مالی متصل به مرحلهٔ `FUNDED_REAL`
  (مسیر: `Transaction.account_id → Account → PropAccount.finance_account_id → PropStage.prop_account_id`)
- `broker / exchange / trust_wallet / bank`: `SUM(Account.balance)` به تفکیک `AccountType`
  (`BROKER / EXCHANGE / CRYPTO_WALLET / BANK`)
- `real-pnl`: `SUM(pnl + commission + swap)` معاملات مرحلهٔ `FUNDED_REAL` و معاملات حساب بروکر
- `net-profit`: `expenses = SUM(FEE + PURCHASE)` → `net = real_pnl − expenses`

### Frontend
- `DashboardPage.tsx`: کارت **«💵 دارایی قابل برداشت»** (تفکیک + مجموع) و کارت **«🧾 سود خالص»**.
- `FinancePage.tsx`: تب **«💰 سود/زیان Real»** (کارت‌ها + جدول + سود خالص).

---

## ۲. فاز ۲۲.۲ — گزارش‌های مالی مهم

| Endpoint | خروجی |
|---|---|
| `GET /api/finance/money-flow` | `{ flows: [{ from, to, amount, currency, type, date }] }` |
| `GET /api/finance/expenses` | `prop_purchase / prop_subscription / exchange_fee / withdrawal_fee / other / total` |
| `GET /api/finance/money-cycle` | `total_deposits / total_withdrawals / total_exchanges / total_transfers / current_balance` |

**محاسبه:**
- `money-flow`: همهٔ تراکنش‌های `DEPOSIT/WITHDRAWAL/EXCHANGE` و هر تراکنش دارای مبدأ/مقصد؛ `from/to` از نوع حساب مبدأ/مقصد.
- `expenses`: تراکنش‌های `FEE/PURCHASE` با طبقه‌بندی بر اساس نوع حساب + کلیدواژه‌های دسته/توضیحات («پراپ»، «اشتراک»، «تبدیل/صرافی»، «برداشت»).
- `money-cycle`: `SUM(amount)` به تفکیک نوع + `SUM(Account.balance)`؛ `total_transfers` = تراکنش‌های دارای `from_account_id` و `to_account_id`.

**Frontend (`FinancePage.tsx`):** تب‌های **«🔀 جریان پول»** (جدول + خلاصهٔ دارایی قابل برداشت)، **«🧾 هزینه‌ها»** (کارت + نمودار میله‌ای)، **«♻️ چرخهٔ پول»** (کارت‌ها).

---

## ۳. فاز ۲۲.۳ — گزارش‌های مالی مفید

| Endpoint | خروجی |
|---|---|
| `GET /api/finance/financial-calendar` | `{ days: [{ date, pnl, trades, deposits, withdrawals }] }` |
| `GET /api/finance/asset-trend` | `{ trend: [{ date, total_usd, total_irr }] }` |
| `GET /api/finance/exchange-rates` | `{ rates: [{ date, from, to, rate }] }` |

**محاسبه:**
- `financial-calendar`: `pnl` معاملات + واریز/برداشت تراکنش‌ها، به تفکیک روز شمسی (`YYYY/MM/DD`).
- `asset-trend`: مجموع تجمعی جریان تراکنش‌ها به تفکیک ارز (DEPOSIT/PROFIT مثبت، WITHDRAWAL/LOSS/FEE/PURCHASE منفی).
- `exchange-rates`: نرخ ضمنی روزانهٔ IRR→USD از تراکنش‌های `EXCHANGE`.

**Frontend:** `FinancePage.tsx` تب‌های **«🗓️ تقویم مالی»** و **«💱 نرخ تبدیل»** + نمودار **«📈 روند دارایی»** در `DashboardPage.tsx`.

---

## ۴. فایل‌های تغییر‌یافته

| فایل | وضعیت | توضیح |
|---|---|---|
| `backend/app/api/finance.py` | ✏️ افزودن | ۹ endpoint + توابع کمکی (`_trade_net_expr`, `_jalali_date_str`, `_prop_stage3_tx_net`, `_balance_sum`, `_compute_real_pnl`, `_expenses_total`) |
| `backend/tests/test_finance.py` | ✏️ افزودن | ۱۰ تست جدید (فاز ۲۲) |
| `frontend/src/api/client.ts` | ✏️ افزودن | ۹ تابع + تایپ‌ها |
| `frontend/src/pages/DashboardPage.tsx` | ✏️ افزودن | کارت دارایی قابل برداشت + سود خالص + نمودار روند دارایی |
| `frontend/src/pages/FinancePage.tsx` | ✏️ افزودن | ۶ تب جدید + state/loader |
| **جدید** | `PHASE22_REPORT.md` | این فایل |

---

## ۵. تصمیم‌های طراحی (مهم)

1. **`prop_stage_3` در دارایی قابل برداشت** به‌صورت **خالص** (`PROFIT − LOSS`) محاسبه شد، نه فقط `PROFIT`.
   علت: «قابل برداشت» باید زیان‌ها را نیز لحاظ کند و با `broker` (که `Account.balance` خالص است) سازگار باشد.
   (در `real-pnl` نیز مطابق اسپک از `net_pnl` معاملات استفاده شده است.)
2. **`TransactionType` مقدار `TRANSFER` ندارد**؛ انتقالات در این پروژه به‌صورت `type=exchange` + `from_account_id/to_account_id` ثبت می‌شوند.
   بنابراین `money-flow` و `money-cycle` بر پایهٔ تراکنش‌های موجود + وجود مبدأ/مقصد ساخته شدند و مقادیر `type` با enum پروژه (lowercase) هم‌خوان‌اند.
3. **`exchange-rates`:** چون هر تراکنش تبدیل فقط یک مبلغ/ارز ذخیره می‌کند، نرخ از نسبت جمع مبلغ‌های IRR به USD در **همان روز شمسی** استخراج می‌شود (در داک‌استرینگ تابع مستند شده است).
4. **`asset-trend`**: تراکنش‌های `EXCHANGE` از جمع تجمعی حذف شدند تا نوسان دوطرفه ایجاد نکنند.
5. تمام گزارش‌ها فقط `is_deleted == False` را در نظر می‌گیرند و تاریخ شمسی بر پایهٔ UTC (هم‌راستا با بقیهٔ گزارش‌ها) است.

---

## ۶. تست

| تست | نتیجه |
|---|---|
| `pytest` (کل، ۶۲ تست) | ✅ **۶۲ passed** (۵۲ قبلی + ۱۰ جدید) |
| `pytest tests/test_finance.py` | ✅ همه پاس |
| `npx tsc -b --force` | ✅ exit=0 |
| `npm run build` | ✅ exit=0 (`FinancePage` ۷۱.۲۲ kB) |
| `py_compile` همه فایل‌های تغییریافته | ✅ exit=0 |
| OpenAPI — ثبت ۹ مسیر | ✅ همه موجود |

**۱۰ تست جدید:** `test_spendable_assets_empty`، `test_spendable_assets`، `test_real_pnl`، `test_net_profit`، `test_money_flow`، `test_expenses_breakdown`، `test_money_cycle`، `test_financial_calendar`، `test_asset_trend`، `test_exchange_rates`.

---

## ۷. محدودیت‌ها / فاز آینده

1. `exchange-rates` یک نرخ **ضمنی** است؛ برای نرخ دقیق، ذخیرهٔ دوطرفهٔ تبدیل (مبلغ مبدأ + مقصد) در تراکنش‌ها لازم است.
2. `expenses` طبقه‌بندی را از کلیدواژه‌های دسته/توضیحات حدس می‌زند؛ افزودن یک فیلد `expense_kind` به `Transaction` دقت را بالا می‌برد.
3. `financial-calendar` فعلاً به‌صورت گرید ساده است؛ افزودن نمای تقویم ماهانه (شبکهٔ ۷ ستونه) در فاز UI بعدی پیشنهاد می‌شود.
4. تراکنش‌های `EXCHANGE` بدون `from/to` در `money-flow` با همان حساب خودِ تراکنش نمایش داده می‌شوند.

---

*گزارش فاز ۲۲ — تهیه‌شده در ۱۴۰۵/۰۷/۰۴.*

