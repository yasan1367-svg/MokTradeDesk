# 📐 PHASE20_DESIGN — تحلیل ۶گانه + داشبورد پول واقعی + ارتباط با حسابداری

> **تاریخ:** ۱۴۰۵/۰۷/۰۴ (2026-09-26) · **مدل:** `deepseek/deepseek-v4-pro`
> **وضعیت:** 📐 طراحی نهایی — تأییدشده توسط کاربر · آماده‌ی پیاده‌سازی
> **دامنه:** فاز ۲۰.۱ تا ۲۰.۶ (Finance bridge → فاز ۲۱+)

---

## ۰. تصمیمات نهایی (تأییدشده)

| # | موضوع | تصمیم | دلیل |
|---|---|---|---|
| ۱ | **سرمایه اولیه** | `SUM(Transaction WHERE type=DEPOSIT)` برای حساب‌های BROKER | دقیق‌تر از `Account.balance` |
| ۲ | **UI پراپ** | انتخاب مستقیم `prop_stage_id` از یک dropdown | ساده‌تر |
| ۳ | **تحلیل پراپ** | شامل `PropRuleEngine.evaluate_stage()` در کنار متریک‌های معاملاتی | نمایش progress/daily DD |
| ۴ | **تحلیل بروکر** | فقط `Account.type = BROKER` | پراپ جدا تحلیل می‌شود |
| ۵ | **Finance bridge** | فاز ۲۱+ (نه در فاز ۲۰) | حجم بالا + نیاز به طراحی دقیق |

---

## ۱. خلاصه‌ی وضعیت فعلی

### ۱.۱ مدل‌ها

| مدل | فایل:خط | وضعیت | شکاف |
|---|---|---|---|
| `Trade` | `models/strategy.py:87-128` | `test_type`، `version_id`، `prop_stage_id`، `finance_account_id` | ✅ کامل |
| `AnalysisResult` | `models/strategy.py:159-191` | **فقط `version_id`** (`NOT NULL`) | 🔴 نیاز به `scope` + ۲ FK |
| `AnalysisRun` | `models/strategy.py:193-219` | **فقط `version_id`** (`NOT NULL`) | 🔴 همان |
| `PropStage` | `models/prop.py:74-100` | `stage_type` (STAGE_1/STAGE_2/FUNDED_REAL) | ✅ کامل |
| `Account` | `models/finance.py:47-80` | `type` (BROKER/PROP/...)، `balance` | ✅ کامل |
| `Transaction` | `models/finance.py:99-124` | `type`، `account_id`، `related_trade_id` | ✅ کامل |
| `PropWithdrawal` | `models/prop.py:102-113` | `prop_stage_id`، `amount` | ✅ کامل |

### ۱.۲ APIهای موجود

| Endpoint | فایل:خط | وضعیت |
|---|---|---|
| `POST /analyze/{version_id}` | `api/analytics.py:63` | فقط version_id |
| `GET /{version_id}` | `api/analytics.py:734` | گارد سازگاری فاز ۱۹ |
| `GET /dashboard` | `api/analytics.py:81` | همه‌ی معاملات (لایه ۲ فاز ۱۹) |
| `GET /strategies/{id}/stats` | `api/strategies.py:293` | غیر-REAL (فاز ۱۹) |
| `POST /prop/stages/{id}/withdraw` | `api/prop.py:570` | ✅ `PropWithdrawal` + `Transaction` می‌سازد |

### ۱.۳ آنچه **موجود** است (نقاط قوت)

- ✅ `Trade` همه‌ی FKهای لازم برای ۶ نوع تحلیل را دارد
- ✅ `PropRuleEngine.evaluate_stage()` آماده است (`api/analytics.py:228` استفاده می‌کند)
- ✅ زیرساخت حسابداری (`Account`, `Transaction`) کامل است
- ✅ برداشت پراپ → `Transaction` از قبل پیاده شده
- ✅ `_scope_filter` + `_net_expr` برای محاسبات SQL موجود است

### ۱.۴ آنچه **کم** است

- ❌ `AnalysisResult` نمی‌تواند تحلیل پراپ/بروکر را نگه دارد (فقط `version_id`)
- ❌ موتور تحلیل در `analyze_version` قفل است (قابل استفاده مجدد نیست)
- ❌ هیچ endpointی برای تحلیل پراپ/بروکر وجود ندارد
- ❌ داشبورد «پول قابل خرج» را تفکیک نمی‌کند
- ❌ فرانت‌اند فقط یک dropdown نسخه دارد (بدون انتخاب نوع تحلیل)

---

## ۲. طراحی Migration

### ۲.۱ Enum جدید

```python
class AnalysisScope(str, enum.Enum):
    VERSION    = "version"      # Backtest / Forward  (test_type=BACKTEST|FORWARD)
    PROP_STAGE = "prop_stage"   # Stage 1/2/3          (test_type=REAL + stage_type)
    BROKER     = "broker"       # حساب بروکر           (test_type=REAL + Account.type=BROKER)
```

### ۲.۲ کلید یکتا — چرا `scope_key`؟

سه FK nullable داریم (فقط یکی در هر ردیف پر می‌شود). `UniqueConstraint` روی
ستون‌های nullable در SQL کار **نمی‌کند** (NULL ≠ NULL). راه‌حل: یک کلید ترکیبی رشته‌ای.

```
scope        | scope_key | version_id | prop_stage_id | finance_account_id
-------------|-----------|------------|---------------|-------------------
'VERSION'    | '5'       | 5          | NULL          | NULL
'PROP_STAGE' | '12'      | NULL       | 12            | NULL
'BROKER'     | '7'       | NULL       | NULL          | 7
```

- `scope` → برای فیلتر/گزارش
- `scope_key` → `str(id)` مربوط به همان scope
- `UniqueConstraint('scope', 'scope_key')` → یک رکورد «جاری» برای هر scope

### ۲.۳ ستون‌های جدید

| جدول | ستون | نوع | nullable | یادداشت |
|---|---|---|---|---|
| `analysis_results` | `scope` | `Enum(AnalysisScope)` | ❌ | `server_default='VERSION'` |
| `analysis_results` | `scope_key` | `String` | ❌ | index |
| `analysis_results` | `prop_stage_id` | `Integer` (FK) | ✅ | |
| `analysis_results` | `finance_account_id` | `Integer` (FK) | ✅ | |
| `analysis_results` | `version_id` | `Integer` (FK) | **تغییر: NOT NULL → NULL** | |
| `analysis_runs` | همان ۵ ستون | | | `scope_key` بدون unique (تاریخچه) |

> **نکته‌ی مهم:** `Enum` در SQLAlchemy 1.4+ به‌صورت پیش‌فرض `create_constraint=False`
> است → ستون به‌شکل `VARCHAR` ساخته می‌شود (بدون CHECK). پس افزودن scope جدید
> در آینده **نیازی به Migration ندارد**.

### ۲.۴ الگوی Migration

SQLite از `ALTER COLUMN` پشتیبانی نمی‌کند → باید `batch_alter_table` (بازسازی جدول).
الگوی پروژه (`9f1a2b3c4d5e`) همین است.

```
۱) batch_alter_table: add_column(scope, scope_key[nullable], prop_stage_id, finance_account_id)
۲) UPDATE ... SET scope_key = CAST(version_id AS TEXT) WHERE scope_key IS NULL
۳) batch_alter_table: alter_column(scope_key NOT NULL) + alter_column(version_id NULL)
                      + create_foreign_key × ۲ + create_unique_constraint + create_index × ۲
```

**دو مرحله لازم است** چون `scope_key` از `version_id` مشتق می‌شود و در یک
`batch_alter_table` واحد نمی‌توان بین add و alter داده را به‌روز کرد.

**Downgrade:** حذف ستون‌های جدید + بازگرداندن `version_id` به `NOT NULL`
(با حذف ردیف‌های غیر-VERSION که بدون version_id معنا ندارند).

---

## ۳. طراحی Backend

### ۳.۱ Refactor موتور تحلیل — `_analyze()` generic

```python
class AnalysisService:
    def analyze_version(self, version_id, test_type=None) -> Dict:
        q = self.db.query(Trade).filter(
            Trade.version_id == version_id, analysis_trades_filter())
        if test_type:
            q = q.filter(Trade.test_type == test_type)
        return self._analyze(q.all(), AnalysisScope.VERSION,
                             version_id=version_id, test_type=test_type)

    def analyze_prop_stage(self, prop_stage_id) -> Dict:
        trades = self.db.query(Trade).filter(
            Trade.prop_stage_id == prop_stage_id).all()
        return self._analyze(trades, AnalysisScope.PROP_STAGE,
                             prop_stage_id=prop_stage_id)

    def analyze_broker(self, finance_account_id) -> Dict:
        trades = self.db.query(Trade).filter(
            Trade.finance_account_id == finance_account_id).all()
        return self._analyze(trades, AnalysisScope.BROKER,
                             finance_account_id=finance_account_id)

    def _analyze(self, trades, scope, version_id=None, prop_stage_id=None,
                 finance_account_id=None, test_type=None) -> Dict:
        """موتور مشترک — همان منطق فعلی، فقط پارامتریک"""
        # 1. گارد: trades خالی → ValueError
        # 2. محاسبه‌ی metrics / session / weekday / hour / custom / consistency
        # 3. upsert AnalysisResult با scope + scope_key
        # 4. افزودن AnalysisRun (تاریخچه)
```

**توجه:** `analyze_prop_stage` و `analyze_broker` از `analysis_trades_filter()`
استفاده **نمی‌کنند** — آن‌ها فقط معاملات REAL همان scope را می‌خواهند.

### ۳.۲ تحلیل پراپ + `PropRuleEngine`

پاسخ `analyze_prop_stage` علاوه بر متریک‌های معاملاتی، خروجی
`PropRuleEngine.evaluate_stage(db, stage_id)` را هم برمی‌گرداند:

```json
{
  "scope": "prop_stage",
  "prop_stage_id": 12,
  "stage": { "stage_type": "funded_real", "account_label": "FTMO 100K" },
  "result": { "total_trades": 34, "win_rate": 58.8, "net_pnl": 2450.0 },
  "prop_rules": { "profit_target": 10000, "progress_percent": 24.5,
                  "max_daily_dd": 5000, "daily_dd_used": 1200 }
}
```

### ۳.۳ APIهای جدید

```
POST /api/analytics/analyze/version/{version_id}?test_type=BACKTEST|FORWARD
POST /api/analytics/analyze/prop/{prop_stage_id}
POST /api/analytics/analyze/broker/{finance_account_id}

GET  /api/analytics/analysis/version/{version_id}?test_type=BACKTEST|FORWARD
GET  /api/analytics/analysis/prop/{prop_stage_id}
GET  /api/analytics/analysis/broker/{finance_account_id}
```

**Backward-compat:** `POST /analyze/{version_id}` و `GET /{version_id}` **باقی می‌مانند**
و به مسیر جدید delegate می‌کنند (فرانت‌اند فعلی نمی‌شکند).

**گارد سازگاری (فاز ۱۹)** برای هر scope تعمیم می‌یابد:
`analyzable_trades` بر اساس scope محاسبه و با `result.total_trades` مقایسه می‌شود.

### ۳.۴ داشبورد «پول قابل خرج»

| متریک | فرمول |
|---|---|
| **سود خالص** | `SUM(net_pnl)` معاملات `stage_type=FUNDED_REAL` + `SUM(net_pnl)` معاملات `Account.type=BROKER` |
| **موجودی کل** | `SUM(Account.balance)` BROKER + سود خالص قابل خرج |
| **سرمایه اولیه** | `SUM(Transaction.amount WHERE type=DEPOSIT)` حساب‌های BROKER |
| ❌ مستثنی | Stage 1، Stage 2، سرمایه اولیه‌ی پراپ |

```python
spendable = or_(
    and_(Trade.finance_account_id.isnot(None),
         Account.type == AccountType.BROKER),
    and_(Trade.prop_stage_id.isnot(None),
         PropStage.stage_type == StageType.FUNDED_REAL),
)
```

**کلید جدید در پاسخ داشبورد:** `"spendable_money": { net_pnl, total_balance, initial_capital }`
(کلیدهای موجود دست‌نخورده می‌مانند → بدون شکستن فرانت‌اند).

### ۳.۵ `GET /strategies/{id}/stats`

بدون تغییر ساختاری — فاز ۱۹ آن را به غیر-REAL محدود کرد (درست است).
فقط یک پارامتر اختیاری `?test_type=BACKTEST|FORWARD` اضافه می‌شود تا آمار
هر نوع تست جدا دیده شود.

### ۳.۶ ارتباط با Finance (وضعیت فعلی + فاز ۲۱)

**موجود:**
- برداشت پراپ → `PropWithdrawal` + `Transaction(type=WITHDRAWAL)`
- `Account.balance` حساب‌های BROKER/PROP
- `Transaction.related_trade_id` (FK به trades)

**در فاز ۲۰ انجام نمی‌شود:**
- ❌ ساخت خودکار `Transaction(type=PROFIT/LOSS)` برای هر معامله
- ❌ به‌روزرسانی خودکار `Account.balance` با بسته‌شدن معاملات
- ❌ Job زمان‌بندی‌شده برای «تحقق سود»

**فاز ۲۰ فقط می‌خواند** (Trades + Accounts + Transactions) — **هیچ نوشتنی در Finance ندارد.**
این یعنی صفر ریسک برای داده‌های حسابداری.

---

## ۴. طراحی Frontend

### ۴.۱ UI — Tab bar (۶ تب)

```
┌──────────────────────────────────────────────────────────────────────┐
│ [📊 بک‌تست] [📈 فوروارد] [🏁 مرحله ۱] [🔍 مرحله ۲] [💰 مرحله ۳] [🏦 بروکر] │
└──────────────────────────────────────────────────────────────────────┘
  └ Tab 1/2: dropdown «نسخه»   └ Tab 3/4/5: dropdown «مرحله»   └ Tab 6: dropdown «حساب بروکر»
```

| تب | انتخابگر | منبع داده |
|---|---|---|
| بک‌تست | dropdown نسخه | `GET /analysis/version/{id}?test_type=BACKTEST` |
| فوروارد | dropdown نسخه | `GET /analysis/version/{id}?test_type=FORWARD` |
| مرحله ۱/۲/۳ | dropdown `prop_stage_id` | `GET /analysis/prop/{stage_id}` |
| بروکر | dropdown حساب بروکر | `GET /analysis/broker/{account_id}` |

### ۴.۲ کامپوننت‌ها

| فایل | تغییر |
|---|---|
| `pages/AnalysisPage.tsx` | افزودن Tab bar + منطق انتخاب منبع (بزرگ‌ترین تغییر) |
| `api/client.ts` | ۶ تابع جدید + نگه‌داشتن ۲ تابع قدیمی |
| `pages/DashboardPage.tsx` | افزودن کارت‌های «پول قابل خرج» |
| `components/` | **بدون تغییر** — نمودارها/جداول موجود بازاستفاده می‌شوند |

### ۴.۳ ذخیره‌ی انتخاب کاربر

`localStorage` با کلید `analysis_selected_scope` (مقدار: `{scope, id, test_type}`).
دلیل: سبک، بدون نیاز به Backend. (`UserSettings` هم گزینه است ولی برای این کار overkill.)

### ۴.۴ صفحه Finance

**در فاز ۲۰ تغییر نمی‌کند.** فقط در فاز ۲۱ (Finance bridge) لمس می‌شود.

---

## ۵. پیشنهادها و هشدارهای Cline

### ✅ پیشنهاد ۱ — گسترش `AnalysisResult` به‌جای ۳ جدول جدید

ساخت `BacktestResult` / `PropAnalysisResult` / `BrokerAnalysisResult` یعنی ۳× duplication
و عدم امکان مقایسه‌ی cross-scope. **یک جدول با `scope` بهتر است.**

### ✅ پیشنهاد ۲ — Refactor به `_analyze()` الزامی است

`analyze_version` الان ~۸۰ خط است. کپی‌کردنش برای prop/broker یعنی ۳ نسخه‌ی تکراری
از منطق session/weekday/hour/consistency. **DRY الزامی است.**

### ⚠️ هشدار ۱ — `analysis_trades_filter()` را در prop/broker استفاده نکنید

آن فیلتر معاملات REAL را **حذف** می‌کند. برای پراپ/بروکر دقیقاً برعکس است:
باید **فقط** REAL را ببینیم. اشتباه اینجا = تحلیل خالی.

### ⚠️ هشدار ۲ — `test_type` در Enum به‌صورت NAME ذخیره می‌شود

فاز ۱۹ این را اثبات کرد: در DB مقدار `'REAL'` است نه `'real'`.
پس فیلترها باید `TestType.REAL` (شیء Enum) بدهند، نه رشته‌ی `'real'`.

### ⚠️ هشدار ۳ — معاملات پراپ هم `version_id` دارند

در دیتابیس واقعی کاربر، ۲۱ معامله‌ی REAL **هم** `version_id=1` دارند **هم** `prop_stage_id=1`.
پس اگر کسی `analyze_version` بزند، این‌ها به‌درستی حذف می‌شوند (فاز ۱۹) —
اما تحلیل پراپ همان‌ها را از مسیر `prop_stage_id` می‌بیند. **دو مسیر مستقل، بدون تداخل.**

### 💡 پیشنهاد ۳ — ساده‌سازی: `scope_key` بدون prefix

مقدار `scope_key` فقط `str(id)` باشد (`"5"`)، نه `"version:5"`. چون `scope`
خودش تفکیک می‌کند و `UniqueConstraint('scope','scope_key')` کامل است.

### 💡 پیشنهاد ۴ — تحلیل خالی = ۴۰۴ (نه رکورد خالی)

اگر scope هیچ معامله‌ای نداشته باشد، **رکورد نمی‌سازیم** و `404` با پیام شفاف
برمی‌گردانیم (هماهنگ با رفتار فاز ۱۹).

### 💡 پیشنهاد ۵ — `AnalysisRun` بدون `UniqueConstraint`

`AnalysisResult` = وضعیت «جاری» (یکی به‌ازای هر scope) · `AnalysisRun` = تاریخچه
(چندین به‌ازای هر scope). پس unique فقط روی `AnalysisResult`.

---

## ۶. تقسیم‌بندی فازها

| فاز | محدوده | فایل‌ها | تخمین |
|---|---|---|---|
| **۲۰.۱** | Enum + مدل + Migration | `models/strategy.py`، `migrations/versions/*`، `services/analysis_service.py` (پرشدن `scope_key`) | ~۱۵۰ خط |
| **۲۰.۲** | Refactor موتور | `services/analysis_service.py` | ~۱۲۰ خط |
| **۲۰.۳** | APIهای جدید + گاردها | `api/analytics.py` | ~۲۰۰ خط |
| **۲۰.۴** | داشبورد پول واقعی | `api/analytics.py` | ~۱۰۰ خط |
| **۲۰.۵** | فرانت‌اند Tab bar | `AnalysisPage.tsx`، `client.ts`، `DashboardPage.tsx` | ~۲۵۰ خط |
| **۲۰.۶** | تست | `tests/test_analysis_scope.py` + فایل جدید | ~۲۵۰ خط |
| **۲۱+** | Finance bridge | `api/finance.py`، `api/prop.py`، `models/finance.py` | TBD |

**ترتیب منطقی:** ۲۰.۱ → ۲۰.۲ → ۲۰.۳ → ۲۰.۴ → ۲۰.۵ → ۲۰.۶
(هر فاز مستقل قابل تست است؛ Backend قبل از Frontend).

---

## ۷. سوالات باقی‌مانده

۱. **آیا `AnalysisResult` برای بروکر باید `Account.balance` را هم نشان دهد**
   (نه فقط سود معاملات)؟ پیشنهاد Cline: بله، به‌عنوان فیلد جدا در پاسخ API
   (نه در جدول) — چون `balance` وضعیت جاری است نه snapshot تحلیل.

۲. **آیا تب‌های مرحله ۱/۲ باید معاملات «شکست‌خورده» را هم نشان دهند؟**
   (مرحله‌هایی که `status=FAILED`). پیشنهاد Cline: بله — با badge «شکست‌خورده»
   تا کاربر بتواند علت شکست را تحلیل کند.

۳. **آیا در داشبورد، «موجودی کل» باید برداشت‌های انجام‌شده را کم کند؟**
   پیشنهاد Cline: بله — `Transaction(type=WITHDRAWAL)` از BROKER/FUNDED کم شود.

---

*طراحی فاز ۲۰ — تهیه‌شده در ۱۴۰۵/۰۷/۰۴.*


