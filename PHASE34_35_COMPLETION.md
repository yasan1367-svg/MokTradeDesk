# 🔗 PHASE 34 & 35 — COMPLETION (Service Wiring)

> **وضعیت:** ✅ کامل — دامنه/اجرا/نتیجه اکنون به‌هم متصل‌اند
> **تاریخ:** ۱۴۰۵/۰۷/۰۹
> **دامنه:** فقط `backend/app/services/analysis_service.py` + تست
> **خروجی تست:** `159 passed` (کل مجموعه) · `10 passed` (فایل فاز ۳۴/۳۵)

---

## ۱. هدف

در گزارش قبلی (`PHASE34_35_IMPL_REPORT.md`) فقط **مدل + مهاجرت** ساخته شد. در این گام،
**سرویس** به مدل‌های جدید وصل شد:

| خواسته | پیاده‌سازی |
|:---|:---|
| `AnalysisService._analyze` ⇒ ساخت `AnalysisScopeRecord` | ✅ |
| پر کردن `AnalysisRun.scope_id` | ✅ |
| پر کردن `AnalysisResult.analysis_run_id` | ✅ |
| Run #1 ثابت + Run #2 جدا | ✅ (هر اجرا ⇒ دامنه + Run جدید) |

---

## ۲. تغییرات

### ۲.۱ `backend/app/services/analysis_service.py`
- import: `AnalysisScopeRecord`, `AnalysisStatus`.
- در `_analyze`، **قبل از** ساخت `AnalysisResult`:

```python
        open_times = [t.open_time for t in trades if t.open_time]
        close_times = [t.close_time for t in trades if t.close_time]
        scope_record = AnalysisScopeRecord(
            strategy_version_id=version_id,
            trade_type=self._resolve_trade_type(scope, test_type, trades),
            personal_trading_account_id=personal_trading_account_id,
            prop_stage_id=prop_stage_id,
            from_date=min(open_times) if open_times else None,
            to_date=max(close_times) if close_times else None,
            is_deleted_filter=True,  # در تحلیل، معاملات حذف‌شده کنار گذاشته می‌شوند
        )
        self.db.add(scope_record)
        self.db.flush()
```

- `AnalysisRun` جدید با فیلدهای فاز ۳۵:

```python
        filters_snapshot = {
            "scope": ..., "scope_key": scope_key, "version_id": version_id,
            "prop_stage_id": prop_stage_id,
            "personal_trading_account_id": personal_trading_account_id,
            "test_type": test_type.name if test_type is not None else None,
            "is_deleted_filter": True,
        }
        run = AnalysisRun(..., scope_id=scope_record.id,
                          filters_snapshot=filters_snapshot,
                          trade_count=basic["total_trades"],
                          status=AnalysisStatus.COMPLETED)
        self.db.add(run); self.db.flush()
        result.analysis_run_id = run.id      # ← اتصال نتیجهٔ جاری به این اجرا
        self.db.commit()
```

- خروجی `_analyze` اکنون `scope_id` را هم برمی‌گرداند:
  `{"result", "run_id", "scope_id", "message"}`.
- متد جدید `_resolve_trade_type(scope, test_type, trades)`:

| scope | trade_type |
|:---|:---|
| `PROP_STAGE` | `REAL_PROP` |
| `PERSONAL_ACCOUNT` | `REAL_PERSONAL` |
| `VERSION` | `test_type` داده‌شده، وگرنه نوع اولین معامله، وگرنه `BACKTEST` |

> ✅ رفتار قبلی (overwrite نتیجهٔ جاری + append Run) **دست‌نخورده** است؛ فقط لینک‌های جدید پر می‌شوند.

### ۲.۲ `backend/tests/test_phase34_35_analysis_context.py` (+۳ تست)
| تست | پوشش |
|:---|:---|
| `test_analyze_creates_scope_record_and_links_run` | ساخت ScopeRecord + پر شدن `scope_id`/`trade_count`/`status`/`filters_snapshot` + `result.analysis_run_id` |
| `test_each_run_gets_its_own_scope_record` | هر اجرا ⇒ دامنهٔ مستقل؛ نتیجهٔ جاری به Run آخر وصل است |
| `test_resolve_trade_type_for_real_scopes` | نگاشت `trade_type` برای PROP/PERSONAL/VERSION |

---

## ۳. خروجی اجرا

```text
pytest tests/test_phase34_35_analysis_context.py .......... 10 passed
pytest (کل مجموعه) ....................................... 159 passed
```

---

## ۴. نتیجه (نمونهٔ واقعی از خروجی سرویس)

```python
out = AnalysisService(db).analyze_version(version_id)
# out == {"result": <AnalysisResult analysis_run_id=2>, "run_id": 2, "scope_id": 2, "message": ...}
# Run #1 (scope_id=1) دست‌نخورده باقی می‌ماند؛ Run #2 جدا ساخته می‌شود.
```
