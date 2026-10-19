# گزارش مرحلهٔ چهارم اصلاح Strategy / Comparison

**تاریخ:** ۲۰۲۶-۱۰-۱۲  
**دامنه:** یافته‌های #12 تا #17 و اصلاح مرز Session برای #16. Stageهای 1–3 حفظ شده‌اند؛ Stage 5 آغاز نشده است.
**قرارداد محصول:** ژورنال تاریخی معاملات بسته، همهٔ حساب‌ها/معاملات USDT؛ بدون معاملهٔ باز/زنده، PnL شناور، تبدیل ارز یا net R استنباطی.

## فایل‌های تغییرکرده در Stage 4

- `backend/app/api/strategies.py`: اعتبارسنجی نام/برچسب/status در create، PATCH و Fork؛ پاسخ Conflict حذف Strategy با وابستگی fork؛ تبدیل رد حذف Version دارای معامله به 409.
- `backend/app/schemas/analytics.py`: اعتبارسنجی Compare IDs، نوع تست و تاریخ/زمان ISO.
- `backend/app/api/analytics.py`: وجودسنجی ID پیش از مقایسه/رتبه‌بندی، نرمال‌سازی date bounds و رد بازهٔ معکوس.
- `backend/app/services/analysis_service.py`: مالکیت transaction پیش از query در Version/Personal/Prop و cleanup بدون معامله، transaction/savepoint جایگزینی تحلیل، provenance، fingerprint نسخه‌دار و freshness قواعد.
- `backend/app/models/strategy.py`: اصلاح توضیح نادرست `updated_at`؛ timestamp تضمین monotonic بودن ندارد.
- `backend/tests/test_strategy_stage4_contracts.py`: رگرسیون‌های API validation، Fork، Compare و deletion.
- `backend/tests/test_analysis_stage4_atomicity.py`: rollback/failure injection، provenance/fingerprint، isolation و SQLite چند-session.
- `STRATEGY_FIX_STAGE4.md`: این گزارش.

سایر تغییرات محلی موجود در Stageهای پیشین (از جمله `metrics.py`، `version_score.py`، UI و گزارش‌های Stage 1–3) در workspace از قبل وجود داشتند و در این مرحله بازنویسی نشدند.

## وضعیت یافته‌ها

| یافته | وضعیت | قرارداد/رفتار اعمال‌شده |
|---|---|---|
| #12 ورودی Strategy/Version | اصلاح شد | name و version label trim می‌شوند؛ blank و status نامعتبر با 422 رد می‌شوند. `real` صریحاً legacy VERSION LABEL است و ذخیره می‌شود؛ به real_personal/real_prop نگاشت نمی‌شود و scope معاملات را تغییر نمی‌دهد. label ناشناخته همچنان 422 است. PATCH omission semantics را نگه می‌دارد. |
| #13 فیلتر Comparison | اصلاح شد | نوع صریح فقط BACKTEST/FORWARD/REAL_PERSONAL/REAL_PROP (حروف کوچک/بزرگ پذیرفته)؛ مقدار invalid به legacy تبدیل نمی‌شود. تاریخ ISO ناممکن/خراب و بازهٔ معکوس 422 است. end-date همچنان شامل روز آخر و semantics timezone قبلی Tehran/UTC دست‌نخورده است؛ اصلاح گسترده timezone به Stage 6 واگذار است. test_type در Comparison اختیاری/legacy-compatible باقی است. |
| #14 شناسه‌ها | اصلاح شد | IDs باید مثبت، یکتا و ۲ تا ۱۰ عدد باشند؛ malformed/duplicate با 422. نسخهٔ ناموجود پیش از رتبه‌بندی 404 می‌دهد؛ نسخهٔ موجودِ بدون تحلیل همچنان item دارای `missing_analysis`/error است. سقف API برابر ۱۰ حفظ شد. UI limit=5 است و اینجا گسترش نیافت. |
| #15 حذف امن | اصلاح شد | Trade/Result/Run/Scope و fork وابسته مانع حذف هستند؛ conflict با 409 و پیام توضیحی. حذف Version واقعاً بدون وابستگی موفق است. هیچ cascade تاریخی یا archive جدیدی اضافه نشد. |
| #16 جایگزینی اتمیک | اصلاح شد | مالکیت transaction در ابتدای Version/Personal/Prop، پیش از SELECTهای autobegin، ثبت می‌شود. تحلیل موفق و cleanup نتیجهٔ کهنه در Session سرویس‌مالک persist می‌شوند؛ transaction صریح caller-owned همچنان کنترل caller است و rollback، create/replacement/cleanup را undo می‌کند. failure نتیجهٔ قبلی و Run/scope تاریخی را حفظ می‌کند. آزمون independent Session/API افزوده شد. |
| #17 provenance/freshness | اصلاح شد | در `AnalysisRun.filters_snapshot` متن rules_note و hash پایدار، scope/type، engine version، policy Score و fingerprint format ذخیره می‌شوند. fingerprint فرمت ۳، trade ID/PnL/commission/swap/R/symbol/open_time/close_time را می‌سنجد. fingerprint فرمت قدیمی/ناشناخته یا snapshot فاقد fingerprint fresh اعلام نمی‌شود؛ re-analysis لازم است. Runهای قدیمی rewrite نمی‌شوند و legacy بودنشان ضمنی به‌عنوان provenance کامل تلقی نمی‌شود. |

## حذف

سیاست مشترک حذف، تاریخچهٔ نسخه را حتی پس از پاک‌شدن معاملات و نتیجهٔ جاری محافظت می‌کند. Strategy دارای fork child، تحلیل، scope یا معامله 409 می‌دهد. Version دارای معامله/نتیجه/Run/scope/fork نیز 409 می‌دهد. آزمون حذف dependency-free Version و Strategy موجود است. وابستگی‌های میان‌جدولی هیچ‌گاه cascade و بی‌صدا پاک نمی‌شوند.

## Transaction و هم‌زمانی

Session فاقد transaction فعال: سرویس transaction را مالک می‌شود و commit/rollback می‌کند. Session دارای transaction: از nested transaction/savepoint استفاده می‌شود و مالکیت transaction بیرونی به caller واگذار می‌شود. آزمون failure injection در flush میانی ثابت می‌کند نتیجه، Run و Scope قبلی باقی می‌مانند.

دیتابیس پشتیبانی‌شدهٔ پروژه SQLite با WAL و busy timeout است. آزمون concurrency از دو Session مستقل روی فایل SQLite واقعی و barrier استفاده می‌کند، نه StaticPool مشترک یا sleep. SQLite ممکن است یکی از writerها را serialize یا با lock رد کند؛ در هر دو حالت خطا rollback می‌شود، نتیجهٔ جاری یکتا می‌ماند و Run قبلی حذف نمی‌شود. این آزمون تضمین fairness/موفقیت هر دو writer را ادعا نمی‌کند.

## سیاست provenance و legacy

- `analysis_engine_version=analysis-engine-1` و `score_policy_version=score-policy-2` در اجرای جدید ثبت می‌شوند.
- hash از JSON canonical شامل `rules_note` با `sort_keys`/separator ثابت ساخته می‌شود؛ تغییر قواعد، تحلیل را stale می‌کند.
- `rules_note` تنها منبع قواعد موجود در مدل فعلی است؛ Rule Builder یا جدول قواعد وجود ندارد.
- Comparison همچنان Score جاری را طبق سیاست پذیرفته‌شده Stage 2/3 محاسبه می‌کند؛ Score فعلی با Score تاریخی snapshot یکی فرض نمی‌شود.
- legacy snapshotها بدون migration/بازنویسی باقی می‌مانند. نبود fingerprint/فرمت سازگار صریحاً نیاز به تحلیل مجدد دارد؛ تاریخچهٔ نامعلوم به‌عنوان current تأیید نمی‌شود.
- زمان‌ها در fingerprint با microsecond precision `isoformat()` سریال می‌شوند؛ `open_time` ویرایش‌شده نیز تغییر fingerprint ایجاد می‌کند. `updated_at` فقط heuristic است و fingerprint محتوایی مرجع تشخیص ویرایش‌های هم‌زمان timestamp است.

## قرارداد خطا

- **422:** ورودی schema نامعتبر، blank name/label، status/test type ناشناخته، ID نامثبت/تکراری، تاریخ خراب/ناممکن یا بازهٔ معکوس.
- **404:** نسخه ناموجود در Compare/Rank؛ نسخه موجود ولی بدون تحلیل به‌صورت item-level missing-analysis؛ تحلیل stale/legacy بدون fingerprint از GET با پیام تحلیل مجدد.
- **409:** حذف Strategy/Version دارای وابستگی تاریخی، trade یا fork.
- ورودی CRUD نامعتبر پیش از persist رد می‌شود؛ عدم تغییر جزئی با regression API بررسی شده است.

## اعتبارسنجی اجراشده

از `C:\MokTradeDesk\backend`:

```text
 .\venv\Scripts\python.exe -m py_compile app\services\analysis_service.py app\api\analytics.py app\api\strategies.py app\schemas\analytics.py app\models\strategy.py tests\test_strategy_stage4_contracts.py tests\test_analysis_stage4_atomicity.py tests\test_analysis_scope.py tests\test_phase48a_get_analysis.py
موفق

 .\venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_strategy_stage4_contracts.py tests\test_analysis_stage4_atomicity.py tests\test_phase53_stale_analysis.py tests\test_phase53_delete_safety.py tests\test_phase48a_comparison.py tests\test_phase52_score_v2.py tests\test_metrics.py tests\test_phase53_strategy_stats.py tests\test_closed_trades_only.py tests\test_phase53_real_comparison.py tests\test_phase48a_score.py tests\test_phase48a_rank.py tests\test_phase48a_get_analysis.py tests\test_analysis_scope.py -q --tb=short
  128 passed؛ هشدارهای deprecation موجود FastAPI/Starlette/Pydantic/SQLAlchemy

Set-Location C:\MokTradeDesk; git diff --check
موفق، بدون خطا
```

Suite تجمیعی بالا شامل `tests/test_analysis_scope.py`, `tests/test_analysis_stage4_atomicity.py`, `tests/test_strategy_stage4_contracts.py` و رگرسیون‌های Stage 1–3 است: **128 passed**. تست‌های independent Session برای تحلیل Personal/Prop و cleanup پس از حذف معاملات افزوده شدند. create و fork payload فعلی UI با `test_type="real"` و رد BOGUS آزموده شدند. GET بی‌نوع latest-result را می‌دهد؛ GET صریح فقط scope همان نوع را می‌خواند. `py_compile` از اجرای قبلی برقرار است؛ این نوبت suite تجمیعی و `git diff --check` موفق شدند.

## ریسک‌های باقی‌مانده

1. کاربر دارای analysis snapshot قدیمی بدون fingerprint format سازگار باید آن را دوباره تحلیل کند؛ دادهٔ تاریخی بازنویسی نمی‌شود.
2. SQLite هم‌زمانی را با lock/serialization مدیریت می‌کند؛ تضمین هم‌زمانی خطی‌پذیرِ مستقل از backend ادعا نشده است.
3. Rules snapshot فقط `rules_note` موجود را می‌تواند ثبت کند؛ structured rules در مدل فعلی وجود ندارد.
4. GETهای بی‌نوع همچنان latest-result سازگارند و ممکن است آخرین snapshot از نوع Backtest یا Forward باشد؛ مصرف‌کننده‌ای که isolation می‌خواهد باید `test_type` صریح ارسال کند.
5. هیچ فایل frontend در این اصلاح تغییر نکرد؛ frontend suite/build اجرا نشد. UI همچنان «real» را می‌فرستد و API اکنون آن را صرفاً به‌عنوان version label legacy می‌پذیرد. روشن‌سازی وسیع‌تر label در برابر trade scope به Stage 5 finding #18 موکول است.

هیچ migration، Dashboard/Finance edit، commit، push، reset، revert یا remote operation انجام نشد. پایان کار در Stage 4 برای بازبینی است.