# Finance Audit — Part 5: Personal Assets

ممیزی ایستای کد؛ تاریخ: ۲۰۲۶-۱۰-۰۸. فقط این گزارش نوشته شده است؛ برنامه، تست، migration و عملیات دیتابیس اجرا نشده‌اند. یافته‌های زیر بر خواندن مستقیم منابع متکی‌اند، نه تأیید ضمنی گزارش‌های قبلی. «تأییدشده» یعنی رفتار قابل استنتاج از کد، نه مشاهده در دادهٔ واقعی.

## 1. Personal Wealth Definition

**نزدیک‌ترین پاسخ موجود به «همهٔ دارایی شخصی من امروز چقدر است؟» خروجی `total.usdt` و `total.irr` از `/api/finance/spendable-assets` است، نه یک عدد واحد و نه کارت «موجودی کل».**

برای هر ارز c، تعریف پیاده‌شده:

`PersonalAssets[c] = Σ FinancialAccount.balance[c] + Σ PersonalTradingAccount.current_balance[c]`

سرمایهٔ اولیهٔ بروکر، سود معاملاتی و مبالغ جابه‌جایی دوباره به این جمع اضافه نمی‌شوند. دریافت‌های پراپ فقط از طریق موجودی حساب مقصد وارد آن می‌شوند. سرمایه و سود دریافت‌نشدهٔ پراپ خارج‌اند.

این یک snapshot از **موجودی‌های ذخیره‌شده** است؛ نه ارزش‌گذاری لحظه‌ای، نه equity مبتنی بر سود باز و نه لزوماً ثروت خالص پس از بدهی‌ها یا دارایی‌های خارج از سیستم. شرط اعتماد: همهٔ محل‌های نگهداری واقعی ثبت شده باشند، یک پول در دو حساب موازی ثبت نشده باشد و موجودی بروکر به‌روز باشد. این شروط با کد aggregate اثبات نمی‌شوند.

شواهد: `i:\trade\MokTradeDesk\backend\app\api\finance.py:1490–1535` و `i:\trade\MokTradeDesk\frontend\src\components\FinancialAssetBalances.tsx:3–46`.

## 2. Financial Accounts

تمام انواع واقعی enum شش مورد زیرند؛ بروکر و پراپ نوعی از FinancialAccount نیستند. منبع همهٔ ردیف‌ها جدول `accounts`، فیلد موجودی `balance` و فیلد ارز `currency` است.

| نوع واقعی | ارز مجاز در API ساخت/ویرایش | Personal Assets / Spendable total | Summary و کارت موجودی کل داشبورد | analytics total_balance | آرشیو |
|---|---|---|---|---|---|
| BANK / bank | USDT، IRR | بله، هر ارز جدا | بله | خیر | در aggregate باقی می‌ماند |
| CASH / cash | USDT، IRR | بله، هر ارز جدا | بله | خیر | همان |
| CARD / card | USDT، IRR | بله، هر ارز جدا | بله | خیر | همان |
| EXCHANGE / exchange | USDT، IRR | بله، هر ارز جدا | بله | خیر | همان |
| CRYPTO_WALLET / crypto_wallet | فقط USDT | بله | بله | خیر | همان |
| TRUST_WALLET / trust_wallet | فقط USDT | بله | بله | خیر | همان |

منابع: `i:\trade\MokTradeDesk\backend\app\models\finance.py:14–42,78–96`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:57–59,607–644,1497–1527`؛ `i:\trade\MokTradeDesk\backend\app\api\analytics.py:484–491,564–570`.

لیست حساب‌ها `is_archived == False` دارد، ولی summary، spendable و money-cycle ندارند. مسیر آرشیو عادی تنها حساب بدون تراکنش و با موجودی تقریباً صفر را می‌پذیرد؛ بنابراین نبود فیلتر به‌تنهایی اثبات بزرگ‌نمایی عدد فعلی نیست. اثر حساب آرشیوشدهٔ غیرصفرِ قدیمی یا تغییریافته نیازمند داده است. منابع: `i:\trade\MokTradeDesk\backend\app\api\finance.py:146–174,287–316,1846–1862`.

کارت بانکی در این مدل یک موجودی مستقل است؛ در aggregate سازوکاری برای تشخیص اینکه کارت و بانک نمایندهٔ یک پول مشترک‌اند دیده نمی‌شود. ثبت یک موجودی واقعی در هر دو ردیف، ریسک ثبت تکراری است، نه باگ قطعی بدون اطلاع از قرارداد داده.

## 3. Personal Broker Accounts

منبع: جدول `personal_trading_accounts`؛ `initial_balance`، `current_balance`، `currency` و `is_active`. آرشیو مالی به این مدل تعمیم ندارد. aggregateهای بروکر فیلتر `is_active` ندارند؛ حساب غیرفعال هم شمرده می‌شود. غیرفعال‌بودن لزوماً به معنای ازدست‌رفتن مالکیت پول نیست.

**ردگیری نویسندگان موجودی:**

| عملیات | اثر تأییدشده روی current_balance | شاهد |
|---|---|---|
| ساخت حساب | مقدار ورودی یا در نبود آن initial_balance | `i:\trade\MokTradeDesk\backend\app\api\trading.py:186–205` |
| ویرایش حساب | انتساب مستقیم فیلدهای payload با setattr؛ اصلاح موجودی دستی ممکن است | `i:\trade\MokTradeDesk\backend\app\api\trading.py:208–227` |
| ساخت گردش بروکر | واریز مثبت، برداشت منفی؛ سمت مالی نیز با WalletService ثبت می‌شود | `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:75–87,97–164` |
| ویرایش گردش | برگشت اثر قدیم و اعمال اثر جدید بر هر دو سمت | `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:189–247` |
| حذف گردش | برگشت تراکنش مالی و اثر بروکر | `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:250–271` |
| ساخت/ویرایش معامله | تغییر Trade؛ فراخوانی sync_closed_trades عملاً no-op است | `i:\trade\MokTradeDesk\backend\app\api\trades.py:574–592,758–799`؛ `i:\trade\MokTradeDesk\backend\app\services\finance_sync_service.py:20–28` |
| حذف تکی/گروهی معامله | حذف Trade و وابستگی‌ها؛ sync مرحلهٔ پراپ، نه موجودی بروکر | `i:\trade\MokTradeDesk\backend\app\api\trades.py:600–689` |
| import معاملات | درج Trade و ImportIdentity؛ sync فقط برای مرحلهٔ پراپ | `i:\trade\MokTradeDesk\backend\app\services\import_engine.py:943–1023` |

نتیجه: در مسیرهای بررسی‌شده، **ثبت سود معامله خودکار current_balance بروکر را افزایش نمی‌دهد**. جست‌وجوی سراسری current_balance و hookهای معمول ORM در کد برنامه نیز نویسندهٔ خودکار دیگری نشان نداد؛ trigger خارجی دیتابیس بررسی نشده است. قرارداد کامنت «موجودی شامل سود است» به معنی تضمین نگهداری خودکار آن نیست.

`broker_pnl = current − initial + withdrawals − deposits` نیز مقدار balance-based است؛ با جمع PnL معاملات بسته الزاماً برابر نیست. منابع: `i:\trade\MokTradeDesk\backend\app\models\trading.py:44–62`؛ `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:23–53`.

## 4. Prop Separation

| مؤلفه | جایگاه در دارایی شخصی |
|---|---|
| سرمایهٔ اسمی حساب/مرحلهٔ پراپ | وارد مجموع شخصی نمی‌شود؛ پول شخصی کاربر فرض نشده است |
| full funded PnL | در analytics total_balance وارد می‌شود، اما در spendable total خیر |
| سهم کاربر | فقط در helper سود قابل برداشت اعمال می‌شود |
| سود دریافت‌نشده | خارج از مجموع شخصی؛ prop_stage_3 فیلد جداگانه است |
| payout دریافت‌شده | در لحظهٔ RECEIVED با WalletService به حساب مالی مقصد افزوده می‌شود |

`funded_pnl`: جمع `pnl + commission + swap` برای REAL_PROP، مرحلهٔ FUNDED_REAL، ارز انتخابی و معاملهٔ بسته؛ **نه کسر سهم شرکت و نه کسر برداشت قبلی**.

`prop_stage_3 = Σ max(stage_net × share − total_withdrawn, 0)`؛ سهم پیش‌فرض ۸۰٪ است. این helper بر خلاف funded_pnl فیلتر close_time و ارز ندارد. بنابراین این دو عدد حتی پیش از payout هم تعریف یکسان ندارند.

منابع: `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:56–106`؛ `i:\trade\MokTradeDesk\backend\app\services\metrics.py:22–33`.

دریافت payout: فقط ورود به وضعیت RECEIVED فراخوانی ثبت مالی دارد؛ transaction_id از ثبت مجدد در مسیر سرویس جلوگیری می‌کند و `stage.total_withdrawn` به اندازهٔ مبلغ افزایش می‌یابد. در مجموع spendable، همان پول فقط در balance مقصد است؛ prop_stage_3 داخل total جمع نمی‌شود. این طراحی در مسیر سالم، دوباره‌شماری دریافت پراپ ندارد. با این حال funded_pnl تاریخی پس از دریافت کم نمی‌شود؛ جمع‌کردن آن با دارایی شخصی توسط مصرف‌کننده دوباره‌شماری ایجاد می‌کند. منابع: `i:\trade\MokTradeDesk\backend\app\services\payout_service.py:139–205`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:1521–1528`.

## 5. Total Balance

سه عدد متفاوت با نام‌های نزدیک وجود دارد:

1. **کارت «موجودی کل» داشبورد:** `summary.assets_by_currency[currency]`، فقط مالی؛ بروکر حذف شده است. منبع: `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:775–785` و `i:\trade\MokTradeDesk\backend\app\api\finance.py:619–624`.
2. **analytics.spendable_money.total_balance:** `broker_balance[c] + funded_pnl[c]`؛ مالی حذف شده، سود کامل پراپ اضافه شده است. با تعریف ثروت شخصی سازگار نیست. منبع: `i:\trade\MokTradeDesk\backend\app\api\analytics.py:484–491,564–570`.
3. **مجموع دارایی شخصی:** مالی + بروکر، دو ارز جدا؛ مناسب‌ترین snapshot موجود با محدودیت به‌روز بودن balanceها. منبع: `i:\trade\MokTradeDesk\backend\app\api\finance.py:1490–1535`.

helper `total_balance(db)` نیز فقط بروکر USDT + funded PnL USDT است؛ نباید از نام آن جامع‌بودن را نتیجه گرفت (`i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:75–77`).

`money-cycle.current_balance` فقط مالی و تفکیک‌شده برحسب ارز است (`i:\trade\MokTradeDesk\backend\app\api\finance.py:1824–1868`). `asset-trend` موجودی امروز را بازسازی نمی‌کند: تجمع جریان‌های بازه از صفر، با جبران سمت بروکر در گردش‌هاست؛ initial/current بروکر و سود معاملاتی را مبنا قرار نمی‌دهد و CONVERT را نادیده می‌گیرد. بنابراین ماندهٔ انتهای آن الزاماً با دارایی شخصی برابر نیست؛ نادیده‌گرفتن تبدیل برای دو سری ارزی نیز تغییر واقعی موجودی هر ارز را منعکس نمی‌کند. منبع: `i:\trade\MokTradeDesk\backend\app\api\finance.py:1923–1984`.

## 6. Spendable Assets

API اصلی به تفکیک هفت محل نگهداری (شش نوع مالی + بروکر) خروجی می‌دهد و total را از همان bucketها می‌سازد. `prop_stage_3` جداست و جمع نمی‌شود. بنابراین نام spendable در اینجا بیشتر «دارایی شخصی ثبت‌شده» است؛ نقدشوندگی، وجه آزاد/مارجین یا امکان برداشت فوری بروکر را کنترل نمی‌کند.

رابط فعلی `FinancialAssetBalances` از by_currency و total استفاده می‌کند؛ نه از فیلدهای legacy و نه prop_stage_3. این component در داشبورد و صفحهٔ مالی مصرف می‌شود. منابع: `i:\trade\MokTradeDesk\frontend\src\components\FinancialAssetBalances.tsx:13–46`؛ `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:857–860`؛ `i:\trade\MokTradeDesk\frontend\src\pages\FinancePage.tsx:1283–1286`؛ اتصال API: `i:\trade\MokTradeDesk\frontend\src\api\client.ts:824–827`.

فیلدهای legacy برای bank/card/cash فقط IRR و برای سایر انواع فقط USDT برمی‌گردانند؛ مثلاً bank.amount نمایندهٔ همهٔ بانک‌ها نیست. by_currency این محدودیت را ندارد. این ریسک قرارداد مصرف‌کنندگان قدیمی است، نه نقص جدول فعلی. منبع: `i:\trade\MokTradeDesk\backend\app\api\finance.py:1530–1534`.

## 7. Currency Separation

| مسیر | وضعیت |
|---|---|
| summary.assets_by_currency | تفکیک درست؛ currency انتخابی دارایی‌ها را به یک ارز تبدیل نمی‌کند |
| کارت موجودی کل داشبورد | انتخاب یک ارز؛ بدون جمع ارزی |
| FinancePage کارت «مجموع دارایی‌ها» | **جمع مستقیم Object.values با reduce؛ USDT + IRR بدون FX** |
| spendable by_currency/total و component فعلی | دو ستون و دو مجموع مستقل؛ درست |
| analytics broker_balance/funded_pnl | فیلتر ارز انتخابی دارد |
| helper total_balance(db) | پیش‌فرض USDT، نه ثروت همهٔ ارزها |
| prop_stage_3 | همهٔ مراحل بدون فیلتر ارز؛ برچسب خروجی USDT؛ ناسازگار |
| money-cycle | جمع مالی به تفکیک ارز |
| asset-trend | دو سری جدا، ولی تبدیل ارز را حذف می‌کند؛ تفکیک اسمی، نه بازسازی کامل مانده |

شاهد خطای جمع UI: `i:\trade\MokTradeDesk\frontend\src\pages\FinancePage.tsx:793–799`. سایر شواهد در بخش‌های ۴ تا ۶ آمده‌اند. برای گردش بروکر همسان‌بودن ارز دو حساب الزام است (`i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:54–64`). در مدل Currency، USD alias همان USDT است؛ این alias نرخ تبدیل یا برابری ارزش بازار را اثبات نمی‌کند (`i:\trade\MokTradeDesk\backend\app\models\finance.py:32–42`).

## 8. Double Counting Scenarios

همهٔ مثال‌ها ردگیری ذهنی کد و در یک ارزند؛ اجرا نشده‌اند.

**الف ـ انتقال ۲٬۰۰۰ به بروکر:** بانک ۱۰٬۰۰۰ + بروکر ۵٬۰۰۰ = ۱۵٬۰۰۰. BrokerCashService بانک را ۲٬۰۰۰ کم و بروکر را ۲٬۰۰۰ زیاد می‌کند: ۸٬۰۰۰ + ۷٬۰۰۰ = **۱۵٬۰۰۰، نه ۱۷٬۰۰۰**. رکورد FinancialTransaction و BrokerCashMovement دو ثبت مرتبط یک رویدادند، نه دو دارایی اضافی. summary فقط ۸٬۰۰۰ و analytics بدون پراپ فقط ۷٬۰۰۰ می‌شود؛ هیچ‌یک به‌تنهایی کل نیست. شواهد: `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:79–87,127–164`؛ `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:197–260`.

**ب ـ سود و برداشت:** بروکر ۱۰٬۰۰۰ + سود خالص بستهٔ ۱٬۰۰۰ − برداشت ۵۰۰ باید **۱۰٬۵۰۰** شود. با ثبت صرف معامله در مسیرهای بررسی‌شده، موجودی همان ۱۰٬۰۰۰ می‌ماند و برداشت آن را **۹٬۵۰۰** می‌کند. اگر ابتدا موجودی با صورت‌حساب واقعی به ۱۱٬۰۰۰ اصلاح شود، برداشت به‌درستی ۱۰٬۵۰۰ می‌دهد. اگر مقصد برداشت حساب مالی خود کاربر باشد، ۵۰۰ از ثروت کل خارج نشده است: بروکر ۱۰٬۵۰۰ + مقصد ۵۰۰ = ۱۱٬۰۰۰. افزودن مجدد سود ۱٬۰۰۰ به موجودی اصلاح‌شده دوباره‌شماری خواهد بود. شواهد: بخش ۳؛ فرمول سود balance-based در `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:31–45`.

**ج ـ پراپ:** سود خالص مرحله ۱٬۰۰۰، سهم کاربر ۸۰٪، دریافت ۳۰۰: قبل از دریافت سهم قابل برداشت ۸۰۰؛ پس از دریافت حساب مقصد +۳۰۰ و prop_stage_3 = ۵۰۰. spendable total فقط +۳۰۰ دارد. funded_pnl همچنان ۱٬۰۰۰ است؛ افزودن آن به موجودی مقصد هم مبلغ دریافت‌شده را تکرار می‌کند، هم سهم شرکت را شخصی فرض می‌کند. با فرض نبود معاملات باز/ارز مخلوط، helper قابل برداشت در این مثال از تکرار ۳۰۰ جلوگیری می‌کند. شواهد: `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:56–106`؛ `i:\trade\MokTradeDesk\backend\app\services\payout_service.py:190–205`.

**د ـ ثبت دستی موازی:** ثبت موجودی پول بروکر در یک FinancialAccount و هم‌زمان در PersonalTradingAccount، یا ثبت یک بانک و کارت متصل با موجودی تکراری، جمع را بزرگ می‌کند. وقوع واقعی تأیید نشده است.

## 9. Reconciliation

قابلیت موجود برای حساب مالی: `GET /accounts/{account_id}/reconcile`؛ جمع اثرهای WalletService.deltas بر تراکنش‌های حساب و مقایسه با balance ذخیره‌شده. خروجی `stored`, `ledger`, `delta = stored − ledger`, `is_balanced`, `entry_count` است. منبع: `i:\trade\MokTradeDesk\backend\app\api\finance.py:590–600`؛ `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:584–621`.

ساخت حساب مالی جدید موجودی اولیه را از طریق ADJUSTMENT ثبت می‌کند، نه صرفاً درج balance (`i:\trade\MokTradeDesk\backend\app\api\finance.py:177–240`). با این حال delta صفر فقط سازگاری داخلی دفتر با balance را نشان می‌دهد، نه تطابق با بانک واقعی، نه عدم ثبت یک پول در دو حساب. delta غیرصفر هم الزاماً فقط «موجودی اولیهٔ ضمنی» نیست؛ هر شکاف دفتر/مانده می‌تواند همین علامت را ایجاد کند.

در مسیرهای بررسی‌شده reconciliation خودکار بروکر با PnL معاملات مشاهده نشد. رابطهٔ لازم برای کنترل، با فرض پوشش کامل معاملات پس از مبنای initial:

`ExpectedBroker = initial + deposits − withdrawals + closed_net_pnl + documented_external_adjustments`

`BrokerDelta = current_balance − ExpectedBroker`

این رابطه پیشنهاد کنترل ممیزی است، **نه endpoint یا قابلیت پیاده‌شده**. اگر initial یک snapshot میانهٔ دوره باشد، افزودن همهٔ معاملات تاریخی غلط است؛ تاریخ مبنا و پوشش import باید معلوم باشند. تطبیق موجودی واقعی بروکر و ثبت کنترل‌شدهٔ اختلاف لازم است؛ بدون این اطلاعات اصلاح خودکار امن نیست.

در تطبیق کل، ابتدا هر ارز جدا، سپس هر حساب و سپس جفت‌های گردش بروکر و payout دریافتی بررسی می‌شوند. دو سناریوی بخش ۸ باید به‌عنوان invariant حسابداری بررسی شوند؛ این ممیزی هیچ اصلاح یا ثبت تطبیقی انجام نداده است.

## 10. Confirmed Bugs

«تأیید» در این جدول source-level است؛ اندازهٔ اثر روی دادهٔ واقعی معلوم نیست.

| شناسه | ایراد | اثر / شدت | شاهد |
|---|---|---|---|
| PA-01 | جمع IRR و USDT بدون FX در کارت مجموع دارایی‌های FinancePage | عدد بی‌معنی در حضور هر دو ارز؛ بالا | `i:\trade\MokTradeDesk\frontend\src\pages\FinancePage.tsx:793–799` |
| PA-02 | کارت داشبورد با عنوان کلی «موجودی کل» فقط مالی را نشان می‌دهد | کم‌نمایی نسبت به دارایی شخصی هنگام موجودی بروکر؛ نقص عنوان/دامنه، بالا | `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:775–785`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:619–624` |
| PA-03 | prop_stage_3 بدون جداسازی ارز با برچسب USDT خروجی می‌شود | مخلوط‌شدن مشروط به وجود مراحل غیر USDT؛ بالا؛ خارج از total فعلی | `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:93–106`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:1523` |
| PA-04 | helper قابل برداشت close_time ندارد، برخلاف funded_pnl | ورود PnL غیرصفر معاملات باز به عدد قابل برداشت؛ متوسط/بالا | `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:64–68,80–87` |
| PA-05 | روند دارایی ارزی اثر CONVERT را حذف می‌کند | روند هر ارز با ماندهٔ واقعی تبدیل‌شده ناسازگار؛ متوسط | `i:\trade\MokTradeDesk\backend\app\api\finance.py:1932–1957` |

**شکاف قطعی پیاده‌سازی با وابستگی به قرارداد:** عدم نگهداری خودکار سود در current_balance بروکر (بخش ۳) برای ادعای «ثروت امروز از معاملات» پرریسک است؛ اگر قرارداد محصول موجودی دستی باشد، خودِ دستی‌بودن باگ نیست، اما به‌روز بودن آن تضمین نشده است. همچنین analytics.total_balance با تعریف ثروت شخصی سازگار نیست؛ بدون تأیید قرارداد API نباید آن را جمع کل دارایی دانست. نبود فیلتر آرشیو/فعال نیز به‌تنهایی خرابی عدد را اثبات نمی‌کند.

## 11. NOT VERIFIED

- عدد واقعی دارایی امروز، موجودی هر ارز، تعداد حساب‌ها و وجود دادهٔ تکراری: دیتابیس خوانده یا اجرا نشده است.
- میزان اختلاف current_balance با صورت‌حساب بروکر و پوشش تاریخی معاملات/import؛ triggerها یا همگام‌سازهای بیرون از کد برنامه.
- موجودی غیرصفر حساب‌های آرشیوشده، سیاست مالکیت حساب غیرفعال و نقش واقعی کارت‌های بانکی.
- وجود مراحل پراپ غیر USDT یا معاملات باز با PnL غیرصفر؛ اینها شرط بروز عددی PA-03 و PA-04 هستند.
- صحت داده‌های قدیمی total_withdrawn و transaction_id، دریافت واقعی payout و امکان وصول مطالبات پراپ.
- بدهی‌ها، دارایی‌های ثبت‌نشده، ارزش لحظه‌ای پوزیشن‌ها، محدودیت برداشت، نرخ FX معتبر و لزوم احتساب سود دریافت‌نشده در تعریف اقتصادی ثروت.
- صحت runtime، رفتار concurrent، خروجی HTTP و نمایش زنده UI؛ هیچ برنامه یا تستی اجرا نشده است.
- گزارش‌های قبلی منبع اثبات این گزارش نیستند؛ تنها موارد دارای شواهد مستقیم بالا مبنای نتیجه‌اند.

## 12. Risk Level

**ریسک کلی: بالا برای تصمیم‌گیری بر مبنای «کل ثروت امروز».** دلیل اصلی ترکیب چند تعریف متفاوت، جمع ارزی نادرست در یک کارت و اتکای مجموع شخصی به موجودی بروکری است که ثبت معامله خودکار آن را تازه نمی‌کند.

در مقابل، فرمول اصلی spendable total به تفکیک ارز و گردش دوطرفهٔ بروکر در مسیر بررسی‌شده درست تفکیک شده‌اند؛ سرمایهٔ پراپ و سود دریافت‌نشده به total فعلی اضافه نمی‌شوند. مشکل را نباید به «همهٔ جمع‌ها دوباره‌شماری دارند» تعمیم داد.

پاسخ عملی ممیزی: **دو مجموع دارایی شخصی USDT و IRR را فقط به‌عنوان مجموع موجودی ثبت‌شده استفاده کنید؛ تا تطبیق موجودی بروکر و بررسی داده‌ها، عنوان «تمام ثروت واقعی امروز» تأییدشدنی نیست.**

کنترل دامنهٔ تغییر: خروجی خوانای Git در شروع فقط چهار گزارش PART1 تا PART4 را untracked نشان داد؛ نه working tree کاملاً clean. در این ادامه تنها فایل `i:\trade\MokTradeDesk\FINANCE_AUDIT_PART5_PERSONAL_ASSETS.md` ایجاد شد. هیچ اصلاح برنامه، داده، تست، commit یا push انجام نشد.