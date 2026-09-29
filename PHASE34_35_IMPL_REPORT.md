# 📊 PHASE 34 & 35 — Analysis Context + AnalysisRun · IMPLEMENTATION REPORT

> **وضعیت:** ✅ کامل (Model + Migration + Tests) — **گزینهٔ A (افزودنی، کم‌ریسک)**
> **تاریخ:** ۱۴۰۵/۰۷/۰۹
> **Revision:** `a7b8c9d0e1f2` → **`b8c9d0e1f2a3`** (head جدید)
> **خروجی تست:** `156 passed` (کل مجموعه) · `7 passed` (Phase 34/35)

---

## ۱. خلاصهٔ اجرایی

طبق تصمیم شما (گزینهٔ A) هیچ enum/جدول موجودی تغییر یا حذف نشد؛ فقط **افزودنی**:

| مورد | فاز | پیاده‌سازی |
|:---|:---|:---|
| جدول `analysis_scopes` | ۳۴ | مدل `AnalysisScopeRecord` (نام متفاوت ⇒ بدون تضاد با enum `AnalysisScope`) |
| `analysis_runs.scope_id` (FK) | ۳۵ | ✅ nullable |
| `analysis_runs.filters_snapshot` (JSON) | ۳۵ | ✅ |
| `analysis_runs.trade_count` (Integer) | ۳۵ | ✅ default 0 |
| `analysis_runs.status` (Enum) | ۳۵ | ✅ `AnalysisStatus` (PENDING/RUNNING/COMPLETED/FAILED) |
| `analysis_results.analysis_run_id` (FK) | ۳۵ | ✅ nullable |

> ✅ **enum فعلی `AnalysisScope` و جدول‌های `analysis_runs`/`analysis_results` دست‌نخورده‌اند؛
> هیچ کدی Refactor نشد.**

---

## ۲. تغییرات فایل‌به‌فایل

### ۲.۱ `backend/app/models/strategy.py`
- افزودن enum جدید `AnalysisStatus` (PENDING/RUNNING/COMPLETED/FAILED).
- افزودن ستون‌های `AnalysisRun`:

```python
    scope_id         = Column(Integer, ForeignKey("analysis_scopes.id"), nullable=True, index=True)
    filters_snapshot = Column(JSON, nullable=True)
    trade_count      = Column(Integer, default=0)
    status           = Column(Enum(AnalysisStatus), nullable=True, default=AnalysisStatus.PENDING)
    scope_record     = relationship("AnalysisScopeRecord", foreign_keys=[scope_id])
```

- افزودن به `AnalysisResult`:

```python
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=True, index=True)
    analysis_run    = relationship("AnalysisRun", foreign_keys=[analysis_run_id])
```

- افزودن مدل جدید `AnalysisScopeRecord` (جدول `analysis_scopes`):

```python
class AnalysisScopeRecord(Base):
    __tablename__ = "analysis_scopes"

    id                          = Column(Integer, primary_key=True, index=True)
    strategy_version_id         = Column(Integer, ForeignKey("strategy_versions.id"), nullable=True)
    trade_type                  = Column(Enum(TestType), nullable=False)
    personal_trading_account_id = Column(Integer, ForeignKey("personal_trading_accounts.id"), nullable=True)
    prop_stage_id               = Column(Integer, ForeignKey("prop_stages.id"), nullable=True)
    from_date                   = Column(DateTime(timezone=True), nullable=True)
    to_date                     = Column(DateTime(timezone=True), nullable=True)
    is_deleted_filter           = Column(Boolean, default=False)
    created_at                  = Column(DateTime(timezone=True), server_default=func.now())

    version = relationship("StrategyVersion", foreign_keys=[strategy_version_id])
```

- افزودن `func` به importهای SQLAlchemy.

### ۲.۲ `backend/migrations/versions/b8c9d0e1f2a3_phase34_35_analysis_context.py` (جدید)
- `create_table analysis_scopes` (۳ FK + ایندکس id).
- `batch_alter_table analysis_runs`: افزودن ۴ ستون + `fk_analysis_runs_scope_id`.
- `batch_alter_table analysis_results`: افزودن `analysis_run_id` + `fk_analysis_results_analysis_run_id`.
- ایندکس‌ها: `ix_analysis_runs_scope_id`, `ix_analysis_results_analysis_run_id`.
- `down_revision = a7b8c9d0e1f2` · downgrade کامل.
- ✅ روی `trading_desk.db` اجرا شد (بکاپ `trading_desk.db.bak_phase34_35_pre`).
  تمام FKها و ایندکس‌ها **از جمله UniqueConstraint `uq_analysis_results_scope_key`** سالم ماندند.

### ۲.۳ `backend/migrations/env.py`
- افزودن `AnalysisRun` و `AnalysisScopeRecord` به importها (تا `target_metadata` کامل باشد).

### ۲.۴ بدون تغییر
`analysis_service.py` / `api/analytics.py` / تست‌های موجود — **هیچ تغییر رفتاری نداشتند**.

---

## ۳. قانون فاز ۳۵ — «Run #1 ثابت، Trade جدید ⇒ Run #2 جدا»

این قانون **از قبل** در `AnalysisService._analyze` برقرار بود (هر اجرا یک `AnalysisRun` جدید
append می‌کند و `AnalysisResult` جاری را بازنویسی می‌کند). با این فاز:

- `AnalysisRun` اکنون می‌تواند به `AnalysisScopeRecord` وصل شود (`scope_id`).
- `AnalysisResult` اکنون می‌تواند به Run مربوطه وصل شود (`analysis_run_id`).
- تاریخچهٔ Runها دست‌نخورده و append-only است.

تست `test_runs_are_separate_history` این را تضمین می‌کند: Run#1 (۱ معامله) و Run#2 (۲ معامله)
هر دو باقی می‌مانند.

---

## ۴. تست‌ها — `backend/tests/test_phase34_35_analysis_context.py` (جدید · ۷ تست)

| تست | فاز | پوشش |
|:---|:---|:---|
| `test_analysis_scope_record_created` | ۳۴ | ساخت دامنه + `created_at`/`is_deleted_filter` |
| `test_analysis_scope_record_with_filters` | ۳۴ | `from_date`/`to_date` + رابطهٔ version |
| `test_analysis_run_scope_link_and_fields` | ۳۵ | `scope_id`/`filters_snapshot`/`trade_count`/`status` |
| `test_analysis_run_default_status_pending` | ۳۵ | پیش‌فرض `PENDING` و `trade_count=0` |
| `test_analysis_result_links_run` | ۳۵ | `analysis_run_id` + رابطه |
| `test_runs_are_separate_history` | ۳۵ | Run #1 ثابت، Run #2 جدا |
| `test_existing_analyze_version_still_works` | رگرسیون | تحلیل موجود بدون تغییر |

---

## ۵. خروجی اجرای تست و مهاجرت

```text
tests/test_phase34_35_analysis_context.py ................ 7 passed
pytest (کل مجموعه) ....................................... 156 passed
alembic upgrade head ..................................... b8c9d0e1f2a3 ✓
analysis_scopes ................ ۹ ستون + ۳ FK + index ✓
analysis_runs .................. + scope_id/filters_snapshot/trade_count/status (+FK/index) ✓
analysis_results ............... + analysis_run_id (+FK/index) ✓
UniqueConstraint uq_analysis_results_scope_key ........ سالم ✓
```

---

## ۶. یادداشت‌ها و گام‌های بعدی (اختیاری)

1. **اتصال سرویس (فاز تکمیلی):** در این فاز فقط مدل/مهاجرت ساخته شد (طبق گزینهٔ A). برای اینکه
   `analyze_version` هر بار یک `AnalysisScopeRecord` بسازد و `scope_id`/`analysis_run_id` را پر
   کند، یک تغییر کوچک در `AnalysisService._analyze` لازم است — در صورت تأیید شما در گام بعد
   انجام می‌شود.
2. **API (اختیاری):** افزودن endpoint `GET /api/analytics/runs/{run_id}` و فیلتر بر اساس
   `filters_snapshot` در گام بعد.
3. **بکاپ‌ها:** `trading_desk.db.bak_phase33_pre` و `trading_desk.db.bak_phase34_35_pre`.

