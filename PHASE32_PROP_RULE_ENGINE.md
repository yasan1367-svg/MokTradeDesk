# 🏢 PHASE 32 — Prop Rule Engine · AUDIT

> **نوع سند:** Audit فقط — **هیچ کدی در این فاز نوشته نشده است.**
> **دامنه:** `PropRuleEngine` + دامنهٔ پراپ (`models/prop.py`, `api/prop.py`) + اتصال‌های آن به Import/Analysis/Finance
> **تاریخ:** ۱۴۰۵/۰۷/۰۶
> **Revision فعلی:** `d4e5f6a7b8c9` (فاز ۳۰/۳۱)
> **آمادهٔ تصمیم‌گیری برای:** Phase 32 Implementation (پس از تأیید این سند)

---

## ۱. خلاصهٔ اجرایی

دامنهٔ پراپ **کار می‌کند** (۲۲ endpoint + ۱۰ تست سبز)، اما سه مسئلهٔ ساختاری دارد:

| # | مسئله | شدت |
|:--|:---|:---:|
| ۱ | **سه تعریف متفاوت از P&L** در سه نقطه: `evaluate_stage` (فقط `pnl`)، `pass_stage` (`pnl+commission+swap`)، `sync_prop_stage_profit` (`pnl × profit_share`). نتیجه: «آمادهٔ پاس»، «موجودی نهایی» و «سود نمایشی مرحله» می‌توانند سه عدد متفاوت باشند | 🔴 P0 |
| ۲ | **یکپارچگی مالی برداشت ناقص است**: ویرایش/حذف `PropWithdrawal` فقط `total_withdrawn` را اصلاح می‌کند و **نه `Transaction` را برمی‌گرداند و نه موجودی حساب مقصد را** ⇒ نشت/ناسازگاری پول بین FINANCE و پراپ | 🔴 P0 |
| ۳ | **قوانین واقعی پراپ مدل نشده‌اند**: `restrictions` (JSON) بی‌استفاده است، `FailureReason.RULE_VIOLATION` هرگز مقدار نمی‌گیرد، قوانین مرز روز معاملاتی/timezone، Trailing DD، Consistency، Daily Profit Cap و News Rule پشتیبانی نمی‌شوند | 🟠 P1 |

**امتیاز کلی دامنهٔ پراپ (ارزیابی این Audit): `۶.۵/۱۰`**

| محور | امتیاز | توضیح کوتاه |
|:---|:---:|:---|
| صحت محاسبات (DD/Target/Days) | ۶/۱۰ | منطق ساده‌سازی‌شده و بدون مرز روز معاملاتی |
| یکپارچگی مالی (پل با FINANCE) | ۵/۱۰ | ثبت اتمیک ✔ اما برگشت‌پذیری ✘ |
| یکپارچگی داده (منبع حقیقت واحد) | ۴/۱۰ | P&L دو/سه‌گانه + `current_profit` کهنه |
| پوشش قوانین پراپ | ۴/۱۰ | فقط Daily DD/Total DD/Target/Min Days |
| Audit & Observability | ۳/۱۰ | بدون تاریخچهٔ ارزیابی، هشدار بدون type/severity |
| کیفیت کد/تست | ۸/۱۰ | تمرکز منطق در یک سرویس + تست‌های سبز |

---

## ۲. روش Audit

بررسی مستقیم کد + اسکیمای **واقعی** دیتابیس (نه مستندات قدیمی):

| مورد بررسی | مسیر | حجم |
|:---|:---|:---|
| موتور قوانین | `backend/app/services/prop_rule_engine.py` | ۲۴۶ خط |
| API پراپ | `backend/app/api/prop.py` | ۱۱۰۰ خط · ۲۲ مسیر |
| مدل‌ها | `backend/app/models/prop.py` | ۱۳۵ خط · ۷ مدل |
| اسکیمای DB | `PRAGMA table_info` روی `trading_desk.db` | ۷ جدول |
| مصرف‌کننده‌ها | `services/import_engine.py`, `services/analysis_service.py`, `api/analytics.py`, `api/trades.py` | — |
| فرانت‌اند | `PropPage.tsx` (۱۶۴۸)، `DashboardPage.tsx` (۱۱۸۴)، `PayoutHistoryPage.tsx` (۴۰۸)، `client.ts` | — |
| تست‌ها | `tests/test_prop.py` (۱۰)، `test_soft_delete_filters.py`، `test_analysis_phase23.py` | — |
| اسناد طراحی | `PROP_FINANCE_INTEGRATION*.md`, `STRATEGY_PROP_ANALYSIS.md`, `FINAL_BLUEPRINT.md` | — |

---

## ۳. موجودی فعلی (Inventory)

### ۳.۱ مدل‌ها — `models/prop.py`

| مدل | جدول | فیلدهای کلیدی (وضعیت واقعی DB) |
|:---|:---|:---|
| `PropFirm` | `prop_firms` | `name`, `default_profit_share`, `website`, `notes` |
| `PropFirmDefaultRules` | `prop_firm_default_rules` | `prop_firm_id`, `stage_type`, `profit_target`, `max_daily_dd`, `max_total_dd`, `min_trading_days`, `profit_share_percentage`, `description` |
| `PropAccount` | `prop_accounts` | `prop_firm_id`, `account_label`, `account_number`, `currency(String!)`, `is_active` — **بدون** `broker_id`/`initial_balance`/قوانین |
| `PropStage` | `prop_stages` | `stage_type`, `status`, `start/end_date`, `profit_target`, `max_daily_dd`, `max_total_dd`, `min_trading_days`, `restrictions(JSON)`, `initial_balance`, `final_balance`, `profit_share_percentage`, `total_withdrawn`, `current_profit`, `failure_reason`, `failure_details` |
| `PropWithdrawal` | `prop_withdrawals` | `prop_stage_id`, `amount`, `withdrawal_date`, `note`, `destination_account_id`→`accounts.id` |
| `PropCost` | `prop_costs` | `prop_account_id`, `cost_type(String)`, `amount`, `currency(String)`, `cost_date`, `description`, `is_refunded(Integer)` |
| `PropAlert` | `prop_alerts` | `prop_stage_id`, `message(Text)`, `is_read(Integer)`, `created_at` — **بدون** type/severity/dedupe |

**Enumها:** `StageType` (STAGE_1/STAGE_2/FUNDED_REAL) · `StageStatus` (ACTIVE/PASSED/FAILED/CLOSED) · `FailureReason` (۶ مقدار).

**تغییرات فاز ۲۸ که روی پراپ اثر گذاشت:** `prop_accounts.finance_account_id` حذف شد
(`migrations/versions/c3d4e5f6a7b8_phase28_finance_cleanup.py`) و `finance_sync_service` به no-op تبدیل شد
(`services/finance_sync_service.py:26-28`) ⇒ پول فقط از مسیر **برداشت** وارد FINANCE می‌شود.
⚠️ اما `client.ts:285-290` هنوز `getPropAccountFinanceAccount`/`createPropFinanceAccount` را صدا می‌زند
که endpointشان حذف شده (`api/prop.py:1034`) ⇒ کد مرده/۴۰۴ در فرانت‌اند (یافتهٔ F-21).

### ۳.۲ `PropRuleEngine` — تنها منبع حقیقت ادعایی

| متد | خطوط | کار |
|:---|:---:|:---|
| `evaluate_stage(db, stage_id)` | ۳۴-۱۹۱ | ارزیابی کامل یک مرحله (خروجی ۲۷ فیلد) |
| `validate_withdrawal(db, stage_id, amount)` | ۱۹۴-۲۱۶ | بررسی مجاز بودن برداشت |
| `_group_daily_pnl(trades)` | ۲۲۲-۲۲۹ | جمع PnL به تفکیک روز (بر پایهٔ `close_time`) |
| `_calculate_max_drawdown(trades, initial)` | ۲۳۲-۲۴۶ | DD بر پایهٔ equity curve از معاملات بسته |

**فرمول‌های واقعی داخل موتور:**

```python
# prop_rule_engine.py
total_pnl   = sum(t.pnl or 0 for t in trades)          # L51  ← فقط pnl
daily_pnl   = _group_daily_pnl(trades)                 # L55  ← کلید = close_time[:10]
max_daily_loss = abs(min(daily_pnl.values()))          # L56  ← بدترین «سود روزانهٔ خالص»
max_total_dd   = _calculate_max_drawdown(trades, initial)   # L59
trading_days   = len(daily_pnl)                        # L62  ← روزهای دارای معاملهٔ بسته
daily_dd_violated = max_daily_loss > max_daily_dd_limit      # L71-75 (اگر limit>0)
total_dd_violated = max_total_dd   > max_total_dd_limit      # L76-80
target_reached    = total_pnl >= profit_target               # L81-83
min_days_met      = trading_days >= min_days                 # L84
user_share        = total_pnl * (profit_share / 100)         # L114
withdrawable      = max(user_share - total_withdrawn, 0)     # L115
```

**خروجی رسمی `evaluate_stage` (۲۷ فیلد — مصرف فرانت‌اند و داشبورد):**
`stage_id, stage_type, status, initial_balance, equity, current_profit, current_profit_percent, profit_target, profit_progress_percent, max_daily_loss, max_daily_dd_limit, daily_dd_progress_percent, daily_dd_violated, max_total_dd, max_total_dd_limit, total_dd_progress_percent, total_dd_violated, trading_days, min_trading_days, days_met, target_reached, ready_to_pass, suggested_status, violations, is_funded, total_withdrawn, profit_share_percentage, withdrawable_profit, total_trades`

**مصرف‌کننده‌ها:**
- `api/prop.py:340` (`GET /stages/{id}/check-pass`) + `api/prop.py:359` (`pass_stage`) + `api/prop.py:562` (`validate_withdrawal`)
- `api/analytics.py:304` (داشبورد: `progress` مراحل ACTIVE)
- `services/analysis_service.py:42` (تحلیل مرحله → `result["prop_rules"]`)
- فرانت: `PropPage.tsx` (`suggested_status`, `ready_to_pass`, `profit_progress_percent`, `trading_days`, `violations`) و `DashboardPage.tsx:839-847`

### ۳.۳ APIهای پراپ (۲۲ مسیر)

| گروه | مسیرها | وضعیت |
|:---|:---|:---|
| Firm | `GET/POST /firms`، `GET /firms/{id}/default-rules` | ✅ (قوانین پیش‌فرض فقط خواندنی) |
| Account | `GET/POST /accounts`، `GET /accounts/{id}`، `GET /accounts/{id}/costs` | ✅ |
| Stage | `GET /stages/all`، `GET /stages/{id}/check-pass`، `POST /stages/{id}/pass`، `POST /stages/{id}/fail`، `PATCH /stages/{id}/rules`، `GET /stages/{id}/trades` | ✅ |
| Payout | `POST /stages/{id}/withdraw`، `GET /stages/{id}/withdrawals`، `GET/POST /payouts`، `GET /payouts/stats`، `PUT+PATCH /payouts/{id}`، `DELETE /payouts/{id}` | ⚠️ ویرایش/حذف ناقص (F-02) |
| Alert | `GET /alerts`، `PATCH /alerts/{id}/read`، `POST /alerts/generate` | ⚠️ منطق در API (F-06) |
| Cost | `POST /costs`، `GET /accounts/{id}/costs` | ⚠️ بدون refund/Enum (F-16) |
| Analytics | `GET /analytics` | ⚠️ محاسبه در لایهٔ API (F-18) |

### ۳.۴ اتصال‌ها به سایر دامنه‌ها

| از | به | نحوهٔ اتصال | وضعیت |
|:---|:---|:---|:---:|
| Import (`import_engine.py:763-783`) | پراپ | `sync_prop_stage_profit` → `current_profit` را می‌نویسد (**با اعمال profit_share برای FUNDED_REAL**) | ⚠️ ناسازگار با موتور |
| Analysis (`analysis_service.py:33-43`) | پراپ | متریک‌ها با `_net_pnl = pnl+commission+swap` + پیوست `prop_rules` | ⚠️ دو تعریف P&L |
| Dashboard (`analytics.py:304`) | پراپ | `evaluate_stage` برای مراحل ACTIVE | ✅ |
| Trades (`api/trades.py:381-392`) | پراپ | ویرایش معامله ⇒ `prop_stage_id` قابل تغییر؛ فقط Trade Contract چک می‌شود | ⚠️ بدون چک وضعیت مرحله |
| Payout (`api/prop.py:605-617`) | FINANCE | `Transaction(WITHDRAWAL)` + `dest.balance += amount` | ✅ ثبت / ✘ برگشت |
| Cost (`api/prop.py:1000-1014`) | FINANCE | `Transaction(PURCHASE)` + `payer.balance -= amount` | ✅ |
| `current_profit` | همه | فقط در Import به‌روزرسانی می‌شود (نه پس از ویرایش/حذف/بازیابی معامله) | ⚠️ کهنه می‌شود |

### ۳.۵ تست‌ها

| فایل | تعداد | پوشش |
|:---|:---:|:---|
| `tests/test_prop.py` | ۱۰ | `_group_daily_pnl`, `_calculate_max_drawdown`, `evaluate_stage` (no-trades/ready/daily-dd/missing), `validate_withdrawal` (not-funded/positive), `funded_withdrawable_profit`, ۲ endpoint |
| `tests/test_soft_delete_filters.py` | ۲ مرتبط | `test_prop_rule_engine_excludes_deleted`, `test_prop_stage_trades_excludes_deleted` |
| `tests/test_analysis_phase23.py` | ۲ مرتبط | استقلال مراحل پراپ + trades مرحله |

**آنچه تست ندارد:** `pass_stage`/`fail_stage`، `withdraw`/payout CRUD (ویرایش/حذف)، `costs`، alerts، `create_account`، رگرسیون P&L در سه نقطهٔ مختلف، رفتار `StageStatus`.

---

## ۴. یافته‌های Audit

### 🔴 P0 — باید قبل از هر قابلیت جدید رفع شوند

#### F-01 · سه تعریف متفاوت از P&L (Divergence منبع حقیقت)

| نقطه | فرمول | شاهد |
|:---|:---|:---|
| `PropRuleEngine.evaluate_stage` | `sum(pnl)` | `prop_rule_engine.py:51` |
| `pass_stage` (موجودی نهایی) | `sum(pnl + commission + swap)` | `api/prop.py:376-380` |
| `sync_prop_stage_profit` (Import) | `sum(pnl)` و برای FUNDED_REAL **`× profit_share/100`** | `import_engine.py:771-781` |
| `AnalysisService` (متریک پراپ) | `net_pnl = pnl + commission + swap` | `analysis_service.py:457-459, 663-665` |

**اثر:** یک مرحله با کمیسیون/سوآپ منفی می‌تواند در UI «آمادهٔ پاس» باشد ولی `final_balance` کمتر
از هدف ثبت شود؛ `current_profit` ذخیره‌شده در DB برای مرحلهٔ رییل **۸۰٪** سود است در حالی که
`prop_rules.current_profit` همان مرحله **۱۰۰٪** را نشان می‌دهد. داشبورد نمودار مذاکره‌ای بسته به
این‌که از کدام مسیر بخواند دو عدد برمی‌گرداند.

**پیشنهاد:** تعریف واحد `net_pnl = pnl + commission + swap` در یک ماژول مشترک
(`app/utils/trade_metrics.py`-style) + `PropMetricsService`؛ `current_profit` همیشه **خام** ذخیره شود،
سهم کاربر (`user_share_profit`) **محاسبه‌ای** بماند؛ `evaluate_stage` و `pass_stage` هر دو از همان تابع.

---

#### F-02 · برداشت (Payout): برگشت‌پذیری مالی وجود ندارد

| عملیات | `PropWithdrawal` | `total_withdrawn` | `Transaction` | موجودی حساب مقصد |
|:---|:---:|:---:|:---:|:---:|
| ثبت (`_create_payout_record`) | ✅ ساخت | ✅ `+= amount` | ✅ ساخت | ✅ `+= amount` |
| ویرایش مبلغ (`update_payout`) | ✅ تغییر | ✅ اصلاح delta | ❌ **بدون تغییر** | ❌ **بدون اصلاح** |
| حذف (`delete_payout`) | ✅ حذف | ✅ `-= amount` (کف صفر) | ❌ **باقی می‌ماند** | ❌ **باقی می‌ماند** |

شواهد: `api/prop.py:786-789` (delta روی `total_withdrawn`)، `api/prop.py:819-829` (حذف بدون reverse).
همچنین `destination_account_id` در ویرایش فقط وجود حساب را چک می‌کند و اگر مقصد **عوض** شود،
پول در حساب قدیمی می‌ماند (`api/prop.py:801-806`).

**اثر:** ناسازگاری حسابداری (FINANCE) با واقعیت؛ گزارش‌های مالی/تقویم مالی/`/real-pnl` عدد اشتباه
نشان می‌دهند؛ حذف اشتباهی payout قابل جبران نیست.

**پیشنهاد:** یک `PayoutService` با سه تضمین: (۱) `transaction_id` روی `PropWithdrawal` ذخیره شود،
(۲) ویرایش = revert تراکنش قبلی + ساخت تراکنش جدید در همان تراکنش DB، (۳) حذف = reversal (یا
soft-delete با ماهیت reversal) و به‌روزرسانی موجودی هر دو طرف؛ همه در یک commit.

---

#### F-03 · `current_profit` منتشر شده از مسیرهای دیگر به‌روزرسانی نمی‌شود

تنها نویسندهٔ `stage.current_profit` تابع `sync_prop_stage_profit` در Import است
(`import_engine.py:763-783`, فراخوانی در `import_engine.py:953-954`). هیچ‌کدام از این‌ها آن را sync نمی‌کنند:

- ویرایش معامله (`PATCH /api/trades/{id}` — مثلاً تغییر `pnl` یا انتقال معامله به مرحلهٔ دیگر)
- حذف نرم / بازیابی / حذف کامل معامله (فاز ۲۵/۲۶)
- حذف groupی معاملات (`POST /api/trades/batch-delete`)
- تراکنش `pass_stage` (که `final_balance` را ست می‌کند ولی `current_profit` را نه)

**اثر:** مقادیر کهنه در `GET /accounts/{id}` (`api/prop.py:287`) و در هر مصرف‌کننده‌ای که از DB می‌خواند؛
دو منبع حقیقت برای سود مرحله.

**پیشنهاد:** `current_profit` از فیلد ذخیره‌شده حذف (یا به «derived cache» با TTL تبدیل) شود و
`evaluate_stage` تنها مسیر خواندن باشد؛ اگر باقی می‌ماند، همهٔ مسیرهای تغییر معامله باید آن را sync کنند
(مشترک با فاز ۳۰: هوک روی `Trade`).

---

#### F-04 · مرز «روز معاملاتی» و Timezone مدل نشده

- `_group_daily_pnl` روز را با `trade.close_time.strftime("%Y-%m-%d")` می‌سازد (`prop_rule_engine.py:227`)
  ⇒ مرز نیمه‌شب **UTC**؛ شرکت‌های پراپ روز را بر اساس **زمان سرور بروکر** (معمولاً ۱۷:۰۰ NY) می‌بندند.
- `max_daily_loss = abs(min(daily_pnl))` **سود خالص روز** است، نه DD از «بالاترین equity روز» یا
  «موجودی ابتدای روز» — تفاوت این دو در معاملات سودآور/زیان‌ده درون‌روزی همان روز بزرگ است.
- معاملات باز (floating) و افت سرمایهٔ بین معاملات لحاظ نمی‌شود.

**اثر:** Daily DD ممکن است **کم‌برآورد** شود ⇒ اعلام «آمادهٔ پاس» روی مرحله‌ای که در واقع نقض شده،
یا هشدارهای دیرهنگام.

**پیشنهاد:** افزودن `PropAccount.daily_reset_time` + `daily_reset_tz` (+ استفاده از `UserSettings.timezone`) و
تعریف رسمی `trading_day(ts, reset_time, tz)`؛ محاسبهٔ DD روزانه بر پایهٔ `max(peak_intraday - equity)`.

---

#### F-05 · وضعیت مرحله (`StageStatus`) در ارزیابی و انتقال‌ها لحاظ نمی‌شود

- `evaluate_stage` هیچ شرطی روی `stage.status` ندارد (`prop_rule_engine.py:34-191`) ⇒ مرحلهٔ
  **FAILED/PASSED/CLOSED** هم می‌تواند `ready_to_pass=True` برگرداند.
- `pass_stage` فقط `FUNDED_REAL` را رد می‌کند (`api/prop.py:355-356`)؛ **مرحلهٔ پاس‌شده دوباره پاس می‌شود**
  (ساخت مرحلهٔ بعدی تکراری)، و مرحلهٔ **فیل‌شده** هم قابل پاس‌کردن است (اگر معیارها برآورده شوند).
- `fail_stage` مرحلهٔ PASSED را هم فیل می‌کند (`api/prop.py:420-437`).
- هیچ نگهبان «یک مرحلهٔ ACTIVE در هر حساب» وجود ندارد ⇒ می‌توان چند مرحلهٔ هم‌زمان فعال ساخت.
- `StageStatus.CLOSED` در هیچ مسیری ست نمی‌شود (مقدار مرده در Enum).

**اثر:** دادهٔ متناقض (دو مرحلهٔ ACTIVE)، آمادهٔ پاس‌شدن مرحلهٔ مرده، شمارش‌های `analytics` خراب.

**پیشنهاد:** ماشین حالت صریح:
`ACTIVE → PASSED | FAILED | CLOSED`، `PASSED/FAILED/CLOSED → terminal (فقط با reopen صریح)`،
قید «یک ACTIVE به ازای هر `prop_account_id`» (unique partial index) و رد ارزیابی برای وضعیت‌های terminal.

---

### 🟠 P1 — اثر مستقیم بر دقت/یکپارچگی قوانین

#### F-06 · منطق هشدارها در لایهٔ API است، نه در موتور

`_generate_alerts_for_stage` (`api/prop.py:835-914`) آستانه‌های **۸۰٪/۹۰٪/۱۰۰٪** را hardcode کرده و
پیام‌های فارسی می‌سازد؛ dedupe با جست‌وجوی **زیررشتهٔ پیام** انجام می‌شود
(`PropAlert.message.contains("Daily DD نقض")` — `api/prop.py:864, 888, 903`). این نقض مستقیم
قرارداد خودِ موتور است («هیچ‌جای دیگه نباید این منطق رو دوباره پیاده کنه» — `prop_rule_engine.py:24`).

**اثر:** تغییر آستانه یا متن پیام ⇒ هشدارهای تکراری/گم‌شده؛ تست‌پذیری صفر؛ نبود severity/type.
**پیشنهاد:** انتقال به `PropAlertService` با `PropAlertType` + `AlertSeverity` + کلید یکتای
`dedupe_key = "{stage_id}:{type}:{period_key}"` و `message` فقط برای نمایش.

#### F-07 · هیچ تاریخچه/اسنپ‌شات ارزیابی وجود ندارد

دامنهٔ استراتژی `AnalysisRun` دارد (تاریخچهٔ اجراها)، اما پراپ صفر رکورد تاریخی دارد؛ نه
«قوانین در آن تاریخ چه بودند» قابل بازسازی است، نه «چرا این مرحله پاس/فیل شد» (فقط `final_balance`
و `failure_reason` ذخیره می‌شود). `pass_stage` هم قوانین مرحلهٔ بعد را از ورودی کاربر می‌گیرد و هیچ
snapshot از قوانین مرحلهٔ قبل نگه نمی‌دارد.

**اثر:** غیرقابل audit؛ `PATCH /stages/{id}/rules` تاریخچه را بازنویسی می‌کند.
**پیشنهاد:** جدول `prop_stage_snapshots` (در هر ارزیابی/روزانه/در لحظهٔ pass-fail) + `rules_json` snapshot.

#### F-08 · قرارداد قوانین ناقص است (`restrictions` بی‌استفاده)

`PropStage.restrictions` (JSON) هیچ‌جا خوانده/نوشته نمی‌شود، و `FailureReason.RULE_VIOLATION` هرگز
مقدار نمی‌گیرد. قوانین رایج شرکت‌ها که مدل نشده‌اند:

| قانون | وضعیت |
|:---|:---:|
| Daily DD / Total DD / Target / MinDays (دلاری) | ✅ |
| **Trailing DD** (equity-high) یا Static/Intraday DD | ❌ |
| **Consistency Rule** (سقف سهم یک روز از کل سود) | ❌ |
| **Daily Profit Cap** | ❌ |
| **Max Lot / Max Positions / Max Risk per Trade** | ❌ |
| **News Trading / Weekend Holding / Hedging Ban** | ❌ |
| پنجرهٔ ساعتی معاملات (Trading Window) | ❌ |
| **Refundable Fee** و شرط بازگشت هزینهٔ چلنج | ❌ (`PropCost.is_refunded` بی‌استفاده) |

**پیشنهاد:** `PropRules` نوعدار (Pydantic + JSON) و `violations` ساختاری
(`{code, rule, severity, message, evidence}`) به‌جای رشتهٔ فارسی؛ `FailureReason` از `violations[].code` مشتق شود.

#### F-09 · قوانین پیش‌فرض شرکت (PropFirmDefaultRules) ناقص است

- فقط `GET /firms/{id}/default-rules`؛ **CRUD/seed** ندارد (`api/prop.py:169-191`).
- قوانین شرکت به مرحله **کپی نمی‌شوند** (فقط auto-fill سمت فرانت) ⇒ تغییر پیش‌فرض‌ها مراحل قدیم را دست نمی‌زند.
- بدون version/`effective_from` ⇒ نمی‌توان فهمید مرحله با کدام نسخهٔ قوانین ساخته شده.

**پیشنهاد:** CRUD + seed + لینک `PropStage.rules_source_id` به نسخهٔ قوانین (+ snapshot در F-07).

#### F-10 · اتمیک‌بودن ناقص در `pass_stage` و نبود idempotency در عملیات پولی

- `pass_stage` **دو commit** دارد: وضعیت مرحله (`api/prop.py:386`) و بعد ساخت مرحلهٔ بعد
  (`api/prop.py:410-411`) ⇒ اگر commit دوم شکست بخورد، مرحله PASSED است ولی مرحلهٔ بعدی ساخته نشده.
- `withdraw`/`payouts`/`costs` تک‌commit هستند ✔ اما هیچ **Idempotency-Key** ندارند؛
  دوبار کلیک/retry ⇒ دو برداشت و دو تراکنش.
- هم‌زمانی: منطق خواندن-قبل-از-نوشتن است؛ دو برداشت هم‌زمان می‌توانند سقف `withdrawable` را رد کنند.

**پیشنهاد:** `pass_stage` در یک تراکنش؛ هدر اختیاری `Idempotency-Key` برای `POST /payouts` و
`POST /costs` با جدول `idempotency_keys(key, scope, request_hash, response_json)`.

#### F-11 · `PropAccount` با دامنهٔ TRADING فاز ۲۸ هم‌راستا نیست

| نیاز | `PersonalTradingAccount` | `PropAccount` |
|:---|:---:|:---:|
| `broker_id` (بروکر مجری) | ✅ | ❌ |
| `initial_balance` / `current_balance` | ✅ | ❌ (روی مرحله است) |
| `currency` تایپ‌دار (Enum) | ✅ | ❌ (String) |
| یکتایی `account_number` | ❌ | ❌ |
| `account_label` | ✅ | ✅ |

**اثر:** دو مدل موازی «حساب معاملاتی»؛ پول واقعی پراپ (خرید/برداشت) در هیچ حساب معاملاتی خودش دیده نمی‌شود.
**گزینه‌ها:** (الف) افزودن `broker_id`/`initial_balance`/`currency Enum` به `PropAccount` (کم‌ریسک)،
(ب) یکسان‌سازی به `TradingAccount(kind=personal|prop)` (پرمخاطره — مهاجرت دادهٔ `trades`).

#### F-12 · پول با `Float` و `cost_type` با `String` آزاد

همهٔ مبالغ پراپ `Float` هستند در حالی که بلوپرینت «Decimal برای Money» را باقی‌مانده می‌داند؛
`cost_type` رشتهٔ آزاد است (`api/prop.py:972`: `lower() == "purchase"`) ⇒ خطر غلط تایپی؛
`PropCost.currency` و `PropAccount.currency` هم `String` هستند نه `Currency`.

#### F-13 · `PropAlert` بدون قرارداد (type/severity/read_at) و `is_read` Integer

`is_read = Column(Integer, default=0)` (`models/prop.py:133`) با پاک‌سازی فاز ۲۸ (Boolean کردن `is_active`ها)
ناسازگار است؛ بدون `type/severity/read_at/dedupe_key` ⇒ فیلتر/گروه‌بندی هشدار در UI ممکن نیست.

#### F-14 · `GET /stages/{id}/check-pass` عوارض جانبی دارد

این GET هشدار می‌سازد و DB را تغییر می‌دهد (`api/prop.py:336-343`) ⇒ غیر idempotent؛
هر باز شدن مودال یک نوشتن؛ رفتار غیرقابل پیش‌بینی در retry/کش.
**پیشنهاد:** GET خالص + نقطهٔ رویداد (پس از Commit ایمپورت/ویرایش معامله) یا `POST .../alerts/refresh`.

#### F-15 · نبود Rate Limit در مسیرهای پول‌محور و سنگین پراپ

`api/prop.py` هیچ `@limiter.limit` ندارد (برخلاف `api/imports.py`، `api/export.py`) در حالی که
`/payouts`, `/costs`, `/stages/{id}/withdraw` عملیات مالی انجام می‌دهند.

#### F-16 · `PropCost` بدون refund، بدون مرحله، بدون تاریخ قابل‌ویرایش

- `is_refunded` هرگز ست نمی‌شود؛ جریان refund وجود ندارد.
- `cost_date` در `PropCostCreate` نیست (`api/prop.py:127-134`) و مدل `default=now` می‌گذارد
  ⇒ هزینهٔ گذشته (خرید چلنج ماه قبل) با تاریخ اشتباه ثبت می‌شود.
- هزینه به `PropAccount` می‌چسبد نه به مرحله ⇒ تحلیل «هزینه به ازای هر چلنج/مرحله» ممکن نیست.

---

### 🔵 P2 — بدهی فنی

| # | یافته | شاهد |
|:--|:---|:---|
| F-17 | DD بر پایهٔ معاملات بسته و ترتیب `close_time`؛ بدون floating equity و بدون تفکیک intraday/daily/static | `prop_rule_engine.py:232-246` |
| F-18 | آمار `/prop/analytics` در لایهٔ API محاسبه می‌شود | `api/prop.py:1038-1100` |
| F-19 | اعداد جادویی: `initial_balance or 10000.0`، `profit_share or 80.0`، آستانه‌های هشدار | `prop_rule_engine.py:50, 110` · `import_engine.py:778` |
| F-20 | `delete_payout` با `max(..., 0)` ناسازگاری را پنهان می‌کند | `api/prop.py:823-825` |
| F-21 | کد مردهٔ فرانت: `getPropAccountFinanceAccount`/`createPropFinanceAccount` (endpoint حذف شده) | `client.ts:285-290` · `api/prop.py:1034` |
| F-22 | `passStage` و `passStageWithRules` کنار هم ⇒ مسیر بدون قوانین مرحلهٔ بعد | `client.ts:261, 305` |
| F-23 | `PropFirm.default_profit_share` عملاً بی‌اثر است (موتور فقط `stage.profit_share_percentage or 80` را می‌خواند) | `models/prop.py:33` · `prop_rule_engine.py:110` |
| F-24 | `destination_account_id` در مدل nullable است (ناسازگار با الزام API) + نبود ایندکس روی `prop_stage_id`/`withdrawal_date` | `models/prop.py:108` |
| F-25 | بدون soft-delete برای پراپ؛ حذف `PropAccount` مراحل/هزینه‌ها را cascade می‌کند اما تراکنش‌ها/برداشت‌ها یتیم می‌مانند | `models/prop.py:69-70, 96-97` |
| F-26 | `evaluate_stage` همهٔ معاملات را در ORM می‌خواند (بدون aggregate در SQL)؛ در داشبورد برای هر مرحلهٔ ACTIVE یک‌بار | `api/analytics.py:300-306` |

### ۴.۱ جمع‌بندی اولویت‌ها

| اولویت | تعداد | یافته‌ها | اثر تجاری |
|:---:|:---:|:---|:---|
| 🔴 P0 | ۵ | F-01…F-05 | عدد اشتباه در تصمیم پاس/فیل و پول (برداشت) |
| 🟠 P1 | ۱۱ | F-06…F-16 | پوشش قوانین، audit، اتمیک، انطباق با فاز ۲۸ |
| 🔵 P2 | ۱۰ | F-17…F-26 | بدهی فنی/تمیزی |

**ترتیب پیشنهادی اجرا:** F-01 → F-02 → F-05 → F-03 → F-04 → F-06/F-07 → بقیهٔ P1 → P2.

---

## ۵. قرارداد جدید — Prop Domain Contract v2 (پیشنهادی، بدون کد)

### ۵.۱ اصول حاکم

| اصل | تعریف | چگونه اعمال می‌شود |
|:---|:---|:---|
| **C-1 · یک تعریف P&L** | `net_pnl(t) = pnl + commission + swap` — تنها فرمول مجاز در کل پروژه | ماژول مشترک (`trade_metrics`/`money`)؛ `PropRuleEngine`, `pass_stage`, `sync_prop_stage_profit`, `analysis_service` همه از آن استفاده کنند |
| **C-2 · منبع حقیقت واحد** | `PropRuleEngine` تنها جایی است که «قانون» تفسیر می‌شود؛ **هیچ محاسبهٔ قاعده‌ای در `api/prop.py`** | انتقال آستانه‌های هشدار و آمار `/analytics` به سرویس (F-06, F-18) |
| **C-3 · هیچ مقدار مشتق‌شدهٔ ذخیره‌شده** | سود/سهم کاربر = **محاسبه‌ای** (یا derived cache با `refreshed_at` + هوک اجباری) | حذف/کش‌کردن `PropStage.current_profit` (F-03) |
| **C-4 · پول با دقت ثابت** | مبالغ با `Numeric(18,2)`؛ گردکردن فقط در لایهٔ نمایش | مهاجرت F-12 |
| **C-5 · عملیات پولی: اتمیک + idempotent + قابل‌برگشت** | یک تراکنش DB + `transaction_id` روی رکورد پراپ + reversal به‌جای mutation کور | F-02, F-10 |
| **C-6 · ماشین حالت صریح** | `StageStatus` با انتقال‌های مجاز؛ ارزیابی برای وضعیت‌های terminal ممنوع | F-05 |
| **C-7 · روز معاملاتی = تابع(زمان سرور بروکر)** | ذخیره UTC، گروه‌بندی روزانه با `trading_day(ts, reset_time, tz)` | F-04 |
| **C-8 · violations ساختاری** | `{code, rule, severity, message, evidence}` به‌جای رشتهٔ فارسی | F-08 |
| **C-9 · هر تغییر قاعده ⇒ snapshot** | `prop_stage_snapshots` + `rules_json` | F-07 |
| **C-10 · هم‌راستایی با TRADING فاز ۲۸** | `PropAccount` با `broker_id` + ارز Enum؛ پل به FINANCE فقط برای پول واقعی | F-11 |

---

### ۵.۲ مدل دادهٔ پیشنهادی (دلتا نسبت به وضعیت فعلی)

#### `PropFirm` — بدون تغییر ساختاری
فقط: `default_profit_share` واقعاً استفاده شود (F-23) و به قوانین پیش‌فرض شرکت هم منتقل شود.

#### `PropFirmDefaultRules` — «نسخهٔ قوانین شرکت»
```text
+ rules_version   Integer        (افزایشی به ازای هر شرکت)
+ effective_from  DateTime
+ is_active       Boolean
+ rules_json      JSON           ← قرارداد typed؛ ستون‌های دلاری فعلی بهعنوان cache نمایش میمانند
```
+ CRUD کامل (`POST/PATCH/DELETE /api/prop/firms/{id}/default-rules`) + `seed` قالب شرکت‌ها + لینک مرحله به نسخه.

#### `PropAccount` — هم‌ترازی با TRADING
```text
+ broker_id        FK brokers.id (nullable ابتدا، الزامی پس از backfill)
+ currency         Currency Enum   (مهاجرت از String)
+ initial_balance  Numeric(18,2)  (پیش‌فرض مرحله ۱)
+ current_balance  Numeric(18,2)  (نمایشی — منبع حقیقت همان مراحل است)
+ daily_reset_time Time  (HH:MM، پیش‌فرض 00:00)
+ daily_reset_tz   String (IANA، پیش‌فرض از UserSettings.timezone)
+ UniqueConstraint(prop_firm_id, account_number)
```

#### `PropStage` — قوانین داده‌محور + حالت
```text
+ rules_json      JSON      ← PropRules نوعدار (جانشین restrictions بیاستفاده)
+ rules_source_id FK prop_firm_default_rules.id
+ stage_index     Integer   (۱،۲،۳… برای نمایش/سورت)
+ closed_at       DateTime  (بهجای/کنار end_date)
  initial_balance / final_balance / profit_target / max_* → Numeric(18,2)
- current_profit  → حذف از منبع حقیقت (derived) یا cache با refreshed_at
```
قیدهای DB: `UniqueConstraint(prop_account_id, stage_type)` + **index یکتا برای «حداکثر یک ACTIVE در هر حساب»**.

#### `PropRules` — قرارداد نوعدار قوانین (پیشنهاد نهایی)
```json
{
  "dd": {
    "daily": {"limit": 500.0, "type": "static|intraday|trailing", "basis": "balance|equity"},
    "total": {"limit": 1000.0, "type": "static|trailing", "basis": "balance|equity"}
  },
  "profit_target": 800.0,
  "target_type": "absolute|percent",
  "min_trading_days": 5,
  "daily_profit_cap": null,
  "consistency": {"max_single_day_share_percent": null, "min_days_required": null},
  "risk": {"max_lot": null, "max_positions": null, "max_risk_percent_per_trade": null},
  "session": {"windows": [], "news_blackout": false, "weekend_holding": false},
  "payout": {"profit_share_percent": 80.0, "min_payout": 0, "frequency": "on_request"}
}
```
هر کلید اختیاری ⇒ نبودش یعنی «این قانون تعریف نشده و بررسی نمی‌شود» (بدون خطا) — سازگار با مراحل موجود.

#### `PropAlert` — typed + dedupe
```text
+ type        Enum(PropAlertType)   # DAILY_DD_WARNING | DAILY_DD_BREACH | TOTAL_DD_WARNING | TOTAL_DD_BREACH
                                   # TARGET_NEAR | CONSISTENCY_RISK | MIN_DAYS_PENDING | PAYOUT_ELIGIBLE | COST_REFUND_DUE
+ severity    Enum(AlertSeverity)  # INFO | WARNING | CRITICAL
+ dedupe_key  String UNIQUE         # "{stage_id}:{type}:{period_key}"
+ read_at     DateTime nullable
  is_read     → Boolean (مهاجرت از Integer)
+ payload     JSON nullable         # اعداد/شواهد برای UI
```

#### `PropWithdrawal` — یکپارچگی مالی
```text
+ transaction_id  FK transactions.id (nullable برای دادههای قدیمی)
+ is_reversed     Boolean
+ reversed_by_id  FK prop_withdrawals.id (nullable — رکورد جبرانی)
+ fee_amount      Numeric(18,2) default 0
+ tax_amount      Numeric(18,2) default 0
+ status          Enum(PENDING | PAID | REVERSED)
  destination_account_id → NOT NULL (همراستا با API)
+ index (prop_stage_id, withdrawal_date)
```

#### `PropCost` — typed + refund + مرحله
```text
+ cost_type    Enum(PURCHASE | RESET | ADDON | DATA_FEE | REFUND | OTHER)
+ stage_id     FK prop_stages.id (nullable)
+ currency     Currency Enum
+ cost_date    → قابل تنظیم از ورودی (نه فقط now)
+ refund_of_id FK prop_costs.id (nullable) ← refund با رکورد جبرانی
  is_refunded  → Boolean (derived cache، همگام با refund_of_id)
```

#### جدول‌های جدید
```text
prop_stage_snapshots(
  id, stage_id, taken_at,
  trigger ENUM(EVALUATION | DAILY | PASS | FAIL | RULE_CHANGE),
  rules_json, metrics_json, violations_json, ready_to_pass, suggested_status
)

idempotency_keys(key, scope, request_hash, response_json, created_at)   # فقط مسیرهای پولی
```

---

### ۵.۳ قرارداد موتور (خروجی `evaluate_stage` نسخهٔ ۲)

```text
PropEvaluation = {
  stage:   { id, stage_type, status, stage_index, started_at, closed_at, initial_balance },
  metrics: { net_pnl, gross_pnl, commission, swap, equity, peak_equity,
             worst_day_loss, worst_day_key, trading_days, last_trade_at },
  rules:   { profit_target, target_reached, profit_progress_percent,
             daily_dd: {limit, type, used, used_percent, violated},
             total_dd: {limit, type, used, used_percent, violated},
             min_trading_days, days_met, daily_profit_cap, cap_violated,
             consistency: {percent_used, limit, violated} },
  funded:  { is_funded, profit_share_percent, user_share_profit, total_withdrawn, fees, taxes,
             withdrawable_profit, payout_eligible },
  verdict: { ready_to_pass, suggested_status,
             violations: [ {code, rule, severity, message, evidence} ] },
  meta:    { computed_at, trades_count, timezone, daily_reset_time, rules_source }
}
```

**قواعد الزامی نسخهٔ ۲:**

1. `net_pnl` با تعریف C-1 در همهٔ مسیرها یکسان باشد؛ `gross_pnl` فقط نمایشی.
2. فیلد `current_profit` خروجی = **`net_pnl` خام** و سهم کاربر جدا (`user_share_profit`) ⇒ پایان F-01.
3. `status ∈ {PASSED, FAILED, CLOSED}` ⇒ همیشه `ready_to_pass = false` (F-05).
4. مرحلهٔ غیررییل: `withdrawable_profit = 0`, `payout_eligible = false`؛ مرحلهٔ رییل: `ready_to_pass = false`.
5. `suggested_status` جدید: `failed_daily_dd | failed_total_dd | failed_consistency | failed_daily_cap |
   ready_to_pass | in_progress | terminal`.
6. **سازگاری با نسخهٔ ۱:** هر ۲۷ فیلد فعلی حفظ شوند (فرانت‌اند و داشبورد نشکنند) و فیلدهای جدید **اضافه** شوند.
7. کارایی: محاسبه با aggregate در SQL یا cache روزانه — هدف: ارزیابی یک مرحله در تعداد کوئری ثابت (رفع F-26).

### ۵.۴ قرارداد API نسخهٔ ۲

| مسیر فعلی | تغییر قرارداد | سازگاری با UI فعلی |
|:---|:---|:---:|
| `GET /stages/{id}/check-pass` | **بدون side effect** + خروجی سوپرست نسخهٔ ۲ | ✅ |
| `POST /stages/{id}/alerts/refresh` | 🆕 تولید هشدار idempotent (با `dedupe_key`) | 🆕 |
| `POST /stages/{id}/pass` | یک تراکنش + رد وضعیت غیر ACTIVE + اعتبارسنجی `next_stage_rules` | ⚠️ درخواست‌های غیرمجاز فعلی ۴۰۰ می‌گیرند (رفتار درست) |
| `POST /stages/{id}/fail` | فقط از `ACTIVE` + پذیرش `violations[]` سیستماتیک | ⚠️ |
| `POST /payouts` · `POST /costs` | پذیرش `Idempotency-Key` + ثبت `transaction_id` + `fee/tax` | ✅ |
| `PATCH/PUT /payouts/{id}` | revert + re-apply مالی در یک تراکنش | ✅ (پاسخ یکسان) |
| `DELETE /payouts/{id}` | reversal + اصلاح تراکنش/موجودی | ✅ |
| `GET /analytics` | محاسبه در سرویس + افزودن `net_pnl`/`costs`/`payouts` ساختاریافته | ✅ سوپرست |
| `GET /firms/{id}/default-rules` (+CRUD) | نسخه‌دار و قابل‌نوشتن | ✅ |
| `GET /stages/{id}/snapshots` | 🆕 تاریخچهٔ ارزیابی | 🆕 |
| پاک‌سازی | حذف/اصلاح توابع مردهٔ فرانت (F-21) و یکی‌کردن `passStage`/`passStageWithRules` (F-22) | ✅ |

### ۵.۵ قرارداد اتمیک/idempotent (F-02, F-10)

```text
PayoutService.create(stage_id, amount, destination_account_id, *, fee=0, tax=0, idempotency_key=None)
  ├─ validate: stage ACTIVE + FUNDED_REAL + PropRuleEngine.validate_withdrawal(net_amount)
  ├─ single transaction: PropWithdrawal(+transaction_id) + Transaction(WITHDRAWAL) + dest.balance += net
  └─ sync: total_withdrawn (derived از Σ برداشتهای غیر-reversed) — یا cache همگامشده

PayoutService.update(id, ...)  → revert تراکنش قبلی (reversal) + اعمال state جدید + سینک سقف
PayoutService.delete(id)       → reversal کامل (تراکنش + موجودی)، نه حذف خام
CostService.create(...)        → همان الگو + پشتیبانی `refund_of_id` برای بازگشت هزینهٔ چلنج
```

---

## ۶. برنامهٔ مهاجرت (Migration Plan)

> ⚠️ همهٔ مراحل **پیشنهادی** هستند و بدون تأیید شما اجرا نمی‌شوند. ترتیب به‌گونه‌ای است که هر مرحله
> مستقل قابل تحویل و Rollback باشد. یک Alembic revision برای هر مرحله (نام‌گذاری `phase32_*`).

### M0 — پیش‌نیاز (بدون کد محصول)
| کار | جزئیات |
|:---|:---|
| Backup | `trading_desk.db.bak_phase32_pre` (روش استفاده‌شده در فاز ۳۰: SQLite backup API) |
| تست طلایی (Golden Test) | ۵ سناریوی مرجع برای پوشش F-01/F-02/F-05/F-10 (قبل از تغییر، رفتار فعلی را قفل می‌کند) |
| شمارش فعلی | `SELECT count(*)` روی ۷ جدول پراپ + `SELECT count(*) FROM transactions WHERE type='WITHDRAWAL'` به‌عنوان خط پایه |
| معیار خروج | تست‌ها سبز + خط پایه ثبت‌شده |

### M1 — یکسان‌سازی P&L (F-01, F-03) 🔴
| مورد | جزئیات |
|:---|:---|
| تغییر کد | تابع مشترک `net_pnl`؛ `PropRuleEngine.evaluate_stage`، `pass_stage`، `sync_prop_stage_profit` و `analysis_service` همه از آن استفاده کنند |
| حذف سهم کاربر از `current_profit` | `sync_prop_stage_profit` دیگر `× profit_share` نکند؛ سهم فقط در خروجی محاسبه شود |
| migration | فقط **داده**: recompute `prop_stages.current_profit` برای همهٔ مراحل = `Σ net_pnl` (بدون تغییر اسکیما) |
| اثر روی UI | `PropPage`/`Dashboard` برای مرحلهٔ رییل عدد خام را می‌بینند (سهم به‌صورت جداگانه در `user_share_profit` نمایش داده شود) |
| ریسک | تغییر عدد نمایشی مرحلهٔ رییل ⇒ نیاز به هماهنگی فرانت (افزودن فیلد، نه تغییر فیلد موجود) |
| معیار خروج | سه نقطه عدد یکسان بدهند + تست رگرسیون P&L |

### M2 — قواعد اتمیک و ماشین حالت (F-05, F-10) 🔴
| مورد | جزئیات |
|:---|:---|
| migration | `prop_stages`: `+ stage_index`, `+ closed_at`, `+ rules_json`; index یکتا برای یک ACTIVE در هر حساب؛ `UniqueConstraint(prop_account_id, stage_type)` (با تمیزکاری داده‌های تکراری موجود) |
| کد | نگهبان انتقال وضعیت + یک‌تراکنشی‌کردن `pass_stage` + رد ارزیابی برای terminal |
| backfill | `stage_index` از نوع مرحله؛ `closed_at = end_date`؛ `rules_json` از ستون‌های دلاری فعلی |
| ریسک | داده‌ی موجود با «چند ACTIVE در یک حساب» ⇒ migration باید تصمیم بگیرد (پیشنهاد: قدیمی‌ترها `CLOSED`) |
| معیار خروج | تست: pass دوباره ۴۰۰/۴۰۹، دو ACTIVE ۴۰۰، ارزیابی مرحلهٔ FAILED ⇒ `ready_to_pass=false` |

### M3 — یکپارچگی مالی برداشت/هزینه (F-02) 🔴
| مورد | جزئیات |
|:---|:---|
| migration | `prop_withdrawals`: `+ transaction_id`, `+ status`, `+ fee_amount`, `+ tax_amount`, `+ is_reversed`, `+ reversed_by_id` + NOT NULL کردن `destination_account_id` + ایندکس‌ها |
| backfill | تطبیق تراکنش‌های موجود با برداشت‌ها (description/amount/date/`related_prop_account_id`) و پر کردن `transaction_id`؛ موارد نامطابق ⇒ `transaction_id = NULL` + گزارش |
| کد | `PayoutService` (create/update/delete با revert/reversal) + استفاده در هر ۳ endpoint |
| ریسک | برداشت‌های قدیمی بدون تراکنش متناظر ⇒ سیاست: «تراکنش جبرانی ساخته نشود، فقط flag گزارش» |
| معیار خروج | تست: ایجاد→ویرایش→حذف برداشت، موجودی حساب مقصد و `Transaction` همیشه منطبق بمانند |

### M4 — هشدارهای نوع‌دار و نقاط رویداد (F-06, F-13, F-14) 🟠
| مورد | جزئیات |
|:---|:---|
| migration | `prop_alerts`: `+ type`, `+ severity`, `+ dedupe_key (unique)`, `+ read_at`, `+ payload`; `is_read` Integer → Boolean |
| backfill | نگاشت متن‌های فعلی به `type` (الگوهای «Daily DD»، «Total DD»، «هدف سود»)؛ `dedupe_key` از stage+type+روز |
| کد | `PropAlertService` (آستانه‌ها از `PropRules`) + حذف side effect از GET + فراخوانی در Commit ایمپورت/ویرایش معامله |
| ریسک | حذف side effect از GET ⇒ اگر فرانت جایی به آن تکیه کرده، هشدارها دیرتر ساخته می‌شوند (افزودن `POST .../alerts/refresh` و صدا زدنش از UI) |
| معیار خروج | یک هشدار در روز به‌ازای هر نوع (بدون تکرار) + GET بدون نوشتن |

### M5 — قوانین نسخه‌دار شرکت + اسنپ‌شات (F-07, F-08, F-09) 🟠
| مورد | جزئیات |
|:---|:---|
| migration | `prop_firm_default_rules`: `+ rules_version`, `+ effective_from`, `+ is_active`, `+ rules_json`; جدول جدید `prop_stage_snapshots`; `PropStage.rules_source_id` |
| backfill | برای هر شرکت یک نسخهٔ v1 از قوانین فعلی؛ اسنپ‌شات «حال حاضر» برای مراحل ACTIVE |
| کد | CRUD قوانین شرکت + seed + snapshot در نقاط EVALUATION/PASS/FAIL/RULE_CHANGE |
| ریسک | افزودن snapshot در هر ارزیابی = رشد جدول ⇒ throttle (حداکثر ۱ snapshot روزانه + نقاط رویداد) |
| معیار خروج | تغییر قوانین مرحله ⇒ snapshot قبلی دست‌نخورده باقی بماند |

### M6 — دقت پول و ارز تایپ‌دار (F-11, F-12) 🟠
| مورد | جزئیات |
|:---|:---|
| migration | `batch_alter_table`: مبالغ پراپ → `Numeric(18,2)`؛ `PropAccount.currency`/`PropCost.currency` → `Currency`؛ `+ PropAccount.broker_id/initial_balance/daily_reset_*` |
| backfill | ساخت/تطبیق `Broker` از `PropFirm.name` (اختیاری، با انطباق بروکرهای موجود) و پر کردن `broker_id` |
| ریسک | تبدیل Enum روی SQLite ⇒ مقادیر نامعتبر قدیمی (مثل `"usd"`) باید normalize شوند؛ Numeric روی مقادیر Float موجود امن است اما **گردکردن** انجام می‌شود (پیشنهاد: ابتدا گزارش اختلاف) |
| معیار خروج | جمع‌های قبلی با جمع‌های جدید (پس از rounding) در بازهٔ ±۰.۰۱ بمانند |

### M7 — کارایی، Rate Limit، پاک‌سازی (F-15, F-18, F-21, F-26) 🔵
| مورد | جزئیات |
|:---|:---|
| کد | aggregate/SQL به‌جای ORM کامل در ارزیابی؛ `@limiter.limit` روی مسیرهای پولی؛ انتقال آمار `/analytics` به سرویس |
| فرانت | حذف `getPropAccountFinanceAccount`/`createPropFinanceAccount`؛ یکی‌کردن `passStage` با `passStageWithRules`؛ نمایش `violations` ساختاری |
| معیار خروج | `tsc -b --force` سبز + داشبورد با همان زمان پاسخ یا بهتر |

### Rollback کلی
```powershell
# هر مرحله مستقل: downgrade یک revision
cd backend; .\venv\Scripts\python.exe -m alembic downgrade -1
# بازگردانی کامل داده در صورت لزوم:
Copy-Item backend\trading_desk.db.bak_phase32_pre backend\trading_desk.db
```

---

## ۷. ارزیابی ریسک (Risk Assessment)

### ۷.۱ ماتریس ریسک اجرا (پیاده‌سازی Phase 32)

| # | ریسک | احتمال | اثر | کاهش (Mitigation) |
|:--|:---|:---:|:---:|:---|
| R-01 | تغییر اعداد نمایشی سود مرحلهٔ رییل (حذف `× share`) ⇒ باور «دادن داده اشتباه» به کاربر | 🟠 متوسط | 🟠 متوسط | انتشار هم‌زمان فرانت + افزودن `user_share_profit`/`gross_pnl` و برچسب «سود خام»/«سهم شما» در UI |
| R-02 | migration روی داده‌ی موجود با «چند مرحلهٔ ACTIVE در یک حساب» | 🟠 متوسط | 🟠 متوسط | تصمیم صریح قبل از اجرا: قدیمی‌ترها `CLOSED` + گزارش؛ تست روی کپی DB |
| R-03 | backfill `transaction_id` برای برداشت‌های قدیمی کامل مطابقت نکند | 🔴 بالا | 🟡 کم | عدم ساخت تراکنش جبرانی؛ فقط flag + گزارش + امکان تطبیق دستی |
| R-04 | تبدیل `Float → Numeric(18,2)` اختلاف رُندینگ در جمع‌ها ایجاد کند | 🟡 کم | 🟠 متوسط | گزارش «اختلاف قبل/بعد» + آستانهٔ ±۰.۰۱ + تست روی کپی |
| R-05 | حذف side effect از `check-pass` ⇒ هشدارها دیگر ساخته نشوند | 🟠 متوسط | 🟡 کم | `POST /alerts/refresh` + فراخوانی از UI + هوک پس از Commit ایمپورت |
| R-06 | فعال‌کردن guard وضعیت‌ها ⇒ شکستن جریان‌های فعلی کاربر (مثلاً pass مرحلهٔ پاس‌شده برای «تصحیح») | 🟠 متوسط | 🟠 متوسط | مسیر «reopen/revert» صریح + پیام خطای راهنما |
| R-07 | `UniqueConstraint(prop_account_id, stage_type)` با داده‌ی فعلی تکراری تصادم کند | 🟠 متوسط | 🟡 کم | پیش‌بررسی `GROUP BY HAVING count>1` + پاک‌سازی/merge دستی |
| R-08 | افزودن `Numeric`/Enum در SQLite با `batch_alter_table` روی جدول‌های وابستهٔ FK | 🟠 متوسط | 🟠 متوسط | الگوی موجود پروژه (batch mode) + تست upgrade/downgrade روی DB موقت (همان روش فاز ۳۰) |
| R-09 | هم‌زمانی/Idempotency: پیاده‌سازی ناقص ⇒ برداشت تکراری | 🟡 کم | 🔴 بالا | جدول `idempotency_keys` + تست دوبار‌ارسال درخواست |
| R-10 | فراموش‌کردن یک مصرف‌کنندهٔ P&L (مثل گزارش PDF/CSV) ⇒ ناسازگاری باقی‌بماند | 🟠 متوسط | 🟠 متوسط | grep اجباری روی `pnl`/`_net_pnl`/`sum(` در کل backend + تست رگرسیون سراسری |
| R-11 | رشد جدول `prop_stage_snapshots` | 🟠 متوسط | 🟡 کم | throttle روزانه + پاک‌سازی خودکار در `backup_service.cleanup` |
| R-12 | شکستن ۱۲۷ تست موجود (خصوصاً `test_prop.py::test_funded_withdrawable_profit`) | 🟠 متوسط | 🟠 متوسط | پیش از تغییر، تست‌ها مستندسازی شوند؛ تغییر مورد انتظار در M1 اعلام و تست به‌روزرسانی شود |

### ۷.۲ ریسک‌های «عدم اقدام» (اگر Phase 32 اجرا نشود)

| ریسک | اثر |
|:---|:---|
| R-13 | ادامهٔ ناسازگاری مالی برداشت‌ها (F-02): گزارش‌های مالی و `real-pnl` عدد اشتباه ⇒ تصمیم‌گیری مالی غلط |
| R-14 | اعلام «آمادهٔ پاس» اشتباه (F-01/F-04) ⇒ از دست رفتن چلنج‌های واقعی (هزینهٔ مالی مستقیم) |
| R-15 | هر قابلیت جدید پراپ (Multi-Account، ROI چلنج، مالیات) روی پایهٔ ناسازگار ساخته می‌شود ⇒ بدهی فنی مرکب |

### ۷.۳ ریسک داده‌ای فعلی (Snapshot وضعیت امروز)

| مورد | مقدار فعلی (DB محلی) |
|:---|:---|
| `prop_firms` / `prop_accounts` / `prop_stages` | ۰ / ۰ / ۰ رکورد |
| `prop_withdrawals` / `prop_costs` / `prop_alerts` | ۰ / ۰ / ۰ رکورد |
| `trades` (REAL_PROP) | ۰ |

> ✅ یعنی **می‌توان تقریباً بدون ریسک مهاجرت داده** مراحل M1–M6 را اجرا کرد؛ ریسک‌های R-02/R-03/R-04/R-07 در
> این دیتابیس فعلاً بی‌اثرند اما در دیتابیس کاربر (با داده) فعال می‌شوند — به همین دلیل برنامهٔ مهاجرت
> با backfill + معیار خروج نوشته شده است.

---

## ۸. سؤالات باز (نیاز به تصمیم شما قبل از Implementation)

| # | سؤال | گزینه‌ها | پیشنهاد این Audit |
|:--|:---|:---|:---|
| Q-1 | آیا `PropStage.current_profit` از مدل حذف شود یا به «derived cache» تبدیل شود؟ | (الف) حذف کامل (ب) نگه‌داشتن با `refreshed_at` و هوک روی Trade | **(ب)** — سازگاری با فرانت فعلی و گزارش‌های موجود، بدون دو منبع حقیقت |
| Q-2 | `PropAccount` با `PersonalTradingAccount` یکی شود یا فقط هم‌راستا؟ | (الف) افزودن فیلد به `PropAccount` (ب) یکسان‌سازی کامل `TradingAccount(kind=…)` | **(الف)** در Phase 32؛ (ب) در فاز جداگانه (نیازمند مهاجرت `Trade.prop_stage_id`/`personal_trading_account_id`) |
| Q-3 | آیا Daily DD بر پایهٔ «مرز روز معاملاتی» بروکر محاسبه شود؟ | (الف) بله + `daily_reset_time/tz` روی حساب (ب) بماند UTC | **(الف)** — چون دقت قوانین پراپ وابسته به همین است |
| Q-4 | سیاست برگشت برداشت (delete payout) | (الف) reversal با رکورد جبرانی (ب) حذف کامل + revert تراکنش (ج) soft-delete | **(الف)** — تاریخچهٔ مالی حفظ می‌شود و audit ممکن است |
| Q-5 | محدودهٔ قوانین جدید (F-08) در همین فاز؟ | (الف) فقط DD/Target/Days + ساختار `rules_json` (ب) + Consistency/Daily Cap (ج) + همهٔ قوانین (Risk/Session/News) | **(ب)** — بیشترین ارزش با ریسک قابل‌کنترل؛ (ج) در فاز بعد |
| Q-6 | آیا مسیرهای فعلی باید «سخت‌گیرانه» شوند (۴۰۰ برای pass مرحلهٔ غیرفعال)؟ | (الف) بله فوری (ب) پشت feature-flag برای یک نسخه | **(الف)** با پیام خطای راهنما (دادهٔ فعلی صفر است ⇒ ریسک کم) |
| Q-7 | اولویت فاز بعدی پراپ | (الف) Multi-Account Dashboard (ب) ROI چلنج/هزینه‌ها + Payout Report (ج) گزارش مالیاتی | **(ب)** — چون به F-16/F-02 گره خورده و همین حالا ناقص است |

---

## ۹. چک‌لیست اجرای Phase 32 (برای فاز پیاده‌سازی — هیچ‌کدام در این Audit انجام نشده)

### پیش از کد
- [ ] تأیید ۷ سؤال باز (بخش ۸)
- [ ] بکاپ `trading_desk.db.bak_phase32_pre`
- [ ] نوشتن ۵ تست طلایی «رفتار فعلی» (P&L، payout، وضعیت‌ها)

### M1 — P&L واحد
- [ ] تابع مشترک `net_pnl` + اعمال در ۴ نقطه
- [ ] recompute `current_profit` + تست رگرسیون P&L
- [ ] فرانت: افزودن `user_share_profit`/`gross_pnl` به UI

### M2 — قواعد اتمیک/حالت
- [ ] migration ستون‌ها + index یکتا ACTIVE
- [ ] نگهبان انتقال + `pass_stage` یک‌تراکنشی
- [ ] تست‌های وضعیت (pass دوباره، fail پاس‌شده، دو ACTIVE)

### M3 — Payout integrity
- [ ] ستون‌های `transaction_id/status/fee/tax/is_reversed`
- [ ] `PayoutService` + استفاده در ۳ endpoint
- [ ] تست: create → update → delete با انطباق تراکنش/موجودی

### M4 — Alerts typed
- [ ] ستون‌های نوع/severity/dedupe + Boolean شدن `is_read`
- [ ] `PropAlertService` + حذف side effect از GET
- [ ] تست idempotency هشدار

### M5 — Rules نسخه‌دار + snapshots
- [ ] CRUD قوانین شرکت + seed
- [ ] `prop_stage_snapshots` + throttle
- [ ] تست: تغییر قوانین، snapshot قبلی حفظ شود

### M6 — دقت پول/ارز
- [ ] `Numeric(18,2)` + Enum ارز + `PropAccount` هم‌راستا
- [ ] گزارش اختلاف رُندینگ
- [ ] تست upgrade/downgrade روی DB موقت

### M7 — کارایی/پاک‌سازی
- [ ] aggregate در SQL + Rate Limit + انتقال آمار به سرویس
- [ ] حذف کد مردهٔ فرانت + یکی‌کردن `passStage`
- [ ] `pytest -q` (۱۲۷+ تست) و `tsc -b --force` و `vitest` سبز

### تخمین زمان (پیشنهاد)
| مرحله | تخمین |
|:---|:---:|
| M0 + M1 | ۳–۴ ساعت |
| M2 | ۳–۴ ساعت |
| M3 | ۴–۶ ساعت |
| M4 | ۲–۳ ساعت |
| M5 | ۴–۵ ساعت |
| M6 | ۳–۴ ساعت |
| M7 | ۲–۳ ساعت |
| مستندسازی/گزارش | ۱–۲ ساعت |
| **جمع** | **۲۲–۳۱ ساعت** (۳–۴ روز کاری) |

---

## ۱۰. پیوست — فایل‌های بررسی‌شده (شواهد Audit)

| فایل | خطوط کلیدی |
|:---|:---|
| `backend/app/services/prop_rule_engine.py` | ۲۴ (ادعای منبع حقیقت), ۳۴-۱۹۱ (evaluate), ۵۱/۵۶/۵۹/۶۲ (فرمول‌ها), ۹۸-۱۲۳ (verdict/funded), ۱۹۴-۲۱۶ (validate_withdrawal), ۲۳۲-۲۴۶ (max DD) |
| `backend/app/api/prop.py` | ۳۶-۳۴۳ (firm/account/stage endpoints), ۳۴۶-۴۱۷ (pass_stage), ۴۲۰-۴۳۷ (fail_stage), ۴۴۱-۴۶۳ (rules), ۴۹۵-۵۳۳ (withdraw/withdrawals), ۵۳۹-۶۳۱ (_create_payout_record), ۶۹۲-۸۲۹ (payouts CRUD), ۸۳۵-۹۱۴ (alerts), ۹۶۹-۱۰۲۵ (costs), ۱۰۳۴ (کامنت حذف پل مالی), ۱۰۳۸-۱۱۰۰ (analytics) |
| `backend/app/models/prop.py` | ۸-۲۶ (enums), ۲۸-۳۹ (firm), ۴۱-۵۵ (default rules), ۵۷-۷۰ (account), ۷۲-۹۸ (stage), ۱۰۰-۱۱۱ (withdrawal), ۱۱۳-۱۲۵ (cost), ۱۲۷-۱۳۵ (alert) |
| `backend/app/services/import_engine.py` | ۷۶۳-۷۸۳ (sync_prop_stage_profit), ۹۵۳-۹۵۴ (فراخوانی) |
| `backend/app/services/analysis_service.py` | ۳۳-۴۳ (analyze_prop_stage), ۴۵۷-۴۵۹, ۶۶۳-۶۶۵ (net_pnl) |
| `backend/app/api/analytics.py` | ۱۰۵-۱۱۴ (analyze prop), ۳۰۰-۳۰۶ (dashboard progress) |
| `backend/app/api/trades.py` | ۳۸۱-۳۹۲ (classification در ویرایش), ۴۳۶-۴۳۹ (تغییر prop_stage_id) |
| `backend/app/services/finance_sync_service.py` | ۱-۲۸ (no-op فاز ۲۸) |
| `backend/migrations/versions/c3d4e5f6a7b8_phase28_finance_cleanup.py` | ۵۱-۵۲ (حذف `prop_accounts.finance_account_id`) |
| `backend/tests/test_prop.py` · `test_soft_delete_filters.py` · `test_analysis_phase23.py` | ۱۰ + ۲ + ۲ تست مرتبط |
| `frontend/src/pages/PropPage.tsx` (۱۶۴۸) · `DashboardPage.tsx` (۱۱۸۴) · `PayoutHistoryPage.tsx` (۴۰۸) | مصرف `suggested_status`/`ready_to_pass`/`profit_progress_percent`/`violations` |
| `frontend/src/api/client.ts` | ۲۴۰-۳۲۲ (Prop Desk + payouts), ۲۸۵-۲۹۰ (کد مرده), ۲۶۱/۳۰۵ (passStage×۲) |
| اسناد | `PROP_FINANCE_INTEGRATION.md` (+`_PHASE5_BACKEND`), `STRATEGY_PROP_ANALYSIS.md`, `STRATEGY_PROP_IMPROVEMENTS.md`, `FINAL_BLUEPRINT.md` (فاز ۶، جداول ۵.۲ و ۶.۲) |

---

## ✅ پایان Audit

- **در این فاز هیچ کدی نوشته/تغییر داده نشد.** تنها خروجی این فاز همین سند است.
- ۲۶ یافته شناسایی شد: **۵× P0**، **۱۱× P1**، **۱۰× P2**.
- آمادهٔ دریافت تصمیم شما روی ۷ سؤال باز (بخش ۸) و سپس شروع `Phase 32 — Implementation` با ترتیب
  M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7.










