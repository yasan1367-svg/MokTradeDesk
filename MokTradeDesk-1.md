MokTradeDesk — Master Project Brief
خلاصه جامع تصمیمات، اهداف، معماری فنی، وضعیت فعلی و برنامه اجرای پروژه
1. هدف پروژه
MokTradeDesk یک Trading Operating System شخصی و Local-first برای مدیریت چرخه کامل معامله است؛ نه صرفاً یک ژورنال ساده.
چرخه اصلی:
Backtest → Analysis → Optimization → Forward Test → Real

اهداف اصلی:
- ثبت و نگهداری معاملات و ژورنال
- نگهداری Screenshot و Review
- Import از Soft4X و MT4/MT5
- مدیریت Strategy و Strategy Version
- مدیریت حساب‌های شخصی و Prop
- تحلیل آماری، زمانی و عملکردی
- مقایسه و بهینه‌سازی استراتژی‌ها
- پشتیبانی از تاریخ شمسی در UI و ذخیره میلادی در DB
- رابط RTL و فونت Vazirmatn
- معماری قابل توسعه برای ماژول مالی شخصی در آینده
2. اصل مهم توسعه
این پروژه باید با معماری صحیح و قابل توسعه ساخته شود و از Quick Fix و Hard-code کردن منطق استراتژی پرهیز شود.
GitHub repository به‌عنوان مرجع Read-only است:
https://github.com/yasan1367-svg/MokTradeDesk-deep
هیچ Commit، Push، Branch، Merge یا تغییر دیگری روی GitHub نباید انجام شود. تمام تغییرات فقط Local انجام می‌شوند.

تا قبل از تأیید نهایی معماری و برنامه، کدنویسی شروع نمی‌شود.
3. معماری Strategy و StrategyVersion
هر معامله باید در حالت استاندارد به یک StrategyVersion دقیق متصل باشد.

نمونه:
SP2L
├── v1
│   └── Backtest
├── v2
│   ├── Backtest
│   └── Forward
└── v3
    ├── Backtest
    ├── Forward
    └── Real

Strategy = خانواده/هویت استراتژی.
StrategyVersion = نسخه دقیق قوانین.

ساخت Version جدید نباید قوانین Version قبلی را به‌صورت مخفی تغییر دهد و نباید تاریخچه معاملات گذشته را خراب کند.
تحلیل باید بتواند فقط معاملات Real مربوط به یک Version مشخص را جداگانه تحلیل کند.
4. قرارداد قطعی طبقه‌بندی Trade
چهار حالت اصلی:

BACKTEST:
test_type = BACKTEST
version_id = required
personal_account_id = NULL
prop_stage_id = NULL

FORWARD:
test_type = FORWARD
version_id = required
personal_account_id = NULL
prop_stage_id = NULL

REAL PERSONAL:
test_type = REAL
version_id = required
personal_account_id = required
prop_stage_id = NULL

REAL PROP:
test_type = REAL
version_id = required
personal_account_id = NULL
prop_stage_id = required

قاعده مهم:
personal_account_id XOR prop_stage_id

یعنی هر Real Trade دقیقاً باید متعلق به یکی از دو Context باشد: Personal Trading Account یا Prop Stage، نه هر دو و نه هیچ‌کدام.

در مدل فعلی version_id می‌تواند برای داده‌های قدیمی/Importشده موقتاً nullable بماند، ولی ایجاد استاندارد معامله باید Version را الزامی کند.
5. تفاوت Personal Trading Account و Personal Finance
PersonalAccount فعلی فقط به معنی Personal Trading Account / Broker Account است و نباید برای Wallet، Exchange، Bank یا Cash استفاده شود.

ماژول مالی آینده:
FinancialAccount
├── Trust Wallet
├── Exchange Wallet
├── Bank Account/Card
└── Cash

FinancialTransaction
├── Income
├── Expense
├── Transfer
├── Conversion
└── Adjustment

Trade PnL و Financial Cashflow دو مفهوم جدا هستند.
انتقال بین حساب‌های خود شخص درآمد یا هزینه نیست.
تبدیل ارز نیز درآمد جدید نیست.
Payout واقعی Prop می‌تواند در Personal Finance به‌عنوان درآمد معاملاتی ثبت شود.

معماری فعلی نباید مانع اضافه شدن این ماژول در آینده شود.
6. ساختار فعلی Repository
backend/app/
  api/
    analytics.py
    imports.py
    personal.py
    prop.py
    settings.py
    strategies.py
    symbol_mappings.py
    trades.py
  core/config.py
  core/database.py
  models/
    personal.py
    prop.py
    settings.py
    strategy.py
  schemas/
    analytics.py
    personal.py
    prop.py
    strategy.py
  services/
    analysis_service.py
    import_service.py
  utils/trade_metrics.py

frontend/src/
  App.tsx
  pages/
    DashboardPage.tsx
    AnalysisPage.tsx
    ComparisonPage.tsx
    StrategyPage.tsx
    TradesPage.tsx
    JournalPage.tsx
    PropPage.tsx
    PersonalPage.tsx
    ImportPage.tsx
    SettingsPage.tsx
  components/...
  api/client.ts
7. مدل‌های فعلی مهم
Strategy:
- id
- name
- description
- created_at
- versions

StrategyVersion:
- id
- strategy_id
- version_name
- rules_note
- status
- forked_from_version_id
- created_at
- strategy
- forked_from
- trades
- analysis_results

Trade فعلی:
- id
- version_id
- prop_stage_id
- personal_account_id
- symbol
- direction
- open_time
- close_time
- open_price
- close_price
- size
- sl
- tp
- pnl
- r_multiple
- commission
- swap
- entry_sequence
- source
- test_type
- note
- screenshot_path
- raw_data
- created_at

Trade Relationshipها:
version، prop_stage، personal_account، journal reviews

نکات فنی آینده:
- Instrument entity برای symbol و مشخصات ابزار
- Decimal برای مقادیر مالی
- UTC/aware datetime
- Soft delete/archive به‌جای حذف مخرب تاریخچه
- Screenshot به‌عنوان منبع اصلی فایل‌ها
- AnalysisRun برای نگهداری تاریخچه تحلیل‌ها
8. API معاملات — وضعیت و اصلاحات لازم
ManualTradeCreate فعلی personal_account_id ندارد و باید اضافه شود.

ساختار هدف:
symbol, direction, open_time, close_time, open_price, close_price, size,
sl, tp, pnl, r_multiple, commission, swap,
version_id, personal_account_id, prop_stage_id, test_type, note

Validation باید در Backend انجام شود:

if test_type in [BACKTEST, FORWARD]:
    version_id required
    personal_account_id = NULL
    prop_stage_id = NULL

if test_type == REAL:
    version_id required
    exactly one of personal_account_id / prop_stage_id

GET /trades باید اطلاعات Personal Account را نیز برگرداند.
Filterها باید توسعه یابند.
Edit فعلی فقط Note را تغییر می‌دهد؛ در آینده Edit کنترل‌شده برای Classification و اطلاعات اصلی معامله لازم است.
9. UX صفحه Trades
UX پیشنهادی:

BACKTEST → Strategy Version only
FORWARD → Strategy Version only
REAL
  → Account Type
      → Personal: Strategy Version + Personal Trading Account
      → Prop: Strategy Version + Prop Stage

کاربر نباید بتواند ترکیب‌های نامعتبر را راحت ایجاد کند.

Filterهای هدف:
- Strategy
- Strategy Version
- Test Type
- Account Type
- Personal Trading Account
- Prop Firm
- Prop Account
- Prop Stage
- Symbol
- Source
- Date From / Date To

Filterهای پیشرفته می‌توانند Collapsible باشند.
10. Import Architecture
Import فعلی Soft4X و MT4 وجود دارد، اما باید به Pipeline استاندارد تبدیل شود:

Upload
↓
Parse
↓
Normalize
↓
Validate
↓
Duplicate Check
↓
Preview
↓
User Confirm
↓
DB Transaction
↓
Trade
↓
Analysis Engine / Prop Engine

ImportResult پیشنهادی:
- total_rows
- parsed_rows
- valid_rows
- invalid_rows
- duplicate_rows
- new_rows
- warnings
- errors

ImportBatch نیز باید ایجاد شود و Source، Account، TestType، StrategyVersion و زمان Import را ثبت کند.

Identity پیشنهادی برای تشخیص Duplicate:
source + external/broker ticket/position id + symbol + direction + times + prices + size

قوانین مهم:
- Real Prop باید هم version_id و هم prop_stage_id داشته باشد.
- Real Personal باید version_id و personal_account_id داشته باشد.
- Account و StrategyVersion دو Dimension جدا هستند.
- Import نباید با parse مستقیم commit کند؛ Preview و Confirm و Transaction لازم است.
- direction نباید برای مقدار نامعتبر به‌صورت پیش‌فرض Sell فرض شود.
- timezone باید در Import لحاظ شود.
11. Soft4X و MT4 Import فعلی
Soft4XImporter:
- XLSX
- Sheet Trades یا Active Sheet
- Parse زمان، Direction، Price، Size، SL/TP، P/L، Commission، R
- raw_data
- source = SOFT4X_IMPORT

MT4Importer:
- HTML
- در حال حاضر وابسته به index ثابت سلول‌هاست
- Direction validation ضعیف است
- Duplicate detection ندارد
- Transaction/rollback کامل ندارد
- Account/Strategy context را کامل منتقل نمی‌کند

این بخش باید در Phase Import بازطراحی شود.
12. Prop Architecture
مدل‌های فعلی:
PropFirm
PropFirmDefaultRules
PropAccount
PropStage
PropWithdrawal
PropCost
PropAlert

StageType:
STAGE_1
STAGE_2
FUNDED_REAL

StageStatus:
ACTIVE
PASSED
FAILED
CLOSED

FailureReason شامل:
MAX_DAILY_DD_EXCEEDED
MAX_TOTAL_DD_EXCEEDED
PROFIT_TARGET_NOT_MET
MIN_TRADING_DAYS_NOT_MET
RULE_VIOLATION
MANUAL
OTHER

PropStage دارای Target، Daily DD، Total DD، Trading Days، Initial/Final Balance، Profit Share، Current Profit و Withdrawal است.

مشکل مهم: منطق محاسبات Prop نباید در endpointها و Import Service پراکنده باشد.
یک Prop Rule Engine مرکزی باید مسئول:
- Daily DD
- Total DD
- Profit Target
- Trading Days
- Current Equity
- Floating PnL
- Withdrawable Profit
- Stage Status
- Rule Violations

همچنین در api/prop.py دو endpoint برای POST withdraw وجود دارد و باید Consolidate شود.
Withdrawal باید Atomic باشد.
13. Withdrawal و Personal Ledger
Withdrawal فعلی به target_personal_account_id اشاره می‌کند که از نظر معماری برای آینده درست نیست، چون Personal Trading Account با Financial Account متفاوت است.

در آینده مقصد Withdrawal باید FinancialAccount باشد.

همچنین current_profit که با Withdrawal کاهش می‌یابد می‌تواند برای تحلیل سود واقعی گمراه‌کننده باشد؛ Gross Trading Profit، Profit Share، Withdrawn و Remaining/Withdrawable Profit باید از هم تفکیک شوند.

Ledger فعلی یک amount و source/destination محدود دارد و برای Personal Finance کامل کافی نیست.
14. Personal Models
PersonalAccount:
- id
- name
- broker_name
- account_number
- currency
- initial_balance
- current_balance
- is_active
- created_at

LedgerTransaction:
- id
- transaction_type
- source_type
- source_id
- personal_account_id
- prop_account_id
- amount
- currency
- description
- transaction_date
- created_at

TransactionType فعلی:
TRADE_PNL
PROP_PAYOUT
DEPOSIT
WITHDRAWAL
CHALLENGE_FEE
EXPENSE
MANUAL_ADJUSTMENT

خطر فعلی: اگر Trade PnL و LedgerTransaction هر دو در Balance لحاظ شوند، Double Counting رخ می‌دهد.
این موضوع باید در معماری نهایی تفکیک شود.
15. Analysis
AnalysisResult فعلی شامل:
- total_trades
- win_rate
- profit_factor
- net_pnl
- net_r
- max_dd
- expectancy
- expectancy_r
- avg_win
- avg_loss
- largest_win
- largest_loss
- max_consecutive_losses
- consistency_analysis
- session_analysis
- weekday_analysis
- hour_analysis
- custom_time_analysis
- time_point_analysis

تحلیل باید بر مبنای StrategyVersion انجام شود و در صورت نیاز Contextهای Backtest/Forward/Real Personal/Real Prop را جدا کند.

معماری آینده:
AnalysisRun = هر اجرای تحلیل
AnalysisResult/Current Result = خروجی فعلی یا Snapshot
تا تاریخچه تحلیل‌ها از بین نرود.
16. Database و Migration
Database فعلی SQLite با SQLAlchemy است.
main.py از Base.metadata.create_all استفاده می‌کند.

requirements شامل:
fastapi
uvicorn
sqlalchemy
alembic
python-multipart
openpyxl
beautifulsoup4
pydantic-settings

در Repository alembic.ini پیدا نشده و Migration History کامل مستقر نیست.

تصمیم:
- قبل از تغییر DB، Backup گرفته شود.
- Migration Strategy مشخص و ترجیحاً Alembic راه‌اندازی شود.
- create_all برای تغییرات Schema کافی نیست.
- DB موجود نباید Blindly تغییر کند.
17. اصول فنی آینده
1. Strategy logic نباید در UI hard-code شود.
2. Backend Source of Truth برای Validation است.
3. Trade Classification باید یک Contract مرکزی باشد.
4. Trade PnL و Cashflow جدا بمانند.
5. Instrument به‌صورت Entity مستقل در آینده.
6. Decimal برای Money.
7. UTC/Timezone-aware datetime.
8. Historical data حذف مخرب نشود.
9. Import transactional و قابل rollback باشد.
10. Prop Rule Engine متمرکز باشد.
11. Analysis قابل تکرار و دارای history باشد.
12. UI RTL و Persian/Shamsi باشد.
13. Design باید حرفه‌ای و خاص باشد، نه شبیه Broker Website.
18. UI و Design
Frontend با React/TypeScript است.
زبان اصلی UI فارسی و RTL است.
فونت موردنظر Vazirmatn است.
تاریخ‌ها در UI شمسی نمایش داده می‌شوند و در DB میلادی ذخیره می‌شوند.

هدف UI:
- Modern
- Professional
- Visually polished
- Unique
- مناسب یک Trading OS شخصی
- نه یک Broker Dashboard کلیشه‌ای

صفحات اصلی:
Dashboard
Analysis
Comparison
Strategy
Trades
Journal
Prop
Personal
Import
Settings
19. وضعیت فعلی پروژه
Audit و Planning روی بخش‌های اصلی انجام شده است.
کدهای فعلی بررسی‌شده شامل API، Models، Schemas، Import Services، صفحات Frontend، Database و Config هستند.

هنوز Implementation اصلی اصلاحات جدید شروع نشده است.
مهم‌ترین اصلاحات هنوز باید به‌صورت Local پیاده‌سازی و تست شوند.

Repository GitHub فقط Reference است و نباید تغییر کند.
20. ترتیب اجرای مورد توافق
PHASE 0 — Final Architecture Sign-off
↓
PHASE 1 — DB Backup + Migration Foundation
↓
PHASE 2 — Trade Contract / Models / Validation
↓
PHASE 3 — Trades API
↓
PHASE 4 — Trades Frontend / Manual Trade / Edit / Filters
↓
PHASE 5 — Import Pipeline
↓
PHASE 6 — Prop Rule Engine + Withdrawal
↓
PHASE 7 — Analysis Engine / AnalysisRun
↓
PHASE 8 — Journal / Screenshot cleanup
↓
PHASE 9 — Testing / Regression
↓
PHASE 10 — Future Personal Finance

اولین کار عملی:
1. بررسی Schema و داده واقعی Local DB
2. Backup
3. تعیین/راه‌اندازی Migration
4. اجرای Trade Contract و Validation
5. اصلاح API
6. اصلاح Frontend
7. اصلاح Import
8. Prop Rule Engine
9. Analysis
10. Testing/Regression
21. اطلاعات استراتژی و Trading Context کاربر
استراتژی اصلی مورد بحث SP2L است و ابزارهای مهم XAUUSD، US30/DJ30، EURUSD و GBPUSD هستند.
بخش زیادی از تست‌ها روی تایم‌فریم 5 دقیقه انجام می‌شود.

در SP2L، Entry #2 مخصوص همین Strategy است و نباید به‌صورت Global برای تمام Strategyها در سیستم اعمال شود.
این موضوع یک اصل معماری مهم است: ویژگی‌های خاص یک Strategy باید قابل تعریف/اختصاص باشند و نباید منطق اختصاصی SP2L در Core Trade hard-code شود.
22. دستورالعمل برای AI بعدی
تو به‌عنوان AI توسعه‌دهنده/همکار پروژه MokTradeDesk باید:
- ابتدا این سند را به‌عنوان Project Context در نظر بگیری.
- GitHub را فقط Read-only Reference بدانی.
- هیچ تغییر، Commit، Push، Branch یا Merge روی GitHub انجام ندهی.
- قبل از تغییرات بزرگ، Architecture و Impact را بررسی کنی.
- Backend را Source of Truth برای قوانین و Validation بدانی.
- داده تاریخی را محافظت کنی.
- از Quick Fixهایی که معماری آینده را خراب می‌کنند خودداری کنی.
- StrategyVersion را محور Classification و Analysis قرار دهی.
- Personal Trading Account را با Personal Finance Account قاطی نکنی.
- Trade PnL را با Cashflow دوباره محاسبه/Double Count نکنی.
- قبل از Migration از DB Backup بگیری.
- تغییرات را Local انجام دهی.
- بعد از هر Phase تست Regression انجام دهی.
- اگر تصمیم معماری جدید لازم شد، ابتدا آن را با کاربر مطرح و تأیید بگیری.

هدف نهایی فقط «کار کردن برنامه» نیست؛ هدف ساخت یک Trading OS شخصی، قابل اعتماد، قابل تحلیل و قابل توسعه است.
