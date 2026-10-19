# FINANCE AUDIT — PART 1

**موضوع:** شناسایی ساختار واقعی Finance از Source Code، بدون اصلاح.

**روش:** خواندن ایستای مدل‌ها، سرویس‌ها، APIها، فراخوانی‌ها و بخش‌های نمایش Frontend. هیچ اتصال به DB، اجرای برنامه، تست، migration، backfill، commit یا push انجام نشده است. تنها خروجی نوشته‌شده همین گزارش است. یافته‌های این گزارش جایگزین فرض‌های موجود در خلاصهٔ جلسات قبلی هستند.

**حد اعتبار:** نام جدول‌ها و فیلدها در این گزارش تعریف ORM هستند؛ وجود و تطابق آن‌ها در DB نصب‌شده `NOT VERIFIED` است. «ذخیره‌شده» یعنی Column تعریف شده، نه تأیید مقدار واقعی دیتابیس. «مالک عدد» یعنی منبع رکورد/محاسبه، نه مالکیت حقوقی یا احراز هویت کاربر. مبالغ اصلی مدل‌ها `Float` هستند.

## 1. Finance Architecture

سیستم سه دامنهٔ جدا دارد:

1. **دفتر مالی شخصی:** `accounts`، `transactions` و `categories`. موجودی مالی در `FinancialAccount.balance` ذخیره می‌شود؛ اثر تراکنش‌ها توسط `WalletService` اعمال/برگردانده می‌شود.
2. **معاملات شخصی بروکر:** `brokers` و `personal_trading_accounts` به‌علاوهٔ معاملات وابسته. `initial_balance` و `current_balance` دو ستون مستقل‌اند، نه property حاصل جمع معاملات.
3. **پراپ:** `prop_accounts`، `prop_stages`، معاملات مرحله، هزینه‌ها و برداشت‌ها. سرمایهٔ مرحله متعلق به دامنهٔ ارزیابی پراپ است، نه موجودی قابل خرج `accounts`.

پل‌های مالی موجود:

- `BrokerCashService`: جابه‌جایی موجودی حساب شخصی بروکر و حساب مالی، همراه با یک `FinancialTransaction` و یک `BrokerCashMovement`.
- `PayoutService`: ثبت برداشت پراپ؛ در RECEIVED تراکنش مالی ساخته می‌شود و موجودی مقصد و `stage.total_withdrawn` تغییر می‌کنند.
- ثبت هزینهٔ خرید پراپ: با شرایط مشخص یک `PropCost` و یک تراکنش PURCHASE ایجاد می‌کند.
- `FinanceSyncService.sync_closed_trades`: **no-op** است؛ همیشه صفر برمی‌گرداند و تراکنش نمی‌سازد.

گزارش‌گیری لایهٔ سرویس یکنواخت ندارد: بخش قابل‌توجهی از محاسبات مستقیماً داخل API است. سرویس‌های مشترک عبارت‌اند از `wallet_service`، `finance_metrics`، `financial_reporting` و `metrics`.

**زیرساخت:** FastAPI + SQLAlchemy، مدل‌های Pydantic برای ورودی، Frontend با TSX و client مشترک. تنظیم پیش‌فرض DB، SQLite در `i:\trade\MokTradeDesk\backend\trading_desk.db` است؛ `DATABASE_URL` قابل override است. فایل دیتابیس باز نشده است. hook اتصال، PRAGMAهای foreign_keys/WAL/busy_timeout را تنظیم می‌کند؛ وضعیت واقعی اجرای آن‌ها `NOT VERIFIED`.

شواهد:
- `i:\trade\MokTradeDesk\backend\app\main.py:183–198` — اتصال routerها.
- `i:\trade\MokTradeDesk\backend\app\core\config.py:9–20` و `i:\trade\MokTradeDesk\backend\app\core\database.py:7–49`.
- `i:\trade\MokTradeDesk\backend\app\services\finance_sync_service.py:20–28`.

## 2. Database Models

### 2.1 موجودی‌ها و رکوردهای اصلی

| Model / DB table | فیلدهای عددی و مالک اصلی | Currency | Balance / Initial / Current | وضعیت و نوع | Foreign Key و مصرف‌کننده |
|---|---|---|---|---|---|
| FinancialAccount / `accounts` | `balance` ذخیره‌شده، متعلق به همان حساب مالی | ستون `currency` | فقط `balance`؛ initial/current جدا ندارد | `type`: bank/exchange/crypto_wallet/card/cash/trust_wallet؛ `is_archived` | خود مدل FK ندارد؛ مقصد FKهای transactions، withdrawals و movements؛ WalletService، Finance API، PayoutService، BrokerCashService |
| PersonalTradingAccount / `personal_trading_accounts` | `initial_balance`, `current_balance` ذخیره‌شده، متعلق به حساب شخصی بروکر | ستون `currency` | هر دو ستون؛ `balance` ندارد | `is_active`؛ account_type/is_archived ندارد | `broker_id → brokers.id`؛ Trading API، finance_metrics، Finance API، Analytics و BrokerCashService |
| Broker / `brokers` | هیچ موجودی یا مبلغ مالی ندارد | ندارد | ندارد | `is_active` | رابطه یک‌به‌چند با حساب‌های شخصی؛ Trading API و نام/ساعت سرور در import و نمایش گردش |
| PropAccount / `prop_accounts` | ظرف هویتی حساب پراپ؛ فاقد موجودی مستقیم | ستون `currency` | balance/initial/current ندارد | `is_active` از نوع Integer؛ archived ندارد | `prop_firm_id → prop_firms.id`؛ Prop API، گزارش Real و finance_metrics |
| PropStage / `prop_stages` | `initial_balance`, `final_balance`, `current_profit`, `total_withdrawn` ذخیره‌شده؛ قواعد `profit_target`, `max_daily_dd`, `max_total_dd`, `profit_share_percentage` | ستون مستقل ندارد؛ ارز از PropAccount | initial/final دارد؛ current_balance ندارد | `stage_type`: stage_1/stage_2/funded_real؛ `status`: active/passed/failed/closed | `prop_account_id → prop_accounts.id`؛ Prop API، rule engine، import، payout، Analytics، Finance |
| Trade / `trades` | `pnl`, `commission`, `swap`, قیمت‌ها، `size`, SL/TP، `r_multiple` ذخیره‌شده؛ `net_pnl` محاسبه‌شده | ستون ارز ندارد؛ برای Real از حساب مرتبط | موجودی ندارد | `test_type`؛ بسته بودن با close_time؛ archived ندارد | version_id، personal_trading_account_id، prop_stage_id؛ CRUD/import، metrics، Analytics و Finance |
| FinancialTransaction / `transactions` | `amount`, `to_amount` ذخیره‌شده؛ مالک رخداد دفتر مالی | `currency`, `to_currency` | balance ندارد؛ delta محاسبه می‌شود | `type`, `cash_flow`, `is_deleted` | سه FK به accounts، FK دسته، معامله و حساب پراپ؛ WalletService و گزارش‌ها |
| BrokerCashMovement / `broker_cash_movements` | `amount` مثبت ذخیره‌شده؛ مالک رخداد گردش بین دو دامنه | ستون `currency` | balance ندارد؛ تغییر دو طرف محاسبه می‌شود | `direction`؛ status/archive ندارد | personal_trading_account_id، financial_account_id، transaction_id؛ BrokerCashService، Broker API، Finance و finance_metrics |

### 2.2 مدل‌های مالی تکمیلی و پشتیبان

| Model / table | دادهٔ مالی / ارز / موجودی | وضعیت، ارتباط و مصرف |
|---|---|---|
| Category / `categories` | عدد مالی، ارز و موجودی ندارد؛ مالک نام/نوع دسته‌بندی | `type`: income/expense/transfer/conversion؛ transactions.category_id؛ Finance API و دسته‌بندی هزینه/برداشت |
| PropWithdrawal / `prop_withdrawals` | `amount`, `currency` ذخیره‌شده؛ `withdrawal_date` و `created_at`؛ موجودی ندارد | FK به prop_stages، accounts مقصد و transactions؛ status requested/approved/processing/received/cancelled؛ PayoutService و Prop API |
| PropCost / `prop_costs` | `amount`, `currency`, `cost_date` ذخیره‌شده؛ موجودی ندارد | FK به prop_accounts؛ cost_type purchase/reset/addon/data_fee/refund/other؛ `is_refunded` Integer؛ Prop API؛ فاقد transaction_id |
| PropFirm / `prop_firms` | `default_profit_share` ذخیره‌شده، درصد است نه پول؛ ارز/موجودی ندارد | مالک تنظیم پیش‌فرض شرکت؛ Prop API، رابطه با accounts/default_rules؛ status/archive ندارد |
| PropFirmDefaultRules / `prop_firm_default_rules` | profit_target، max_daily_dd، max_total_dd، profit_share_percentage و min_trading_days؛ ارز/موجودی ندارد | FK prop_firm_id؛ stage_type؛ قواعد پیش‌فرض ایجاد/ارزیابی مراحل، نه دفتر مالی |
| RuleViolation / `rule_violations` | `actual_value`, `limit_value` خروجی ذخیره‌شدهٔ ارزیابی؛ واحد وابسته به rule_type، نه Currency مستقل | FK prop_stage_id؛ severity PASS/WARNING/VIOLATION، occurred_at؛ PropRuleEngine و Prop API؛ منبع مجموع دارایی نیست |
| PropAlert / `prop_alerts` | مبلغ ساختاریافته، ارز و موجودی ندارد | FK prop_stage_id؛ متن هشدار و is_read/created_at؛ Prop API و Dashboard؛ منبع دفتر نیست |
| StrategyVersion / `strategy_versions` و Strategy / `strategies` | در مسیر Finance مالک موجودی نیستند؛ هویت/نسخهٔ استراتژی | Trade.version_id اجباری و StrategyVersion.strategy_id؛ پشتیبان طبقه‌بندی معاملات، نه ورودی مستقل مجموع دارایی |

برای ردیف‌هایی که موجودی ندارند، Balance/Initial/Current **در مدل تعریف نشده** است؛ این با `NOT VERIFIED` بودن DB اجرایی تفاوت دارد. مدل‌های پشتیبان قانون/هشدار در مرز دامنه آورده شده‌اند، نه به‌عنوان منابع مستقیم summary یا spendable-assets.

شواهد مدل‌ها:
- `i:\trade\MokTradeDesk\backend\app\models\finance.py:14–175`.
- `i:\trade\MokTradeDesk\backend\app\models\trading.py:24–90`.
- `i:\trade\MokTradeDesk\backend\app\models\prop.py:112–283`.
- `i:\trade\MokTradeDesk\backend\app\models\strategy.py:77–239`.

## 3. Personal Trading Account Model

### 3.1 تمام فیلدها و معنای موجودی

| فیلد | تعریف Source / مالک |
|---|---|
| id | PK |
| broker_id | FK اجباری و indexed به brokers |
| account_number | String اجباری؛ شناسهٔ نمایشی حساب، نه مبلغ |
| account_label | String اختیاری |
| currency | Enum(Currency)، اجباری، پیش‌فرض USDT |
| initial_balance | Float اجباری، default=0؛ baseline ذخیره‌شده |
| current_balance | Float اجباری، default=0؛ موجودی جاری ذخیره‌شده، نه property محاسباتی |
| is_active | Boolean اجباری، default=True |
| server_utc_offset_minutes | Integer اجباری، default/server_default=0 |
| created_at | DateTime(timezone=True)، server_default=func.now() |
| updated_at | **در مدل وجود ندارد** |
| account_type / type | **در مدل وجود ندارد**؛ شخصی بودن از دامنهٔ مدل و REAL_PERSONAL معامله می‌آید |
| is_archived / archived_at | **در مدل وجود ندارد**؛ غیرفعال‌سازی با is_active است |

در API ایجاد، اگر current_balance ارسال نشده یا None باشد، مقدار آن initial_balance می‌شود. در PATCH فیلدهای صریحاً ارسال‌شده با setattr نوشته می‌شوند؛ تغییر initial_balance به‌تنهایی current_balance را مجدداً محاسبه نمی‌کند. initial/current در schema شرط ge=0 دارند؛ PATCH برای فیلدهای Optional مقدار None را می‌پذیرد و exclude_unset فقط ارسال‌نشدن را حذف می‌کند، نه null صریح. نتیجهٔ persistence برای null اجباری اجرا نشده: `NOT VERIFIED`.

### 3.2 روابط

- `trades.personal_trading_account_id → personal_trading_accounts.id`: یک حساب، چند معامله.
- FK مستقیم از `transactions` به personal account **وجود ندارد**.
- مسیر غیرمستقیم اول: `transactions.related_trade_id → trades → personal_trading_accounts`؛ اختیاری است و ایجاد خودکار دفتر از PnL نیست.
- مسیر غیرمستقیم دوم: `broker_cash_movements.personal_trading_account_id` و `transaction_id`؛ پل واقعی ثبت گردش وجه.
- `brokers.accounts` دارای cascade all/delete-orphan در ORM است. API حذف broker/account قبل از حذف، معاملات و سپس گردش بروکر را بررسی می‌کند؛ حذف دارای معامله با 409 و تعداد معامله متوقف می‌شود. حذف حساب شخصی از نوع hard delete است، نه archive.

### 3.3 مسیرهای خواندن و نوشتن موجودی

| مسیر | اثر دقیق |
|---|---|
| Trading API POST accounts | نوشتن initial/current، current پیش‌فرض برابر initial |
| Trading API PATCH accounts | نوشتن مستقیم مقادیر ارسالی initial/current؛ مانع تغییر ارز در صورت وجود BrokerCashMovement |
| BrokerCashService.create | deposit_to_broker: current += amount؛ withdrawal_from_broker: current -= amount |
| BrokerCashService.update | حذف اثر گردش قبلی و اعمال اثر جدید؛ امکان تغییر حساب؛ کنترل موجودی projected |
| BrokerCashService.delete | برگشت اثر بروکر و WalletService.reverse برای طرف مالی |
| Trading API GET accounts | serialize initial/current؛ فیلتر اختیاری broker_id، بدون فیلتر is_active |
| finance_metrics.broker_balance | SUM(current_balance) با فیلتر ارز |
| finance_metrics.initial_capital | SUM(initial_balance) با فیلتر ارز |
| finance_metrics.broker_pnl | SUM(current) − SUM(initial) + withdrawals − deposits، هر کدام در همان ارز |
| Finance spendable-assets | SUM(current_balance) گروه‌بندی‌شده بر اساس ارز |
| Analytics | current برای میانگین موجودی ریسک؛ initial برای baseline منحنی equity؛ fallback=10000 در مسیرهای تعریف‌شده |

جست‌وجوی ارجاعات current_balance/initial_balance و PersonalTradingAccount در `i:\trade\MokTradeDesk\backend\app` مسیر خودکار افزایش current_balance با PnL ثبت/ویرایش/import معامله را نشان نداد. نویسندگان صریح مشاهده‌شده Trading API و BrokerCashService هستند؛ import از حساب برای اعتبارسنجی/زمان سرور استفاده می‌کند. همگام‌سازی خارجی، trigger دیتابیس و اسکریپت‌های خارج از این محدوده `NOT VERIFIED` هستند.

Frontend در `i:\trade\MokTradeDesk\frontend\src\pages\BrokersPage.tsx:291–314` فقط initial_balance را در AccountForm می‌فرستد؛ current_balance در این فرم ارسال نمی‌شود، با اینکه API پذیرای آن است. دریافت حساب‌ها در BrokersPage، ImportPage، TradesPage، AnalysisPage و PayoutHistoryPage از client مشترک انجام می‌شود.

شواهد اصلی:
- `i:\trade\MokTradeDesk\backend\app\api\trading.py:54–115,177–251`.
- `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:125–271`.
- `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:23–53`.
- `i:\trade\MokTradeDesk\backend\app\api\analytics.py:180–238,484–491,564–570`.

## 4. Financial Account Model

`FinancialAccount` مالک موجودی دفتر مالی است؛ جدول آن همچنان `accounts` است. `balance` ذخیره می‌شود. initial_balance/current_balance/updated_at در مدل ندارد. created_at با زمان UTC برنامه مقداردهی می‌شود؛ کارت اختیاری در card_number ذخیره و در پاسخ API mask می‌شود.

ارزهای تعریف‌شده IRR و USDT هستند؛ `Currency.USD` alias برای USDT است و ورودی USD با سازگاری پذیرفته می‌شود. ارز ذخیره‌شدهٔ داده‌های قدیمی و casing واقعی enumها `NOT VERIFIED`.

**ایجاد موجودی اولیه:** API حساب را با balance=0 می‌سازد و مبلغ اولیهٔ غیرصفر را با تراکنش ADJUSTMENT و توضیح «موجودی اولیه» از WalletService عبور می‌دهد. در create_pair دو حساب IRR/USDT ساخته می‌شود و عدد ورودی اولیه برای هر کدام جداگانه اعمال می‌شود؛ این تبدیل نرخ ارز نیست.

**تغییر موجودی:** AccountUpdate فیلد balance ندارد. نویسندهٔ صریح تغییر balance در کد بررسی‌شده `WalletService.apply_effects` است:

`account.balance = old_balance + sign × transaction_delta`

**تطبیق دفتر:** GET reconcile، stored را با مجموع deltas تراکنش‌های مرتبط مقایسه می‌کند؛ delta=stored−ledger. این محاسبه است، نه اصلاح خودکار و نه تضمین تراز واقعی DB.

**آرشیو:** DELETE فقط اگر هیچ تراکنش در account/from/to نداشته باشد و balance نزدیک صفر باشد، is_archived=True می‌کند. شمارش تراکنش برای این محافظ شامل soft-deletedها هم هست. GET accounts آرشیوی‌ها را حذف می‌کند؛ summary/spendable-assets query فیلتر archive ندارند.

شواهد: `i:\trade\MokTradeDesk\backend\app\api\finance.py:62–77,146–240,287–316,590–645`؛ `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:235–260,584–622`.

## 5. Transactions Model

### 5.1 مالک رخداد مالی

`FinancialTransaction / transactions` شامل amount، to_amount، currency، to_currency، date، description، type، cash_flow، is_deleted و created_at است. updated_at یا موجودی مستقل ندارد.

Foreign Keyها:

- account_id → accounts.id، اجباری و indexed؛ حساب منتسب به رکورد.
- from_account_id / to_account_id → accounts.id، اختیاری؛ طرف‌های حرکت پول.
- category_id → categories.id.
- related_trade_id → trades.id.
- related_prop_account_id → prop_accounts.id.

ثبت یک تراکنش به معنی مالکیت موجودی بروکر نیست. در TRANSFER دوطرفه، WalletService.post حساب رکورد را مقصد می‌گذارد ولی deltas از from/to استفاده می‌کند. در CONVERT مبلغ و ارز سمت دریافت مجزا هستند.

### 5.2 اثر موجودی در WalletService

| نوع | اثر روی موجودی |
|---|---|
| DEPOSIT / PROFIT / EXTERNAL_INCOME | +amount روی account_id |
| WITHDRAWAL / LOSS / FEE / PURCHASE / EXTERNAL_EXPENSE | −amount روی account_id |
| ADJUSTMENT | amount علامت‌دار روی account_id |
| TRANSFER دوطرفه | −amount روی from و +amount روی to |
| TRANSFER بدون یکی از طرف‌ها | delta خالی؛ در post طرف‌ها پاک می‌شوند و صرفاً ثبت تاریخی است |
| CONVERT | −amount روی from و +to_amount روی to |

PATCH عمومی ابتدا اثر قبلی را برمی‌گرداند، ورودی را اعمال، حساب‌ها/مبلغ را اعتبارسنجی و اثر جدید را ثبت می‌کند. EXTERNAL_INCOME فقط to=account دارد و EXTERNAL_EXPENSE فقط from=account. سپس cash_flow بازمحاسبه می‌شود. account_id در TransactionUpdate قابل ارسال نیست. تراکنش متصل به BrokerCashMovement یا PropWithdrawal از PATCH/DELETE عمومی منع می‌شود. حذف معمولی، soft delete با برگشت اثر WalletService است.

### 5.3 دو تعریف مستقل درآمد

**cash_flow ذخیره‌شده** توسط detect_cash_flow:

- external_income و profit → income.
- external_expense، withdrawal، loss، fee و purchase → expense.
- transfer از بانک به غیربانک → expense؛ غیربانک به بانک → income؛ سایر transferها → none.
- deposit، adjustment و convert → none.

**bank_income_filter / is_bank_income** در زمان گزارش:

- فقط تراکنش غیرحذف‌شده و amount>0.
- DEPOSIT و PROFIT بدون محدودکردن نوع حساب.
- EXTERNAL_INCOME فقط اگر حساب رکورد BANK باشد.
- TRANSFER غیر‌بانک به بانک با account_id=to_account_id و طرف‌های متفاوت.

بنابراین cash_flow=income و «درآمد طبق helper بانکی» هم‌ارز نیستند. مثال قابل استنتاج: external_income کیف پول در summary درآمد است ولی در cashflow بانکی نیست؛ deposit در helper بانکی درآمد است ولی cash_flow آن none است.

شواهد: `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:154–232,435–535`؛ `i:\trade\MokTradeDesk\backend\app\services\financial_reporting.py:6–51`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:110–125,499–587`.

## 6. Broker Cash Movement Model

`BrokerCashMovement / broker_cash_movements` سه FK اجباری با ondelete=RESTRICT دارد: حساب شخصی، حساب مالی و transaction_id. transaction_id همچنین unique است؛ در تعریف مدل هر تراکنش حداکثر به یک movement متصل است. direction رشتهٔ 32 کاراکتری و دو مقدار پذیرفته‌شدهٔ سرویس دارد. amount/currency/date/note/created_at ذخیره می‌شوند؛ initial/current/status/archive/updated_at وجود ندارند.

| رخداد | طرف بروکر | تراکنش طرف مالی |
|---|---|---|
| deposit_to_broker | current += amount | ADJUSTMENT با amount منفی |
| withdrawal_from_broker به BANK | current -= amount | DEPOSIT مثبت با دستهٔ «واریز از بروکر» |
| withdrawal_from_broker به غیربانک | current -= amount | ADJUSTMENT مثبت |

سرویس حساب شخصی فعال، حساب مالی غیرآرشیوی، ارز برابر، مبلغ مثبت finite و کفایت موجودی طرف پرداخت را کنترل می‌کند. initial_balance تغییر نمی‌کند. ویرایش اثر قدیم را برمی‌گرداند و اثر جدید را اعمال می‌کند؛ حذف، movement را hard delete و تراکنش مالی را reverse می‌کند.

آمار GET cash-movements/stats از خود movementهاست: total مجموع قدرمطلق مبالغ هر دو جهت، total_deposits/total_withdrawals جدا، count/average/largest و گروه ماه/حساب. total در این endpoint **خالص گردش یا PnL نیست**. ارز پیش‌فرض USDT است. مسیرهای قدیمی payouts فقط withdrawal_from_broker را نمایش می‌دهند.

money-flow، تراکنش مالی وابسته به movement را کنار می‌گذارد و یک حرکت بروکر می‌سازد تا هر رخداد دو بار نمایش داده نشود. asset-trend طرف بروکر را برای خنثی‌کردن اثر جابه‌جایی داخلی اضافه می‌کند.

شواهد: `i:\trade\MokTradeDesk\backend\app\models\trading.py:65–90`؛ `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:54–87,125–271`؛ `i:\trade\MokTradeDesk\backend\app\api\broker.py:59–89,115–286`.

## 7. Trade / PnL Relationship

مالک پایهٔ سود معامله، `trades.pnl/commission/swap` است:

`net_pnl = coalesce(pnl,0) + coalesce(commission,0) + coalesce(swap,0)`

net_pnl ستون نیست؛ هم property مدل و هم عبارت SQL در metrics دارد. commission/swap با علامت ذخیره‌شده جمع می‌شوند. close_time غیرNULL معیار بسته بودن در گزارش‌های Real بررسی‌شده است.

قید طبقه‌بندی مدل:
- BACKTEST/FORWARD: نه حساب شخصی، نه prop stage.
- REAL_PERSONAL: حساب شخصی اجباری و stage تهی.
- REAL_PROP: stage اجباری و حساب شخصی تهی.
- version_id در همهٔ حالت‌ها اجباری است.

`real-summary` صریحاً test_type را با دامنهٔ REAL_PERSONAL یا REAL_PROP + FUNDED_REAL محدود می‌کند؛ currency از حساب و تاریخ از close_time می‌آید. `_compute_real_pnl` با join حساب شخصی/مرحلهٔ funded و close_time کار می‌کند و شرط test_type جدا ندارد؛ سازگاری آن با طبقه‌بندی به قید مدل/داده وابسته است.

اعداد مشتق‌شدهٔ real-summary:
- net_pnl = مجموع net معاملات بسته در دامنه.
- winning/losing = شمارش net مثبت/منفی؛ win_rate=winning/total×100.
- gross_profit = جمع netهای مثبت؛ gross_loss = قدرمطلق جمع netهای منفی.
- profit_factor از metrics.profit_factor_from_sums.
- max_dd از equity تجمعی net با شروع صفر، نه از current_balance حساب‌ها.
- sparkline آخرین ۳۰ نقطهٔ روزهای دارای معامله از تجمع PnL است؛ برخلاف توضیح «۳۰ روز»، تقویم روزهای بدون معامله را تولید نمی‌کند.

**دو PnL متفاوت بروکر:** Finance real-pnl از جمع net معاملات بسته می‌آید، ولی Analytics spendable_money از تغییر current−initial تعدیل‌شده با گردش نقدی استفاده می‌کند. هیچ برابری خودکار بین این دو در کد مشاهده‌شده وجود ندارد.

شواهد: `i:\trade\MokTradeDesk\backend\app\models\strategy.py:127–239`؛ `i:\trade\MokTradeDesk\backend\app\services\metrics.py:27–33`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:1427–1469,1547–1660`؛ `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:31–45`.

## 8. Prop Account Relationship

ساختار: `prop_firms → prop_accounts → prop_stages → trades / prop_withdrawals`؛ هزینه‌ها مستقیماً به prop_accounts متصل‌اند. PropAccount فقط ارز/هویت/فعال‌بودن دارد؛ initial_balance متعلق به Stage است.

### 8.1 منابع اعداد مرحله

- initial_balance/final_balance: ستون‌های سرمایهٔ شروع/پایان مرحله؛ API مرحله از آن‌ها استفاده می‌کند.
- current_profit: مقدار ذخیره‌شده؛ `sync_prop_stage_profit` برای مرحلهٔ ACTIVE از همهٔ معاملات مرحله net می‌گیرد؛ funded آن را در سهم `(profit_share_percentage or 80)/100` ضرب می‌کند، سایر مراحل net کامل. در این تابع close_time فیلتر نشده و مرحلهٔ غیرACTIVE به‌روز نمی‌شود.
- total_withdrawn: ستون تجمیعی ذخیره‌شده؛ PayoutService در دریافت/ویرایش/حذف برداشت مرتبط تغییر می‌دهد.
- سود Real در Finance از معاملات دوباره محاسبه می‌شود، نه از current_profit ذخیره‌شده.
- `finance_metrics.prop_stage_3`: برای هر FUNDED_REAL، `max(sum(net معاملات REAL_PROP) × share − total_withdrawn, 0)`؛ پیش‌فرض سهم هنگام None برابر ۸۰٪. در این تابع فیلتر ارز، close_time یا status مرحله نیست. خروجی spendable-assets آن را با برچسب USDT برمی‌گرداند، اما در total دارایی جمع نمی‌کند.

### 8.2 برداشت و ورود به دفتر

REQUESTED → APPROVED → PROCESSING → RECEIVED؛ مسیر CANCELLED از وضعیت‌های غیرنهایی تعریف شده است. در RECEIVED تراکنش ساخته و transaction_id روی برداشت نوشته می‌شود.

**تفاوت کامنت و بدنهٔ فعلی:** توضیح ابتدای PayoutService می‌گوید غیربانک ADJUSTMENT است، اما بدنهٔ `_post_income` بدون شرط، `TransactionType.PROFIT` به WalletService می‌دهد. update نیز new_type=PROFIT دارد. متغیر is_bank محاسبه شده ولی انتخاب نوع به آن وابسته نیست. در این گزارش رفتار بدنه ملاک است، نه کامنت. بنابراین کد فعلی دریافت پراپ به هر مقصد معتبر را PROFIT ثبت می‌کند؛ نتیجهٔ داده‌های اجرایی `NOT VERIFIED`.

### 8.3 هزینه پراپ

POST costs همیشه PropCost می‌سازد؛ فقط اگر create_transaction فعال و cost_type=PURCHASE باشد، حساب پرداخت لازم است و تراکنش PURCHASE از WalletService ساخته می‌شود. PropCost FK مستقیم به تراکنش ندارد؛ transaction_id در پاسخ API می‌آید، تراکنش related_prop_account_id دارد. گزارش expenses/net-profit جدول PropCost را مستقیماً جمع نمی‌کند؛ از transactions می‌خواند. ثبت هزینهٔ پراپ لزوماً مساوی وجود هزینه در دفتر مالی نیست.

شواهد:
- `i:\trade\MokTradeDesk\backend\app\services\import_engine.py:810–831`.
- `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:56–106`.
- `i:\trade\MokTradeDesk\backend\app\services\payout_service.py:130–205,298–378`.
- `i:\trade\MokTradeDesk\backend\app\api\prop.py:1160–1239`.

## 9. API Map

### 9.1 endpointهای اصلی و منشأ عدد

| HTTP / مسیر کامل | داده و محاسبهٔ واقعی | Frontend اثبات‌شده |
|---|---|---|
| GET `/api/finance/summary` | assets_by_currency=Σaccounts.balance؛ income/expense=Σtransactions.amount بر اساس cash_flow؛ transfers فقط TRANSFER؛ تراکنش‌های غیرحذف‌شده، تفکیک IRR/USDT | FinancePage و DashboardPage |
| GET `/api/finance/accounts` | balance ذخیره‌شده؛ حذف archivedها؛ فیلتر type/currency | FinancePage، DashboardPage، فرم‌های مقصد مالی |
| GET `/api/finance/spendable-assets` | به تفکیک ارز: Σbalance همه حساب‌های مالی + Σcurrent_balance حساب‌های شخصی؛ بدون جمع سرمایه/سود دریافت‌نشدهٔ پراپ؛ prop_stage_3 جدا | FinancePage و DashboardPage |
| GET `/api/finance/real-summary` | net و متریک معاملات بستهٔ REAL_PERSONAL + FUNDED_REAL؛ currency و date_from/date_to | DashboardPage |
| GET `/api/finance/real-pnl` | جمع net معاملات بسته متصل به حساب شخصی یا funded، تفکیک broker/prop | FinancePage |
| GET `/api/finance/net-profit` | real_pnl − Σ(FEE,PURCHASE)؛ تک‌ارز و by_currency؛ بازه تاریخ ندارد | FinancePage و DashboardPage |
| GET `/api/finance/charts/cashflow` | درآمد=bank_income_filter؛ هزینه=WITHDRAWAL/LOSS/FEE/PURCHASE؛ گروه سال/ماه میلادی، فیلتر year/currency | FinancePage و DashboardPage |
| GET `/api/finance/asset-trend` | تجمع signed transactions و جبران طرف بروکر در movementها؛ دو ارز، روز شمسی؛ شروع تجمع صفر در بازه | DashboardPage |
| GET `/api/trading/accounts` | initial/current ذخیره‌شده؛ broker_id اختیاری، بدون active filter | BrokersPage، ImportPage، TradesPage، AnalysisPage، PayoutHistoryPage |
| GET `/api/broker/cash-movements` و `/stats` | جدول movement، جهت/حساب/ارز/تاریخ؛ stats از مبالغ گردش | PayoutHistoryPage |
| GET `/api/finance/money-flow` | تراکنش‌های جریان/دارای لینک + movementها، حذف نمایش دوبارهٔ تراکنش بروکر | FinancePage |
| GET `/api/finance/expenses` | FEE/PURCHASE/EXTERNAL_EXPENSE؛ دسته‌بندی با متن category/description و نوع حساب، by_currency | FinancePage |
| GET `/api/finance/money-cycle` | deposits=DEPOSIT+EXTERNAL_INCOME؛ withdrawals=WITHDRAWAL+EXTERNAL_EXPENSE؛ total_exchanges=TRANSFER؛ total_transfers=رکوردهای دارای هر دو لینک؛ current_balance=Σaccounts.balance | FinancePage |
| GET `/api/analytics/dashboard` | spendable_money.net_pnl=broker_pnl تعدیل‌شده+funded_pnl؛ total_balance=broker_balance+funded_pnl؛ initial_capital=Σinitial | DashboardPage از getDashboardData |

نام literal `/api/finance/cash-flow` در router بررسی‌شده تعریف نشده است؛ مسیر cash flow موجود `/api/finance/charts/cashflow` است. این با money-flow و ستون cash_flow سه مفهوم/مسیر مجزا است.

### 9.2 سایر مسیرهای Finance

- accounts: POST؛ PATCH/DELETE `/{account_id}`؛ GET `/{account_id}/stats` و `/reconcile`.
- categories: GET/POST؛ PATCH/DELETE `/{category_id}`؛ POST `/api/finance/seed` برای seed دسته‌ها (فقط شناسایی، اجرا نشده).
- transactions: GET/POST؛ PATCH/DELETE `/{transaction_id}`.
- withdrawals: GET/POST؛ GET `/stats`؛ PUT/PATCH/DELETE `/{withdrawal_id}`. این‌ها نمایی از FinancialTransaction هستند، نه جدول جدید prop_withdrawals.
- POST `/api/finance/sync/trades`: فراخوانی سرویس no-op.
- GET `/api/finance/charts/distribution`: count و sum amount بر اساس نوع، date range؛ فیلتر ارز ندارد.
- GET `/api/finance/reports/monthly`: تراکنش‌ها، سال شمسی، یک ارز، حساب اختیاری، income helper و EXPENSE_TYPES.
- GET `/api/finance/reports/category-breakdown`: گروه category/kind، مبلغ/تعداد/درصد؛ ارز و سال/ماه/حساب اختیاری.
- GET `/api/finance/reports/account-comparison`: balance ذخیره‌شده و income/expense محاسبه‌شدهٔ حساب، ارز اختیاری؛ query حساب‌ها archive filter ندارد.
- GET `/api/finance/reports/profit-loss`: income−expense تراکنش‌ها، نه Trade PnL؛ year برای انتخاب monthly، totals از دادهٔ query کل دوره محاسبه می‌شود.
- GET `/api/finance/financial-calendar`: همهٔ معاملات بسته بدون فیلتر test_type/currency و تراکنش‌های DEPOSIT/WITHDRAWAL غیرحذف‌شده؛ روز شمسی. این endpoint دامنهٔ Real-summary را ندارد.

### 9.3 مسیرهای مرتبط Trading/Broker/Prop

- `/api/trading/brokers`: GET/POST و PATCH/DELETE `/{broker_id}`.
- `/api/trading/accounts`: GET/POST و PATCH/DELETE `/{account_id}`.
- `/api/broker/cash-movements`: GET/POST، GET `/stats`، PATCH/DELETE `/{movement_id}`.
- `/api/broker/payouts` و `/payouts/stats`: GET سازگار با مسیر قدیمی، فقط برداشت بروکر.
- `/api/prop/accounts`، `/accounts/{id}`، `/stages/all` و مسیرهای pass/fail/rules/trades/evaluate/violations: مدیریت حساب/مرحله و ارزیابی.
- `/api/prop/stages/{stage_id}/withdraw` و `/withdrawals`؛ `/api/prop/payouts` و `/payouts/stats`؛ PUT/PATCH/DELETE payout؛ POST `/status` و `/transfer`.
- POST `/api/prop/costs` و GET `/api/prop/accounts/{account_id}/costs`.

مراجع API: `i:\trade\MokTradeDesk\backend\app\api\finance.py:146–2005`، `i:\trade\MokTradeDesk\backend\app\api\trading.py:121–251`، `i:\trade\MokTradeDesk\backend\app\api\broker.py:115–286`، `i:\trade\MokTradeDesk\backend\app\api\prop.py:263–1239`.

## 10. Data Flow

در مسیرهایی که سرویس مستقل ندارند، «Service» عملاً helper/query داخل API است؛ لایهٔ فرضی به معماری اضافه نشده است.

### 10.1 Finance summary
```text
DB accounts + transactions
→ FinancialAccount + FinancialTransaction
→ query حساب‌ها + _cash_flow_sum / _tx_sum / _tx_count داخل API
→ GET /api/finance/summary
→ client.getFinanceSummary
→ FinancePage.summary / DashboardPage.finance.summary
```

### 10.2 Finance accounts
```text
DB accounts
→ FinancialAccount.balance (stored)
→ query مستقیم API با is_archived=False
→ GET /api/finance/accounts
→ client.getFinanceAccounts
→ لیست/کارت حساب‌ها و انتخاب مقصد در Frontend
```

### 10.3 Spendable assets
```text
DB accounts + personal_trading_accounts
→ FinancialAccount.balance + PersonalTradingAccount.current_balance
→ SUM/group_by داخل API بر اساس نوع و ارز
→ GET /api/finance/spendable-assets (by_currency + total)
→ client.getSpendableAssets
→ FinancePage / DashboardPage

DB prop_stages + trades
→ PropStage + Trade
→ finance_metrics.prop_stage_3
→ همان API، فیلد جداگانه prop_stage_3 (خارج از total)
```

### 10.4 Real summary / Net profit
```text
DB trades + personal_trading_accounts + prop_stages + prop_accounts
→ Trade و حساب‌های مرتبط برای currency/scope
→ metrics.net_pnl_sql + aggregation/equity داخل API
→ GET /api/finance/real-summary
→ client.getRealSummary → DashboardPage

همان جداول → _compute_real_pnl
DB transactions → _expenses_total (FEE/PURCHASE)
→ تفریق دو مقدار
→ GET /api/finance/net-profit
→ client.getNetProfit → FinancePage / DashboardPage
```

### 10.5 Cash flow / Asset trend
```text
DB transactions + accounts مرتبط
→ FinancialTransaction
→ financial_reporting.bank_income_filter + گروه‌بندی SQL ماهانه
→ GET /api/finance/charts/cashflow
→ client.getFinanceCashflow → نمودار FinancePage / DashboardPage

DB transactions + broker_cash_movements
→ FinancialTransaction + BrokerCashMovement
→ جدول علامت نوع تراکنش + broker_delta + تجمع روز شمسی
→ GET /api/finance/asset-trend
→ client.getAssetTrend → DashboardPage.assetTrend → AreaChart
```

Asset trend snapshot موجودی نیست: current/initial حساب شخصی و PnL معاملات را نمی‌خواند؛ TRANSFER/CONVERT به دلیل نبود در جدول sign کنار گذاشته می‌شوند؛ با date_from از صفر داخل همان بازه شروع می‌شود و ماندهٔ قبل از بازه را حمل نمی‌کند.

### 10.6 Personal accounts / Broker movements
```text
DB personal_trading_accounts + brokers
→ PersonalTradingAccount + Broker
→ query و _serialize_pta داخل Trading API
→ GET /api/trading/accounts
→ client.getPersonalTradingAccounts
→ BrokersPage / ImportPage / TradesPage / AnalysisPage / PayoutHistoryPage

DB broker_cash_movements + حساب‌ها
→ BrokerCashMovement و relationshipها
→ _movement_query / _serialize / stats داخل Broker API
→ GET /api/broker/cash-movements[/stats]
→ client.getBrokerCashMovements / getBrokerCashMovementStats
→ PayoutHistoryPage
```

مسیرهای نوشتن موجود در Source (در این audit اجرا نشده):
```text
فرم حساب شخصی → Trading API → initial/current ذخیره‌شده
فرم گردش → Broker API → BrokerCashService
  → current_balance حساب شخصی
  → WalletService → FinancialTransaction + FinancialAccount.balance
  → BrokerCashMovement با transaction_id
فرم تراکنش → Finance API → WalletService → transactions + accounts.balance
برداشت پراپ RECEIVED → PayoutService → WalletService → transactions + accounts.balance
  → prop_withdrawals.transaction_id + prop_stages.total_withdrawn
```

### 10.7 شواهد Frontend و تبدیل نمایشی

- `i:\trade\MokTradeDesk\frontend\src\api\client.ts:407–408,695–710,766–877,948–978`: مسیرهای درخواست.
- `i:\trade\MokTradeDesk\frontend\src\pages\FinancePage.tsx:244–329`: دریافت summary/cashflow، گزارش‌های پیشرفته و گزارش‌های جدید.
- `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:202–233`: دریافت Real با بازه، summary بدون currency، cashflow با currency، net-profit با currency و asset-trend بدون date range.
- `i:\trade\MokTradeDesk\frontend\src\pages\PayoutHistoryPage.tsx:144,163`: دریافت لیست/آمار گردش و حساب‌های شخصی.
- `i:\trade\MokTradeDesk\frontend\src\pages\FinancePage.tsx:796–799`: عدد اصلی کارت دارایی از `Object.values(summary.assets_by_currency).reduce(...)` ساخته می‌شود؛ یعنی مبالغ ارزهای مختلف در Frontend جمع می‌شوند، درحالی‌که زیرنویس تفکیک ارز را نشان می‌دهد.
- `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:780–783`: دارایی انتخاب‌شده از assets_by_currency[currency] نمایش داده می‌شود.
- `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:482–523,867–869`: نمایش متریک‌های Real و نمودار assetTrend.

## 11. Unknown / NOT VERIFIED

1. schema واقعی DB، وجود جدول‌ها/قیدها/indexها، داده‌های فعلی و مانده‌ها: `NOT VERIFIED`؛ اتصال انجام نشده است.
2. فعال بودن DATABASE_URL پیش‌فرض، revision اعمال‌شده، heads و وضعیت migration/backfill قدیمی: `NOT VERIFIED`.
3. سازگاری داده‌های cash_flow ذخیره‌شده با detect_cash_flow فعلی، casing enumهای قدیمی و صحت currency رکوردها: `NOT VERIFIED`.
4. برابری accounts.balance با ledger، current_balance بروکر با initial+PnL±movements، total_withdrawn با برداشت‌های RECEIVED: `NOT VERIFIED`؛ صرفاً فرمول‌ها/نویسندگان کد شناسایی شده‌اند.
5. وجود trigger، job، script نگهداری، import خارجی یا نویسندهٔ موجودی خارج از backend/app بررسی‌شده: `NOT VERIFIED`.
6. وضعیت واقعی کارکرد UI، نتیجهٔ HTTP، commit/rollback تحت خطای DB، رفتار concurrent و گذر تست‌ها: `NOT VERIFIED`؛ هیچ runtime/test اجرا نشده است.
7. اثر عملی یافته‌های تفاوت گزارش بر ماندهٔ کاربر یا وقوع double counting در دادهٔ واقعی: `NOT VERIFIED`؛ گزارش فقط تفاوت مسیرها و فرمول‌ها را اثبات می‌کند.
8. پوشش تمام بخش‌های نامرتبط پروژه، backup/restore و همهٔ جزئیات risk/import خارج از اتصال مستقیم Finance: `NOT VERIFIED` و خارج از هدف این مرحله.
9. صرف اشارهٔ comment/docstring به «تنها منبع حقیقت»، «۳۰ روز» یا «فقط بانک» اثبات رفتار نیست؛ در موارد اختلاف، بدنهٔ تابع در گزارش نقل شده است.

## 12. Findings

1. **سه مالک مستقل عدد وجود دارد:** موجودی مالی در accounts.balance، موجودی شخصی بروکر در personal_trading_accounts.current_balance، سود معامله در trades با net محاسباتی.
2. **PersonalTradingAccount دو موجودی ذخیره‌شده دارد** و account_type، is_archived و updated_at ندارد. current در ایجاد می‌تواند از initial مقدار بگیرد، ولی تغییر initial یا ثبت معامله الزاماً current را تغییر نمی‌دهد.
3. **پل واقعی بروکر با دفتر، BrokerCashMovement است**؛ نه FK مستقیم transactions به personal account. سرویس هم‌زمان طرف مالی و موجودی بروکر را تغییر می‌دهد.
4. **FinanceSyncService معامله را به تراکنش تبدیل نمی‌کند.** مقدار برگشتی sync صفر است.
5. **Summary، cashflow و net-profit تعریف واحد درآمد/هزینه ندارند.** summary از cash_flow، cashflow از bank helper و فهرست انواع، net-profit از PnL منهای FEE/PURCHASE استفاده می‌کند.
6. **پشتیبانی external expense در همه گزارش‌ها یکسان نیست:** expenses و asset-trend و money-cycle آن را دارند؛ cashflow، expense stats حساب، گزارش‌های پیشرفته مبتنی بر EXPENSE_TYPES و net-profit آن را در فهرست هزینهٔ خود ندارند.
7. **Spendable-assets سرمایه و سود دریافت‌نشدهٔ پراپ را در total جمع نمی‌کند.** total آن شامل حساب‌های مالی و current بروکر است؛ prop_stage_3 جداست و helper آن فیلتر ارز/بسته‌بودن معامله ندارد.
8. **PnL بروکر در Analytics و Finance دو فرمول متفاوت دارد:** تغییر موجودی تعدیل‌شده با گردش در برابر جمع net معاملات بسته.
9. **Asset trend موجودی تاریخی کامل نیست:** از جریان‌های منتخب و جبران حرکت بروکر، با شروع صفر ساخته می‌شود؛ current/initial بروکر و Trade PnL را نمی‌خواند و CONVERT را محاسبه نمی‌کند.
10. **بدنهٔ PayoutService با توضیح آن همخوان نیست:** دریافت پراپ در کد فعلی بدون وابستگی به نوع مقصد PROFIT است؛ ادعای ADJUSTMENT برای غیربانک فقط در توضیح دیده می‌شود.
11. **PropCost منبع مستقیم گزارش هزینه نیست.** تنها مسیر مشروط PURCHASE تراکنش مالی می‌سازد؛ مدل هزینه FK تراکنش ندارد.
12. **فیلترهای وضعیت یکسان نیستند:** لیست حساب مالی archived را پنهان می‌کند، ولی aggregationهای summary/spendable چنین فیلتری ندارند؛ aggregation بروکر نیز is_active را فیلتر نمی‌کند.
13. **برخی اعداد Frontend دوباره ساخته می‌شوند:** کارت اصلی دارایی FinancePage مقادیر چند ارز را جمع می‌کند؛ Dashboard برای همان مفهوم کلید ارز انتخابی را می‌خواند. پارامترهای بازه/ارز همهٔ درخواست‌های Dashboard نیز یکسان نیستند.
14. **financial-calendar و distribution دامنه/ارز متفاوت دارند:** calendar همهٔ معاملات بسته را می‌خواند؛ هر دو query بدون تفکیک ارز برای برخی مبالغ خروجی‌اند.

این یافته‌ها توصیف Source فعلی هستند؛ هیچ Fix یا پیشنهاد اجرایی در این مرحله ارائه یا اعمال نشده است.