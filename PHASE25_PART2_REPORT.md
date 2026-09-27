# 📋 گزارش فاز ۲۵ — بخش ۲: رفع فیلترهای `is_deleted` در پراپ/مالی/تحلیل/گزارش

> **تاریخ:** ۱۴۰۵/۰۷/۰۵ (2026-09-27) · **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ کامل — ✅ ۹۰ تست بک‌اند پاس (۱۱ تست جدید) · ✅ `app` import OK
> **قوانین:** ✅ Auto-approve غیرفعال · ✅ ترتیب: prop.py ← finance.py ← analysis_service.py ← بقیه ← تست

---

## ۱. بررسی قبل از تغییر (فهرست کامل کوئری‌های `Trade`)

| فایل | محل | وضعیت قبل |
|---|---|---|
| `api/prop.py` | `pass_stage` (L414)، `get_stage_trades` (L509) | ❌ بدون فیلتر |
| `api/finance.py` | `_compute_real_pnl` → prop_row (L1153)، broker_row (L1163)، `get_financial_calendar` (L1369) | ❌ بدون فیلتر |
| `services/analysis_service.py` | `analyze_prop_stage` (L35)، `analyze_broker` (L43) | ❌ بدون فیلتر |
| `services/prop_rule_engine.py` | `evaluate_stage` (L44) | ❌ بدون فیلتر |
| `services/finance_sync_service.py` | `sync_closed_trades` (L31) | ❌ بدون فیلتر |
| `services/import_service.py` | `_update_prop_stage_profit` × ۲ (L150، L382) | ❌ بدون فیلتر |
| `api/analytics.py` | `_scope_filter` (L49)، dashboard (L204)، yesterday (L408)، risk-metrics (L483)، open-exposure (L529)، calendar (L753)، `_guard_analyzable` (L892) | ❌ بدون فیلتر |
| `api/export.py` | CSV (L148)، PDF (L214) | ❌ بدون فیلتر |
| `api/strategies.py` | `_trades_count_by_version` (L31)، `delete_version` guard (L242)، `get_version_trades` (L301) | ❌ بدون فیلتر |
| `api/personal.py` | `create_review` (L36) | ❌ بدون فیلتر |

---

## ۲. تغییرات

### helper مرکزی — `utils/trade_scope.py`
```python
def not_deleted_filter() -> ColumnElement:
    """شرط SQL: فقط معاملات حذف‌نشده (Soft Delete — فاز ۲۵)."""
    return Trade.is_deleted == False
```
(و `analysis_trades_filter()` از قبل شامل این شرط بود.)

### `api/prop.py`
```python
trades = db.query(Trade).filter(
    Trade.prop_stage_id == stage_id, Trade.is_deleted == False
).all()
```

### `api/finance.py`
```python
.filter(PS.stage_type == StageType.FUNDED_REAL, Trade.pnl.isnot(None), Trade.is_deleted == False)
.filter(Account.type == AccountType.BROKER, Trade.pnl.isnot(None), Trade.is_deleted == False)
for t in db.query(Trade).filter(Trade.close_time.isnot(None), Trade.is_deleted == False).all():
```

### `services/analysis_service.py`
`analyze_prop_stage` و `analyze_broker` → `Trade.is_deleted == False` اضافه شد.

### `services/prop_rule_engine.py`
`evaluate_stage` → `Trade.is_deleted == False` (معاملات حذف‌شده در equity/DD/تعداد روز لحاظ نمی‌شوند).

### `services/finance_sync_service.py`
`sync_closed_trades` → `Trade.is_deleted == False` (هرگز با حسابداری همگام نمی‌شود).

### `services/import_service.py`
`_update_prop_stage_profit` (هر دو کلاس Soft4X و MT4) → فقط معاملات غیرحذف‌شده.

### `api/analytics.py`
- `_scope_filter` → `query.filter(Trade.is_deleted == False)` (یعنی dashboard + risk-advanced).
- dashboard (open trades)، yesterday، risk-metrics، open-exposure، calendar، `_guard_analyzable` → فیلتر اضافه شد.

### `api/export.py`
دو کوئری خروجی CSV/PDF → `query.filter(Trade.is_deleted == False)`.

### `api/strategies.py`
`_trades_count_by_version`، guard حذف نسخه، و `get_version_trades` → فیلتر اضافه شد.

### `api/personal.py`
`create_review` → برای معامله‌ی حذف‌شده `404`.

### `api/trades.py` (تکمیلی)
`update_trade` و `upload_screenshot` → معامله‌ی حذف‌شده `404`.

---

## ۳. موارد **عمداً** بدون فیلتر

| محل | دلیل |
|---|---|
| `trades.py` → `delete_trade` | باید معامله‌ی حذف‌شده را هم پیدا کند تا `hard delete`/پاسخ idempotent کار کند |
| `trades.py` → `batch_delete_trades` | باید حذف‌شده‌ها را ببیند تا در `skipped` گزارش کند و hard delete انجام دهد |
| `import_service.py` → `trade_hash` (L117، L349) | تشخیص تکرار در Import باید نسبت به **همهٔ** ردیف‌ها (حتی حذف‌شده) باشد تا re-import باعث تکرار رکورد نشود |

---

## ۴. تست

فایل جدید: `backend/tests/test_soft_delete_filters.py` (۱۱ تست)

| تست | سناریو |
|---|---|
| `test_prop_stage_trades_excludes_deleted` | `GET /api/prop/stages/{id}/trades` فقط ۱ معامله |
| `test_prop_rule_engine_excludes_deleted` | `evaluate_stage` → `total_trades=1`, `equity` بدون حذف‌شده |
| `test_analyze_prop_stage_excludes_deleted` | `AnalysisService.analyze_prop_stage` → `total_trades=1` |
| `test_analyze_broker_excludes_deleted` | `AnalysisService.analyze_broker` → `total_trades=1` |
| `test_finance_real_pnl_excludes_deleted` | `GET /api/finance/real-pnl` → پراپ ۱ / بروکر ۱ |
| `test_finance_calendar_excludes_deleted` | `GET /api/finance/financial-calendar` → ۱ معامله |
| `test_analytics_dashboard_excludes_deleted` | `GET /api/analytics/dashboard` → `total_trades=1` |
| `test_analytics_calendar_excludes_deleted` | `GET /api/analytics/calendar` → ۱ معامله |
| `test_finance_sync_skips_deleted` | `FinanceSyncService` فقط ۱ تراکنش می‌سازد |
| `test_strategies_trades_count_excludes_deleted` | `GET /api/strategies/versions/all` → `trades_count=1` |
| `test_version_trades_excludes_deleted` | `GET /api/strategies/versions/{id}/trades` → ۱ ردیف |

**نتایج:**
| ابزار | نتیجه |
|---|---|
| `pytest tests/test_soft_delete_filters.py` | ✅ ۱۱ پاس (EXIT=0) |
| `pytest` (کل) | ✅ **۹۰ پاس** (EXIT=0) |

---

## ۵. فایل‌های تغییر‌یافته

| فایل | نوع |
|---|---|
| `backend/app/utils/trade_scope.py` | ✏️ افزودن `not_deleted_filter()` |
| `backend/app/api/prop.py` | ✏️ ۲ کوئری |
| `backend/app/api/finance.py` | ✏️ ۳ کوئری |
| `backend/app/api/analytics.py` | ✏️ ۷ محل |
| `backend/app/api/export.py` | ✏️ ۲ کوئری |
| `backend/app/api/strategies.py` | ✏️ ۳ کوئری |
| `backend/app/api/personal.py` | ✏️ ۱ کوئری |
| `backend/app/api/trades.py` | ✏️ `update_trade` + `upload_screenshot` |
| `backend/app/services/analysis_service.py` | ✏️ ۲ کوئری |
| `backend/app/services/prop_rule_engine.py` | ✏️ ۱ کوئری |
| `backend/app/services/finance_sync_service.py` | ✏️ ۱ کوئری |
| `backend/app/services/import_service.py` | ✏️ ۲ کوئری (هر دو ایمپورتر) |
| `backend/tests/test_soft_delete_filters.py` | 🆕 ۱۱ تست |
| `PHASE25_PART2_REPORT.md` | 🆕 این گزارش |

---

## ۶. نکات

- Frontend تغییری نداشت (فیلترها سمت سرور اعمال شدند) → نیازی به `tsc`/`vitest` نبود.
- Migration جدیدی لازم نبود (`is_deleted` در بخش ۱ ساخته شده بود).
- برای دو فایلی که بلوک کد کاملاً یکسان داشتند (`import_service.py`, `export.py`)، از اسکریپت موقت پایتون برای جایگزینی هر دو استفاده شد و اسکریپت پس از اجرا حذف گردید.
- اعتبارسنجی نهایی: اسکن مجدد همهٔ `query(Trade)`ها → تنها موارد باقی‌مانده همان ۳ استثنای عمدی بخش ۳ هستند.
