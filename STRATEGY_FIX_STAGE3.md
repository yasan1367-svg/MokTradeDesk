# گزارش مرحلهٔ سوم اصلاح Strategy / Comparison

**تاریخ:** ۲۰۲۶-۱۰-۱۲  
**دامنه:** Stage 3 و follow-up محدود به یافته‌های #10 و #25؛ Stage 1 و Stage 2 حفظ شدند. Stage 4 آغاز نشده است.

## تغییرات و فایل‌ها

- `backend/app/api/strategies.py`: آمار Strategy همچنان شمارش aggregate را حفظ می‌کند، اما نام‌گذاری و metadata آن را «خلاصهٔ تاریخی ترکیبی، نه عملکرد پرتفوی» می‌کند؛ به آمار per-version افزوده شد تفکیک هر `test_type`. PF از helper مشترک وضعیت‌دار می‌آید. Sharpe قدیمی به‌صورت عددی سازگار باقی است و تعریف اندازه‌گیری در metadata مشخص است.
- `backend/app/services/metrics.py`: helper PF وضعیت‌های `finite`، `no_losses` و `no_usable_pnl` را ارائه می‌کند؛ `calculate_basic_metrics` نیز status را بازمی‌گرداند.
- `backend/app/services/version_score.py`: PF score بر status تکیه می‌کند؛ مقدار sentinel legacy به‌عنوان اندازه‌گیری وارد امتیاز نمی‌شود. `no_losses` امتیاز PF=100، `no_usable_pnl` امتیاز PF=0 و `finite` طبق نسبت محدودشده به ۰..۱۰۰ امتیاز می‌گیرد.
- `backend/app/services/analysis_service.py`: status و دادهٔ پایهٔ PF به Comparison منتقل شدند؛ خطا/`no_data` در best و rank معتبر شرکت نمی‌کند؛ tie، ترتیب ثابت و توضیح ضعف/محدودیت داده افزوده شد.
- `backend/app/api/analytics.py`: metadata `best_ties` برای مصرف‌کننده‌های legacy best حفظ‌شده اضافه شد.
- `frontend/src/api/client.ts`, `frontend/src/pages/ComparisonPage.tsx`: نمایش «بدون باخت»/بدون PnL قابل استفاده بر اساس status، تشخیص چند برندهٔ هم‌رتبه و نمایش PF score/status.
- `frontend/src/pages/StrategyPage.tsx`: برچسب aggregate و scope، آمار test type، برچسب صادقانهٔ شاخص PnL معامله و PF وضعیت‌دار.
- تست‌ها: `backend/tests/test_metrics.py`, `test_phase48a_comparison.py`, `test_phase52_score_v2.py`, `test_phase53_strategy_stats.py`; تست جدید `frontend/src/__tests__/comparisonPage.stage3.test.tsx`.
- فایل‌های Stage 1/2 و تغییرات موجود workspace حفظ شدند. Dashboard و Finance و schema/migration دست‌نخورده‌اند.

### تکمیل پذیرش #10 و #25 (۲۰۲۶-۱۰-۱۲)

- **PF precision:** gross sums بدون گردکردن در مسیر `calculate_basic_metrics` و Analysis نگه داشته می‌شوند؛ PF قبل از گردکردن presentation محاسبه می‌شود. Regression برای +1.004 و -0.006 USDT مقدار PF=167.33 را در Comparison ثبت می‌کند. Strategy و Analysis از net PnL دقیق tradeها استفاده می‌کنند و Comparison filtered نیز از محاسبهٔ زندهٔ همان trades بهره می‌برد.
- **Legacy metadata:** وقتی gross sums/status در snapshot تازه موجود نباشد، Comparison از trades بستهٔ همان version/test_type و همان symbol/date filters (در صورت وجود) محاسبه می‌کند. Freshness guard قبل از repair اجرا می‌شود و snapshot کهنه همچنان رد می‌شود. اگر gross sums قابل بازیابی نباشند، `profit_factor_status=unavailable` و PF score خنثی ۵۰ خواهد بود. دادهٔ واقعی صفر سود/زیان همچنان `no_usable_pnl` و امتیاز صفر می‌گیرد. اعداد 100/999 بدون status دیگر برای `no_losses` تفسیر نمی‌شوند؛ numeric-only legacy به‌عنوان مقدار finite سازگار محاسبه می‌شود. فیلد عددی no-loss همچنان sentinel compatibility است و status مرجع است.
- **PF charts:** Bar و Radar مقدار غیر-finite (`no_losses`, `no_usable_pnl`, `unavailable`) را به gap نگاشت می‌کنند. Radar محور PF را فقط در صورت وجود دست‌کم یک PF finite درج می‌کند؛ PF finite=0 همچنان مقدار اندازه‌گیری‌شدهٔ صفر است و با gap اشتباه نمی‌شود.
- **Tie explanations:** tie-break فقط پس از Score با وضعیت/مقدار finite PF و سپس حجم نمونه مرتب می‌کند؛ مقدار PF برای non-finite در sorting مصرف نمی‌شود. توضیح معیار تعیین‌کننده بعد از تولید دلایل عادی append می‌شود و در خروجی API می‌ماند. full tie دارای Score/PF/sample یکسان بر اساس input order برندهٔ یکتا نمی‌سازد و `best_ties` مشترک باقی می‌ماند. تست backend از Comparison endpoint واقعی مقدارهای PF 6 و 8 و تصمیم حجم نمونه را بررسی می‌کند؛ تست UI نمایش متن بازگشتی و تست Radar تبدیل واقعی داده را بررسی می‌کنند.
- **Cleanup:** کلید تکراری `profit_factor_status` در `strategies.py` و `analysis_service.py` حذف شد. empty summary status در Strategy همچنان `no_usable_pnl` است.
- **تست‌های افزوده:** fractional-USDT PF، legacy snapshot recovery، PF score legacy finite=2، unknown PF status، full tie reversed، explanation از response واقعی API برای PF/sample، نمایش explanation در UI، و رفتار واقعی تبدیل دادهٔ Radar برای PF finite/missing.

## قرارداد متریک و رتبه

- Aggregate فعالیت برای سازگاری باقی است؛ دادهٔ عملکرد فقط به‌عنوان خلاصهٔ تاریخی ترکیبی گزارش می‌شود. «per_version» و `by_test_type` دامنهٔ روشن دارند؛ معاملات حذف/دوباره‌شماری نشده‌اند. تجمیع همچنان portfolio/equity واقعی نیست.
- PF از PnL خالص تاریخی موجود (که شامل اجزای net سیستم است) به دست می‌آید؛ PF وضعیت‌دار مرجع است. فیلد عددی legacy برای سازگاری نگه داشته شده؛ در مسیرهای قدیمی ممکن است sentinel `999` باقی باشد، ولی مصرف‌کنندگان فعلی Strategy/Comparison status را برای نمایش و Score می‌خوانند.
- Statusها: نسبت finite واقعی؛ `no_losses` یعنی سود با صفر زیان (نمایش «بدون باخت»، نه مقدار بی‌نهایت عددی)؛ `no_usable_pnl` یعنی سود و زیان قابل استفاده صفر/داده خالی. در Score، به‌ترتیب نسبت، امتیاز سقف PF=100، و امتیاز PF=0. هیچ وابستگی به sentinel برای تعیین امتیاز وجود ندارد.
- `sharpe_ratio` legacy حذف نشده؛ `sharpe_ratio_measure=trade_pnl_mean_std_sqrt_n`. فرمول همان میانگین PnL هر معامله / انحراف معیار نمونه‌ای × √تعداد معاملات است؛ Sharpe بازده دوره‌ای یا annualized نیست. UI با عنوان «شاخص PnL معامله» و توضیح فرمول نشان می‌دهد.
- رتبه‌بندی: معیار اصلی Score؛ سپس وضعیت/مقدار PF و تعداد معاملات به‌عنوان معیارهای ثانویهٔ صریح؛ شناسهٔ نسخه فقط ترتیب قطعی ایجاد می‌کند و tie را نمی‌شکند. رتبه‌های مساوی metadata `rank_tie`, `tie_count` دارند؛ `best` legacy به اولین عضو مرتب‌شده اشاره می‌کند و `best_ties` همهٔ هم‌برندگان را دارد. خطا، `missing_analysis` و `no_data` بدون رتبه/eligibility هستند. Tie کامل ورودی‌ناوابسته است.
- توضیحات می‌گویند معیارهای روشن، ضعف Expectancy و محدودیت DD/R؛ برچسب «عملکرد نزدیک» حذف شد. Stage 2 gross-price-R eligibility و neutral fallbackها بدون تغییر مفهومی حفظ شدند.

## اعتبارسنجی اجراشده

Backend از `C:\MokTradeDesk\backend`:

```text
.\venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_phase53_stale_analysis.py tests/test_phase53_strategy_stats.py tests/test_closed_trades_only.py tests/test_phase53_real_comparison.py tests/test_phase52_score_v2.py tests/test_phase48a_score.py tests/test_phase48a_comparison.py tests/test_phase48a_rank.py tests/test_metrics.py
88 passed, 9 warnings in 7.78s
```

Warnings، deprecationهای موجود FastAPI/Starlette، Pydantic و SQLAlchemy هستند.

Frontend از `C:\MokTradeDesk\frontend`:

```text
npx vitest run --pool=forks --maxWorkers=1
9 files passed, 94 tests passed (25.28s)

npm run build
TypeScript و Vite production build موفق
```

Lint هدفمند:

```text
npx eslint src/pages/ComparisonPage.tsx src/pages/StrategyPage.tsx src/__tests__/comparisonPage.stage3.test.tsx
ناموفق: 9 خطای no-explicit-any و 1 warning در فایل‌های frontend هدف
```

این lint findingها از baseline موجود همان فایل‌هاست؛ به‌عنوان خطای تازهٔ Stage 3 معرفی نمی‌شوند. `git diff --check` بدون خطا اجرا شد.

## سازگاری و ریسک‌های باقی‌مانده

- فیلد PF عددی legacy برای API compatibility باقی است؛ مصرف‌کنندگان خارج از این مسیر که status را نخوانند ممکن است sentinel قدیمی را همچنان به‌صورت عدد تعبیر کنند. مهاجرت به API/status-only نیازمند نسخه‌بندی جداست.
- `best` همچنان یک مورد است تا مصرف‌کنندگان قدیمی نشکنند؛ tie-aware مصرف‌کنندگان باید `best_ties` یا `rank_tie` را بخوانند. UI Comparison این را انجام می‌دهد.
- آمار aggregate تاریخی ترکیبی همچنان ممکن است توالی معاملات ناهم‌زمان/نسخه‌های جایگزین و انواع تست متفاوت را ترکیب کند؛ آن را نباید equity، بازده یا عملکرد پرتفوی تفسیر کرد.
- Sharpe-like legacy صرفاً نام‌گذاری و metadata آن اصلاح شد؛ مدل بازده دوره‌ای جدید ساخته نشد.
- lint هدفمند موفق نیست (۹ خطا، ۱ هشدار). کل lint پروژه در این Stage اجرا نشد.
- هیچ migration، commit، push یا عملیات remote انجام نشد. Stage 3 در این گزارش متوقف می‌شود.

## نتایج follow-up پذیرش

Backend از `C:\MokTradeDesk\backend`:

```text
.\venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_phase48a_comparison.py tests/test_phase52_score_v2.py tests/test_metrics.py tests/test_phase53_strategy_stats.py tests/test_phase53_stale_analysis.py tests/test_closed_trades_only.py tests/test_phase53_real_comparison.py tests/test_phase48a_score.py tests/test_phase48a_rank.py
94 passed, 9 warnings in 5.61s
```

Frontend از `C:\MokTradeDesk\frontend`:

```text
npm run build
TypeScript و Vite production build موفق (اجرا نهایی: 4.23s)

npx vitest run --pool=forks --maxWorkers=1 --reporter=dot
10 files passed, 97 tests passed (43.05s)
```

Lint هدفمند follow-up:

```text
npx eslint src/pages/ComparisonPage.tsx src/components/charts/ComparisonBarChart.tsx src/utils/comparisonChartData.ts src/__tests__/comparisonPage.stage3.test.tsx src/__tests__/comparisonChartData.stage3.test.ts
ناموفق: 3 error و 1 warning؛ شامل `no-explicit-any` موجود در chart و ComparisonPage و hook ordering/useEffect warning موجود در ComparisonPage. lint موفق گزارش نمی‌شود.
```

`git diff --check` موفق بود. اجرای هم‌زمان pytest در مرحلهٔ عیب‌یابی یک failure ناپایدار در stale GET نشان داد؛ اجرای مجزای همان regression و اجرای suite نهایی ترتیبی همگی موفق بودند. Regression مربوط به equal-score که علاوه بر helper مقایسهٔ مقدارها، response واقعی Comparison را validate می‌کند در `test_equal_score_secondary_reason_and_full_tie_survives_reverse` ثبت است.
## Freshness regression acceptance correction (2026-10-12)

This is a **regression in preserved Stage 1 behavior**, not a Stage 4 task. The reviewer reproduced `test_stale_after_time_edit` and `test_stale_after_pnl_edit` as 93 passed / 1 failed on each of two independent runs (404 expected, 200 received).

Root cause: Stage 1's freshness predicate compared closed-trade count and only rejected when `max(Trade.updated_at) > AnalysisResult.created_at`. SQLAlchemy `onupdate` uses wall-clock `datetime.now`, while timestamp resolution/storage and transaction timing can produce equal timestamps; the strict less-than check therefore accepted changed data at equality. The check did not validate trade content. Existing timestamp ordering remains in place, with a SHA-256 signature of each version analysis's closed trade IDs, PnL, commission, swap, and close_time stored in the existing AnalysisRun JSON `filters_snapshot`; GET and filtered/unfiltered Comparison share `check_analysis_freshness` and now compare that signature too. Legacy runs without the additional JSON key retain timestamp/count behavior; no migration or historical rewrite is required. Closed scope and explicit test_type filtering are unchanged.

Deterministic PnL and close-time regressions force the trade update timestamp to equal the result's stored timestamp and require stale responses via both GET routes and both Comparison query forms. Existing unchanged-data test remains fresh. An initial test iteration failed because Comparison requires >=2 versions and the result does not expose `stale` for successful entries; tests were adjusted using the existing endpoint contract. A subsequent test iteration exposed a missing `AnalysisResult` import; fixed. These are test-authoring failures, not hidden; final checks below supersede them.

Validation (backend venv, `C:\\MokTradeDesk\\backend`):

```text
Initial targeted freshness tests before correction: 2 passed (did not trigger clock collision).
Initial expanded freshness test run: 3 failed — invalid one-version Comparison request (422).
Second expanded freshness run: 3 failed — success-entry assertion incorrectly expected a stale key.
Next run: 2 failed — test missing AnalysisResult import (NameError).
Final freshness file: .\\venv\\Scripts\\python.exe -m pytest -p no:cacheprovider tests/test_phase53_stale_analysis.py -q
17 passed (existing deprecation warnings).
Reported backend suite: .\\venv\\Scripts\\python.exe -m pytest -p no:cacheprovider tests/test_phase48a_comparison.py tests/test_phase52_score_v2.py tests/test_metrics.py tests/test_phase53_strategy_stats.py tests/test_phase53_stale_analysis.py tests/test_closed_trades_only.py tests/test_phase53_real_comparison.py tests/test_phase48a_score.py tests/test_phase48a_rank.py -q
94 passed (existing deprecation warnings).
Repeated relevant stability run: PnL-edit, close-time-edit and unchanged-data tests run three consecutive times; 3 passed on each run.
```

No Stage 4, Dashboard/Finance changes, migration, commit, or remote action. Existing workspace edits were preserved.
