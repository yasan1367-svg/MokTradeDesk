# PHASE 48a — مقایسه و رتبه‌بندی Versionها (گزارش نهایی)

> بازهٔ commit: `dd45c73 → f985f91` · وضعیت: ✅ کامل و **push شده**
> دامنه: Backend (مقایسه/رتبه‌بندی + تحلیل زمانی) + Frontend (`ComparisonPage`)

---

## ۱) خلاصهٔ اجرایی

Phase 48a قرار بود «مقایسهٔ Versionها + فیلتر + رتبه‌بندی ساده» را از حالت شکسته به یک قابلیت
قابل‌اتکا برساند. در عمل **یک باگ P0** (مقایسه همیشه خالی) + یک باگ تصمیم‌گیری نامعین (`GET`) رفع شد،
قرارداد مقایسه **بازطراحی تمیز** شد (Score/Rank/Reasons)، تحلیل زمانی به **زمان ورود** منتقل شد،
و فرانت با قرارداد جدید هم‌آهنگ شد.

| KPI | نتیجه |
|---|---|
| pytest (backend) | **۳۷۳ passed** |
| ruff | **All checks passed!** |
| tsc | **EXIT=0** |
| vitest | **۹ passed** (۲ فایل) |
| build | **EXIT=0** (✓ built in 3.07s) |
| تست جدید backend | **+۱۶** (۳۵۷ → ۳۷۳) |
| تست جدید frontend | ۰ (تست‌های موجود دست‌نخورده) |

---

## ۲) تسک‌ها

### ۴۸a.۱ — رفع باگ `scope_key` در `compare_versions` + قرارداد جدید
- **باگ:** `compare_versions` کلید legacy `str(version_id)` را می‌خواند، ولی
  `analyze_version(test_type=...)` با `version_scope_key` = `"12:BACKTEST"` ذخیره می‌کرد
  ⇒ مقایسه **همیشه خالی** بود.
- **Fix:** lookup با `version_scope_key(vid, test_type)` + fallback به کلید legacy (`str(vid)`)
  برای سازگاری با رکوردهای قدیمی.
- **قرارداد جدید:** `{comparison, test_type, filters, best}` — هر item: `version_id`, `rank`, `score`,
  `metrics`, `reasons[{icon,text}]`, `error?`.
- **فیلترها:** `symbol`, `date_from`, `date_to` (بازهٔ تاریخ **شامل آخرین روز**، روی `open_time`).
- **حذف dead code:** متد قدیم `compare_versions` + `_build_reasons` + `_find_symbol_bests` +
  `_find_detail_bests` + `_calculate_score` و اسکیماهای `VersionComparison*`/`SkippedItem`/`SymbolBest`/`DetailBests`
  (**۴۲۷ خط حذف**).
- **`version_score.py` جدید:** `calculate_version_score` — WR ۳۵٪ + PF ۳۵٪ + NetPnL ۳۰٪ − DD penalty ۲۰٪ (کلمپ ۰..۱۰۰).
- **تست‌ها:** +۶ (`test_phase48a_comparison.py`) + آپدیت ۳ تست `test_phase41_compare.py`.

### ۴۸a.۲ — `GET /api/analytics/{version_id}` قطعی
- **باگ:** `.first()` روی `AnalysisResult.version_id` وقتی نسخه هم Backtest و هم Forward داشت ⇒ نتیجهٔ **نامعین**.
- **Fix:** پارامتر `test_type` (پیش‌فرض `BACKTEST`) + lookup با `version_scope_key` + fallback قطعی
  (`.order_by(AnalysisResult.id.desc())`). گارد سازگاری فاز ۱۹ حفظ شد و **هم‌نوع با رکورد سرو‌شده** می‌شمارد
  (helper جدید `_tt_from_scope_key`).
- **تست‌ها:** +۲ (`test_phase48a_get_analysis.py`).

### ۴۸a.۳ — تحلیل زمانی روی `open_time`
- `_analyze_by_session` · `_analyze_by_weekday` · `_analyze_by_hour` · `_analyze_by_custom_intervals`
  همگی از `close_time` به **`open_time`** منتقل شدند (زمان ورود ملاک است).
- ℹ️ گارد «معاملات باز» هم به `open_time` منتقل شد ⇒ معاملات باز نیز در تحلیل زمانی لحاظ می‌شوند.
- ⚠️ تحلیل‌های ذخیره‌شدهٔ قبلی مقدار قدیمی دارند ⇒ برای نتیجهٔ جدید «تحلیل مجدد» لازم است.
- **تست‌ها:** +۳ (`test_phase48a_time_analysis.py`).

### ۴۸a.۴ — تست‌های Score
- ماژول `version_score.py` در 48a.1 ساخته شده بود؛ این تسک فقط تست است.
- **تست‌ها:** +۴ (`test_phase48a_score.py`) — perfect=۱۰۰ · zero=۰ · high-DD penalty (۲۷.۵ → ۱۷.۵) · clamp ۰..۱۰۰.

### ۴۸a.۵ — `POST /api/analytics/rank`
- endpoint رتبه‌بندی: `{ranking, best}` (مرتب نزولی بر اساس Score).
- **تست‌ها:** +۱ (`test_phase48a_rank.py`) — ۳ نسخه با ترتیب ورودی به‌هم‌ریخته ⇒ اثبات مرتب‌سازی `[good, mid, bad]`.

### ۴۸a.۶ — فرانت `ComparisonPage` + `client.ts`
- **`client.ts`:** + `CompareRequest`/`Reason`/`VersionComparisonItem`/`CompareResponse`/`RankResponse`
  و `compareVersions`/`rankVersions`؛ − `compareVersionsWithDetails` و `min_trades`.
- **`ComparisonPage.tsx`:** بازنویسی کامل (۶۷۱ → ۵۲۹ خط):
  فیلتر Test Type/نماد/تاریخ · نگاشت `version_id → «استراتژی / نسخه»` · جدول رتبه‌بندی
  (rank/score/metrics/reasons) · نمایش `error` نسخهٔ تحلیل‌نشده · کارت «🏆 بهترین نسخه» با `best.score` ·
  ۴ نمودار Bar + ۱ Radar (با آرایهٔ مشتق‌شدهٔ flat — **بدون تغییر کامپوننت‌های چارت**) · Drawer دلایل (icon+text) ·
  حالت‌های `Skeleton`/`EmptyState`/`toast`.
- **گزارش تفصیلی:** `PHASE48A_6_FRONTEND.md`.

---

## ۳) تست‌ها (تعداد جدید)

| فایل | جدید |
|---|---|
| `tests/test_phase48a_comparison.py` | ۶ |
| `tests/test_phase48a_get_analysis.py` | ۲ |
| `tests/test_phase48a_time_analysis.py` | ۳ |
| `tests/test_phase48a_score.py` | ۴ |
| `tests/test_phase48a_rank.py` | ۱ |
| `tests/test_phase41_compare.py` | (آپدیتِ ۳ تست موجود، بدون افزایش) |
| **جمع جدید** | **+۱۶** |

**روند شمارش:** ۳۵۷ (پایان 47a) → **۳۷۳** (پایان 48a).
Frontend: `9 passed` (بدون تغییر) — هیچ تستی برای `ComparisonPage` وجود نداشت و نیازی به افزودن نبود.

---

## ۴) فایل‌های تغییر یافته (در ۷ commit فاز 48a)

**Backend — کد:**
- `M backend/app/api/analytics.py` (compare جدید، rank جدید، `GET /{version_id}` قطعی)
- `M backend/app/schemas/analytics.py` (`CompareRequest` جای قرارداد قدیم)
- `M backend/app/services/analysis_service.py` (`compare_versions` + helpers، `open_time`، حذف ۴۲۷ خط dead code)
- `A backend/app/services/version_score.py`

**Backend — تست:**
- `M backend/tests/test_phase41_compare.py`
- `A backend/tests/test_phase48a_comparison.py`
- `A backend/tests/test_phase48a_get_analysis.py`
- `A backend/tests/test_phase48a_time_analysis.py`
- `A backend/tests/test_phase48a_score.py`
- `A backend/tests/test_phase48a_rank.py`

**Frontend:**
- `M frontend/src/api/client.ts`
- `M frontend/src/pages/ComparisonPage.tsx`

**سایر:**
- `M .gitignore` (`*.db-wal`, `*.db-shm`)
- `A PHASE48A_6_FRONTEND.md`

---

## ۵) نکات باقی‌مانده

1. **`getAnalysis()` در `client.ts` (`GET /api/analytics/{id}`) هنوز `test_type` نمی‌فرستد.**
   بک‌اند پیش‌فرض `BACKTEST` دارد، پس برای بکتست درست است ولی برای **فوروارد** نتیجهٔ درست نمی‌دهد
   ⇒ بهتر است امضا به `getAnalysis(versionId, testType?)` تغییر کند و مصرف‌کننده‌ها (صفحهٔ تحلیل) آن را پاس دهند.
2. **پایداری فیلترها در URL نیست.** `symbol`/`date_from`/`date_to`/`test_type`/انتخاب نسخه‌ها در URL ذخیره
   نمی‌شوند ⇒ refresh = از دست رفتن فیلترها. (خارج از دامنهٔ پلن 48a.)
3. **`reasons` فرمت `{icon, text}[]`** است (تصمیم «گزینه الف») — اگر بعداً به دسته‌بندی
   `{strengths, weaknesses, comparisons}` نیاز شد، تغییر فقط در `generate_reasons` + Drawer است.
4. **تحلیل‌های ذخیره‌شدهٔ قبل از 48a.3** (session/weekday/hour بر پایهٔ `close_time`) برای دیدن مقدار جدید
   نیاز به **«تحلیل مجدد»** دارند.
5. موارد **عمداً skip شدهٔ Phase 48a:** Sharpe/Sortino/RoR · Health Score پیچیده · ML Ranking ·
   مقایسهٔ ۱۰+ استراتژی · Comparison Snapshot · E2E/Hypothesis Test.

---

## ۶) آماده برای Phase 50

- قرارداد مقایسه/رتبه‌بندی **تک‌منبعی و تست‌شده** است: `/api/analytics/compare` + `/api/analytics/rank`.
- Score سادهٔ واحد در `app/services/version_score.py` (قابل استفاده در داشبورد/گزارش‌ها).
- فرانت با تایپ‌های typed (`CompareResponse`/`RankResponse`) به بک‌اند متصل است.
- هیچ migration جدیدی لازم نشد (فاز 48a فقط کد بود) و working tree تمیز است.

---

## ۷) commitهای فاز 48a

```
f985f91  Phase 48a.6: rewrite ComparisonPage for new compare contract + report
57aa035  Phase 48a.6: frontend client types (compare/rank) + remove legacy min_trades
ccebf71  Phase 48a.5: POST /analytics/rank endpoint + test
4d2014b  Phase 48a.4: Score tests (4 tests, incl. clamp 0..100)
7ae3f0a  Phase 48a.3: Time analysis on open_time (session/weekday/hour/custom)
9d40365  Phase 48a.2: Fix non-deterministic GET /analytics/{version_id} + test_type param + 2 tests
da95110  Phase 48a.1: Fix scope_key bug in compare + remove dead code + new contract + 6 tests
```

