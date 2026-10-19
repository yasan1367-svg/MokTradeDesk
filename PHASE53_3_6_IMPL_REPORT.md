# PHASE 53.3 → 53.6 — همهٔ باگ‌های باقی‌مانده

> **تاریخ:** ۱۴۰۵/۰۷/۱۱ · **وضعیت:** ✅ پیاده‌شده · ⛔ آمادهٔ commit (منتظر تأیید کاربر)
> **مبنا:** Phase 53.2 = `0e2e9e3` · **بدون migration جدید**

---

## ۱) خلاصهٔ اجرایی

| زیرفاز | موضوع | وضعیت |
|:--|:--|:--|
| **53.3** | R از Initial SL (Soft4X) + آمار مادر (تجمیعی + per-version) | ✅ |
| **53.4** | مقایسهٔ REAL_PERSONAL / REAL_PROP + فیلتر بر پایهٔ close_time | ✅ |
| **53.5** | Import حساب شخصی + PDF با test_type + حفظ فیلترها در CSV/PDF | ✅ |
| **53.6** | دکمهٔ اعلان 🔔 + خطاهای بی‌صدا + تنظیمات (Theme) + بکاپ با تصاویر | ✅ |

**نتیجهٔ کل:** `422 passed + 1 xfailed` (قبل: ۴۱۰ ⇒ **+۱۲**) · `TSC=0` · `vitest 29 passed` · `BUILD=0`.

---

## ۲) PHASE 53.3 — R از Initial SL + آمار مادر

### 53.3.1 — R از Initial SL
- `utils/trade_metrics.py::calculate_r_multiple(..., initial_sl=None)`: اگر `initial_sl` موجود باشد، ریسک بر پایهٔ آن (fallback به `sl`).
- `services/import_service.py` (Soft4X): ستون `Initial SL` خوانده میشود → `raw_data["initial_sl"]` + مبنای R.
- `services/import_engine.py::normalize_trade`: در نبود `r_multiple`، `initial_sl` از `raw_data` استفاده میشود.
- تست: `test_phase53_r_initial_sl.py` — `test_r_uses_initial_sl` · `test_r_fallback_to_sl`

### 53.3.2 — آمار استراتژی مادر
- `api/strategies.py`: helper مشترک `_summarize_trades()` (تجمیعی + per-version).
- خروجی `GET /api/strategies/{id}/stats`: افزودن `"scope": "aggregate"` + `"per_version": [...]` (کلیدهای قبلی دست‌نخورده).
- فرانت `StrategyPage.tsx`: برچسب «📊 تجمیعی (همهٔ N نسخه)» + بخش «🧩 تفکیک هر نسخه».
- تست: `test_phase53_strategy_stats.py` — `test_strategy_stats_aggregate_labeled` · `test_strategy_stats_per_version`

---

## ۳) PHASE 53.4 — مقایسهٔ Real

- `_calculate_filtered_metrics`: با `test_type` مشخص، **همان نوع** فیلتر میشود (نه فقط غیر-REAL) و بازهٔ تاریخ روی **`close_time`** اعمال میشود.
- `compare_versions`: برای `REAL_PERSONAL`/`REAL_PROP` **زنده** محاسبه میشود (بدون نیاز به `AnalysisResult` ذخیره‌شده).
- فرانت از قبل `REAL_PERSONAL`/`REAL_PROP` را در `COMPARISON_TEST_TYPES` داشت ⇒ بدون تغییر.
- تست: `test_phase53_real_comparison.py` — `test_compare_real_personal` · `test_compare_real_prop` · `test_compare_real_by_close_time`

---

## ۴) PHASE 53.5 — Import شخصی + PDF/CSV

### 53.5.1 — Import حساب شخصی
- بکاند از قبل `personal_trading_account_id` را در `/imports/preview` و `/imports/soft4x` می‌پذیرفت.
- فرانت `ImportPage.tsx`: گزینهٔ «💼 حساب شخصی» + انتخابگر نسخه + حساب شخصی (`getPersonalTradingAccounts`).
- تست: `test_phase53_import_export.py::test_import_real_personal`

### 53.5.2 — PDF با test_type
- `api/export.py::export_analysis_pdf`: پارامتر `test_type` (Backtest/Forward) → تحلیل + فیلتر معاملات مطابق آن.
- فرانت: `client.ts::exportAnalysisPdf(versionId, testType?)` + `AnalysisPage` مقدار scope را می‌فرستد.
- تست: `test_phase53_import_export.py::test_pdf_with_test_type`

### 53.5.3 — حفظ فیلترها در CSV/PDF
- `export.py`: `date_from/date_to` به `filter_by_range` منتقل شد (**شامل آخرین روز**، سازگار با بقیهٔ گزارش‌ها).
- فرانت `TradesPage.tsx::downloadExport`: ارسال `date_from`/`date_to`.
- تست: `test_phase53_import_export.py::test_export_preserves_filters`

---

## ۵) PHASE 53.6 — UI + تنظیمات + بکاپ

### 53.6.1 — دکمهٔ اعلان 🔔
- `App.tsx`: دکمهٔ 🔔 حالا به هشدارهای پراپ وصل است — نشانگر تعداد خوانده‌نشده (`getPropAlerts({unread_only:true})`) + کلیک ⇒ صفحهٔ پراپ.
- تست: endpoint `GET /api/prop/alerts` از قبل با `test_phase38_personal_finance.py` پوشش داشت (بدون تغییر بکاند).

### 53.6.2 — خطاهای بی‌صدا
- `FinancePage.tsx`: سه `catch { /* silent */ }` اصلی (گزارش‌ها/پیشرفته/فاز۲۲) حالا با `toast.error` نمایش داده می‌شوند.
- `JournalPage.tsx`: از قبل `error` state + نمایش خطا داشت (بدون تغییر).
- تست: پوشش فرانت (TSC) — این تغییر صرفاً UI است.

### 53.6.3 — تنظیمات بی‌اثر (Theme منبع یگانه)
- فایل جدید `frontend/src/utils/theme.ts`: `readStoredTheme` · `applyTheme` (کلاس `<html>` + localStorage + رویداد مشترک) · `resolveInitialTheme`.
- `App.tsx::useTheme` حالا از همین ابزار استفاده می‌کند و به `THEME_EVENT` گوش می‌دهد.
- `SettingsPage.tsx`: بارگذاری ⇒ اگر انتخاب محلی نبود تم API اعمال می‌شود؛ ذخیره ⇒ `applyTheme` فوری (همگام با App).
- تست: `test_phase53_backup_settings.py::test_settings_roundtrip` (پایداری theme/timezone/currency/calendar در API).

### 53.6.4 — بکاپ تصاویر
- `services/backup_service.py`: `create_backup_archive()` (zip شامل DB + `storage/screenshots/**`) و `restore_backup_archive()` (استخراج امن + بازیابی DB).
- `api/backup.py`: `POST /api/backup/archive` + `POST /api/backup/restore-archive/{filename}`.
- سازگاری: مسیرهای موجود (`create_backup`/`list_backups`/`restore_backup`/rotation) دست‌نخورده.
- تست: `test_phase53_backup_settings.py::test_backup_includes_screenshots`

---

## ۶) تست‌ها و اعتبارسنجی

```
Backend : 422 passed, 1 xfailed   (قبل: 410 · +12)
Frontend: TSC_EXIT=0 · vitest 29 passed · BUILD_EXIT=0
```

### ۱۲ تست جدید
| فایل | تعداد |
|:--|:--|
| `test_phase53_r_initial_sl.py` | ۲ |
| `test_phase53_strategy_stats.py` | ۲ |
| `test_phase53_real_comparison.py` | ۳ |
| `test_phase53_import_export.py` | ۳ |
| `test_phase53_backup_settings.py` | ۲ |

---

## ۷) آماده‌بودن برای commit

```
 M backend/app/api/backup.py
 M backend/app/api/export.py
 M backend/app/api/strategies.py
 M backend/app/services/analysis_service.py
 M backend/app/services/backup_service.py
 M backend/app/services/import_engine.py
 M backend/app/services/import_service.py
 M backend/app/utils/trade_metrics.py
 M frontend/src/App.tsx
 M frontend/src/api/client.ts
 M frontend/src/pages/AnalysisPage.tsx
 M frontend/src/pages/FinancePage.tsx
 M frontend/src/pages/ImportPage.tsx
 M frontend/src/pages/SettingsPage.tsx
 M frontend/src/pages/StrategyPage.tsx
 M frontend/src/pages/TradesPage.tsx
?? backend/tests/test_phase53_backup_settings.py
?? backend/tests/test_phase53_import_export.py
?? backend/tests/test_phase53_r_initial_sl.py
?? backend/tests/test_phase53_real_comparison.py
?? backend/tests/test_phase53_strategy_stats.py
?? frontend/src/utils/theme.ts
```

**پیشنهاد commit (پس از تأیید):**
```
git add backend/app/api/backup.py backend/app/api/export.py backend/app/api/strategies.py \
        backend/app/services/analysis_service.py backend/app/services/backup_service.py \
        backend/app/services/import_engine.py backend/app/services/import_service.py \
        backend/app/utils/trade_metrics.py backend/tests/test_phase53_*.py \
        frontend/src/utils/theme.ts frontend/src/api/client.ts frontend/src/App.tsx \
        frontend/src/pages/AnalysisPage.tsx frontend/src/pages/FinancePage.tsx \
        frontend/src/pages/ImportPage.tsx frontend/src/pages/SettingsPage.tsx \
        frontend/src/pages/StrategyPage.tsx frontend/src/pages/TradesPage.tsx

git commit -m "Phase 53.3-53.6: initial-SL R, per-version stats, real comparison, personal import, export filters, alerts/theme/backup"
```

> ⛔ **commit زده نشد** — منتظر تأیید کاربر.

**git log (آخرین ۳):**
```
0e2e9e3 (HEAD -> main, origin/main) Phase 53.2: daily-return Sharpe/Sortino (no annualization) + scope-aware risk capital
d5004b7 Phase 53.1: stale-analysis guard (trade.updated_at) + strategy delete safety (409)
fd848a8 Phase 52: new version ranking formula (expectancy/sample/dd-percent)
```

---

## ۸) نکات و محدودیت‌ها
1. **بدون migration جدید** (هیچ ستون/جدولی تغییر نکرد).
2. `calculate_r_multiple` با پارامتر اختیاری `initial_sl` **سازگار عقب‌رو** است (فراخوانی‌های موجود دست‌نخورده).
3. Sharpe سوم در `strategies.py:465` طبق تأیید قبلی همچنان **خارج از دامنه** است.
4. 53.6.3 فقط **Theme** را کاملاً به منبع یگانه منتقل کرد؛ `timezone`/`calendar`/`currency` در API ذخیره/بازخوانی می‌شوند (تست roundtrip) ولی اتصال عمیق آن‌ها به همهٔ مصرف‌کننده‌های UI یک کار بزرگ‌تر است و در این فاز انجام نشد.

