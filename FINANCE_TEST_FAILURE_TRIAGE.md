# MokTradeDesk — Finance Test Failure Triage

## خلاصه مدیریتی

بررسی در حالت read-only انجام شد؛ هیچ فایل کد یا تستی تغییر نکرد و commit/push انجام نشد. تست‌های هدفمند مجدداً اجرا شدند: **6 شکست**. اجرای کامل backend در وضعیت فعلی: **13 شکست، 680 پاس و 1 xfailed از 694 مورد جمع‌آوری‌شده**.

ریشهٔ بخش مالی، اختلاف قراردادهاست: `backend/app/services/payout_service.py` صریحاً می‌گوید payout دریافتی به کیف‌پول/صرافی `ADJUSTMENT` است و درآمد نمی‌شود؛ تنها دریافت بانکی `PROFIT` و درآمد است. بنابراین پنج assertion انتظار `total_income == 500` برای payout به کیف‌پول، با قرارداد موجود ناسازگارند. در مقابل، تست سپردهٔ بانکی `total_income == 0` با رفتار فعلی «سپردهٔ بانکی درآمد است» ناسازگار است و به‌نظر می‌رسد stale باشد.

تغییرات working tree فقط به `wallet_service.py` و `financial_reporting.py` محدود نیست: `broker_cash_service.py`، `finance_metrics.py` و `tests/test_broker_cash_movements.py` نیز تغییرکرده‌اند و فایل `DASHBOARD_FULL_AUDIT_2026-10-09.md` untracked است. پس شکست‌های غیرمرتبط را نمی‌توان به کل تغییرات قبلی working tree نسبت نداد. `git diff --check` خطایی گزارش نکرد.

## فهرست دقیق همهٔ شکست‌ها

### شش شکست مجموعهٔ هدفمند

| # | تست کامل و فایل | assertion شکست‌خورده | انتظار | واقعی | دسته‌بندی |
|---|---|---|---:|---:|---|
| 1 | `tests/test_finance.py::test_create_transaction_and_filter[deposit-0]` | `tests/test_finance.py:376` — `summary["total_income"] == expected_income` | 0 | 500.0 | REGRESSION نسبت به انتظار قدیمی / قرارداد stale |
| 2 | `tests/test_phase33_withdrawal.py::test_status_transitions_and_income_at_received` | `tests/test_phase33_withdrawal.py:159` — `summary["total_income"] == 500.0` | 500.0 | 0.0 | STALE TEST نسبت به قرارداد payout فعلی |
| 3 | `tests/test_phase33_withdrawal.py::test_transfer_is_not_income` | `tests/test_phase33_withdrawal.py:207` — `income_before == 500.0` | 500.0 | 0.0 | STALE TEST نسبت به قرارداد payout فعلی |
| 4 | `tests/test_phase39_wallet.py::test_payout_still_works` | `tests/test_phase39_wallet.py:507` — `total_income == 500.0` | 500.0 | 0.0 | STALE TEST؛ docstring تست با assertion تناقض دارد |
| 5 | `tests/test_phase40_full_regression.py::test_full_cycle_finance_after_prop_payout` | `tests/test_phase40_full_regression.py:370` — `summary["total_income"] == 500.0` | 500.0 | 0.0 | STALE TEST نسبت به قرارداد payout فعلی |
| 6 | `tests/test_phase40_full_regression.py::test_full_cycle_payout_transfer_is_not_income` | `tests/test_phase40_full_regression.py:669` — `total_income == 500.0` پیش از انتقال | 500.0 | 0.0 | STALE TEST نسبت به قرارداد payout فعلی |

### هفت شکست دیگر در اجرای کامل

| # | تست کامل و فایل | assertion/خطای شکست | انتظار | واقعی | دسته‌بندی |
|---|---|---|---|---|---|
| 7 | `tests/test_phase36_performance.py::test_phase36_indexes_exist` | `tests/test_phase36_performance.py:91` — مجموعهٔ indexهای مورد انتظار زیرمجموعهٔ indexهای موجود نیست | indexهای تعریف‌شده در تست | یک یا چند نام مورد انتظار غایب است | UNRELATED؛ نیازمند تطبیق migration/schema |
| 8 | `tests/test_phase44_money.py::test_dashboard_no_double_counting` | assertion در آزمون dashboard؛ خروجی واقعی `0.0` | 500.0 | 0.0 | UNRELATED به طبقه‌بندی payout؛ احتمالاً قرارداد/تغییر metricهای مالی |
| 9 | `tests/test_phase44_scenario.py::test_scenario_no_double_counting` | assertion سناریوی dashboard؛ `500.0 == 700.0` ناموفق | 700.0 | 500.0 | UNRELATED به طبقه‌بندی payout؛ احتمالاً قرارداد/تغییر metricهای مالی |
| 10 | `tests/test_phase4_initial_sl.py::test_patch_sl_does_not_change_r_when_initial_sl_exists` | `KeyError: 'id'` | وجود کلید `id` در response پیش‌مرحله | `id` موجود نیست | UNRELATED؛ response/fixture/import engine |
| 11 | `tests/test_phase4_initial_sl.py::test_patch_open_price_without_initial_sl_warns` | `KeyError: 'id'` | وجود کلید `id` در response پیش‌مرحله | `id` موجود نیست | UNRELATED؛ response/fixture/import engine |
| 12 | `tests/test_phase4_initial_sl.py::test_patch_open_price_with_initial_sl_no_warn` | `KeyError: 'id'` | وجود کلید `id` در response پیش‌مرحله | `id` موجود نیست | UNRELATED؛ response/fixture/import engine |
| 13 | `tests/test_phase58_prop_migration.py::test_phase58_migration_adds_modes_and_preserves_legacy_total_mode` | `sqlalchemy.exc.NoSuchTableError: trades` | جدول `trades` در DB مهاجرت تست | جدول وجود ندارد | UNRELATED؛ ساخت/ترتیب migration تست |

خروجی کامل: **680 passed, 13 failed, 1 xfailed**. تفکیک خارج از شش تست هدفمند: **1 index + 2 Phase 44 + 3 Phase 4 + 1 Phase 58 = 7**. هیچ شکست دیگری در summary pytest ثبت نشد.

## تحلیل علت هر شکست

### 1. سپردهٔ بانکی با انتظار درآمد صفر

تست `test_create_transaction_and_filter[deposit-0]` حساب را از نوع `bank` می‌سازد و `deposit` به مبلغ 500 ثبت می‌کند؛ summary مقدار 500 برمی‌گرداند، نه صفر. کد فعلی `detect_cash_flow` در `wallet_service.py` صریحاً `DEPOSIT` را فقط در صورت مقصد بانکی `INCOME` می‌کند. فیلتر درآمد بانکی در `financial_reporting.py` نیز `DEPOSIT` متصل به حساب بانک را می‌پذیرد. بنابراین شکست مستقیماً ناشی از تغییر جدید است؛ اما با قرارداد bank-aware فعلی و معنی deposit بانکی سازگار است. تست قدیمی انتظار `0` را حفظ کرده و باید با قرارداد جاری مقایسه/به‌روزرسانی شود، نه اینکه صرفاً منطق جدید بدون تصمیم محصولی برگردانده شود.

### 2–6. payout و انتقال‌های پس از آن

در هر پنج تست، payout مبلغ 500 به حساب **Trust Wallet**/کیف‌پول می‌رسد. این دریافت یک payout پراپ است؛ نوع تراکنش طبق پیاده‌سازی جاری `ADJUSTMENT` مثبت است (نه `PROFIT` یا `DEPOSIT` بانکی) و مقصد کیف‌پول غیر‌بانکی است. حساب مبدأ مستقل از پرداخت‌کنندهٔ خارجی در ledger مالی payout ثبت نمی‌شود؛ payout در مقصد ثبت و موجودی مقصد افزایش داده می‌شود. بنابراین این رویداد از دید ثبت مالی، دریافت دارایی/تعدیل است، نه انتقال داخلی بین دو `FinancialAccount` و نه درآمد بانکی.

مواضع پروژه:

- `payout_service.py` docstring (ابتدای فایل): تنها payout دریافتی در بانک `PROFIT` و درآمد است؛ دریافت در wallet/exchange `ADJUSTMENT` مثبت است تا دارایی ثبت شود، بدون گزارش درآمد پیش از واریز بانکی.
- همان سرویس برای انتقال واقعی می‌گوید انتقال غیربانک به بانک می‌تواند در گزارش درآمد لحاظ شود و انتقال بانک به بانک درآمد جدید نیست.
- `financial_reporting.py::bank_income_filter` تنها ورودی‌های بانکی و انتقال غیربانک→بانک را درآمد بانکی حساب می‌کند.
- `wallet_service.py::detect_cash_flow` انتقال wallet→exchange را `NONE` می‌کند؛ انتقال داخلی این دو حساب درآمد نیست.

| تست | مورد آزموده‌شده | نتیجهٔ قرارداد |
|---|---|---|
| `test_status_transitions_and_income_at_received` | حساب مقصد در helper به‌عنوان account عادی ساخته شده؛ در تست workflow نام نوع مقصد به‌تنهایی صریح نیست. نوع transaction را پاسخ آزمون به‌صورت `PROFIT` انتظار دارد، اما با سیاست موجود برای مقصد غیربانکی باید `ADJUSTMENT` باشد. | انتظار `total_income=500` برای مقصد غیربانکی با قرارداد payout جاری ناسازگار است. نوع account مقصد در fixture باید هنگام بررسی نهایی صریحاً ثبت شود؛ assertion فعلی واقعاً `PROFIT` را چک می‌کند. |
| `test_transfer_is_not_income` | payout مقصد Trust Wallet؛ سپس انتقال Trust Wallet→Exchange. | payout در wallet درآمد بانکی نیست؛ انتقال بعدی داخلی هم درآمد نیست. آزمونِ «انتقال درآمد اضافه نکند» با قرارداد سازگار است، ولی baseline آن (`income_before=500`) نیست. |
| `test_payout_still_works` | destination صریحاً `TRUST_WALLET`; docstring می‌گوید «بدون ثبت درآمد بانکی»، اما assertion خط 507 درآمد کل 500 می‌خواهد. | assertion مستقیماً با docstring و قرارداد payout تعارض دارد؛ STALE TEST. |
| `test_full_cycle_finance_after_prop_payout` | مقصد صریحاً `trust_wallet`. | payout غیربانکی نباید در bank income/total incomeِ bank-qualified گزارش شود؛ انتظار 500 stale است. |
| `test_full_cycle_payout_transfer_is_not_income` | مقصد Trust Wallet و سپس حساب Exchange. | انتقال wallet→exchange داخلی است؛ نه bank income، نه income تازه. assertion اولیهٔ 500 ناسازگار است؛ assertion اینکه انتقال درآمد را افزایش ندهد مطابق قرارداد است، هرچند summary انتقال‌ها باید جداگانه تأیید شود. |

**تفکیک متریک برای payout 500:**

- **Bank income:** فقط وقتی مبلغ واقعاً به حساب `BANK` واریز/ثبت شود. در نمونه‌های wallet، مقدار درآمد بانکی صفر است.
- **`total_income`:** در قرارداد مورد بحث، مجموع درآمدهای قابل‌شناسایی مالی که در بانک ثبت شده‌اند؛ نباید صرف وصول payout به wallet را درآمد بانکی جلوه دهد. اگر محصول `total_income` را درآمد اقتصادی مستقل از bank income تعریف می‌کند، مرز این دو متریک باید روشن شود.
- **Realized trading PnL:** سود معاملات بستهٔ `REAL_PROP` که در `finance_metrics.py::funded_pnl`/محاسبهٔ مرحله جمع می‌شود. این سود معاملاتی جدا از وجه نقد payout است و نباید با دریافت 500 دوباره شمرده شود. payout «PnL تحقق‌یافتهٔ معامله» نیست.
- **Cash flow:** برای `ADJUSTMENT` در wallet در قرارداد فعلی `NONE` (و برای `PROFIT` فقط در مقصد بانکی `INCOME`). انتقال داخلی wallet→exchange نیز `NONE` است. موجودی کیف پول افزایش می‌یابد، اما آن را نباید خودکار درآمد بانکی شمرد.

#### اثر تغییر اخیر/پیش از تغییر

کد فعلی payout service سیاست غیربانکی را از قبل به‌صراحت مستند می‌کند؛ بااین‌حال `financial_reporting.py` اینجا تغییر working-tree دارد و فیلتر جدید bank-only باعث صفر شدن income برای payoutهای غیربانکی شده است. بنابراین پنج failure در برابر assertionهای قدیمی **با تغییر اخیر در reporting** آشکار شده‌اند، ولی این assertionها با قرارداد جاری payout ناسازگارند. این‌ها regression عملکردی نسبت به تست‌ها هستند، اما از شواهد فعلی stale بودن تست در برابر قرارداد محصول محتمل‌تر است. برای تست Phase 33 که پاسخ نوع `PROFIT` را هم assertion می‌کند، اختلاف نوع تراکنش به‌تنهایی با assertion `total_income` توضیح داده نمی‌شود: helper مقصد را می‌سازد و خود تست `tx.type == PROFIT` را الزام می‌کند؛ برای آن ترکیب، قرارداد دقیق نوع تراکنش با توجه به نوع مقصد helper باید به‌طور صریح تصمیم‌گیری شود.

### شکست‌های خارج از شش مورد

- **Index / Phase 36:** تست از inspect روی schema واقعی استفاده کرده و مجموعه‌ای از indexها را انتظار دارد. خروجی می‌گوید زیرمجموعه‌بودن برقرار نیست اما نام index مفقود در summary کوتاه pytest مشخص نشده است. قرارداد schema/migration از فایل‌های بررسی‌شده به‌طور کامل معلوم نیست؛ جزئیات index را `UNKNOWN` می‌گذاریم. ارتباط مستقیم با تغییرات finance reporting/wallet دیده نمی‌شود.
- **Phase 44 dashboard:** `test_dashboard_no_double_counting` انتظار 500 و actual صفر؛ `test_scenario_no_double_counting` انتظار 700 و actual 500. `finance_metrics.py` نیز تغییرات uncommitted دارد و همین دو آزمون دربارهٔ dashboard/محاسبهٔ توازن‌اند. انتساب به تغییرات working tree محتمل، اما بدون تحلیل کامل diff و مسیر endpoint نمی‌توان علت قطعی گفت: `UNKNOWN` در مورد root cause، `UNRELATED` به طبقه‌بندی نقدی bank-income.
- **Phase 4:** سه تست PATCH قبل از رسیدن به assertions رفتاری با `KeyError: 'id'` در response helper شکست می‌خورند. ریشه در شکل response/fixture/import است و ارتباط مالی ندارد. تغییرات `wallet_service.py`/`financial_reporting.py` به‌عنوان علت محتمل نیست؛ علت دقیق `UNKNOWN`.
- **Phase 58:** migration test با `NoSuchTableError: trades` شکست می‌خورد، پیش از assertion قراردادی. مرتبط با ایجاد/ترتیب schema migration است، نه گزارش‌دهی مالی؛ علت دقیق `UNKNOWN`.

## تفکیک وضعیت‌ها

- **REGRESSION:** مورد سپردهٔ بانکی نسبت به assertion موجود، خروجی عوض شده (0→500) بر اثر تغییر bank-aware. بااین‌حال semantics جدید با قرارداد فعلی واریز به بانک هم‌راستا است؛ بنابراین regression تست/انتظار قدیمی است مگر محصول `deposit` را صرفاً جابه‌جایی وجه موجود تعریف کند.
- **STALE TEST:** پنج assertion payout=500، به‌ویژه Phase 39 که docstring خودش صریحاً «بدون درآمد بانکی» می‌گوید.
- **CONTRACT AMBIGUITY:** مرز `total_income` در برابر bank income؛ تعریف `DEPOSIT` در برابر درآمد خارجی/انتقال پول موجود؛ و رفتار/نوع تراکنش payout بسته به نوع مقصد. این ابهام روی صورت‌بندی تست‌ها اثر دارد.
- **UNRELATED:** index، سه Phase 4 و Phase 58 به تغییرات bank-aware از نظر موضوعی نامرتبط‌اند. Phase 44 نیز موضوعاً خارج از payout cash classification است.
- **UNKNOWN:** انتساب قطعی علت برای شکست‌های خارج از finance، نام دقیق indexهای مفقود و نوع مقصد در helper آزمون Phase 33 از خروجی خلاصه/فایل‌های خوانده‌شده به دست نیامد. همچنین چون چند فایل دیگر در working tree تغییر کرده‌اند، انتساب قطعی Phase 44 به تنها یک diff ممکن نیست.

## قراردادهای محصولی که نیاز به تصمیم دارند

1. آیا `total_income` مترادف «درآمد بانکی تأییدشده» است یا شامل payout دریافت‌شده در کیف‌پول هم می‌شود؟ قرارداد payout فعلی گزینهٔ اول را می‌گوید.
2. آیا `DEPOSIT` در حساب بانک درآمد واقعی/خارجی است یا صرفاً ثبت ورود سرمایه‌ای که از قبل متعلق به کاربر بوده؟ رفتار فعلی و bank-income filter آن را درآمد می‌شمارند، ولی `external_income` نیز وجود دارد و تست قدیمی deposit را درآمد نمی‌داند.
3. برای payout در بانک، wallet، exchange و سایر انواع مقصد، نوع ledger transaction دقیقاً `PROFIT`/`ADJUSTMENT`/`TRANSFER` کدام است؟ کد payout مستندشده می‌گوید بانک `PROFIT` و wallet/exchange `ADJUSTMENT`.
4. انتقال غیربانک→بانک در bank-income گزارش می‌شود؛ آیا همیشه انتقال داخلی دارایی است یا ورود وجه از منبع خارجی نیز ممکن است با این شکل ثبت شود؟ قرارداد فعلی آن را درآمد گزارش می‌کند، اما باید مانع double counting در انتقال بعدی باشد.
5. آیا PnL تحقق‌یافتهٔ prop صرفاً متریک عملیاتی است یا در `total_income` مالی هم وارد می‌شود؟ `finance_metrics.py` آن را جداگانه به funded PnL اختصاص می‌دهد؛ نباید با payout دوباره شمرده شود.

## وضعیت working tree و diff

در snapshot بررسی‌شده، `git status --short`:

```text
 M backend/app/services/broker_cash_service.py
 M backend/app/services/finance_metrics.py
 M backend/app/services/financial_reporting.py
 M backend/app/services/wallet_service.py
 M backend/tests/test_broker_cash_movements.py
?? DASHBOARD_FULL_AUDIT_2026-10-09.md
```

هیچ فایل تست هدفمند یا Phase 36/44/4/58 در status تغییرکرده نشان داده نشد. Diff stat گزارش‌شده برای پنج فایل tracked: **99 additions, 26 deletions**. `git diff --check` عبور کرد. با این حال Phase 44 می‌تواند از تغییر `finance_metrics.py` تأثیر گرفته باشد، و آزمون‌های broker cash از تغییر broker service/test. تست‌های دیگر در شش مورد هدفمند عمدتاً با تغییر `financial_reporting.py`/`wallet_service.py` توضیح‌پذیرند. به علت وجود تغییرهای uncommitted پیشین، هیچ baseline clean-tree برای مقایسه اجرا نشده؛ بنابراین «پیش از تغییر هم شکست می‌خورد» را نمی‌توان برای هر مورد با قطعیت ادعا کرد.

## پیشنهاد اصلاح به ترتیب اولویت (بدون اجرای اصلاحات)

1. ابتدا قرارداد محصولی را برای bank income در برابر `total_income` و معنی `DEPOSIT` تصویب کنید؛ سپس assertion قدیمی deposit را با آن قرارداد تطبیق دهید یا رفتار را بازنگری کنید.
2. تست‌های payout را بر اساس نوع واقعی مقصد تفکیک کنید: wallet/exchange باید افزایش موجودی و نبود bank income را بسنجند؛ مقصد بانک باید به‌طور مستقل مسیر درآمد بانکی را پوشش دهد. برای Phase 33 assertion نوع `PROFIT` را با نوع مقصد واقعی و قرارداد مصوب تطبیق دهید.
3. برای انتقال wallet→exchange، فقط انتقال داخلی و عدم افزایش income را assert کنید؛ ثبت payout اولیه را با متریک تعریف‌شده (دارایی/adjustment یا bank income) بسنجید.
4. Phase 44 را جداگانه با diff کامل `finance_metrics.py` و endpointهای مصرف‌کنندهٔ metrics بررسی کنید؛ با اعداد fixture و قرارداد double-counting منشأ expected 500/700 را پیدا کنید.
5. شکست index را با چاپ مجموعهٔ مورد انتظار و موجود و migrationهای schema حل‌وفصل کنید؛ migration Phase 58 را جدا از finance classification بررسی و ترتیب ایجاد جدول `trades` را اصلاح/مستند کنید.
6. برای سه Phase 4 پاسخ واقعی API و fixture/version helper را ردیابی کنید تا علت فقدان `id` پیش از ارزیابی assertions رفتاری روشن شود.
7. پس از تصمیم و اصلاحات مصوب، ابتدا شش تست هدفمند و سپس کل suite را روی working tree با تغییرات قبلی حفظ‌شده اجرا کنید؛ هیچ تستی صرفاً برای سبز شدن بدون تصمیم قراردادی تغییر نکند.

---

**محدودیت بررسی:** اجرای pytest فقط وضعیت فعلی working tree را توصیف می‌کند؛ clean baseline اجرا نشده است. پس نسبت‌دادن علت به تغییر خاص، جز جایی که منطق و assertion به‌طور مستقیم قابل تطبیق‌اند، احتمالی است نه قطعی.