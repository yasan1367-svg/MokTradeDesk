# PHASE 54.1 — Audit: Architecture

## 🎯 هدف
بررسی معماری کلی MokTradeDesk: دامنه‌ها، جداسازی، جریان داده، الگوها (Service/DTO) و ساختار API.

## 📌 دامنهٔ بررسی و روش
- **حالت:** فقط‌خواندنی (Read-only) — هیچ فایلی تغییر داده نشد (به‌جز همین فایل گزارش).
- **دامنه:** کد فعلی زیر `C:\MokTradeDesk\backend\app\` (models، services، schemas، api) + ثبت Routerها در `main.py`.
- **وضعیت Git هنگام بررسی:** پاک (clean) روی شاخهٔ `main`، HEAD ≈ `76829b8`.
- **روش:** خواندن مستقیم کد + جست‌وجوی الگوها (importها، decoratorهای route، ساختار مدل‌ها). این گزارش تحلیل استاتیک است؛ تست/build اجرا نشده است.

---

## ۱. دامنه‌ها (`models/`)

پوشهٔ `backend/app/models/` شامل ۷ ماژول دامنه + `__init__.py` است:

| فایل | دامنه | موجودیت‌های اصلی |
|:---|:---|:---|
| `strategy.py` | **Strategy / Analysis / Trade** | `Strategy`, `StrategyVersion`, `Trade`, `AnalysisResult`, `AnalysisRun`, `AnalysisScopeRecord`, `CustomTimeInterval`, `TimePoint` + enumهای `StrategyStatus`, `TradeSource`, `TestType`, `AnalysisScope`, `AnalysisStatus` |
| `trading.py` | **Trading** | `Broker`, `PersonalTradingAccount`, `BrokerCashMovement` |
| `prop.py` | **Prop** | `PropFirm`, `PropFirmDefaultRules`, `PropAccount`, `PropStage`, `PropWithdrawal`, `PropCost`, `PropAlert`, `RuleViolation` + enumهای وضعیت/قاعده/برداشت |
| `finance.py` | **Finance** | `FinancialAccount`, `Category`, `FinancialTransaction` + enumهای `AccountType`, `Currency`, `CategoryType`, `TransactionType` |
| `personal.py` | **Journal** | `JournalReview`, `Screenshot` |
| `imports.py` | **Import** | `ImportProfile`, `ImportBatch`, `ImportBatchRow`, `ImportIdentity` + enumهای `ImportSourceFormat`, `ImportStatus`, `ImportRowStatus` |
| `settings.py` | **Settings** | `UserSettings` |

**نکته:** دامنهٔ Analysis داده‌ی مستقل نیست؛ روی `Trade` (در `strategy.py`) بنا شده و از سه scope مستقل (`VERSION` / `PROP_STAGE` / `PERSONAL_ACCOUNT`) پشتیبانی می‌کند.

---

## ۲. جداسازی دامنه‌ها

### ۲.۱ دامنه‌ها جدا هستند؟
**تا حد خوبی بله، اما نه کامل.** مرزهای زیر عمدی و مستندشده‌اند:

- **حساب مالی ≠ حساب معاملاتی:** `FinancialAccount` (finance) از `PersonalTradingAccount` (trading) و `PropAccount`/`PropStage` (prop) جدا شده است. در docstring مربوطه صریحاً آمده: «یک حساب معاملاتی حساب مالی نیست» (`models/trading.py:1-10`، `models/finance.py:14-29`).
- **معامله دیگر به حساب مالی وصل نیست:** `Trade` فقط به `personal_trading_account_id` / `prop_stage_id` متصل است و پل قدیمی `finance_account_id` حذف شده است (فاز ۲۷/۲۸).
- **ورود پول به Finance فقط از مسیر برداشت:** `PropWithdrawal.destination_account_id` → `FinancialAccount` و ساخت `FinancialTransaction` فقط در نقطهٔ `RECEIVED`.

### ۲.۲ Coupling چقدر است؟
coupling بین‌دامنه‌ای در سطح مدل و سرویس وجود دارد و آگاهانه است:

| نوع coupling | نمونه | ارزیابی |
|:---|:---|:---|
| مدل → مدل (enum مشترک) | `trading.py`, `prop.py` از `finance.Currency` import می‌کنند | 🟢 قابل‌قبول (value مشترک) |
| Prop → Finance | `PropWithdrawal.destination_account_id` → `accounts.id`، `transaction_id` → `transactions.id` | 🟡 وابستگی واقعی دامنه (پول پراپ) |
| Trading → Finance | `BrokerCashMovement.financial_account_id` و `transaction_id` | 🟡 گردش وجه دو دامنه |
| Import → Prop/Strategy/Trading | `import_engine` به `PropStage`, `StrategyVersion`, `PersonalTradingAccount` تکیه دارد | 🟡 لازم برای تخصیص مقصد |
| Analysis → Prop | `AnalysisService.analyze_prop_stage` → `PropRuleEngine` | 🟢 خواندنی |
| Finance → Trade (خواندنی) | `_trade_net_expr()`, `funded_pnl` روی `Trade` | 🟡 گزارش‌گیری روی Trade خام |
| `FinancialTransaction` → Trade | `related_trade_id` FK | ⚪ باقی‌ماندهٔ تاریخی (کم‌کاربرد) |

**جمع‌بندی coupling:** هیچ دامنه‌ای کاملاً ایزوله نیست؛ اما couplingها از نوع «وابستگی واقعی دامنه» (پول/مقصد) هستند، نه گرفتگی تصادفی. مهم‌ترین نقطهٔ تمرکز، مثلث **Prop ↔ Finance ↔ Trading** به‌واسطهٔ گردش پول است.

### ۲.۳ Duplication چقدر است؟
تکرارها کم اما قابل‌ردیابی‌اند:

1. **DTOهای تکراری بین `schemas/` و `api/`:** `StrategyCreate`/`VersionCreate` در `schemas/strategy.py` و منطق مشابه در `api/strategies.py`؛ `PropFirmCreate` در `schemas/prop.py` و هم‌نام آن در `api/prop.py`.
2. **helper ساخت دسته‌بندی:** `_get_or_create_category` هم در `api/prop.py:40` و هم در `services/payout_service.py:54` (تقریباً یکسان).
3. **دو فرمول net_pnl:** در گذشته چند نقطه بود؛ فاز ۴۳ به `services/metrics.py::net_pnl_sql()` متمرکز شد (کاهش موفق تکرار).
4. **مسیر Import دوگانه:** `api/imports.py` (legacy: Preview خودکار + Commit) و `api/import_engine.py` (Preview دستی + Commit) هر دو روی یک موتور کار می‌کنند اما قرارداد API متفاوت دارند.
5. **`WithdrawalCreate` هم‌نام:** در `api/finance.py` (برداشت مالی) و `api/prop.py` (برداشت پراپ) هم‌نام‌اند اما معنای متفاوت دارند — ریسک ابهام نام.

---

## ۳. جریان داده

### ۳.۱ Trade ← Analysis
```
Import / Manual  →  Trade  →  AnalysisService  →  AnalysisResult (جاری) + AnalysisRun (تاریخچه)
                                │
                                └─ scope: VERSION | PROP_STAGE | PERSONAL_ACCOUNT
```
- `Trade` یک `CheckConstraint` دارد که XOR مقصد را تضمین می‌کند: BACKTEST/FORWARD بدون مقصد، REAL_PERSONAL فقط personal، REAL_PROP فقط prop (`models/strategy.py:185-197`).
- تحلیل روی scope اجرا و متریک‌ها از `services/metrics.py` گرفته می‌شود؛ هر اجرا یک `AnalysisRun` جدا می‌سازد (`services/analysis_service.py`).
- **گارد تحلیل کهنه:** `_guard_analyzable` با `Trade.updated_at` تشخیص می‌دهد تحلیل ذخیره‌شده هنوز معتبر است یا نه (`api/analytics.py`، فاز ۵۳.۱).

### ۳.۲ Payout ← Finance
```
PropStage (FUNDED_REAL) → PropWithdrawal (REQUESTED → APPROVED → PROCESSING → RECEIVED)
                                   │
                    در RECEIVED، فقط مقصد بانکی:
                                   ▼
              WalletService.post(...) → FinancialTransaction (PROFIT) + balance update
```
- `PayoutService` وضعیت‌ها را با `WITHDRAWAL_TRANSITIONS` کنترل می‌کند (`models/prop.py:95-110`).
- **قانون مالی:** فقط دریافت در حساب بانکی «درآمد» است؛ در کیف‌پول/صرافی به‌صورت `ADJUSTMENT` مثبت ثبت می‌شود تا درآمد زودتر از واریز بانکی گزارش نشود (`services/payout_service.py:1-9`).
- `WalletService` تنها نویسندهٔ `FinancialAccount.balance` است (`services/wallet_service.py`).

### ۳.۳ Import ← Trade
```
File → Parse → Normalize → Validate (TradeValidator) → Duplicate Detection
     → Preview (ImportBatchRow staging) → User Confirm → Atomic Commit → Trade + ImportIdentity
```
- **Commit اتمیک:** خطای یک رکورد ⇒ rollback کامل و `status=FAILED` (`services/import_engine.py`).
- **Duplicate Detection:** `ImportIdentity` (هویت کامل) + `trade_hash` (legacy) + شمارهٔ سفارش/نماد+زمان (احتمالی). Soft-deletedها هم دیده می‌شوند تا re-import دوباره‌کاری نکند.
- **Import هیچ‌وقت `FinancialAccount` نمی‌سازد** (دامنه از Finance مستقل است).


---

## ۴. الگوهای معماری

### ۴.۱ Service Layer (`services/`)
پوشهٔ `services/` ۱۳ ماژول دارد:

| سرویس | نقش | وضعیت |
|:---|:---|:---|
| `analysis_service.py` | تحلیل نسخه/پراپ/حساب شخصی + ذخیره نتیجه و run | ✅ فعال |
| `import_engine.py` | موتور ایمپورت (Preview/Commit/Duplicate) | ✅ فعال (هستهٔ Import) |
| `import_service.py` | Parserهای Soft4X/MT4 (parse فایل) | ✅ فعال (low-level) |
| `payout_service.py` | چرخهٔ برداشت پراپ + اتصال به Finance | ✅ فعال |
| `wallet_service.py` | تنها نویسندهٔ `FinancialAccount.balance` (post/reverse/reconcile) | ✅ فعال (مرکزی) |
| `broker_cash_service.py` | گردش وجه بروکر ↔ حساب مالی | ✅ فعال |
| `prop_rule_engine.py` | ارزیابی قوانین پراپ (DD/Target/Days) | ✅ فعال |
| `metrics.py` | تعریف واحد net_pnl و متریک‌های تحلیل | ✅ فعال |
| `version_score.py` | امتیازدهی/رتبه‌بندی نسخه | ✅ فعال |
| `financial_reporting.py` | فیلتر/تشخیص درآمد بانکی | ✅ فعال |
| `finance_metrics.py` | متریک‌های مالی (`funded_pnl` و …) | ✅ فعال |
| `backup_service.py` | Backup SQLite + زمان‌بندی | ✅ فعال |
| `finance_sync_service.py` | همگام‌سازی Trade→Finance | ⚠️ **no-op از فاز ۲۸** |

**ارزیابی:** لایهٔ Service وجود دارد و چند سرویس مرکزی (Wallet, Payout, Import, Analysis) واقعاً منطق را از API جدا کرده‌اند؛ اما این الگو سراسری نیست — چند API بزرگ هنوز منطق دامنه را درون خود دارند (بخش ۵).

### ۴.۲ DTO (`schemas/`)
پوشهٔ `schemas/` فقط **۳ فایل** دارد: `analytics.py`، `prop.py`، `strategy.py`.

- **فقط `api/analytics.py`** به‌صورت مستقیم از `schemas/` import می‌کند (`CustomTimeIntervalCreate`, `CompareRequest`, …).
- **بقیهٔ DTOها درون خود API تعریف شده‌اند:** Finance (`AccountCreate`, `TransactionCreate`, …)، Trade (`TradeUpdate`, `ManualTradeCreate`, `BatchDeleteRequest`)، Prop (`PropFirmCreate`, `PropAccountCreate`, `PayoutUpdate`, …)، Import (`ImportProfileCreate`, `ImportCommitRequest`)، Journal (`JournalReviewCreate`)، Trading (`BrokerCreate`, `PersonalTradingAccountCreate`)، Broker، Backup.
- **دوگانگی:** `StrategyCreate`/`VersionCreate` (schemas) و `PropFirmCreate` (schemas) کلاس‌های هم‌نام در APIها دارند ⇒ خطر drift قرارداد.

**ارزیابی:** DTO یک لایهٔ ناقص است. استاندارد پروژه عملاً «تعریف DTO درون API» است و `schemas/` فقط در بخشی از analytics استفاده می‌شود.

---

## ۵. ساختار API

### ۵.۱ شمار و اندازه
پوشهٔ `api/` شامل **۱۴ ماژول feature + `__init__.py` = ۱۵ فایل Python** است (شمار «۱۶ فایل» در شرح فاز با وضعیت فعلی منطبق نیست). در `main.py` **۱۵ Router** ثبت شده‌اند.

| فایل | خطوط | تعداد route (ایستا) |
|:---|---:|---:|
| `finance.py` | ۱۷۹۱ | ۳۷ |
| `analytics.py` | ۱۳۰۵ | ۲۱ |
| `prop.py` | ۱۲۶۱ | ۳۰ |
| `trades.py` | ۸۱۴ | ۹ |
| `strategies.py` | ۶۴۷ | ۱۴ |
| `export.py` | ۴۹۶ | ۴ |
| `import_engine.py` | ۴۵۷ | ۱۰ |
| `broker.py` | ۲۸۶ | ۷ |
| `imports.py` | ۲۲۴ | ۲ |
| `personal.py` | ۲۰۱ | ۷ |
| `trading.py` | ۱۹۴ | ۸ |
| `backup.py` | ۱۱۹ | ۹ |
| `symbol_mappings.py` | ۱۱۲ | ۵ |
| `settings.py` | ۶۹ | ۲ |
| **جمع** | — | **≈ ۱۶۵** |

> شمار routeها شمارش ایستای decoratorهای `@router.*` است؛ به‌تنهایی جایگزین بررسی کامل قرارداد مسیرها نیست.

### ۵.۲ نقشهٔ Routerها (prefixها)
```
/api/strategies · /api/prop · /api/personal · /api/imports (دو روتر هم‌prefix)
/api/analytics · /api/export · /api/trades · /api/symbol-mappings
/api/settings · /api/finance · /api/broker · /api/trading · /api/backup
```
- دو روتر (`imports` و `import_engine`) روی یک prefix مشترک `/api/imports` سوار می‌شوند.

### ۵.۳ مشاهدات ساختاری
1. **نامتوازنی مسئولیت:** `finance.py` و `prop.py` و `analytics.py` هم کوئری DB، هم منطق دامنه، هم serialization و هم مدیریت transaction را در یک ماژول دارند.
2. **دسترسی مستقیم API به DB:** الگوی `db.query(...)`, `db.add(...)`, `db.commit(...)` درون بدنهٔ endpointها پرتکرار است (به‌ویژه strategies، finance، trades، prop).
3. **serialization دستی:** توابع `_serialize_*` به‌صورت پراکنده در APIها (trades, prop, broker, trading, finance) تعریف شده‌اند؛ الگوی سراسری Response Model وجود ندارد.
4. **import درون‌تابعی (lazy):** برخی ماژول‌ها داخل تابع import می‌کنند (مثلاً `from ..models.strategy import Trade` در `api/prop.py:505` و `api/analytics.py`) — قابل‌قبول برای شکستن چرخه اما نشانهٔ وابستگی بالا.
5. **مدیریت تراکنش ناهمگون:** بعضی سرویس‌ها `commit` را داخلی انجام می‌دهند (`AnalysisService`, `ImportEngine`) و بعضی API مسئول commit است (`PayoutService` با `commit=False`). این ناهمگونی ریسک تراکنش‌های نیمه‌کاره را بالا می‌برد.


---

## ۶. نقاط قوت
- ✅ **جداسازی هویت حساب‌ها:** `FinancialAccount` ≠ `PersonalTradingAccount` ≠ `PropAccount` — از خطای «یکی‌گرفتن حساب مالی و معاملاتی» جلوگیری می‌کند.
- ✅ **قرارداد Trade در دو لایه:** `TradeValidator` (اپلیکیشن) + `CheckConstraint` (DB).
- ✅ **WalletService به‌عنوان تنها نویسندهٔ balance:** حذف «دو منبع حقیقت» و امکان `reconcile`.
- ✅ **Import اتمیک با Preview/Duplicate:** staging + تأیید + rollback کامل.
- ✅ **گارد تحلیل کهنه:** تحلیل ذخیره‌شده پس از تغییر معاملات بی‌اعتبار می‌شود.
- ✅ **متمرکزسازی net_pnl:** تعریف واحد در `metrics` (فاز ۴۳).
- ✅ **بهینه‌سازی‌های عملکردی:** `selectinload`/`joinedload`/`with_entities` برای رفع N+1 و کاهش ستون‌های واکشی.

## ۷. ریسک‌ها و بدهی‌ها
| # | یافته | شدت | شواهد |
|:--|:---|:---:|:---|
| ۱ | دسترسی مستقیم APIها به DB و منطق دامنه درون endpoint | 🟠 متوسط | `finance.py`, `prop.py`, `trades.py`, `strategies.py` |
| ۲ | لایهٔ DTO ناقص؛ تکرار schema بین `schemas/` و `api/` | 🟠 متوسط | فقط `analytics` از `schemas` import می‌کند |
| ۳ | ناهمگونی مدیریت transaction (commit داخل سرویس vs API) | 🟠 متوسط | `AnalysisService`/`ImportEngine` vs `PayoutService` |
| ۴ | سه ماژول API بزرگ (`finance`/`analytics`/`prop`) | 🟡 متوسط | ۱۷۹۱ / ۱۳۰۵ / ۱۲۶۱ خط |
| ۵ | helper تکراری `_get_or_create_category` | 🟢 کم | `api/prop.py:40`، `services/payout_service.py:54` |
| ۶ | `FinanceSyncService` no-op و endpoint `/finance/sync/trades` بی‌اثر | 🟢 کم | `services/finance_sync_service.py` |
| ۷ | مسیر Import دوگانه (legacy vs جدید) با قرارداد متفاوت | 🟡 متوسط | `api/imports.py` vs `api/import_engine.py` |
| ۸ | `FinancialTransaction.related_trade_id` باقی‌ماندهٔ تاریخی | ⚪ ناچیز | `models/finance.py:145` |
| ۹ | وابستگی مدل Prop/Trading به `Currency` مالی | 🟢 کم | `models/prop.py`, `models/trading.py` |
| ۱۰ | شمار «۱۶ فایل API» در شرح فاز با ۱۵ فایل فعلی منطبق نیست | ⚪ ناچیز | `api/` count=۱۵ |
| ۱۱ | فقدان احراز هویت (Local-First) | 🔴 بالا (عملیاتی) | بدون auth در `main.py`/روترها |

## ۸. جمع‌بندی
معماری فعلی **ماژولارِ دامنه‌محور با لایه‌بندی ناقص و مرزهای سرویس‌محورِ نامتوازن** است:
- مرزهای هویتی حساب‌ها و قرارداد Trade محکم‌اند.
- couplingهای بین‌دامنه‌ای از نوع «پول/مقصد» و آگاهانه‌اند (Prop ↔ Finance ↔ Trading).
- بزرگ‌ترین بدهی‌ها: **دسترسی مستقیم API به DB + منطق دامنه در Routerها**، **پوشش محدود `schemas/`** و **ناهمگونی مدیریت transaction**.
- تکرارها محدود اما مشخص‌اند (helper دسته‌بندی، DTOهای هم‌نام، مسیر Import دوگانه).

## ۹. پیشنهادهای جهت‌دار (بدون اعمال)
1. یکدست‌سازی مسیر commit: یا همهٔ سرویس‌ها commit داخلی داشته باشند یا همه به API بسپارند (الگوی واحد Unit-of-Work).
2. مهاجرت تدریجی DTOها به `schemas/` و حذف هم‌نام‌ها (`StrategyCreate`, `PropFirmCreate`).
3. شکستن `finance.py`/`prop.py`/`analytics.py` به زیرماژول‌های domain/report.
4. استخراج `_get_or_create_category` به یک util مشترک.
5. تصمیم دربارهٔ `FinanceSyncService`: احیا یا حذف به‌همراه endpoint بی‌اثر.
6. یکپارچه‌سازی مسیر Import legacy روی رابط جدید یا مستندسازی صریح تفاوت قرارداد.

---
**وضعیت:** این فایل تنها خروجی این فاز است. در این فاز هیچ فایل کد، migration یا تستی تغییر نکرد و **commit زده نشد**.

