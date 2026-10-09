# FINAL FINANCE AUDIT

ممیزی نهایی مالی — ۲۰۲۶-۱۰-۰۸. روش: بررسی ایستای منبع فعلی و تطبیق ادعاهای پنج گزارش قبلی. «تأییدشده» در این سند یعنی قابل استنتاج از کد، نه آزموده‌شده در محیط اجرا. هیچ برنامه، تست، migration یا عملیات دیتابیس اجرا نشده است. این سند پیشنهاد پیاده‌سازی یا طراحی UI نیست.

## 1. Executive Summary

**آیا Finance Backend قبل از هر بازطراحی UI نیازمند اصلاح است؟ بله.** قرارداد موجودی، کنترل ارز، تعریف درآمد/هزینه، جداسازی سود شخصی از پراپ و معنای روند دارایی باید پیش از اتکا به UI جدید تصحیح و تأیید شوند. تغییر ظاهر این اختلاف‌ها را حل نمی‌کند.

**آیا Personal Total Wealth بدون دوباره‌شماری قابل محاسبه است؟** برای «مجموع موجودی ثبت‌شدهٔ حساب‌های شخصی» و برای هر ارز جداگانه، بله:

`RecordedPersonalAssets[c] = Σ FinancialAccount.balance[c] + Σ PersonalTradingAccount.current_balance[c]`

این همان مبنای `spendable-assets.total` است؛ initial، PnL، گردش بروکر و payout دریافتی نباید دوباره به آن اضافه شوند. اما پاسخ برای «ثروت واقعی، کامل، به‌روز و تطبیق‌شدهٔ امروز» **NOT VERIFIED** است: موجودی بروکر با ثبت معاملات تازه نمی‌شود، صحت داده‌ها بررسی نشده و این مجموع ارزش‌گذاری پوزیشن‌های باز، بدهی‌ها و دارایی‌های خارج از سیستم نیست. جمع IRR و USDT بدون FX معتبر نیز ثروت واحد تولید نمی‌کند.

نتیجهٔ درست: هستهٔ جمع دارایی الزاماً دوباره‌شمار نیست؛ چند خروجیِ دارای عنوان مشابه، دامنه و مبنای ناسازگار دارند. نه ادعای «همه‌چیز صحیح است» پذیرفتنی است، نه ادعای «همهٔ جمع‌ها دو بار حساب می‌شوند».

### تطبیق گزارش‌های قبلی با منبع فعلی

| گزارش قبلی با مسیر مطلق | حکم نهایی دربارهٔ ادعاهای اصلی |
|---|---|
| `i:\trade\MokTradeDesk\FINANCE_AUDIT_PART1_STRUCTURE.md` | تفکیک حساب مالی/معاملاتی و فرمول‌های متفاوت تأیید شد. نام‌های total و spendable دلیل بر ثروت شخصی نیستند. کامنت‌ها در برابر بدنهٔ اجرا مرجع نهایی نیستند. |
| `i:\trade\MokTradeDesk\FINANCE_AUDIT_PART2_BROKER_ACCOUNTS.md` | عدم به‌روزرسانی current با Trade و امکان overwrite مستقیم تأیید شد. شدت «باگ موجودی» مشروط به قرارداد است: موجودی دستی ذاتاً غلط نیست؛ ادعای تازه‌شدن خودکار از معاملات غلط است. |
| `i:\trade\MokTradeDesk\FINANCE_AUDIT_PART3_TRANSACTIONS.md` | خنثی‌بودن انتقال در دارایی و ناسازگاری تعریف Cash Flow تأیید شد. ادعای عمومی اعتبارسنجی ویرایش نباید به مسیر اختصاصی withdrawals تعمیم یابد؛ آن مسیر validate_accounts ندارد. |
| `i:\trade\MokTradeDesk\FINANCE_AUDIT_PART4_PNL_NET_PROFIT.md` | Real PnL بسته، هزینهٔ علامت‌دار، اختلاف هزینه‌ها و مشکل helper پراپ تأیید شد. closed-only بودن تمام مسیرهای پراپ رد می‌شود؛ دریافت پراپ برای همهٔ مقصدها PROFIT است، نه فقط بانک. |
| `i:\trade\MokTradeDesk\FINANCE_AUDIT_PART5_PERSONAL_ASSETS.md` | فرمول موجودی شخصی، خروج پراپ دریافت‌نشده از total و ایراد جمع ارز UI تأیید شد. خواندن گزارش به‌تنهایی اثبات صحت یافته‌ها نیست. ادعای تاریخی Git انتهای گزارش از وضعیت فعلی قابل اثبات نیست. |

این جدول تأیید فراگیر تک‌تک ادعاهای فرعی گزارش‌های پیشین نیست. فقط یافته‌های دارای شاهد مستقیم این سند مبنای حکم نهایی‌اند؛ ادعاهای تاریخیِ اجرا، migration، Git و داده مستقل از منبع فعلی همچنان تأییدنشده‌اند.

## 2. Finance Architecture

سه دامنه وجود دارد: دفتر مالی (`accounts` و `transactions`)، معاملات شخصی (`personal_trading_accounts` و `trades`) و پراپ (`prop_accounts`، `prop_stages` و برداشت‌ها). حساب مالی با حساب بروکر حتی در صورت برابر بودن id یک موجودیت نیست.

- `WalletService` دلتای تراکنش را روی balance مالی اعمال می‌کند؛ Trade به‌خودی‌خود تراکنش مالی نیست.
- `BrokerCashService` یک movement و سند سمت مالی را به هم متصل می‌کند و current بروکر را تغییر می‌دهد.
- `PayoutService` دریافت پراپ را در حساب مالی ثبت می‌کند؛ مبلغ واردشده از همان balance در دارایی شخصی دیده می‌شود.
- Finance API و Analytics چند تعریف مستقل aggregate دارند؛ اشتراک نام به معنی اشتراک فرمول نیست.

شواهد: `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:197–260`؛ `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:125–164`؛ `i:\trade\MokTradeDesk\backend\app\services\payout_service.py:130–205`؛ `i:\trade\MokTradeDesk\backend\app\services\finance_sync_service.py:20–28`.

## 3. Personal Broker Accounts

موجودی جاری ذخیره‌شده است، نه جمع زندهٔ معاملات. ساخت حساب current ورودی یا initial را می‌گذارد؛ PATCH فیلدهای ارسالی را مستقیم overwrite می‌کند. نویسندگان صریح runtime در جست‌وجوی منبع برنامه، ساخت حساب و create/update/delete گردش بروکر بودند؛ PATCH با setattr نیز نویسندهٔ غیرمستقیم است. این جست‌وجو اثبات نبود trigger یا نویسندهٔ خارج از برنامه نیست.

`BrokerPnL_from_balance[c] = Σcurrent − Σinitial + Σwithdrawals − Σdeposits`

این فرمول Trade PnL نیست. معاملهٔ سودده، زیان‌ده، ویرایش، حذف یا import در مسیرهای بررسی‌شده current شخصی را تازه نمی‌کند. FinanceSyncService نیز no-op است. بنابراین عبارت «current خودش شامل سود است» در مستندات finance_metrics یک پیش‌فرض مصرف‌کننده است، نه تضمین نویسندگان موجودی.

تغییر ارز فقط با وجود movement منع می‌شود؛ حساب دارای معامله یا موجودی ولی فاقد movement می‌تواند بدون تبدیل عدد relabel شود. حذف حساب بدون معامله/movement نیز مانع موجودی غیرصفر ندارد. غیرفعال‌سازی با آرشیو مالی فرق دارد و aggregate بروکر active filter ندارد.

شواهد: `i:\trade\MokTradeDesk\backend\app\api\trading.py:177–251`؛ `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:5–52`؛ `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:157,233–266`؛ `i:\trade\MokTradeDesk\backend\app\api\trades.py:765–801`؛ `i:\trade\MokTradeDesk\backend\app\services\import_engine.py:999–1019`؛ `i:\trade\MokTradeDesk\backend\app\services\finance_sync_service.py:26–28`.

## 4. Financial Accounts

Financial Balance جمع balance ذخیره‌شدهٔ حساب‌های مالی است؛ summary فقط این دامنه را می‌گیرد و بروکر شخصی در آن نیست. spendable-assets شش نوع BANK، CASH، CARD، EXCHANGE، CRYPTO_WALLET و TRUST_WALLET را به تفکیک ارز جمع می‌کند. کارت و بانک اگر دو نمای یک پول واقعی باشند، ثبت هم‌زمان موجودی در هر دو، ریسک دادهٔ تکراری دارد؛ وقوع آن اثبات نشده است.

WalletService تغییر حساب را از deltas اعمال می‌کند. reconcile مالی stored را با دفتر مقایسه می‌کند، نه با صورت‌حساب بانک واقعی و نه با بروکر. summary و spendable فیلتر archive ندارند. مسیر عادی آرشیو حساب غیرصفر یا دارای تراکنش را رد می‌کند؛ پس نبود فیلتر به‌تنهایی اثبات بیش‌نمایی فعلی نیست.

شواهد: `i:\trade\MokTradeDesk\backend\app\api\finance.py:287–316,590–645,1497–1528`؛ `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:235–260`.

## 5. Transactions

| رخداد | اثر موجودی و حکم |
|---|---|
| درآمد/واریز مثبت و هزینه/برداشت | افزایش/کاهش حساب مالی مطابق نوع؛ لزوماً سود/هزینهٔ اقتصادی نیست |
| ADJUSTMENT | اثر amount علامت‌دار؛ خودِ اصلاح موجودی درآمد نیست |
| TRANSFER دوطرفه | مبدأ −x، مقصد +x؛ account_id بار سوم اعمال نمی‌شود |
| TRANSFER بدون طرف‌های کامل در قرارداد legacy | دلتای خالی؛ مدرک انتقال مؤثر موجودی نیست |
| CONVERT | مبدأ −amount، مقصد +to_amount در ارز متفاوت |
| بانک→بروکر | مالی −x با ADJUSTMENT، بروکر +x؛ ثروت همان ارز ثابت |
| بروکر→بانک | بروکر −x، مالی +x با DEPOSIT؛ ثروت ثابت ولی نمودار آن را income می‌شمارد |

PATCH عمومی تراکنش اعتبارسنجی حساب/ارز دارد و تراکنش مرتبط با movement یا payout را برای ویرایش/حذف عمومی رد می‌کند. **مسیر اختصاصی PUT/PATCH withdrawals همان محافظ ارز را ندارد:** اثر قبلی را برمی‌گرداند، فیلدهای ورودی را می‌گذارد، فقط مبلغ را اعتبارسنجی می‌کند و اثر جدید را اعمال می‌کند. apply_effects هم تطابق ارز را کنترل نمی‌کند. این یافته مربوط به برداشت مالی است، نه اثبات نقص یکسان در دریافت پراپ.

شواهد: `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:197–260,300–360`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:499–587,823–880`؛ `i:\trade\MokTradeDesk\backend\app\services\broker_cash_service.py:54–87,125–164`.

## 6. Trading PnL

`net_pnl = coalesce(pnl,0) + coalesce(commission,0) + coalesce(swap,0)`

commission و swap با علامت ذخیره‌شده جمع می‌شوند؛ مثبت بودن خودکار به هزینهٔ منفی تبدیل نمی‌شود. pnl=100، commission=−7، swap=−3 نتیجهٔ 90 می‌دهد. pnl=NULL با همان هزینه‌ها نتیجهٔ −10 می‌دهد، نه صفر و نه حذف معامله.

`_compute_real_pnl` معاملات شخصی و FUNDED_REAL را با close_time غیرNULL و ارز حساب مرتبط جمع می‌کند. مدل Trade طبقه‌بندی شخصی/پراپ را جدا می‌کند؛ اجرای constraint در DB واقعی بررسی نشده است. helper خالص به‌خودی‌خود شرط بسته‌بودن ندارد؛ caller مسئول آن است. `_stage_net_pnl` و sync سود مرحله این شرط را ندارند.

ارز Trade از حساب مرتبط می‌آید؛ relabel حساب می‌تواند طبقه‌بندی ارزی تاریخچه را تغییر دهد. قرارداد فایل import دربارهٔ gross یا net بودن pnl و علامت هزینه‌ها تأیید نشده؛ اگر pnl از قبل net باشد، جمع هزینهٔ جدا می‌تواند هزینه را دوباره اعمال کند.

شواهد: `i:\trade\MokTradeDesk\backend\app\services\metrics.py:22–33`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:1435–1468`؛ `i:\trade\MokTradeDesk\backend\app\models\strategy.py:182–193`؛ `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:56–106`؛ `i:\trade\MokTradeDesk\backend\app\services\import_engine.py:810–829`.

## 7. Expenses

تعریف واحدی وجود ندارد:

- `/net-profit`: FEE و PURCHASE حذف‌نشده در همان ارز، بدون تخصیص هزینه به بروکر شخصی و بدون پارامتر بازهٔ زمانی.
- `/expenses`: همان دو نوع به‌علاوهٔ EXTERNAL_EXPENSE.
- cash_flow ذخیره‌شده: علاوه بر هزینه‌ها، WITHDRAWAL، LOSS و انتقال بانک→غیربانک را expense می‌نامد.
- هزینهٔ commission/swap قبلاً در net معامله اعمال شده است؛ FEE مالی بابت همان رخداد می‌تواند کسر دوباره باشد. وقوع دادهٔ تکراری NOT VERIFIED است.

PropCost با payer می‌تواند PURCHASE مالی ایجاد کند؛ صرف رکورد هزینهٔ پراپ به معنی خروج قطعی پول از حساب شخصی نیست. این هزینه‌ها نباید بی‌توضیح «هزینهٔ معاملات شخصی» تلقی شوند.

شواهد: `i:\trade\MokTradeDesk\backend\app\api\finance.py:1472–1484,1663–1688,1770–1781`؛ `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:154–186`؛ `i:\trade\MokTradeDesk\backend\app\api\prop.py:1190–1226`.

## 8. Prop Separation

سرمایهٔ پراپ دارایی شخصی کاربر نیست. funded PnL کامل، سهم کاربر، مبلغ قابل برداشت و payout دریافتی چهار مفهوم متفاوت‌اند. net-profit کنونی سود بستهٔ شخصی و **۱۰۰٪** سود بستهٔ funded را جمع و هزینه‌های مشترک را کم می‌کند؛ پس Personal Broker Net Profit نیست.

RuleEngine قابل برداشت را از `max(closed_pnl × share − total_withdrawn, 0)` می‌سازد. finance_metrics.prop_stage_3 همهٔ معاملات مرحله، حتی باز، را می‌خواند و ارز را تفکیک نمی‌کند؛ API نتیجه را USDT نام می‌گذارد. sync مرحله نیز همهٔ Tradeها را جمع می‌کند و برای share صفر از `or 80` استفاده می‌کند؛ برخلاف RuleEngine که فقط None را پیش‌فرض می‌داند.

دریافت RECEIVED با PROFIT به حساب مالی مقصد وارد می‌شود و total_withdrawn افزایش می‌یابد. بدنهٔ اجرا برای همهٔ مقصدها PROFIT است؛ docstring «فقط بانک درآمد است» نادرست است. وجود transaction_id و تکرار وضعیت جاری محافظ تکرار همان برداشت است، نه اثبات ایمنی درخواست‌های همزمان یا برداشت‌های جداگانهٔ تکراری.

شواهد: `i:\trade\MokTradeDesk\backend\app\services\payout_service.py:130–205`؛ `i:\trade\MokTradeDesk\backend\app\services\prop_rule_engine.py:116–121,225–233`؛ `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:80–106`؛ `i:\trade\MokTradeDesk\backend\app\services\import_engine.py:818–829`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:1521–1528,1663–1688`.

## 9. Personal Assets

در spendable-assets، حساب‌های مالی و بروکر جدا SUM می‌شوند؛ join معاملات که موجودی حساب را به تعداد Trade تکثیر کند وجود ندارد. هر ردیف حساب یک بار در ارز خودش شمرده می‌شود. payout دریافتی در balance مقصد است؛ prop_stage_3 خارج از total قرار دارد. نبود active/archive filter باید با سیاست مالکیت تفسیر شود، نه اینکه خودکار حساب غیرفعال بی‌ارزش فرض شود.

Frontend یک قرارداد یگانه ندارد: کارت «مجموع دارایی‌ها» FinancePage مقادیر summary.assets_by_currency را بدون FX جمع می‌کند. کارت «موجودی کل» DashboardPage ارز منتخب summary را می‌گیرد؛ ارزها را جمع نمی‌کند، اما بروکر را هم ندارد. این دومی کمبود دامنه/عنوان است، نه دوباره‌شماری بروکر.

شواهد: `i:\trade\MokTradeDesk\backend\app\api\finance.py:619–624,1505–1535`؛ `i:\trade\MokTradeDesk\frontend\src\pages\FinancePage.tsx:793–799`؛ `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:775–785`.

## 10. Total Wealth

سه عدد قابل جایگزینی با هم نیستند:

1. summary: فقط موجودی مالی.
2. spendable-assets.total: موجودی مالی + current بروکر، به تفکیک ارز؛ نزدیک‌ترین نمای موجود برای دارایی شخصی ثبت‌شده.
3. analytics.spendable_money.total_balance: broker_balance + funded_pnl؛ فاقد حساب‌های مالی و شامل سود پراپ دریافت‌نشدهٔ کامل. ثروت شخصی یا پول قابل خرج نیست.

افزودن Trade PnL به current بدون دانستن مبنای snapshot امن نیست: اگر current تازه و شامل سود باشد، دوباره‌شماری می‌شود؛ اگر قدیمی باشد، افزودن همهٔ تاریخچه ممکن است سود دورهٔ قبل را دوباره وارد کند. هیچ عدد نهایی واقعی بدون تطبیق داده در این ممیزی اعلام نمی‌شود.

شواهد: `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:23–77`؛ `i:\trade\MokTradeDesk\backend\app\api\analytics.py:564–570`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:619–624,1505–1528`.

## 11. Reconciliation Matrix

در این جدول c یک ارز و N خالص معامله طبق بخش ۶ است. ارجاعات هر ردیف در بخش توضیح همان متریک آمده‌اند.

| Metric | Source | Formula | Includes | Excludes | Currency | Closed Only? | Double Count Risk |
|---|---|---|---|---|---|---|---|
| Broker Balance | PTA.current؛ بخش ۳ | Σcurrent | حساب‌های شخصی حتی غیرفعال | initial/PnL به‌عنوان جمع مستقل | c | موضوعیت ندارد؛ snapshot | افزودن PnL یا ثبت حساب تکراری |
| Financial Balance | accounts.balance؛ بخش ۴ | Σbalance | شش نوع حساب مالی؛ archived نیز در aggregate | PTA و سرمایهٔ پراپ | c | موضوعیت ندارد | بانک/کارت موازی، سند تکراری |
| Personal Assets | spendable-assets؛ بخش ۹ | Financial + Broker | payout در balance مقصد | پراپ دریافت‌نشده، initial مستقل | USDT/IRR جدا | از balance، نه Trade | فرمول مستقیم تکرار ندارد؛ داده مشروط |
| Trading PnL | real-pnl؛ بخش ۶ | ΣN شخصی + ΣN funded | commission/swap علامت‌دار | معاملات باز، مراحل ۱/۲ | ارز حساب | بله | فایل net به‌علاوهٔ هزینهٔ مجدد |
| Expenses | expenses؛ بخش ۷ | ΣFEE/PURCHASE/EXTERNAL_EXPENSE | اسناد حذف‌نشده | هزینهٔ صرفاً داخل Trade | c | موضوعیت ندارد | تکرار هزینهٔ Trade در سند |
| Net Profit | net-profit؛ بخش ۷/۸ | Real PnL − FEE − PURCHASE | شخصی و funded کامل | EXTERNAL_EXPENSE؛ payout به‌عنوان جمع مجزا | c | جزء Trade بله | fee تکراری؛ اختلاط دامنه نیز مستقل از تکرار |
| Cash Flow | summary / charts؛ بخش ۵/۷ | ستون cash_flow / bank_income_filter و انواع هزینه | قواعد متفاوت ورود/خروج | هم‌ارز تغییر دارایی نیست | c | موضوعیت ندارد | برگشت سرمایه و انتقال داخلی درآمد می‌شوند |
| Asset Trend | asset-trend؛ بخش ۱۲/۱۵ | تجمع signed tx + broker delta از صفر | سند مالی و جبران گردش بروکر | current/initial بروکر، Trade PnL، CONVERT، ماندهٔ قبل بازه | دو سری جدا | Trade نمی‌خواند | انتقال بروکر خنثی؛ نمودار ناقص است نه snapshot |
| Prop Payout | PayoutService؛ بخش ۸ | RECEIVED → PROFIT → balance | دریافت ثبت‌شده و total_withdrawn | requested و سود دریافت‌نشده در دارایی شخصی | ارز برداشت/مقصد | receipt-based | جمع مجدد payout با balance یا درآمد انتقال بعدی |
| Total Wealth | قرارداد بخش ۱۰/۱۸ | دارایی ثبت‌شده[c]؛ ثروت کامل نامعلوم | فقط مالکیت شخصی تأییدشده | سرمایهٔ پراپ؛ سود تکراری | بدون FX مجموع واحد ندارد | وابسته به مبنای ارزش‌گذاری | افزودن balance + PnL + payout ممنوع |

## 12. Scenario Reconciliation

اعداد زیر مثال تحلیلی کد هستند، نه اجرای تست یا دادهٔ واقعی. هر ردیف مستقل، حساب‌ها هم‌ارز و commit موفق فرض شده‌اند؛ جز سناریوی چندارزی. F موجودی مالی، B موجودی بروکر و W=F+B است. «انتظار» قرارداد دارایی شخصی است.

| # | Scenario | انتظار / رفتار فعلی | حکم |
|---|---|---|---|
| 1 | bank only | F=100، B=0؛ spendable=100 و summary=100 | صحیح در دامنهٔ ثبت‌شده |
| 2 | broker only | F=0، B=100؛ spendable=100 ولی summary=0 | جمع صحیح؛ عنوان summary معادل ثروت نیست |
| 3 | bank + broker | F=100، B=200؛ spendable=300؛ analytics لزوماً 300 نیست | صحیح در spendable |
| 4 | bank→broker | انتقال 20 از F=100/B=200 → 80/220؛ W=300 | صحیح؛ هزینهٔ اقتصادی نیست |
| 5 | broker→bank | انتقال 20 → 120/180؛ W=300؛ chart income=20 | دارایی صحیح؛ درآمد اقتصادی نادرست |
| 6 | trading profit | Trade بسته +50؛ PnL +50 ولی B و W ثابت | به‌روز بودن ثروت از Trade تضمین نمی‌شود |
| 7 | trading loss | Trade بسته −30؛ PnL −30 ولی B و W ثابت | همان شکاف؛ زیان در موجودی منعکس نمی‌شود |
| 8 | commission + swap | pnl=100، commission=−7، swap=−3 → N=90؛ B ثابت؛ FEE اضافی همان هزینه تکرار است | helper صحیح؛ تطبیق هزینه مشروط |
| 9 | broker A→B | دو گردش از واسطهٔ مالی: A−20، واسطه+20 سپس−20، B+20؛ W ثابت | دو درخواست، نه انتقال اتمیک مستقیم؛ واسطهٔ بانک income می‌سازد |
| 10 | multiple currencies | 100 USDT و 100000 IRR دو مجموع‌اند؛ کارت Finance عدد 100100 می‌دهد | backend تفکیک صحیح؛ جمع UI نادرست |
| 11 | multiple brokers | B1=100 و B2=200 هم‌ارز → 300، مستقل از تعداد Trade | صحیح؛ هویت تکراری حساب واقعی NOT VERIFIED |
| 12 | archived account | archived مالی در aggregate هست؛ مسیر عادی فقط صفر/بدون تراکنش را آرشیو می‌کند؛ PTA inactive هم باقی است | عدد غیرصفر تاریخی و سیاست مالکیت NOT VERIFIED |
| 13 | prop profit | funded بسته 100، share=80٪، بدون دریافت؛ personal assets ثابت؛ net-profit جزء پراپ=100 | جداسازی دارایی صحیح؛ سود شخصی خواندن 100 غلط |
| 14 | prop payout | RECEIVED=80 → F+80؛ total_withdrawn+80؛ personal assets+80 فقط از balance | صحیح؛ افزودن دوبارهٔ payout غلط |
| 15 | expense | EXTERNAL_EXPENSE=30 → F−30 و expenses+30؛ net-profit هزینهٔ آن را نمی‌گیرد | ناسازگاری تعریف هزینه قطعی |
| 16 | open trade with stored PnL | pnl=100 و هزینه=−10؛ Real PnL=0؛ helper پراپ با share=80٪ و بدون برداشت 72 می‌دهد | Real صحیح؛ قابل برداشت پراپ نادرست |
| 17 | closed trade with null PnL but charges | pnl=NULL، commission=−7، swap=−3 → Real N=−10؛ B ثابت | هزینه از Real حذف نمی‌شود؛ پوشش balance تضمین نشده |
| 18 | internal transfer | بانک A→B یا Wallet→Bank، −20/+20 و W ثابت؛ Wallet→Bank income می‌شود | موجودی صحیح؛ تفسیر درآمد اقتصادی غلط |

منابع سناریوها: شواهد بخش‌های ۳ تا ۱۰. Asset Trend نیز با سناریوها تطبیق کامل ندارد: جابه‌جایی بروکر را خنثی می‌کند، ولی موجودی اولیهٔ مستقل بروکر و تغییر آن با Trade را نمی‌خواند؛ CONVERT را حذف می‌کند و با date_from ماندهٔ قبل از بازه را حمل نمی‌کند. پس انتهای نمودار الزاماً مساوی W نیست. شاهد: `i:\trade\MokTradeDesk\backend\app\api\finance.py:1923–1984`.

## 13. Double Counting Risks

**کنترل‌های صحیح:** جمع مستقیم موجودی‌ها بدون افزودن initial/PnL؛ دو دلتای TRANSFER بدون اعمال مجدد account_id؛ خنثی‌سازی گردش بروکر در دارایی؛ payout دریافتی فقط در balance مقصد؛ عدم ایجاد سند خودکار از FinanceSyncService.

**ریسک‌های مشروط به داده یا مصرف خروجی:**

- balance + Trade PnL وقتی balance سود را از قبل دارد؛ balance + payout وقتی دریافت ثبت شده است.
- commission در Trade و FEE مالی بابت همان هزینه؛ فایل PnL از قبل net به‌علاوهٔ commission جدا.
- PROFIT=80 در Wallet و انتقال همان 80 به Bank: helper درآمد هر دو را می‌گیرد، income=160 بدون افزایش دوم ثروت.
- بانک→بروکر→بانک می‌تواند درآمد نمودار بسازد، بدون هیچ سود اقتصادی.
- بانک/کارت موازی یا دو ردیف بروکر برای یک حساب واقعی؛ aggregate هویت اقتصادی را نمی‌شناسد.
- ثبت دستی DEPOSIT علاوه بر گردش واقعی؛ unique بودن لینک یک movement به معنی جلوگیری از دو رخداد مستقل تکراری نیست.

جمع ارزهای متفاوت «دوباره‌شماری» نیست، بلکه خطای واحد است. افزودن کل funded به سهم شخص نیز الزاماً تکرار نیست، بلکه خطای مالکیت/دامنه است. stale balance هم نقص تازگی است؛ این سه نباید با double counting یکی نامیده شوند.

## 14. P0 Findings

تعریف P0 در این ممیزی: مسیر قابل اثباتی که تمامیت مبلغ/ارز یا بقای موجودی ثبت‌شده را نقض می‌کند و پیش از اعتماد مالی باید تعیین تکلیف شود؛ این برچسب اثبات وقوع خسارت واقعی نیست.

| ID | یافته | شاهد و اثر |
|---|---|---|
| P0-01 | ویرایش برداشت مالی بدون validate_accounts | `i:\trade\MokTradeDesk\backend\app\api\finance.py:853–880` و `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:235–260`؛ امکان ناسازگاری ارز سند و حساب و اثر عددی بدون تبدیل |
| P0-02 | relabel ارز PTA دارای موجودی/Trade و فاقد movement | `i:\trade\MokTradeDesk\backend\app\api\trading.py:218–224`؛ جابه‌جایی مصنوعی مانده و تاریخچهٔ ارزی PnL |
| P0-03 | حذف PTA بدون تاریخچه حتی با current غیرصفر | `i:\trade\MokTradeDesk\backend\app\api\trading.py:230–250`؛ حذف دارایی ثبت‌شده بدون رخداد خروج وجه |

## 15. P1 Findings

P1: مانع قابل اتکا بودن متریک مالی یا قرارداد ثروت، حتی اگر جمع حساب‌ها از نظر نحوی صحیح باشد.

| ID | یافته و شرط اثر | شاهد |
|---|---|---|
| P1-01 | current بروکر از Trade تازه نمی‌شود؛ تضمین «ثروت امروز» یا برابر بودن balance-PnL با Trade-PnL وجود ندارد | بخش ۳؛ trading.py:192–224، finance_sync_service.py:26–28 با مسیرهای مطلق در همان بخش |
| P1-02 | Cash Flow انتقال داخلی/بازگشت سرمایه را درآمد می‌گیرد و با summary هم‌معنا نیست | `i:\trade\MokTradeDesk\backend\app\services\financial_reporting.py:6–51`؛ `i:\trade\MokTradeDesk\backend\app\services\wallet_service.py:154–186` |
| P1-03 | Net Profit شخصی و funded کامل را مخلوط و مجموعهٔ متفاوتی از expenses کم می‌کند | `i:\trade\MokTradeDesk\backend\app\api\finance.py:1435–1484,1663–1688,1770–1781` |
| P1-04 | سود قابل برداشت پراپ شامل Trade باز و بدون تفکیک ارز؛ خروجی برچسب USDT دارد | `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:80–106`؛ `i:\trade\MokTradeDesk\backend\app\api\finance.py:1523` |
| P1-05 | sync سود مرحله شامل معاملات باز و share صفر را ۸۰٪ می‌کند | `i:\trade\MokTradeDesk\backend\app\services\import_engine.py:818–829`؛ گزارش stored: `i:\trade\MokTradeDesk\backend\app\api\prop.py:1281–1283` |
| P1-06 | Asset Trend تاریخچهٔ ثروت نیست: حذف تبدیل، baseline بروکر و carry-in بازه | `i:\trade\MokTradeDesk\backend\app\api\finance.py:1923–1984` |
| P1-07 | جمع IRR و USDT در کارت FinancePage بدون FX | `i:\trade\MokTradeDesk\frontend\src\pages\FinancePage.tsx:793–799` |
| P1-08 | Analytics total_balance حساب مالی را ندارد و funded دریافت‌نشده را دارد؛ برای ثروت شخصی نامعتبر است | `i:\trade\MokTradeDesk\backend\app\api\analytics.py:564–570` |

## 16. P2 Findings

P2: ابهام دامنه، مستندسازی یا سیاست نمایش که نباید جایگزین اصلاح تمامیت و فرمول شود.

- **P2-01:** عنوان «موجودی کل» داشبورد فقط subtotal مالی ارز منتخب است؛ با broker-only گمراه‌کننده می‌شود. شاهد: `i:\trade\MokTradeDesk\frontend\src\pages\DashboardPage.tsx:775–785`.
- **P2-02:** docstring دریافت پراپ و ادعای «current شامل سود است» با تضمین واقعی مسیرهای اجرا همخوان نیستند. شواهد: `i:\trade\MokTradeDesk\backend\app\services\payout_service.py:163–204`؛ `i:\trade\MokTradeDesk\backend\app\services\finance_metrics.py:5–9`.
- **P2-03:** سیاست آرشیو/غیرفعال‌بودن باید از مالکیت پول جدا باشد؛ حذف این حساب‌ها از مجموع بدون قرارداد نیز می‌تواند کم‌نمایی ایجاد کند. نبود فیلتر، به‌تنهایی خرابی عدد فعلی را ثابت نمی‌کند. شواهد: `i:\trade\MokTradeDesk\backend\app\api\finance.py:287–316,1510–1519`.

## 17. NOT VERIFIED

- موجودی واقعی بانک/بروکر، عدد ثروت امروز، بدهی‌ها، دارایی‌های خارج از سیستم و قابلیت برداشت واقعی.
- اعمال migration/constraint در DB، triggerها، jobهای بیرونی، سابقهٔ overwrite موجودی و پوشش کامل import.
- وجود واقعی حساب تکراری، کارت و بانک با پول مشترک، هزینهٔ تکراری یا payout تکراری.
- مبنای زمانی snapshot بروکر؛ gross/net و علامت هزینه در فایل‌های واقعی؛ نرخ و زمان FX.
- دادهٔ غیرصفر archived، پراپ غیر USDT، Trade باز با pnl ذخیره‌شده و برداشت با ارز ناسازگار در محیط واقعی.
- concurrency، atomicity اجرایی، HTTP، timezone مرورگر و خروجی UI زنده؛ هیچ تست یا برنامه‌ای اجرا نشده است.
- ادعاهای تاریخی موفقیت بررسی Git در گزارش پنجم و نتایج قبلیِ ابزار با خروجی خالی. خروجی خالی در این ممیزی شاهد موفقیت محسوب نشد.

کنترل دامنهٔ نوشتن: وضعیت خوانای Git پیش از ایجاد این سند فقط پنج گزارش PART1 تا PART5 را untracked نشان داد؛ diff آماری فایل‌های tracked خالی بود. این وضعیت «کاملاً clean» نیست و تاریخچهٔ جلسهٔ قبلی را اثبات نمی‌کند. تنها فایل مجاز برای نوشتن در این کار `i:\trade\MokTradeDesk\FINANCE_FINAL_AUDIT.md` است. پنج hash مبنا برای کنترل حفظ گزارش‌های قبلی:

| گزارش | SHA256 پیش از نوشتن |
|---|---|
| PART1 | `00C33A55FDEB194E5AFEA9D7DF125959BAD8FFF6893D8CC04505E4EAC1398A3F` |
| PART2 | `78926E3603D08A297146E7544C131BDD1E088A9396C1A4DACE635DDFC8A8847C` |
| PART3 | `67D06A45D21AB05A562AC43953552D47D4A754C2537296C1066CB88F953D5A8A` |
| PART4 | `0F2A7A38EC49E0841D5752AA4423D278A2F129CB0649F55F76081203D7B51D41` |
| PART5 | `3DF7BBC4CA88F206ECDC29C35A73D122C8BD01EE7E5B93DCEE0A8AEA1B63F7B0` |

## 18. Final Finance Contract

این بخش قرارداد معنایی لازم برای پذیرش مالی است، نه طرح فنی پیاده‌سازی:

1. دارایی ثبت‌شدهٔ شخصی برای هر ارز، جمع محل‌های نگهداری مستقلِ تحت مالکیت شخص است؛ یک پول فقط یک بار.
2. موجودی snapshot، سود دوره، درآمد خارجی و گردش داخلی چهار کمیت مستقل‌اند. افزودن آن‌ها بدون تطبیق ممنوع است.
3. current بروکر باید مبنای زمانی و نسبت مشخص با realized PnL داشته باشد؛ تازگی آن را صرف وجود معاملات نمی‌توان فرض کرد.
4. انتقال داخلی هم‌ارز ثروت کل را تغییر نمی‌دهد و درآمد/هزینهٔ اقتصادی نیست؛ تبدیل دو ارز اثر جدا در هر ارز دارد.
5. Real Trading PnL فقط معاملات بسته را با pnl+commission+swap علامت‌دار شامل می‌شود؛ null pnl هزینه‌های ثبت‌شده را حذف نمی‌کند.
6. هزینهٔ مستقل فقط یک بار و در دامنه/بازهٔ همان سود کسر می‌شود؛ هزینهٔ داخل net معامله دوباره کسر نمی‌شود.
7. سرمایهٔ پراپ شخصی نیست؛ funded PnL کامل، سهم کاربر، قابل برداشت و دریافت نقدی جدا می‌مانند. RECEIVED فقط از balance مقصد وارد دارایی می‌شود.
8. هر خروجی نام‌گذاری‌شدهٔ Total Wealth باید دامنهٔ حساب‌ها، ارز، زمان، بدهی‌ها و مبنای ارزش‌گذاری را روشن کند؛ مجموع موجودی ثبت‌شده به‌تنهایی ثروت کامل نیست.
9. هیچ مجموع واحد IRR+USDT بدون مبنای FX پذیرفته نیست. inactive/archive به‌تنهایی مالکیت را از بین نمی‌برد.
10. روند دارایی زمانی قابل تطبیق است که دامنه و baseline آن با snapshot هم‌معنا باشد؛ روند فعلی چنین تضمینی ندارد.

## 19. Required Fix Order

ترتیب لازم برای رفع مانع پذیرش، بدون پیشنهاد کد، migration یا طراحی:

1. **تمامیت داده و واحد پول — P0:** تعیین تکلیف اعتبارسنجی برداشت مالی، relabel ارز و حذف موجودی غیرصفر بروکر.
2. **قرارداد موجودی بروکر و تطبیق واقعی — P1 / NOT VERIFIED:** روشن شدن baseline، تازگی و نسبت موجودی با معاملات و گردش‌ها؛ عدم ادعای ثروت واقعی تا تأیید داده.
3. **قرارداد سود و هزینه — P1:** جداسازی شخصی/پراپ، closed-only، سهم صفر و تخصیص یکتای هزینه‌ها.
4. **جریان پول و تاریخچهٔ دارایی — P1:** رفع تناقض درآمد داخلی، هزینه‌های ناهماهنگ، تفکیک ارز و معنای Asset Trend.
5. **پذیرش سناریوها و داده — NOT VERIFIED:** اثبات ۱۸ سناریو، عدم تکرار و سازگاری snapshot/دفتر در محیط مجاز؛ در این ممیزی انجام نشده است.
6. **قرارداد مصرف UI — P1/P2:** عناوین و جمع‌های نمایشی فقط پس از تثبیت معنای backend قابل اتکا هستند؛ جمع ارزی نادرست و subtotal با عنوان total قابل پذیرش نیستند.

**حکم نهایی:** Finance Backend پیش از هر بازطراحی UI نیازمند اصلاح و تأیید قرارداد مالی است. امروز فقط مجموع موجودی ثبت‌شدهٔ شخصی به تفکیک ارز را می‌توان از فرمول موجود بدون افزودن دوبارهٔ سود/برداشت استخراج کرد؛ صحت اقتصادی و عدد واقعی Personal Total Wealth هنوز تأیید نشده است.