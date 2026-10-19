# FINANCE AUDIT — PART 2

دامنه: حساب‌های شخصی بروکر در MokTradeDesk. روش: بررسی ایستای Source فعلی، نه اتکا به گزارش مرحلهٔ اول. هیچ برنامه، تست، migration یا اتصال دیتابیس اجرا نشده است. تنها نوشتهٔ این مرحله همین گزارش است. عبارت «در DB رخ می‌دهد» در سناریوها یعنی اثر کد در صورت موفقیت درخواست و commit، نه مشاهدهٔ DB واقعی.

## 1. Personal Trading Account Model

مدل `PersonalTradingAccount`، جدول `personal_trading_accounts`، مستقل از `FinancialAccount / accounts` است.

| فیلد | تعریف ORM و کاربرد |
|---|---|
| id | Integer، PK، indexed |
| broker_id | Integer، NOT NULL، indexed، FK به brokers.id |
| account_number | String، NOT NULL؛ شمارهٔ حساب نمایشی؛ unique نیست |
| account_label | String nullable؛ نام اختیاری |
| currency | Enum(Currency)، NOT NULL، default=USDT |
| initial_balance | Float، NOT NULL، default=0؛ مقدار اولیهٔ ذخیره‌شده |
| current_balance | Float، NOT NULL، default=0؛ مقدار جاری ذخیره‌شده |
| is_active | Boolean، NOT NULL، default=True |
| server_utc_offset_minutes | Integer، NOT NULL، default و server_default برابر صفر |
| created_at | DateTime(timezone=True)، server_default=func.now()؛ nullable در تعریف مدل |

تمام فیلدهای مدل همین‌ها هستند. `login` جداگانه، رمز یا اتصال احراز‌شده به بروکر، `account_type`، `balance`، `updated_at`، `is_archived` و `archived_at` در این مدل وجود ندارند. account_number ممکن است توسط کاربر برابر login وارد شود؛ اتصال آن به login واقعی اثبات نشده است. UniqueConstraint برای `(broker_id, account_number)` نیز تعریف نشده است.

روابط ORM: `broker`، `trades` و `cash_movements`. Broker شامل id/name/website/notes/is_active/server_utc_offset_minutes/created_at است و موجودی ندارد؛ رابطهٔ accounts آن cascade all/delete-orphan دارد.

API شمارهٔ حساب را trim و خالی‌نبودن/حداکثر ۱۰۰ کاراکتر را کنترل می‌کند. initial/current در schema حداقل صفر دارند؛ این محدودیت API است، نه CheckConstraint موجودی در مدل. timestamp و offset در ورودی CRUD حساب شخصی عرضه نشده‌اند؛ serializer offset را هم برنمی‌گرداند. تغییرات موجودی timestamp مستقل یا سابقهٔ snapshot ندارند.

شواهد: `i:\trade\MokTradeDesk\backend\app\models\trading.py:24–90`؛ `i:\trade\MokTradeDesk\backend\app\api\trading.py:54–115`.

## 2. Balance Ownership

**پاسخ اصلی: current_balance یک ماندهٔ ذخیره‌شده با مقداردهی/بازنویسی دستی از API و تغییر افزایشی توسط گردش وجه بروکر است؛ ماندهٔ محاسبه‌شده از معاملات یا دفتر تراکنش‌ها نیست.**

| تعبیر | پاسخ مبتنی بر کد |
|---|---|
| موجودی واقعی و زندهٔ بروکر؟ | تضمین نمی‌شود؛ دریافت موجودی از اتصال بروکر در مسیرهای بررسی‌شده وجود ندارد |
| موجودی پس از معاملات؟ | خودکار خیر؛ تنها اگر ورودی دستی قبلاً آن را منعکس کرده باشد |
| موجودی پس از Deposit/Withdrawal؟ | بله، برای گردش‌های ثبت‌شده از BrokerCashService، نسبت به مقدار ذخیره‌شدهٔ قبلی |
| دستی وارد می‌شود؟ | بله؛ POST/PATCH مقدار current را می‌پذیرند. فرم BrokersPage فقط initial را می‌فرستد |
| از trades محاسبه می‌شود؟ | خیر؛ PnL و commission/swap حساب شخصی را تغییر نمی‌دهند |
| از transactions محاسبه می‌شود؟ | خیر؛ WalletService فقط accounts.balance را تغییر می‌دهد |
| از broker_cash_movements بازسازی می‌شود؟ | خیر؛ اثر هر عملیات روی مقدار موجود اعمال می‌شود، نه rebuild کل تاریخچه |
| ترکیبی از منابع؟ | ترکیب «آخرین مقداردهی مستقیم + دلتاهای گردش پس از آن»، نه جمع چهار جدول |

بدون PATCH مستقیم، از زمان ایجاد API:

`current = current_input_if_supplied_else_initial + deposits − withdrawals`

ویرایش/حذف گردش‌ها نیز اثر قبلی را اصلاح/برمی‌گرداند. پس از overwrite دستی، baseline این رابطه مقدار جدید است. تغییر initial به‌تنهایی current را تغییر نمی‌دهد. رابطهٔ `initial + net_trade_pnl + deposits − withdrawals` در کد برای current برقرار نشده است.

توضیح ابتدای finance_metrics ادعا می‌کند broker_balance «خودش شامل سود است»؛ این پیش‌فرض مصرف‌کننده است، نه عملیاتی که نویسندگان current انجام دهند. تفاوت این قرارداد و بدنهٔ مسیرهای نوشتن، یافتهٔ اصلی این مرحله است.

شواهد: `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:1–52`؛ `i:\trade\MokTradeDesk\backend\app\api\trading.py:186–227`؛ `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:125–271`.

## 3. Balance Update Paths

### نویسندگان current و initial

| مسیر | نوشتن و اثر جانبی |
|---|---|
| ORM defaults | initial=0 و current=0 مستقل؛ ایجاد مستقیم مدل الزاماً current=initial نمی‌کند |
| POST حساب شخصی | initial ورودی؛ current ورودی یا initial در صورت None/عدم ارسال؛ فقط ایجاد PTA، بدون FinancialTransaction یا Movement |
| PATCH حساب شخصی | `model_dump(exclude_unset=True)` سپس setattr؛ overwrite مستقیم initial/current؛ بدون سند مالی، movement یا reconciliation |
| BrokerCashService.create | خط 157: current قدیم + amount در deposit، یا −amount در withdrawal؛ initial ثابت |
| BrokerCashService.update | خطوط 189–198 و 233–235: حذف دلتای قبلی و اعمال جدید؛ در تغییر حساب، هر دو PTA تغییر می‌کنند |
| BrokerCashService.delete | خطوط 260–266: current − دلتای گردش؛ initial ثابت |
| migration تاریخی phase28 | خطوط 103–113، initial و current هر دو از balance حساب BROKER قدیمی کپی می‌شوند؛ اجرا/اعمال واقعی NOT VERIFIED |

جست‌وجوی current_balance در فایل‌های Python/SQL backend غیرتست و ارجاعات PersonalTradingAccount در backend/app، نویسندهٔ runtime دیگری نشان نداد. migrationهای قدیمی‌تر نیز تعریف ستون legacy دارند؛ تعریف ستون با نویسندهٔ runtime جدول فعلی یکسان نیست. `finance.py:1862` فیلدی هم‌نام در پاسخ money-cycle است، نه نوشتن PTA.

### خوانندگان موجودی

| Service / helper | خواندن |
|---|---|
| finance_metrics.broker_balance | SUM(current) به تفکیک currency، بدون active filter |
| finance_metrics.broker_pnl | SUM(current) − SUM(initial) + SUM(withdrawals) − SUM(deposits)، هم‌ارز؛ نه Trade PnL |
| finance_metrics.initial_capital | SUM(initial) با currency |
| finance_metrics.total_balance | فراخوانی broker_balance + funded_pnl با ارز پیش‌فرض USDT؛ تابع خودش نویسنده نیست |
| BrokerCashService | current برای کنترل کفایت، محاسبهٔ مقدار جدید و برگشت؛ initial را تغییر نمی‌دهد |
| Trading API serializer | initial/current ذخیره‌شده در GET/PATCH |
| Finance spendable-assets | SUM(current) گروه‌بندی‌شده با currency |
| Analytics._scope_avg_balance | میانگین current حساب‌های دامنهٔ real یا همهٔ حساب‌ها؛ fallback فرضی 10000 |
| Analytics._scope_initial_balance_with_source | جمع initial هر id یکتا، currency اختیاری؛ baseline equity |

ImportEngine و TradeValidator حساب را برای وجود FK، طبقه‌بندی و ساعت سرور می‌خوانند، نه برای به‌روزکردن current. WalletService نویسندهٔ **FinancialAccount.balance** است، نه current حساب شخصی. FinanceSyncService.sync_closed_trades هم no-op و return 0 است.

### API Map حساب شخصی و وابستگی‌های مستقیم

| روش و مسیر کامل | رفتار |
|---|---|
| GET `/api/trading/accounts` | همهٔ PTAها؛ broker_id اختیاری؛ بدون فیلتر active/currency؛ ترتیب created_at نزولی |
| POST `/api/trading/accounts` | ساخت؛ وجود Broker بررسی می‌شود، فعال‌بودن Broker نه |
| PATCH `/api/trading/accounts/{account_id}` | broker_id، number، label، currency، initial، current، is_active؛ ارز دارای movement قابل تغییر نیست |
| DELETE `/api/trading/accounts/{account_id}` | hard delete؛ معامله → 409؛ movement → 400؛ موجودی غیرصفر مانع نیست |
| GET/POST `/api/trading/brokers` | فهرست/ساخت Broker |
| PATCH/DELETE `/api/trading/brokers/{broker_id}` | ویرایش/حذف Broker؛ حذف با محافظ معاملات و movements زیرمجموعه؛ cascade حساب‌ها |
| GET/POST `/api/broker/cash-movements` | فهرست/ثبت گردش PTA↔FinancialAccount |
| GET `/api/broker/cash-movements/stats` | آمار گردش، نه PnL و نه مانده |
| PATCH/DELETE `/api/broker/cash-movements/{movement_id}` | اصلاح/برگشت هر دو طرف |
| GET `/api/broker/payouts` و `/api/broker/payouts/stats` | نمای legacy فقط withdrawal_from_broker |
| GET `/api/trades/`، GET/PATCH/DELETE `/api/trades/{trade_id}` | خواندن/ویرایش/حذف معاملات مرتبط؛ فیلتر personal_trading_account_id در فهرست |
| POST `/api/trades/manual` و `/api/trades/batch-delete` | ایجاد/حذف گروهی؛ بدون تغییر current شخصی |
| POST `/api/imports/preview` و `/api/imports/commit/{batch_id}` | ورود معاملات با context حساب؛ commit معاملات/هویت‌های import، بدون sync current |
| POST `/api/imports/soft4x` و `/api/imports/mt4` | ورودی‌های import قدیمی؛ نویسندهٔ current در جست‌وجو مشاهده نشد |
| POST `/api/analytics/analyze/personal-account/{personal_trading_account_id}` | تحلیل دامنهٔ حساب؛ API تحلیل، نه تغییر موجودی |
| GET `/api/analytics/analysis/personal-account/{personal_trading_account_id}` | دریافت تحلیل حساب |
| GET `/api/finance/spendable-assets`، `/real-pnl`، `/real-summary`، `/net-profit` | موجودی یا PnL مرتبط، طبق فرمول‌های متفاوت |
| GET `/api/analytics/dashboard`، `/risk-metrics`، `/risk-advanced` | مصرف تحلیل/مانده در دامنهٔ Analytics |
| GET `/api/finance/money-flow`، `/asset-trend`، `/withdrawals/stats` | مصرف movement یا جریان مالی مربوط به بروکر |

در router حساب‌ها GET تک‌حساب، PUT، archive، reconcile PTA و انتقال مستقیم PTA→PTA تعریف نشده است. endpointهای import batch/profile مدیریت ورودند، نه مدیریت موجودی. router prefixها از main.py بررسی شدند.

شواهد: `i:\trade\MokTradeDesk\backend\app\api\trading.py:121–251`؛ `i:\trade\MokTradeDesk\backend\app\api\broker.py:34–286`؛ `i:\trade\MokTradeDesk\backend\app\main.py:183–198`؛ `i:\trade\MokTradeDesk\backend\app\api\analytics.py:176–238,305–316,484–491,568,1126`؛ `i:\trade\MokTradeDesk\backend\app\api\import_engine.py:203–295`؛ `i:\trade\MokTradeDesk\backend\migrations\versions\a1b2c3d4e5f6_phase28_trading_domain.py:62–113`.

## 4. Trade Relationship

`trades.personal_trading_account_id` FK nullable به PTA است؛ CheckConstraint مدل برای REAL_PERSONAL آن را اجباری و prop_stage_id را تهی می‌خواهد. version_id نیز لازم است. هر حساب چند معامله دارد؛ مالک حساب با FK تعیین می‌شود، نه account_number.

`net_pnl = (pnl or 0) + (commission or 0) + (swap or 0)`؛ property محاسباتی است، نه ستون یا trigger. هزینه‌ها با علامت ذخیره‌شده جمع می‌شوند؛ commission مثبت به‌صورت خودکار منفی نمی‌شود.

ایجاد دستی Trade، pnl/commission/swap را ذخیره می‌کند؛ فراخوانی بعدی FinanceSyncService برای حساب شخصی کاری نمی‌کند. PATCH همین فیلدها یا اتصال حساب را تغییر می‌دهد ولی current هیچ‌یک از حساب‌های شخصی تغییر نمی‌کند. حذف معامله هم اثر معکوس بر current ندارد؛ لینک nullable تراکنش تاریخی به معامله در مسیر hard delete پاک می‌شود، نه اثر مبلغ آن.

Import commit معاملات، ImportIdentity و وضعیت batch را ذخیره می‌کند؛ sync بعدی فقط برای prop_stage است. انتقال معامله از PTA اول به دوم، انتقال وجه نیست و مانده‌ها را جابه‌جا نمی‌کند.

Trade ارز مستقل ندارد؛ گزارش Real از ارز **فعلی حساب مرتبط** استفاده می‌کند. بنابراین تغییر ارز PTA بدون movement، حتی با معاملات قبلی، طبقه‌بندی ارزی تاریخچهٔ PnL را تغییر می‌دهد، بدون تبدیل عدد.

شواهد: `i:\trade\MokTradeDesk\backend\app\models\strategy.py:127–224`؛ `i:\trade\MokTradeDesk\backend\app\api\trades.py:530–660,765–801`؛ `i:\trade\MokTradeDesk\backend\app\services\import_engine.py:974–1019`؛ `i:\trade\MokTradeDesk\backend\app\services\finance_sync_service.py:20–28`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:1450–1469,1572–1589`.

## 5. Transaction Relationship

transactions FK مستقیم به PTA ندارد. account_id/from_account_id/to_account_id همگی به accounts.id اشاره دارند. حتی اگر id مالی و شخصی عدد یکسانی داشته باشند، دو دامنهٔ متفاوت‌اند.

دو اتصال غیرمستقیم وجود دارد:

1. transactions.related_trade_id → trades.personal_trading_account_id؛ ارتباط اختیاری، بدون sync موجودی شخصی.
2. broker_cash_movements.transaction_id و personal_trading_account_id؛ اتصال عملیاتی گردش وجه.

WalletService.deltas و apply_effects فقط موجودی حساب مالی را تغییر می‌دهند. ثبت دستی PROFIT/FEE/DEPOSIT به حساب مالی، current بروکر را تغییر نمی‌دهد. TRANSFER مالی نیز فقط بین حساب‌های accounts است.

PATCH/DELETE عمومی تراکنش متصل به movement در Finance API رد می‌شود؛ مسیر اصلاح آن BrokerCashService است. برگشت WalletService تراکنش را soft-delete و اثر حساب مالی را معکوس می‌کند.

شواهد: `i:\trade\MokTradeDesk\backend\app\models\finance.py:134–175`؛ `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:197–260,540–578`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:517,578`.

## 6. Broker Cash Movement Relationship

هر movement دارای PTA، حساب مالی، transaction_id unique، direction، amount مثبت، currency، date، note و created_at است. سه FK اصلی NOT NULL و ondelete=RESTRICT هستند. status/soft-delete مستقل ندارد.

| عمل | current شخصی | حساب مالی / transactions |
|---|---|---|
| deposit_to_broker | +amount | ADJUSTMENT با مبلغ منفی؛ balance مالی −amount |
| withdrawal_from_broker به BANK | −amount | DEPOSIT مثبت؛ balance مالی +amount؛ دستهٔ «واریز از بروکر» |
| withdrawal_from_broker به غیربانک | −amount | ADJUSTMENT مثبت؛ balance مالی +amount |

ثبت، transaction مالی و movement و تغییر مانده‌ها را پیش از commit نهایی انجام می‌دهد. ایجاد و ویرایش: PTA باید فعال، حساب مالی غیرآرشیوی و ارز دو طرف برابر باشد؛ مبلغ finite و مثبت؛ کنترل کفایت موجودی با tolerance برابر 0.005. فعال‌بودن Broker والد بررسی نمی‌شود.

ویرایش، دلتای قبلی را از مانده حذف و جدید را اعمال می‌کند؛ می‌تواند حساب/جهت/مبلغ/تاریخ را عوض کند. تغییر حساب movement «تصحیح تاریخچه» است، نه ساخت انتقال تازه بین دو PTA. حذف پس از کنترل موجودی، transaction را reverse، current را معکوس و movement را hard-delete می‌کند؛ حتی برای PTA غیرفعال، delete شرط active ندارد. update همان movement روی PTA غیرفعال از _load_accounts رد می‌شود.

آمار total جمع مبلغ هر دو جهت است؛ deposit+withdrawal را سود تلقی نمی‌کند. query فهرست/آمار به‌صورت پیش‌فرض USDT و دارای فیلتر PTA/حساب مالی/جهت/تاریخ است. در API ساخت، currency ورودی مستقلی نیست؛ از حساب گرفته می‌شود.

شواهد: `i:\trade\MokTradeDesk\backend\app\models\trading.py:65–90`؛ `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:54–87,98–271`؛ `i:\trade\MokTradeDesk\backend\app\api\broker.py:34–89,115–227`.

## 7. Multi-Account Behavior

- چند حساب روی یک Broker یا Brokerهای مختلف مجاز است. موجودی‌ها مستقل و بر اساس id هستند.
- شمارهٔ تکراری در یک Broker در مدل/CRUD منع نشده؛ دو رکورد از یک حساب واقعی می‌توانند جداگانه در total جمع شوند. وقوع واقعی چنین داده‌ای NOT VERIFIED است.
- spendable-assets همهٔ حساب‌های هم‌ارز را یک بار جمع می‌کند؛ join با trades/movements در SUM آن وجود ندارد، پس تکثیر سطر ناشی از join رخ نمی‌دهد.
- broker_pnl متریک تجمیعی ارزی است، نه API سود تک‌حساب؛ کل current/initial و کل movements همان ارز را می‌خواند.
- baseline اولیهٔ Analytics از مجموعهٔ idهای یکتا ساخته می‌شود؛ تعداد معاملات یک حساب initial آن را چند برابر نمی‌کند.
- انتقال مستقیم PTA→PTA وجود ندارد. دو گردش از طریق یک FinancialAccount هم‌ارز از نظر کد قابل ثبت‌اند، ولی دو درخواست مستقل‌اند، نه یک انتقال اتمیک. این توصیف رفتار موجود است، نه پیشنهاد اجرایی.

شواهد: `i:\trade\MokTradeDesk\backend\app\api\finance.py:1505–1528`؛ `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:23–52`؛ `i:\trade\MokTradeDesk\backend\app\api\analytics.py:222–238`.

## 8. Currency Separation

Currency فعلی IRR و USDT است؛ USD alias سازگاری USDT است. هر PTA یک currency دارد. list_accounts فیلتر ارز ندارد، ولی هر ردیف ارز خود را برمی‌گرداند. UI هر current را کنار ارز حساب نمایش می‌دهد.

spendable-assets دو total مستقل `usdt` و `irr` و by_currency دارد؛ broker legacy مربوط به USDT و broker_irr مربوط به IRR است. finance_metrics نیز currency را فیلتر می‌کند. گردش دو ارز مختلف رد می‌شود؛ تبدیل نرخ در BrokerCashService وجود ندارد.

محدودیت: PATCH ارز فقط وجود movement را بررسی می‌کند، نه موجودی غیرصفر یا trades. در حساب فاقد movement، مقدار 10000 USDT می‌تواند صرفاً با تغییر enum به 10000 IRR تبدیل برچسب شود؛ هیچ exchange-rate اعمال نمی‌شود و PnL تاریخی نیز با ارز جدید گزارش می‌شود.

Analytics._scope_avg_balance در شاخهٔ all همهٔ currentها را بدون فیلتر ارز میانگین می‌گیرد؛ این helper برای تعبیر پولی چندارزی ایمن نیست. دامنه و فراخوانی runtime آن اجرا نشده است. کارت اصلی FinancePage نیز summary.assets_by_currency را جمع می‌کند، اما آن summary فقط حساب‌های مالی را دارد؛ این مورد **جمع دوبارهٔ موجودی شخصی بروکر نیست**.

شواهد: `i:\trade\MokTradeDesk\backend\app\models\finance.py:32–42`؛ `i:\trade\MokTradeDesk\backend\app\api\trading.py:218–224`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:1505–1534`؛ `i:\trade\MokTradeDesk\backend\app\api\analytics.py:176–200`؛ `i:\trade\MokTradeDesk\frontend\src\pages\FinancePage.tsx:796–799`.

## 9. Archive Behavior

PTA قابلیت archive مدل‌شده ندارد. PATCH is_active=False فقط همان flag را تغییر می‌دهد:

- current/initial و تاریخچه حفظ می‌شوند؛ هیچ movement یا transaction جبرانی ایجاد نمی‌شود.
- از GET حساب‌ها و SUMهای دارایی حذف نمی‌شود.
- ایجاد/ویرایش گردش روی آن رد می‌شود؛ حذف گردش شرط فعال‌بودن ندارد.
- TradeValidator فقط وجود حساب را کنترل می‌کند، نه فعال‌بودن؛ در اعتبارسنجی حساب import نیز شرط active مشاهده نشد.
- is_active=False برای Broker، flag فرزندان را تغییر نمی‌دهد؛ خود Broker شرط ورود گردش نیست.

DELETE جایگزین archive نیست: با trades/movements ممنوع، در غیر این صورت hard delete حتی با current غیرصفر است. DELETE Broker نیز همین محافظ‌های تاریخچه را دارد و می‌تواند حساب‌های بدون تاریخچه ولی دارای مانده را با cascade حذف کند. در نتیجه total دارایی کاهش می‌یابد، بدون سند برداشت.

شواهد: `i:\trade\MokTradeDesk\backend\app\api\trading.py:136–171,177–251`؛ `i:\trade\MokTradeDesk\backend\app\utils\trade_validator.py:15–24`؛ `i:\trade\MokTradeDesk\backend\app\services\import_engine.py:634–641`؛ `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:54–65,251–267`.

## 10. Double Counting Analysis

### مسیرهای واقعی جمع

| خروجی | فرمول مربوط به حساب شخصی | شمارش تکراری خودکار چهار منبع؟ |
|---|---|---|
| Finance spendable-assets | ΣFinancialAccount.balance + ΣPTA.current، برای هر ارز | خیر؛ transactions/movements/trades دوباره به total اضافه نمی‌شوند |
| Finance summary.assets_by_currency | فقط ΣFinancialAccount.balance | خیر؛ PTA اصلاً در این total نیست |
| Analytics spendable_money.total_balance | broker_balance + funded_pnl | Trade PnL شخصی به current اضافه نمی‌شود؛ funded مربوط به پراپ است |
| Finance real-pnl / real-summary | net معاملات بسته، نه total assets | خروجی مجزا؛ جمع خودکار آن با current مشاهده نشد |
| asset-trend | signed transactions + broker movement delta | دو سمت انتقال با علامت مخالف خنثی می‌شوند؛ current و trades خوانده نمی‌شوند |
| money-flow | حذف transactionهای دارای movement از نمایش، سپس افزودن خود movement | یک رخداد دو بار نمایش داده نمی‌شود |

برای واریز داخلی x: `Δtotal = (+x PTA) + (−x financial) = 0`. برای برداشت هم `−x+x=0`. وجود سند transaction و movement به‌خودی‌خود double counting نیست.

### مسیرهای مشروطِ ثبت تکراری/بیش‌نمایی

این‌ها امکان قابل استنتاج از API هستند، نه مدرک وقوع در دادهٔ واقعی:

1. **ثبت دوبارهٔ برداشت به شکل تراکنش مستقل:** ابتدا withdrawal movement به مبلغ x → current−x و financial+x؛ سپس DEPOSIT/PROFIT دستی مستقل برای همان دریافت → financial دوباره +x، بدون کاهش PTA. spendable-assets از مسیر financial.balance مبلغ x را اضافه نشان می‌دهد. تراکنش اضافه transaction_id متفاوت دارد و محافظ لینک movement آن را شناسایی نمی‌کند.
2. **ماندهٔ دستی شامل گردش، سپس ثبت دوبارهٔ همان گردش:** current=10000؛ PATCH به 12000 برای snapshotی که واریز 2000 را شامل است؛ سپس deposit movement همان رخداد → current=14000 و financial−2000. در قیاس با snapshot صحیح current باید 12000 باشد؛ total به اندازهٔ 2000 اضافه می‌شود. خود aggregate دوباره جمع نکرده، baseline و رخداد تکرار شده‌اند.
3. **سود هم در snapshot و هم در دفتر مالی بدون خروج واقعی:** current دستی شامل +500 سود؛ ثبت PROFIT +500 در حساب مالی برای همان سودِ هنوز در بروکر → Σcurrent+Σfinancial دو بازنمایی یک سود را می‌شمارد. ثبت Trade +500 به‌تنهایی عامل این تکرار نیست.
4. **دو PTA برای یک حساب واقعی:** POST با broker_id/account_number تکراری و current یکسان مجاز است؛ هر دو رکورد در SUM وارد می‌شوند. هیچ dedup بر اساس login واقعی نیست.
5. **ایجاد موجودی اولیهٔ PTA برای پولی که هنوز در حساب مالی ثبت است:** POST initial=10000 هیچ بدهکارکردن حساب مالی ندارد؛ اگر این دو رکورد نمایندهٔ یک پول باشند، total آن را دو بار می‌شمارد. کد تشخیص نمی‌دهد دو موجودی مستقل‌اند یا یک منبع تکراری.

در مسیر عادی بدون ورودی دستی تکراری، مشکل اصلی **جاافتادن اثر PnL شخصی از current** است، نه جمع مجدد trades. این مسئله با ریسک مشروط double counting فرق دارد.

شواهد: `i:\trade\MokTradeDesk\backend\app\api\finance.py:607–645,1490–1535,1694–1759,1923–1984`؛ `i:\trade\MokTradeDesk\backend\app\api\analytics.py:484–491,564–570`؛ `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:197–260`.

## 11. Scenario Results

پیش‌فرض سناریوهای A تا F: یک Broker موجود، حساب شخصی فعال USDT، یک حساب مالی هم‌ارز با ماندهٔ W و W≥2000، ورودی معتبر و commit موفق؛ هیچ PATCH دستی current بین مراحل نیست. معاملات بسته و REAL_PERSONAL هستند. برای E هزینهٔ فرضی commission=−10 و swap=−5 استفاده شده است؛ این اعداد دادهٔ واقعی نیستند.

| سناریو | اثر قابل استنتاج در DB | initial / current و پیامد |
|---|---|---|
| A. ایجاد با 10000 USDT | یک PTA جدید؛ initial=10000؛ current ارسال نشده پس 10000؛ بدون transactions/movements | initial=10000، current=10000؛ مالی W؛ total=W+10000 |
| B. واریز 2000 | movement deposit و transaction ADJUSTMENT −2000؛ مالی W−2000؛ PTA +2000 | initial=10000، current=12000؛ total همچنان W+10000 |
| C. معامله +500 | یک Trade با pnl=500؛ finance sync هیچ سندی نمی‌سازد؛ موجودی‌ها ثابت | current=12000، نه 12500؛ Trade net تجمعی +500 |
| D. معامله −300 | Trade دوم با pnl=−300؛ موجودی‌ها ثابت | current=12000، نه 12200؛ Trade net تجمعی +200 |
| E. commission/swap | ذخیرهٔ −10 و −5 روی Trade؛ net تجمعی +185؛ نه movement و نه transaction خودکار | current=12000، نه 12185؛ اگر فقط فایل واقعی بروکر هزینه دارد و وارد نشده، DB تغییر نمی‌کند |
| F. برداشت 1000 | movement withdrawal؛ transaction DEPOSIT به بانک یا ADJUSTMENT مثبت به غیربانک؛ مالی W−1000 | initial=10000، current=11000؛ total=W+10000؛ ماندهٔ معاملاتی مبتنی بر A–F با هزینهٔ فرضی 11185 است، اما در current ذخیره نشده |

پس از A–F، `broker_pnl = 11000−10000+1000−2000 = 0`، ولی جمع net معاملات `185` است. اختلاف از کد ناشی می‌شود؛ هیچ اجرا یا دستکاری DB برای تولید این مثال انجام نشده است.

**E، حالت سند مالی جداگانه:** اگر کاربر FEE مالی نیز ثبت کند، accounts.balance کم می‌شود، نه PTA.current. پرداخت commission از موجودی بروکر با پرداخت هزینه از کیف پول مالی یک مسیر نیست؛ ثبت هر دو برای یک هزینه ممکن است خروجی‌های هزینه/PnL را تکراری کند، ولی خود trades به total assets جمع نمی‌شود.

**G. انتقال بین دو PTA:** endpoint مستقیم ندارد. درخواست TRANSFER مالی با PTA id معنای حساب شخصی ندارد؛ id در namespace accounts تفسیر می‌شود. با دو گردش مستقل x از PTA اول به مالی و سپس از مالی به PTA دوم: اولی −x، دومی +x، مالی در پایان بدون تغییر، دو movement و دو transaction؛ initialها ثابت. اگر درخواست دوم شکست بخورد فقط مرحلهٔ اول commit شده است. تغییر personal_trading_account_id یک movement قدیمی، بازنویسی نسبت تاریخی همان گردش است، نه ثبت این انتقال دو مرحله‌ای.

**H. چند حساب همزمان:** ایجاد هرکدام یک ردیف مستقل؛ trades/movements متعلق به FK خودشان؛ جمع فقط برای ارز مشترک. سود معاملهٔ یک حساب current هیچ حسابی را تغییر نمی‌دهد. حساب غیرفعال هم در جمع هست. دو درخواست همزمان روی یک حساب جدا از «چند حساب» است؛ آزمون concurrent انجام نشده است.

**I. Archive:** endpoint/فیلد archive وجود ندارد. غیرفعال‌سازی فقط flag را تغییر می‌دهد؛ دارایی حذف نمی‌شود و تاریخچه باقی است. DELETE پس از A بدون trade/movement می‌تواند ردیف با 10000 موجودی را حذف کند؛ پس از A–F به‌علت تاریخچه رد می‌شود. این حذف برداشت مالی یا archive نیست.

**J. USDT و IRR همزمان:** مثلاً حساب USDT با current=10000 و حساب IRR با current=500000000؛ سهم broker در by_currency به‌ترتیب همین دو عدد است، نه جمع عددی آن‌ها. گردش هرکدام حساب مالی هم‌ارز می‌خواهد؛ بین دو ارز رد می‌شود. پیش‌فرض لیست movement/stats ارز USDT است و برای IRR باید currency مشخص شود. تغییر ارز حساب فاقد movement تنها relabel است، نه تبدیل.

## 12. Confirmed Bugs

«Confirmed» در این بخش یعنی نقص/ناسازگاری قابل اثبات از Source و مثال قطعی کد، نه مشاهدهٔ خطا در محیط اجرایی.

| شناسه | یافتهٔ تأییدشده | اثر و شدت |
|---|---|---|
| B1 | finance_metrics ماندهٔ بروکر را شامل سود معرفی می‌کند، اما مسیرهای ثبت/ویرایش/import معامله current را تغییر نمی‌دهند؛ فرم BrokersPage هم current را برای تصحیح نمی‌فرستد | ماندهٔ دارایی و broker_pnl از معاملات عقب می‌مانند مگر overwrite خارجی؛ High |
| B2 | تغییر ارز PTA دارای معاملات ولی فاقد movement مجاز است؛ هیچ تبدیل مبلغ یا محافظ تاریخچهٔ Trade ندارد | انتقال مصنوعی مانده و PnL تاریخی بین ارزها؛ High |
| B3 | DELETE حساب و Broker والد ماندهٔ غیرصفر حساب‌های بدون trade/movement را کنترل نمی‌کند | حذف منبع دارایی از total بدون ثبت خروج وجه؛ High |
| B4 | schema PATCH مقدار null صریح برای فیلدهای NOT NULL مانند current/initial/currency/is_active/broker_id/account_number می‌پذیرد و setattr آن را اعمال می‌کند؛ اعتبارسنجی null مشابه movement update ندارد | ناسازگاری قرارداد ورودی با ORM/DB؛ نوع پاسخ خطای واقعی NOT VERIFIED؛ Medium |

موارد زیر رفتار/ریسک تأییدشده‌اند، ولی بدون قرارداد محصول به‌تنهایی «باگ قطعی» نامیده نمی‌شوند: نبود archive، باقی‌ماندن حساب غیرفعال در دارایی، نبود انتقال مستقیم PTA، مجازبودن current دستی، عدم uniqueness شمارهٔ حساب، نبود updated_at، عدم ارائهٔ current در فرم و پذیرش Broker غیرفعال برای فرزند فعال. هرکدام در بخش مربوط توضیح داده شد.

شواهد B1: `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:1–45`؛ `i:\trade\MokTradeDesk\backend\app\api\trades.py:765–801`؛ `i:\trade\MokTradeDesk\frontend\src\pages\BrokersPage.tsx:291–314`.

شواهد B2–B4: `i:\trade\MokTradeDesk\backend\app\api\trading.py:72–89,148–171,208–251`؛ `i:\trade\MokTradeDesk\backend\app\models\trading.py:44–58`.

## 13. NOT VERIFIED

- schema واقعی دیتابیس، revision migration، فعال‌بودن constraints/foreign keys و تعداد/مبالغ حساب‌ها بررسی نشده است.
- اینکه currentهای موجود واقعاً از صورت‌حساب بروکر وارد شده‌اند یا نه، timestamp آخرین همگام‌سازی و مطابقت با بروکر واقعی NOT VERIFIED است.
- داده‌های legacy، اجرای migration phase28 و پاکسازی حساب‌های مالی قدیمی BROKER بررسی اجرایی نشده؛ صرف مشاهدهٔ migration دلیل وقوع double counting فعلی نیست.
- هیچ درخواست HTTP، تست، import، تراکنش یا سناریوی مالی اجرا نشده است. سناریوها تحلیل Source هستند.
- وقوع واقعی ثبت دوبارهٔ سود/برداشت، حساب‌های تکراری و overwriteهای دستی NOT VERIFIED است.
- رفتار concurrent، lost update، isolation و rollback زیر خطای DB آزموده نشده؛ عملیات current از نوع read-modify-write است، ولی وقوع race اثبات نشده است.
- اسکریپت‌های خارجی، triggerهای نصب‌شده و integration خارج از مخزن نمی‌توانند با جست‌وجوی Source نفی شوند.
- همهٔ مصرف‌کنندگان runtime یا پردازش‌های خارج از backend/app و frontend/src قابل اثبات نیستند. جست‌وجوی balance در backend غیرتست و migrationها و خواندن مسیرهای مستقیم این گزارش انجام شد؛ متن گزارش‌های قبلی مدرک مستقل محسوب نشده است.
- معنای محصولی «فعال»، الزام یکتایی login و قرارداد snapshot دستی مشخص نشده‌اند؛ برای این موارد نقص طراحی قطعی ادعا نشده است.

## 14. Risk Level

**سطح کلی: HIGH برای اتکا به current_balance به‌عنوان موجودی واقعی پس از معاملات.** دلیل: مقدار برای total assets و کفایت برداشت استفاده می‌شود، ولی معاملات و هزینه‌های معاملاتی آن را به‌روز نمی‌کنند و API اجازهٔ overwrite بدون سابقهٔ اصلاح می‌دهد.

| حوزه | سطح | مبنا |
|---|---|---|
| تطابق current با معاملات واقعی | High | B1؛ اختلاف عددی سناریوی A–F |
| حفظ ارز تاریخچه | High | B2؛ relabel مانده و PnL بدون تبدیل |
| حذف مانده بدون سند | High | B3 |
| Double counting خودکار چهار جدول در spendable-assets | مشاهده نشد | SUM فقط دو ستون مانده، بدون join تکثیرکننده |
| ثبت تکراری دستی/duplicate account | High، مشروط | مسیرهای بخش 10 ممکن‌اند؛ وقوع داده‌ای NOT VERIFIED |
| تفکیک ارز در total اصلی spendable-assets | Low برای اختلاط مستقیم | دو total جدا؛ این نتیجه به helperهای دیگر تعمیم داده نمی‌شود |
| گردش داخلی استاندارد بروکر↔مالی | متوازن در تحلیل ایستا | دلتاهای برابر و مخالف؛ صحت runtime/concurrency NOT VERIFIED |
| غیرفعال‌سازی/اعتبارسنجی PATCH | Medium | معنای محدود is_active و nullهای ناسازگار |

نتیجه: current_balance «snapshot/ماندهٔ دستی تعدیل‌شده با گردش‌های ثبت‌شده» است؛ نه ماندهٔ خودکار مبتنی بر trades و نه ledger بازسازی‌شده. این گزارش صرفاً Audit است و هیچ Fix، پیشنهاد پیاده‌سازی، تغییر کد یا داده انجام نشده است.