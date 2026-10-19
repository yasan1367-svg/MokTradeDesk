# گزارش مرحلهٔ پنجم اصلاح Strategy / Comparison

**تاریخ:** ۲۰۲۶-۱۰-۱۲
**دامنه:** فقط یافته‌های #18 تا #24؛ Stageهای 1–4 حفظ شدند. Stage 6 آغاز نشده است.
**قرارداد محصول:** ژورنال تاریخی معاملات بسته؛ معاملهٔ باز/زنده وارد این مسیرها نمی‌شود؛ همهٔ مبالغ USDT؛ بدون FX، floating PnL یا net R استنباطی.

## تغییرات و وضعیت یافته‌ها

| یافته | وضعیت | اصلاح و قرارداد |
|---|---|---|
| **#18 label در برابر scope واقعی** | اصلاح شد | فرم label نسخه اکنون Backtest، Forward، legacy `real` و labelهای real_personal/real_prop را با عنوان روشن «برچسب نسخه، نه طبقه‌بندی معامله» عرضه می‌کند. `/versions/all` و `/versions` مقدار label و `forked_from_version_id` می‌دهند؛ تعداد فقط معاملات بسته را بر اساس `Trade.test_type` واقعی تفکیک می‌کند. label نامشخص/قدیمی به `unspecified` شمارش می‌شود؛ هیچ classification ساخته نمی‌شود. |
| **#19 persistence فرم** | اصلاح شد | create، status و test_type را ارسال می‌کند؛ PATCH اعتبارسنجی‌شده test_type افزوده شد. فیلد omitted حفظ می‌شود و null صریح label را پاک می‌کند. موفقیت edit فقط پس از پاسخ API اعلام می‌شود. تغییر label هیچ Trade را تغییر نمی‌دهد. API requestهای واقعی create/PATCH و دادهٔ ذخیره‌شده آزموده شدند. |
| **#20 رقابت درخواست Strategy** | اصلاح شد | بارگیری versions/stats/chart و live-performance به ID انتخاب‌شده و generation وابسته است؛ catch/finally پاسخ superseded بی‌اثر است. تغییر Strategy دادهٔ قبلی را پاک می‌کند؛ unmount generation را invalidate می‌کند. آزمون deferred، A→B با خطا و موفقیت دیررس A را پوشش می‌دهد. |
| **#21 چرخهٔ Comparison** | اصلاح شد | هر درخواست snapshot ثابت شامل IDs/type/symbol/date دارد؛ فیلترهای submit‌شده نمایش داده می‌شوند. تغییر ورودی، Clear یا unmount generation را باطل می‌کند؛ پاسخ/خطای دیررس اثر ندارد. هر مقایسهٔ جدید نتیجهٔ قبلی را پیش از submit حذف می‌کند و خطای جدید موفقیت قدیمی را باقی نمی‌گذارد. Drawer و loading/error نیز در Clear reset می‌شوند. Deferred tests تغییر فیلتر، پاسخ دیررس، خطای superseded و Clear را پوشش می‌دهند. |
| **#22 refresh mutationها** | اصلاح شد؛ coverage هدفمند افزوده شد | Version create/edit/delete و Fork پس از موفقیت یک `loadStats` مشترک انجام می‌دهند؛ این فراخوانی مالک versions/stats/chart است و مسیرهای قبلی که `loadVersions` و `loadStats` را همزمان اجرا می‌کردند حذف شدند تا versions دو بار fetch نشود. refresh فقط برای همان Strategy انتخاب‌شده اعمال می‌شود. UI deferred tests، delete و Fork را تا پاسخ mutation نگه می‌دارند و refresh را بررسی می‌کنند؛ mutation refresh با پاسخ versions قدیمیِ دیررس هم پوشش داده شده است. |
| **#23 نمودار Strategy** | اصلاح شد | دانلود سریالی tradeها و محاسبهٔ تکراری PnL در کلاینت حذف شد. `GET /api/strategies/{id}/chart-aggregate` با scope واقعی Backtest یا Forward، symbol/date filters، predicate بستهٔ پذیرفته‌شده و `metrics.net_pnl_sql()` پاسخ aggregate می‌دهد. قرارداد پولی: SQL sums در raw precision جمع می‌شوند؛ `net_pnl` و مقادیر منحنی به دو رقم اعشار گرد می‌شوند؛ `by_version.net_pnl` تا ۱۲ رقم اعشار برای حفظ جمع‌پذیریِ زیرسنت نگه داشته می‌شود. بنابراین مجموع نسخه‌های پر‌دقت، ورودی گردکردن کل است؛ مقایسهٔ مجموع نسخه‌های جداگانه گرد‌شده با کل مجاز نیست. محدودیت 240 ماه با 422 آشکار است، نه truncation پنهان. R histogram هم server-side است. UI دادهٔ مشترک را نمایش می‌دهد و آن را «PnL تجمعی تاریخی» (نه equity/portfolio curve) می‌نامد؛ loading/error مانع نمایش chart ناقص می‌شود. فیلترها و قرارداد aggregate fractional آزموده شدند. |
| **#24 Radar** | اصلاح شد | کلید داده/سری `version_id` است و نام فقط label (با ID یکتا) است. سود خالص منفی از Radar حذف و در Bar پولی باقی می‌ماند؛ tooltip مقدار اصلی و واحد را همراه نمرهٔ نرمال‌شده نشان می‌دهد و UI نسبی‌بودن مقیاس به مجموعهٔ مقایسه را توضیح می‌دهد. PF بدون اندازه‌گیری gap می‌ماند؛ PF=0 finite حفظ و محور PF در نبود همهٔ مقادیر finite حذف می‌شود. تست duplicate name، negative PnL و PF gap/zero اضافه شد. |

## قراردادهای فنی/سازگاری

- Version labelهای `real` و legacy نامشخص حفظ می‌شوند؛ هیچ‌کدام به `REAL_PERSONAL`/`REAL_PROP` Trade تبدیل نمی‌شوند. برچسب فقط metadata است.
- مسیر `live-performance` موجود فقط نام legacy endpoint است؛ قابلیت live جدیدی اضافه نشد. نمودار جدید فقط معاملات بستهٔ Backtest/Forward است.
- مدل Trade در این workspace soft-delete ندارد و حذف تاریخی hard-delete است؛ شمارش closed با `close_time IS NOT NULL` انجام می‌شود. فیلد ساختگی `is_deleted` اضافه نشد.
- endpoint نمودار تمام خروجی را aggregate می‌کند؛ هیچ full-history trade download یا client-side net PnL calculation ندارد. خلاصهٔ آن فعالیت تاریخی ترکیبی نسخه‌هاست، نه عملکرد پرتفوی.
- Stageهای 1–4، predicateهای scope، امتیاز PF و قراردادهای unavailable/no-loss دست‌نخورده‌اند. Dashboard، Finance، migrations و تاریخچه تغییر نکردند.

## فایل‌های تغییرکرده

- `backend/app/api/strategies.py`
- `backend/tests/test_strategy_stage4_contracts.py`
- `backend/tests/test_strategy_chart_aggregate_stage5.py` (جدید)
- `frontend/src/api/client.ts`
- `frontend/src/pages/StrategyPage.tsx`
- `frontend/src/pages/ComparisonPage.tsx`
- `frontend/src/components/charts/ComparisonBarChart.tsx`
- `frontend/src/components/charts/ComparisonRadarChart.tsx`
- `frontend/src/__tests__/strategyPage.stage5.test.tsx` (جدید)
- `frontend/src/__tests__/comparisonPage.stage3.test.tsx`
- `frontend/src/__tests__/comparisonChartData.stage3.test.ts`
- `STRATEGY_FIX_STAGE5.md` (این گزارش)

## پیگیری تکمیلی و نتایج نهایی

- اشکال assertion اولیهٔ chart scope، نقص selector نبود: mock اولیه پاسخ resolved می‌داد و mock deferred به درخواست scope موردنظر متصل نبود. تست اصلاح‌شده خود درخواست `getStrategyChartAggregate(1, {test_type: 'forward'})` را deferred می‌کند، تنها یک درخواست را تأیید می‌کند، summary قبلی را در حالت pending رد می‌کند، سپس summary جدید را پس از resolve می‌سنجد.
- در failure واقعی، `loadStats` مقدار `stats` را null می‌کرد و به‌دلیل قرارداشتن loading/error داخل branch وابسته به stats، feedback از DOM حذف می‌شد. feedback اکنون در `showStats` و بیرون از شرط stats، یک‌بار رندر می‌شود؛ error با `role=alert` و loading با `role=status` واقعی و قابل‌دسترسی است. fallback بدون stats کنترل Backtest/Forward را نیز حفظ می‌کند.
- تست‌های UI جدید سناریوهای scope deferred/success، failure، superseded response که دیرتر می‌رسد، A→B→A، refresh جهش با پاسخ نسخهٔ قدیمی، حذف A پس از انتخاب B، اتمام save قدیمی هنگام بازبودن فرم جدید، و deferred delete/Fork را پوشش می‌دهند. تست backend aggregate fractional-USDT موجود ثابت می‌کند مجموع rounded، انتهای curve و مجموع نسخه‌ها با هم سازگارند.
- درخواست‌های chart و stats با `requestGeneration`، فهرست نسخه‌ها با `versionsGeneration` و درخواست‌های closed-real-performance با `liveGeneration` مستقل می‌مانند. تغییر scope فقط یک `loadStats` صریح اجرا می‌کند و effect دیگری برای scope وجود ندارد. live-performance در scope change/refresh مجدداً آغاز می‌شود، اما promise و invalidation آن جدا از chart/stats ownership است. mutation refreshها از `chartScope` فعلی به‌عنوان default استفاده می‌کنند.
- قرارداد rounding API aggregate: مقادیر خام SQL تا پایان جمع‌زدن نسخه‌ها حفظ می‌شوند؛ `net_pnl` کلی و نقاط `equity_curve` با `round(value, 2)` ارائه می‌شوند. `by_version.net_pnl` با `round(value, 12)` ارائه می‌شود تا sub-cent precision حفظ و جمع نسخه‌ها با raw aggregate قابل بازسازی باشد. نمونهٔ regression: دو نسخهٔ هرکدام `0.004`، مجموع خام `0.008`، `net_pnl` و curve endpoint برابر `0.01`، و `by_version` برابر `0.004` + `0.004`. قرارداد عامدانه تضمین نمی‌کند که cent-rounded subtotals جمعشان با cent-rounded total برابر شود.

## فرمان‌ها و نتایج نهایی

از `C:\MokTradeDesk\backend`:

```text
.\venv\Scripts\python.exe -m py_compile app\api\strategies.py tests\test_strategy_chart_aggregate_stage5.py tests\test_strategy_stage4_contracts.py
.\venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_strategy_chart_aggregate_stage5.py tests\test_strategy_stage4_contracts.py tests\test_analysis_stage4_atomicity.py tests\test_phase53_stale_analysis.py tests\test_phase53_delete_safety.py tests\test_phase48a_comparison.py tests\test_phase52_score_v2.py tests\test_metrics.py tests\test_phase53_strategy_stats.py tests\test_closed_trades_only.py tests\test_phase53_real_comparison.py tests\test_phase48a_score.py tests\test_phase48a_rank.py tests\test_phase48a_get_analysis.py tests\test_analysis_scope.py -q --tb=short
128 passed؛ deprecation warnings موجود FastAPI/Starlette/Pydantic/SQLAlchemy

.\venv\Scripts\python.exe -m pytest --collect-only -q
781 collected tests across the complete backend repository (collection only).

.\venv\Scripts\python.exe -m pytest -p no:cacheprovider -q --tb=short
779 passed, 2 failed, 1 xfailed. Existing unrelated failures:
tests/test_phase34_35_analysis_context.py::test_each_run_gets_its_own_scope_record
  expected current.analysis_run_id == 2; actual None
tests/test_phase41_compare.py::test_compare_unanalyzed_returns_error
  expected HTTP 200; actual HTTP 404 for missing version IDs [999, 998]
No tests were deselected or removed; the 128 focused count is the exact test-file list above. Reported 133/136 counts are not reproduced by these commands and no basis for removed/excluded tests was found.
.\venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_strategy_chart_aggregate_stage5.py tests\test_strategy_stage4_contracts.py tests\test_analysis_stage4_atomicity.py tests\test_phase53_stale_analysis.py tests\test_phase53_delete_safety.py tests\test_phase48a_comparison.py tests\test_phase52_score_v2.py tests\test_metrics.py tests\test_phase53_strategy_stats.py tests\test_closed_trades_only.py tests\test_phase53_real_comparison.py tests\test_phase48a_score.py tests\test_phase48a_rank.py tests\test_phase48a_get_analysis.py tests\test_analysis_scope.py -q --tb=short
128 passed؛ deprecation warnings موجود FastAPI/Starlette/Pydantic/SQLAlchemy
```

از `C:\MokTradeDesk\frontend`:

```text
npm test -- --pool=forks --maxWorkers=1 --reporter=dot --silent
11 فایل، 113 تست passed

npm run build
TypeScript و Vite production build موفق

npx eslint src/pages/StrategyPage.tsx src/__tests__/strategyPage.stage5.test.tsx
ناموفق فقط به علت 6 خطای no-explicit-any موجود در StrategyPage.tsx (خطوط 359، 383، 443، 465، 496، 520)؛ فایل تست تازه lint error ندارد.
```

از `C:\MokTradeDesk`:

```text
git diff --check
موفق؛ بدون whitespace error
```

## بررسی دو failure گزارش‌شده در Full Backend

هر دو مورد با اجرای جداگانه بازتولید و با قرارداد فعلی API/service تطبیق داده شدند؛ هیچ تغییر runtime لازم نبود.

| تست | نتیجهٔ بررسی / تصمیم | اصلاح هدفمند |
|---|---|---|
| `test_each_run_gets_its_own_scope_record` | انتظار تست با الگوی transaction سرویس ناسازگار بود. `analyze_version` تراکنش caller را حفظ می‌کند و FK جاری را در حافظه تنظیم می‌کند؛ Session پروژه `autoflush=False` است، پس query دیتابیسی پیش از flush مقدار جدید را نمی‌بیند. تعهد سرویس، اجرای جدا و بازگرداندن run/result مرتبط است؛ commit/flush بر عهدهٔ caller است. | فقط تست تغییر کرد تا بعد از اجرای دوم، پیش از query رکورد جاری `flush()` کند؛ سپس آخرین `analysis_run_id` را می‌سنجد. بدون تغییر سرویس و بدون تضعیف assertion. |
| `test_compare_unanalyzed_returns_error` | تست شناسه‌های خیالی `999, 998` می‌فرستاد. قرارداد endpoint: نسخهٔ ناموجود ⇒ HTTP 404؛ نسخهٔ موجود اما بدون تحلیل ⇒ HTTP 200 و entry دارای `error`. service و مستندات Phase 41 این تفکیک را تثبیت می‌کنند. | فقط fixture تست به دو نسخهٔ واقعی و تحلیل‌نشده تغییر کرد؛ بررسی status 200، دو error و best=None حفظ شد. رفتار 404 برای شناسهٔ ناموجود تغییر نکرد. |

## نتایج اعتبارسنجی این بررسی

از `C:\MokTradeDesk\backend` با `venv` پروژه:

```text
tests/test_phase34_35_analysis_context.py::test_each_run_gets_its_own_scope_record -q --tb=short
1 passed

tests/test_phase41_compare.py::test_compare_unanalyzed_returns_error -q --tb=short
1 passed

pytest -p no:cacheprovider -q --tb=short
781 collected; 780 passed, 1 xfailed, 0 failed (exit 0)

Focused Stage 1–5 suite (the 15-file command listed above)
128 passed, 0 failed (exit 0)

git diff --check
passed; no whitespace errors
```

The full run’s sole xfail and existing deprecation warnings remain; neither is one of the two investigated failures.

## ریسک‌های باقیمانده

1. `Trade` فاقد soft-delete است؛ شمارش و aggregate بر ردیف‌های موجود و بسته اتکا دارد. این Stage schema/historical cleanup اضافه نمی‌کند.
2. Full backend suite همچنان دو failure مشخص‌شده در بالا دارد؛ این فایل‌ها از focused acceptance command حذف نیستند، بلکه full run جداگانه اجرا شد و failures ثبت شدند.
3. lint هدف StrategyPage هنوز به‌سبب شش `any` قدیمی پاس نیست؛ فایل تست Stage 5 clean است. Build و full frontend suite موفق‌اند.
4. full suite backend نشان داد 781 مورد جمع‌آوری می‌شود؛ 128 قبلی/کنونی نتیجهٔ لیست focused Stage 1–5 است، نه کل backend. ادعاهای 133 و 136 از شواهد فعلی بازتولید نشدند.

Stage 5 follow-up کامل شد و برای بازبینی متوقف می‌شود. Stage 6 آغاز نشده است.