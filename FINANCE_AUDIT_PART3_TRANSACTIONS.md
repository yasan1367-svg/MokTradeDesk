# FINANCE AUDIT — PART 3

دامنه: Transactions / Cash Flow / Internal Transfers. بررسی ایستای سورس؛ بدون اجرای برنامه، تست، migration یا دسترسی/نوشتن دیتابیس. تنها خروجی این مرحله همین گزارش است. یافته‌های Part 2 مبنای اثبات این گزارش قرار نگرفتند. «تأییدشده» در این متن یعنی قابل استنتاج از سورس، نه بازتولید در محیط اجرا. مثال‌ها فرضی‌اند.

## 1. Transaction Model

مدل `FinancialTransaction` جدول `transactions` است: شناسه، `account_id` اجباری به `accounts`، دسته‌بندی اختیاری، `amount` و `currency`، `to_amount/to_currency` برای تبدیل، تاریخ رویداد، توضیح، نوع، مبدأ/مقصد اختیاری، ارتباط اختیاری با معامله/پراپ، `cash_flow`، حذف نرم و تاریخ ایجاد. پول با `Float` ذخیره می‌شود، نه Decimal. `DateTime` بدون `timezone=True` تعریف شده، هرچند default از UTC-aware استفاده می‌کند.

منبع: `i:\trade\MokTradeDesk\backend\app\models\finance.py:134–175`.

- این مدل دفتر دوبل با دو ردیف بدهکار/بستانکار نیست؛ یک ردیف انتقال می‌تواند دو موجودی را تغییر دهد.
- ارتباط با معامله، به‌خودی‌خود محاسبه یا ثبت PnL نیست؛ در مدل uniqueness برای `related_trade_id` وجود ندارد.
- POST عمومی از WalletService استفاده می‌کند؛ PATCH اثر قبلی را معکوس و اثر جدید را اعمال می‌کند؛ DELETE اثر را برمی‌گرداند و حذف نرم می‌کند. حذف تکراری سرویس بی‌اثر است، اما ایجاد تکراری idempotent نیست.
- مسیر عمومی ویرایش/حذف، تراکنش متصل به BrokerCashMovement یا PropWithdrawal را مسدود می‌کند؛ عملیات باید از دامنهٔ مالک انجام شود.
- موجودی اولیهٔ حساب مالی نیز با ADJUSTMENT ثبت می‌شود؛ این نوع فقط تصحیح خطا نیست.

منابع: `i:\trade\MokTradeDesk\backend\app\api\finance.py:204–231,444–587`؛ `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:396–578`.

## 2. All Transaction Types

تمام ۱۱ مقدار enum فعلی در جدول زیر آمده‌اند. «CF ستون» خروجی `detect_cash_flow` است؛ «نمودار» قواعد مستقل `/charts/cashflow` است. «PnL» در این جدول معنای مالی نوع را بیان می‌کند، نه اینکه از جدول معاملات محاسبه شده باشد.

| نام / مقدار واقعی | معنی و علامت amount | مبدأ → مقصد مؤثر | اثر موجودی | CF ستون / نمودار | PnL؟ | فقط Ledger Event؟ |
|---|---|---|---|---|---|---|
| DEPOSIT / `deposit` | واریز؛ مثبت | بیرون/نامشخص → account_id | +amount | none / income | لزوماً نه؛ می‌تواند اصل سرمایه باشد | خیر |
| WITHDRAWAL / `withdrawal` | برداشت؛ مثبت | account_id → بیرون/نامشخص | −amount | expense / expense | لزوماً نه | خیر |
| PROFIT / `profit` | ثبت سود یا دریافت payout؛ مثبت | بیرون/نامشخص → account_id | +amount | income / income | برچسب سود؛ نه الزاماً سود همان معامله | خیر |
| LOSS / `loss` | ثبت زیان؛ مثبت | account_id → بیرون/نامشخص | −amount | expense / expense | زیان ثبت‌شده، نه محاسبهٔ خودکار معامله | خیر |
| FEE / `fee` | کارمزد؛ مثبت | account_id → بیرون/نامشخص | −amount | expense / expense | هزینه، نه ذاتاً trade PnL | خیر |
| PURCHASE / `purchase` | خرید، از جمله خرید پراپ؛ مثبت | account_id → بیرون/نامشخص | −amount | expense / expense | هزینه، نه سود معامله | خیر |
| TRANSFER / `transfer` | انتقال؛ مثبت | from_account_id → to_account_id | −amount / +amount | بانک→غیربانک expense؛ معکوس income؛ بقیه none / فقط غیربانک→بانک income | خیر | فقط در حالت بدون دو طرف معتبرِ ثبت‌شده |
| CONVERT / `convert` | تبدیل ارز؛ amount و to_amount مثبت | from_account_id → to_account_id با ارز متفاوت | −amount ارز مبدأ؛ +to_amount ارز مقصد | none / حذف از هر دو سری | خیر؛ سود نرخ/کارمزد خودکار ندارد | خیر |
| ADJUSTMENT / `adjustment` | اصلاح/افتتاحیه/سمت مالی گردش بروکر؛ مثبت یا منفیِ غیرصفر | account_id؛ جهت از علامت | همان amount | none / حذف از هر دو سری | خیر | خیر |
| EXTERNAL_INCOME / `external_income` | ورود از خارج؛ مثبت | خارج → account_id | +amount | income / فقط اگر حساب BANK باشد income | الزاماً نه؛ شارژ سرمایه نیز هست | خیر |
| EXTERNAL_EXPENSE / `external_expense` | خروج به خارج؛ مثبت | account_id → خارج | −amount | expense / در فهرست هزینه نیست | الزاماً نه | خیر |

**CONVERSION نام TransactionType نیست**؛ نام واقعی `CONVERT="convert"` است. `CategoryType.CONVERSION="conversion"` جداست. `EXCHANGE` نوع تراکنش فعلی نیست؛ نوع حساب `EXCHANGE` همچنان وجود دارد. `deposit_to_broker` و `withdrawal_from_broker` جهت BrokerCashMovement هستند، نه enum تراکنش.

منابع: `i:\trade\MokTradeDesk\backend\app\models\finance.py:14–72`؛ `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:64–87,130–186,197–232,300–391`؛ `i:\trade\MokTradeDesk\backend\app\services\financial_reporting.py:6–51`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:897–966,1383–1387`.

فرم تراکنش ۱۰ نوع را عرضه می‌کند؛ ADJUSTMENT در گزینه‌های آن نیست و شرط amount>0 دارد. قابلیت API و UI یکسان نیست. دریافت payout پراپ با PROFIT ثبت می‌شود و خرید پراپ در صورت وجود پرداخت‌کننده با PURCHASE. این‌ها مصرف‌کنندگان transaction هستند، نه موضوع ممیزی کامل پراپ در این بخش.

منابع: `i:\trade\MokTradeDesk\frontend\src\components\TransactionForm.tsx:34–44,99–129`؛ `i:\trade\MokTradeDesk\backend\app\services\payout_service.py:171–205`؛ `i:\trade\MokTradeDesk\backend\app\api\prop.py:1199–1224`.

## 3. Sign Convention

همهٔ انواع جز ADJUSTMENT مبلغ finite و بزرگ‌تر از صفر می‌خواهند. LOSS و WITHDRAWAL را نباید با مبلغ منفی ارسال کرد؛ علامت اثر از نوع گرفته می‌شود. ADJUSTMENT صفر را نمی‌پذیرد ولی منفی مجاز است. CONVERT هر دو مبلغ مثبت می‌خواهد و مقدار دریافتی توسط کاربر تعیین می‌شود، نه از موتور نرخ ارز.

TRANSFER دوطرفه مجموع دلتای همان ارز را صفر می‌کند و `account_id` را دوباره بستانکار نمی‌کند. جمع خام `amount`ها نه تغییر موجودی است، نه سود و نه خالص Cash Flow. مثلاً برداشت 100 با amount=100 ذخیره می‌شود ولی اثرش −100 است.

POST عمومی و تبدیل، overdraft را مجاز می‌کنند؛ این رفتار صریح سورس است و بدون قرارداد محصول، به‌تنهایی باگ اعلام نمی‌شود. ADJUSTMENT از محافظ موجودی مستثناست. BrokerCashService پیش از ثبت، موجودی سمت پرداخت‌کننده را جداگانه کنترل می‌کند. PATCH عمومی از مسیر apply_effects می‌گذرد و محافظ کف موجودی ندارد؛ حذف معمولی برای معکوس‌کردن بستانکاریِ خرج‌شده، کف موجودی را کنترل می‌کند.

منابع: `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:130–151,197–285,300–386,537–578`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:444–563`؛ `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:127–157`.

## 4. Source / Destination

- تمام FKهای `account_id/from_account_id/to_account_id` در transactions به **حساب مالی** اشاره می‌کنند؛ شناسهٔ PersonalTradingAccount در این فیلدها معنای بروکر ندارد.
- برای TRANSFER و CONVERT، `account_id=to_account_id` است؛ اثر واقعی با دو فیلد طرفین تعیین می‌شود. سایر انواع فقط account_id را تغییر می‌دهند، حتی اگر metadata طرفین روی ردیف وجود داشته باشد.
- POST انتقال با یک/هر دو طرف نامشخص، هر دو فیلد را null کرده و ردیف بدون اثر موجودی ثبت می‌کند. PATCH داشتن فقط یک طرف را رد می‌کند؛ بدون هر دو طرف همچنان ledger-only است. UI فعلی دو طرف را الزام می‌کند.
- تبدیل نیازمند دو حساب متفاوت با ارز متفاوت است؛ انتقال عادی دو حساب هم‌ارز می‌خواهد. وجود گزینهٔ داخلی `allow_cross_currency` به معنی مجازبودن آن در POST عمومی نیست.
- لیست `/transactions?account_id=...` فقط account_id را فیلتر می‌کند؛ در نتیجه انتقال خروجیِ حساب مبدأ را نشان نمی‌دهد. در مقابل ledger سرویس سه رابطه را با OR می‌خواند. پس لیست فیلترشده را نباید گردش کامل آن حساب دانست.

منابع: `i:\trade\MokTradeDesk\backend\app\models\finance.py:146–158`؛ `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:197–232,300–360,442–499,703–738`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:382–408,528–543`؛ `i:\trade\MokTradeDesk\frontend\src\components\TransactionForm.tsx:80–127`.

## 5. Internal Transfers

مبنای «دارایی کل» این جدول جمع حساب مالی و حساب شخصی بروکر در همان ارز است؛ نه فقط بانک و نه جمع عددی ارزهای متفاوت. مقدار فرضی X>0 و بدون کارمزد است.

| مسیر | ثبت واقعی | تغییر موجودی‌ها / کل | Cash Flow و امکان خطای برداشت |
|---|---|---|---|
| Bank → Broker | movement: deposit_to_broker + transaction: ADJUSTMENT(−X) | بانک −X؛ بروکر +X؛ کل صفر | ستون none و نمودار حذف؛ هزینه ثبت نمی‌شود |
| Broker → Bank | movement: withdrawal_from_broker + transaction: DEPOSIT(X) | بروکر −X؛ بانک +X؛ کل صفر | ستون none؛ **نمودار income=X حتی اگر بازگشت اصل سرمایه باشد** |
| Broker A → Broker B | مسیر مستقیم در مدل/سرویس بررسی‌شده وجود ندارد | از واسطهٔ مالی: A −X، واسطه +X سپس −X، B +X؛ کل صفر | اگر واسطه BANK باشد، برداشت A در نمودار درآمد است؛ برای واسطه غیربانکی هر دو سمت مالی ADJUSTMENT و بدون درآمد |
| Bank A → Bank B | یک TRANSFER دوطرفه | A −X؛ B +X؛ کل صفر | ستون none؛ نمودار نه درآمد نه هزینه؛ مقصد فقط یک بار بستانکار می‌شود |

دو پرش Broker→واسطه→Broker دو درخواست/رویداد جدا هستند، نه انتقال اتمیک مستقیم؛ تکمیل‌نشدن پرش دوم پول را روی واسطه باقی می‌گذارد. ادعای وجود endpoint مستقیم broker-to-broker تأیید نشد؛ مدل movement دقیقاً یک حساب شخصی و یک حساب مالی می‌پذیرد.

انتقال Bank→Exchange/Wallet در **ستون CashFlow هزینه** و معکوس آن درآمد می‌شود، با وجود ثابت‌بودن دارایی کل. نمودار هزینهٔ پرش اول را نمی‌آورد ولی درآمد پرش برگشت را می‌آورد. اگر معیار محصول «ورود به بانک» باشد بخشی از این برچسب‌گذاری عمدی است؛ اگر معیار «درآمد شخص/ورود پول خارجی» باشد، انتقال داخلی به‌اشتباه درآمد/هزینه محسوب شده است. این دو معنا نباید یکی فرض شوند.

در `/summary.assets_by_currency` فقط FinancialAccount جمع می‌شود؛ بنابراین Bank→Broker این subtotal را کم می‌کند، نه دارایی اقتصادی کل را. این تفاوت دامنه است، نه ازبین‌رفتن پول.

منابع: `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:54–87,127–164`؛ `i:\trade\MokTradeDesk\backend\app\models\trading.py:69–90`؛ `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:154–186,197–232`؛ `i:\trade\MokTradeDesk\backend\app\services\financial_reporting.py:6–29`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:619–645,897–940`.

## 6. Broker Cash Movements

دو جدول برای گردش بروکر **دو نمایش مرتبط از یک رویداد اقتصادی** هستند، نه دو ورودی درآمد مستقل:

1. `broker_cash_movements` طرف بروکر، حساب مالی مقابل، جهت، مبلغ مثبت، ارز، تاریخ و transaction_id را نگه می‌دارد.
2. `transactions` سمت حساب مالی همان رویداد را نگه می‌دارد؛ نه کل دو طرف را.
3. transaction_id در مدل movement اجباری و unique است؛ یک transaction نمی‌تواند طبق این مدل متعلق به چند movement باشد. این محدودیت جلوی ثبت مجدد همان رویداد با دو transaction جدید را نمی‌گیرد.
4. create ابتدا transaction را بدون commit مستقل ثبت می‌کند، سپس movement و تغییر current_balance را در همان Session می‌نویسد و commit نهایی دارد.
5. update اثر قبلی مالی/بروکر را جایگزین می‌کند؛ delete تراکنش را نرم‌حذف، موجودی بروکر را معکوس و movement را حذف واقعی می‌کند. این نتیجه از سورس است؛ atomicity واقعی محیط اجرا آزموده نشد.
6. برداشت بروکر به حساب غیربانکی ADJUSTMENT مثبت است، ولی به BANK، DEPOSIT مثبت؛ سمت خروج به بروکر همیشه ADJUSTMENT منفی است.

گزارش `/money-flow` transactionهای مرتبط با movement را با transaction_id کنار می‌گذارد و movement را یک بار نمایش می‌دهد؛ اینجا جلوگیری صریح از دوباره‌شماری وجود دارد. `/asset-trend` به‌جای حذف، دلتای طرف بروکر را جبران می‌کند تا دو سمت همان رویداد خنثی شوند. این جمع، جمعِ دو درآمد نیست.

منابع: `i:\trade\MokTradeDesk\backend\app\models\trading.py:69–90`؛ `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:79–87,98–271`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:517–520,578–581,1694–1759,1944–1971`.

## 7. Cash Flow Calculation

**در پروژه یک تعریف یگانه وجود ندارد.**

| خروجی | محاسبهٔ واقعی | چه چیزی نیست؟ |
|---|---|---|
| `/summary.total_income/total_expense` | SUM(amount) روی cash_flow ذخیره‌شده، حذف‌نشده و یک ارز | نه همهٔ واریزها، نه trading PnL، نه تغییر همهٔ موجودی‌ها |
| `/charts/cashflow` | درآمد: bank_income_filter؛ هزینه: WITHDRAWAL/LOSS/FEE/PURCHASE؛ ماه/سال میلادی از date | از ستون cash_flow استفاده نمی‌کند؛ EXTERNAL_EXPENSE حذف می‌شود |
| `/reports/monthly` و category-breakdown | is_bank_income و همان چهار نوع هزینه؛ با بازهٔ شمسی | معادل خلاصه نیستند |
| `/money-flow` | فهرست مسیر رویدادها، با جایگزینی transaction مرتبط با movement | صورت سود و زیان یا خالص دارایی نیست |
| `/money-cycle` | جمع نوع‌های واریز/برداشت و انواع دارای لینک، همراه موجودی مالی | مؤلفه‌های آن مستقل و قابل جمع‌کردن با هم نیستند |
| `/asset-trend` | تجمع دلتای انواع منتخب transactions با جبران سمت بروکر؛ شروع از صفر در بازه | snapshot واقعی دارایی/تغییر ارزش بازار نیست؛ CONVERT را نادیده می‌گیرد |

`bank_income_filter` نام گمراه‌کننده‌ای برای قاعدهٔ فعلی است: DEPOSIT و PROFIT را برای هر نوع حساب می‌شمارد، EXTERNAL_INCOME را فقط برای BANK و TRANSFER را فقط از غیربانک به BANK. دسته‌بندی کاربر مرجع تعیین درآمد/هزینهٔ این نمودار نیست.

**سود معامله دوباره شمرده می‌شود؟** در `/charts/cashflow` اصلاً جدول Trade جمع نمی‌شود. FinanceSyncService در سورس no-op است و همیشه صفر برمی‌گرداند. در نتیجه ثبت خودکار PnL معامله و سپس دوباره‌جمع‌کردن آن در این نمودار از مسیر بررسی‌شده وجود ندارد. ولی PROFIT دستی یا payout به Cash Flow وارد می‌شود؛ انتقال بعدی همان پول از غیربانک به بانک می‌تواند بار دوم درآمد گزارش شود. صرف related_trade_id مانع چنین ثبت یا جمعی نیست. تقویم مالی pnl معاملات و deposits/withdrawals را در فیلدهای جدا برمی‌گرداند؛ این جداسازی مجوز جمع‌زدن آن‌ها نیست.

مثال‌های فرضی، با ارز یکسان و دادهٔ جدید:

- DEPOSIT=100: موجودی +100؛ درآمد خلاصه 0؛ درآمد نمودار 100.
- EXTERNAL_EXPENSE=40: موجودی −40؛ هزینه خلاصه 40؛ هزینه نمودار 0.
- EXTERNAL_INCOME=100 به Wallet: درآمد خلاصه 100؛ نمودار 0؛ انتقال همان 100 به بانک، income دیگری در خلاصه ثبت می‌کند.
- PROFIT=100 به Wallet، سپس TRANSFER=100 به Bank: دارایی فقط 100 افزایش می‌یابد ولی درآمد هر دو گزارش 200 می‌شود.
- Bank→Broker=100 و برگشت همان 100: تغییر دارایی کل صفر؛ نمودار درآمد 100 و هزینه صفر؛ خلاصه درآمد و هزینه هر دو صفر.

منابع: `i:\trade\MokTradeDesk\backend\app\api\finance.py:607–645,897–966,1045–1169,1369–1387,1694–1759,1824–1984`؛ `i:\trade\MokTradeDesk\backend\app\services\financial_reporting.py:6–51`؛ `i:\trade\MokTradeDesk\backend\app\services\finance_sync_service.py:20–28`؛ `i:\trade\MokTradeDesk\backend\app\services\payout_service.py:190–205`.

## 8. Date / Timezone

- transactions.date و movement.date هر دو DateTime بدون timezone=True هستند؛ default زمان UTC-aware می‌سازد. از این تعریف به‌تنهایی نمی‌توان حفظ offset در DB را تضمین کرد.
- WalletService تاریخ دریافتی را همان‌طور ذخیره می‌کند؛ normalize صریح به UTC در post/convert ندارد. BrokerCashService به تاریخ naive برچسب UTC می‌زند ولی تاریخ aware را به UTC تبدیل نمی‌کند.
- فیلتر عمومی date_range تاریخ ورودی را به روز کاهش می‌دهد و بازهٔ `[روز شروع 00:00 UTC، روز بعد پایان 00:00 UTC)` می‌سازد. ساعت/offset ورودی در این مسیر حفظ نمی‌شود؛ تاریخ نامعتبر به None تبدیل و آن سمت فیلتر حذف می‌شود.
- فیلتر broker برای تاریخ پایانِ دقیقاً YYYY-MM-DD از time.max و `<=` استفاده می‌کند؛ datetime دارای offset را به UTC-naive تبدیل می‌کند. بنابراین قرارداد فیلتر broker و finance عیناً یکسان نیست.
- نمودار Cash Flow از extract سال/ماه روی مقدار ذخیره‌شده استفاده می‌کند، بدون تبدیل تهران؛ ماه میلادی DB است. گزارش شمسی بازه را از نیمه‌شب تهران به UTC تبدیل می‌کند، ولی در حلقهٔ `/reports/monthly` سال/ماه/روز خام t.date را به شمسی تبدیل می‌کند، بدون to_tehran.
- نتیجهٔ قطعی در فرض ذخیرهٔ UTC مطابق قرارداد: تراکنش 00:30 تهران در نخستین روز ماه، در UTC روز قبل است؛ گزارش شمسی آن را در ماه قبل قرار می‌دهد یا در مرز سال، با شرط jy!=target_year کنار می‌گذارد، با اینکه query آن را داخل بازه گرفته است. `_current_jalali_year` نیز از روز UTC استفاده می‌کند، نه تهران.
- asset-trend و financial-calendar برای برچسب روز از to_tehran استفاده می‌کنند؛ اما فیلتر بازهٔ asset-trend همچنان روز UTC است. ساعات 00:00 تا 03:30 تهرانِ روز اول برای بازهٔ UTC همان روز بیرون می‌افتند.
- UI تاریخ را از PersianDateInput می‌گیرد و بدون افزودن timezone ارسال می‌کند؛ ورودی تاریخ، هنگام نمایش از `new Date(value)` و getterهای محلی مرورگر استفاده می‌کند. خطر اختلاف روز در timezoneهای دیگر وجود دارد؛ رفتار دقیق مرورگر/نسخهٔ Pydantic اجرا نشد.

منابع: `i:\trade\MokTradeDesk\backend\app\models\finance.py:152,167`؛ `i:\trade\MokTradeDesk\backend\app\models\trading.py:84–86`؛ `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:374–380,501–507`؛ `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:27–33`؛ `i:\trade\MokTradeDesk\backend\app\utils\date_range.py:11–51`؛ `i:\trade\MokTradeDesk\backend\app\utils\time_utils.py:46–66`؛ `i:\trade\MokTradeDesk\backend\app\api\broker.py:24–31,85–88`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:914–939,1024–1087,1390–1399,1944–1950`؛ `i:\trade\MokTradeDesk\frontend\src\components\TransactionForm.tsx:108–129`؛ `i:\trade\MokTradeDesk\frontend\src\components\PersianDateInput.tsx:22–29,52–54`.

## 9. Double Counting

### مواردی که دو بار اعمال نمی‌شوند

- TRANSFER صحیح یک ردیف با دو delta است؛ account_id مقصد دوباره اعمال نمی‌شود.
- BrokerCashMovement و transaction مرتبط، دو سمت یک رویدادند؛ money-flow یکی را جایگزین دیگری می‌کند و asset-trend دو سمت را خنثی می‌کند.
- نمودار Cash Flow، PnL جدول Trade را به transactions اضافه نمی‌کند.

### موارد خطر واقعی

- **دوباره‌شماری درآمد در مسیر پول:** PROFIT در Wallet سپس انتقال به Bank، درآمد دو بار؛ EXTERNAL_INCOME غیربانکی سپس انتقال به بانک نیز در summary دو بار.
- **اشتباه‌گرفتن بازگشت سرمایه با درآمد:** Broker→Bank با DEPOSIT به نمودار income وارد می‌شود. انتقال مکرر رفت‌وبرگشت می‌تواند درآمد نمودار را بدون سود اقتصادی زیاد کند.
- **ثبت دوبارهٔ ورودی:** درخواست create دوباره یا DEPOSIT دستی علاوه بر movement، transaction جدا می‌سازد؛ شناسهٔ رویداد خارجی/idempotency key در مدل/مسیرهای بررسی‌شده نیست. unique بودن movement.transaction_id این حالت را پوشش نمی‌دهد.
- **جمع‌کردن آمارهای هم‌پوشان:** در money-cycle، total_exchanges جمع TRANSFER است و total_transfers جمع هر ردیف دارای هر دو لینک؛ انتقال عادی در هر دو قرار می‌گیرد. این‌ها را نباید جمع کرد؛ نام total_exchanges اکنون به معنی CONVERT نیست.
- **جمع‌زدن transaction.amount و movement.amount:** مبلغ سمت مالی و نمایش کامل رویداد قابل جمع به عنوان دو درآمد مستقل نیستند.
- **PnL دستی + payout:** اگر کاربر سود تحقق‌نیافته/سود معامله را به‌صورت PROFIT روی حساب مالی ثبت و دریافت بعدی را هم ثبت کند، دارایی/درآمد می‌تواند تکراری شود؛ وقوع واقعی چنین داده‌ای NOT VERIFIED است.

منابع: `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:197–232,501–535`؛ `i:\trade\MokTradeDesk\backend\app\models\finance.py:145–167`؛ `i:\trade\MokTradeDesk\backend\app\models\trading.py:77–80`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:1694–1759,1834–1863,1959–1971`؛ قواعد درآمد در بخش ۷.

## 10. Confirmed Bugs

موارد زیر نقص قابل اثبات از مسیر سورس‌اند؛ هیچ تست یا درخواست واقعی برای بازتولید اجرا نشده است. اختلاف معنای «ورود به بانک» و «درآمد اقتصادی» جدا از نقص محاسباتی ذکر شده است.

### B1 — اختلاف موتور گزارش Cash Flow (High)

summary از cash_flow استفاده می‌کند ولی نمودار/گزارش ماهانه از قواعد دیگر. DEPOSIT، EXTERNAL_EXPENSE، EXTERNAL_INCOME غیربانکی و Bank→غیربانک خروجی‌های ناسازگار دارند. با EXTERNAL_EXPENSE=40، هزینه summary=40 و نمودار=0 است؛ این اختلاف از نوع و فیلترها مستقیم به دست می‌آید، نه از timezone یا دادهٔ قدیمی.

شاهد: `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:154–186`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:629–630,924–937,1369–1387`؛ `i:\trade\MokTradeDesk\backend\app\services\financial_reporting.py:13–29`.

### B2 — گروه‌بندی ناسازگار با مرز تهران در گزارش ماهانهٔ شمسی (Medium)

فیلتر تهران→UTC است ولی bucket از روز خام UTC ساخته می‌شود؛ رویداد ساعات ابتدای ماه به ماه قبل می‌رود و ابتدای سال می‌تواند حذف شود. تعیین سال پیش‌فرض نیز بر مبنای UTC است. پیش‌شرط مثال: تاریخ‌ها طبق قرارداد پروژه UTC باشند؛ نحوهٔ واقعی ذخیره در محیط اجرا بررسی نشد.

شاهد: `i:\trade\MokTradeDesk\backend\app\api\finance.py:1024–1042,1055–1087`.

### B3 — ویرایش برداشت بدون اعتبارسنجی ارز حساب (High)

PUT/PATCH `/withdrawals/{id}` فقط وجود account_id جدید و اعتبار مبلغ را بررسی می‌کند؛ `validate_accounts` ندارد. می‌توان در سورس مسیر، حساب یک برداشت USDT را به حساب IRR تغییر داد و همان عدد amount را از موجودی IRR کم کرد، در حالی که currency ردیف هنوز USDT است. POST و PATCH عمومی transaction کنترل تطابق ارز دارند، اما این مسیر جایگزین ندارد.

شاهد: `i:\trade\MokTradeDesk\backend\app\api\finance.py:852–880` در مقایسه با `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:344–360,489–499` و `i:\trade\MokTradeDesk\backend\app\api\finance.py:553`.

### B4 — حذف اثر تبدیل از روند تفکیک‌شدهٔ ارزها (Medium)

CONVERT موجودی مبدأ را کم و موجودی ارز مقصد را زیاد می‌کند، ولی asset-trend چون نوع را در sign ندارد، هر دو اثر را صفر فرض می‌کند. مثال تبدیل 100 USDT به 6,000,000 IRR: تغییر مورد انتظار سبدها −100 و +6,000,000 است، ولی نمودار هیچ‌کدام را ثبت نمی‌کند. حتی اگر ارزش اقتصادی کل ثابت باشد، صفرگرفتن هر دو سریِ تفکیک ارز صحیح نیست.

شاهد: `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:214–216,362–386`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:1929–1957`.

### رفتارهای اثبات‌شده با ابهام قرارداد محصول

- درآمد چندبارهٔ PROFIT→Wallet→Bank و درآمد شمردن بازگشت سرمایهٔ بروکر، از قواعد ثابت می‌شود؛ برای معیار «درآمد اقتصادی شخص» نادرست است، ولی کامنت‌های بخشی از سورس عمداً «ورود به بانک» را می‌خواهند. این گزارش آن را به‌عنوان خطر معنایی مهم ثبت می‌کند، نه ادعای قرارداد محصول تأییدشده.
- غیبت انتقال خروجی در فیلتر account_id نقص نسبت به انتظار «گردش کامل حساب» است؛ endpoint واقعاً فقط حساب اصلی ردیف را فیلتر می‌کند. ledger سرویس رفتار متفاوت دارد.
- overdraft مسیر دستی، ledger-only transfer و صفر شروع‌شدن روند در بازه، رفتارهای صریح‌اند؛ بدون قرارداد مکمل به‌تنهایی باگ قطعی نام‌گذاری نمی‌شوند.

## 11. NOT VERIFIED

- schema واقعی دیتابیس، اجرای migrationها، backfill ستون cash_flow، داده‌های legacy و سلامت FK/uniqueها بررسی نشدند.
- تعداد/مبلغ واقعی ردیف‌های تکراری، نامتوازن یا طبقه‌بندی‌شده با قواعد قدیمی مشخص نیست.
- هیچ برنامه، تست، migration، API یا DB query اجرا نشد؛ بازتولید runtime تمام مثال‌ها انجام نشده است.
- حفظ/حذف offset توسط driver، timezone دیتابیس/سیستم/مرورگر و پذیرش date-only توسط نسخهٔ نصب‌شده بررسی اجرایی نشدند.
- رقابت درخواست‌های هم‌زمان، isolation، lost update، rollback روی خطای واقعی و idempotency لایه‌های خارج از مسیرهای خوانده‌شده آزمایش نشدند.
- جست‌وجوی سازنده‌های FinancialTransaction و WalletService.post/convert در `i:\trade\MokTradeDesk\backend\app` انجام شد؛ این جست‌وجو تضمین نبودن raw SQL، اسکریپت خارجی یا نویسندهٔ خارج از برنامه نیست.
- مسیر مستقیم Broker A→Broker B در مدل و APIهای بررسی‌شده یافت نشد؛ کاربر می‌تواند دو پرش از حساب مالی انجام دهد، اما چنین سناریویی اجرا نشده است.
- این گزارش ممیزی کامل معاملات/پراپ نیست؛ فقط رابطهٔ آن‌ها با transactions و جریان پول بررسی شد. هیچ نتیجهٔ بخش‌های قبلی بدون خواندن مجدد سورس به‌عنوان شاهد استفاده نشد.

## 12. Risk Level

**Overall: High — عمدتاً صحت گزارش مالی و تفسیر درآمد؛ نه اثبات ازبین‌رفتن واقعی وجه.**

- High: تعاریف متناقض Cash Flow، درآمدشمردن برخی انتقال‌های داخلی و دوباره‌شماری درآمد در چند پرش؛ مسیر ویرایش برداشت با امکان ناسازگاری ارز.
- Medium: مرز روز/ماه/سال، حذف تبدیل از روند سبدهای ارزی، هم‌پوشانی شاخص‌های money-cycle و گزارش ناقص حساب مبدأ.
- کنترل‌های مثبت: delta دوطرفهٔ انتقال بدون بستانکاری تکراری؛ پیوند یکتای movement→transaction در مدل؛ جلوگیری از ویرایش/حذف مستقیم تراکنش وابسته؛ dedup نمایش money-flow؛ جبران سمت بروکر در asset-trend؛ جداسازی PnL معاملات از نمودار Cash Flow.

نتیجه: Cash Flow فعلی را نمی‌توان معادل Trading PnL، تغییر دارایی کل یا صورت جامع ورود/خروج خارجی دانست. هر خروجی باید با تعریف خودش خوانده شود. هیچ Fix، تغییر کد/تست، عملیات دیتابیس، commit یا push در این ممیزی انجام نشد.