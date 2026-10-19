# PHASE 53.1 — Data Integrity (تحلیل کهنه + حذف cascade)

> **تاریخ:** ۱۴۰۵/۰۷/۱۱ (2026-10-02) · **وضعیت:** ✅ پیاده‌شده · ⛔ آمادهٔ commit (منتظر تأیید کاربر)
> **مبنا:** Phase 52 = `fd848a8` · **Alembic head:** `f53a1b2c3d4e`

---

## ۱) خلاصهٔ اجرایی

دو مسیر از دست رفتن/کهنه‌شدن داده که Audit ChatGPT کشف کرد، بسته شد:

| تسک | باگ | راه‌حل |
|:--|:--|:--|
| **53.1.1** | گارد «تحلیل کهنه» فقط **تعداد** معاملات را می‌سنجید ⇒ ویرایش سود/زمان بدون تغییر تعداد، تحلیل کهنه را «تازه» نشان می‌داد | ستون `trades.updated_at` + مقایسه با `AnalysisResult.created_at` در **هر دو** گارد |
| **53.1.2** | `DELETE /api/strategies/{id}` بدون گارد، با cascade **سخت** کل نسخه‌ها/معاملات/تحلیل‌ها را پاک می‌کرد | گارد معامله + تحلیل ⇒ **۴۰۹** به‌جای حذف خاموش |

- **Backend:** ۳ فایل ویرایش + ۲ تست جدید + ۱ Migration جدید.
- **Frontend:** پیام تأیید حذف استراتژی اصلاح شد (۱ خط).
- **تست‌ها:** `406 passed + 1 xfailed` (قبلاً ۴۰۰ ⇒ **+۶**) · TSC=0 · Migration head تک‌شاخه.

---

## ۲) تسک 53.1.1 — تحلیل کهنه (`updated_at`)

### قبل
```python
# _guard_analyzable: تنها معیار تازگی = شمارش
if result.total_trades != count:
    raise HTTPException(404, "تحلیل کهنه است ...")
# get_analysis (/{version_id}): گارد inline مشابه، فقط شمارش
if result.total_trades != analyzable_trades:
    raise HTTPException(404, "تحلیل ذخیره‌شده کهنه است ...")
```

### بعد
```python
# ۱) مدل — ستون جدید
updated_at = Column(
    DateTime(timezone=True),
    default=lambda: datetime.now(timezone.utc),
    onupdate=lambda: datetime.now(timezone.utc),   # با هر UPDATE
    nullable=True,
)

# ۲) در هر دو گارد، پس از چک تعداد:
max_updated = q.with_entities(func.max(Trade.updated_at)).scalar()
if max_updated is not None and result.created_at is not None:
    if _as_naive(result.created_at) < _as_naive(max_updated):
        raise HTTPException(404, "تحلیل کهنه است (معاملات پس از تحلیل ویرایش شده‌اند). ...")
```

### چرا **هر دو** گارد؟
دو مسیر GET تحلیل وجود دارد و هر دو گارد مستقل دارند:
| Endpoint | گارد | مصرف‌کنندهٔ فرانت |
|:--|:--|:--|
| `GET /api/analytics/analysis/version/{id}` | `_guard_analyzable` | `getAnalysisVersion` |
| `GET /api/analytics/{id}` | گارد inline در `get_analysis` | `getAnalysis` / `getVersionAnalysis` |

> ⚠️ نکتهٔ کشف‌شده حین کار: پچ اولیه فقط `_guard_analyzable` را پوشش داد و تست ۲۰۰ برگرداند؛ چون UI عمدتاً از `/{id}` (گارد inline) استفاده می‌کند. هر دو اصلاح و در تست پوشش داده شدند.

### Timezone Normalization (طبق راهنمای کاربر)
```python
def _as_naive(dt):
    """حذف tzinfo برای مقایسهٔ ایمن aware/naive (SQLite)."""
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if getattr(dt, "tzinfo", None) is not None else dt
```

### Migration
`backend/migrations/versions/f53a1b2c3d4e_phase53_trade_updated_at.py`
```python
revision = "f53a1b2c3d4e"
down_revision = "d6e4f1c9a203"   # head فعلی

def upgrade():
    if "updated_at" not in _existing_columns("trades"):
        op.add_column("trades", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

def downgrade():
    if "updated_at" in _existing_columns("trades"):
        op.drop_column("trades", "updated_at")
```
- idempotent (الگوی فاز ۳۹/۴۵) · `nullable=True` ⇒ رکوردهای قدیمی NULL.
- تأیید اجرا: `alembic heads` → `f53a1b2c3d4e (head)` · `test_migrations` → `d6e4f1c9a203 -> f53a1b2c3d4e` بدون diff برای `updated_at`.



---

## ۳) تسک 53.1.2 — گارد حذف استراتژی

### قبل
```python
@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="استراتژی پیدا نشد")
    db.delete(strategy)          # ← cascade سخت: نسخهها + معاملات + تحلیلها + اجراها
    db.commit()
    return {"message": "استراتژی حذف شد"}
```

### بعد
```python
def _check_strategy_deletable(db, strategy_id):
    """(trade_count, analysis_count) — وابستگیهای استراتژی."""
    trade_count = (db.query(Trade)
        .join(StrategyVersion, Trade.version_id == StrategyVersion.id)
        .filter(StrategyVersion.strategy_id == strategy_id, Trade.is_deleted == False)
        .count())
    analysis_count = (db.query(AnalysisResult)
        .join(StrategyVersion, AnalysisResult.version_id == StrategyVersion.id)
        .filter(StrategyVersion.strategy_id == strategy_id)
        .count())
    return trade_count, analysis_count


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="استراتژی پیدا نشد")

    trade_count, analysis_count = _check_strategy_deletable(db, strategy_id)
    if trade_count > 0:
        raise HTTPException(status_code=409,
            detail=f"این استراتژی {trade_count} معامله دارد و قابل حذف نیست. ابتدا معاملات آن را حذف کنید.")
    if analysis_count > 0:
        raise HTTPException(status_code=409,
            detail=f"این استراتژی {analysis_count} تحلیل ذخیرهشده دارد و قابل حذف نیست. ابتدا تحلیلها را پاک کنید.")

    db.delete(strategy)
    db.commit()
    return {"message": "استراتژی حذف شد"}
```
- Import جدید: `AnalysisResult` در `api/strategies.py`.
- حالا `delete_strategy` هم‌رفتار با `delete_version` (که از قبل گارد داشت) شد.

### Frontend
پیام تأیید `StrategyPage.tsx` اصلاح شد (رفع ابهام Audit):
```
قبل:  آیا مطمئنید ...؟ \n تمام نسخههای آن نیز حذف میشوند.
بعد:  آیا مطمئنید ...؟ \n اگر این استراتژی معامله یا تحلیل داشته باشد، حذف نمیشود.
```
(نمایش پیام ۴۰۹ از قبل در `catch` وجود داشت و دست‌نخورده مانده است.)

---

## ۴) تست‌ها

### ۶ تست جدید
**`tests/test_phase53_stale_analysis.py`** (۳):
| تست | سناریو |
|:--|:--|
| `test_not_stale_if_no_changes` | بدون تغییر ⇒ ۲۰۰ در هر دو endpoint |
| `test_stale_after_pnl_edit` | ویرایش `pnl` (تعداد ثابت) ⇒ ۴۰۴ در هر دو endpoint |
| `test_stale_after_time_edit` | ویرایش `close_time` (تعداد ثابت) ⇒ ۴۰۴ در هر دو endpoint |

**`tests/test_phase53_delete_safety.py`** (۳):
| تست | سناریو |
|:--|:--|
| `test_delete_empty_strategy_ok` | بدون وابستگی ⇒ ۲۰۰ |
| `test_delete_strategy_with_trades_409` | معامله دارد ⇒ ۴۰۹ + داده دست‌نخورده |
| `test_delete_strategy_with_analysis_409` | تحلیل ذخیره‌شده دارد (بدون معاملهٔ فعال) ⇒ ۴۰۹ |

### نتیجهٔ اجرا
```
Backend : 406 passed, 1 xfailed in 34.35s   (قبل: 400 · +6)
Frontend: tsc -b --force → TSC_EXIT=0
Migration: alembic heads → f53a1b2c3d4e (head) · test_migrations ✅
```

---

## ۵) آماده‌بودن برای commit

```
 M backend/app/api/analytics.py
 M backend/app/api/strategies.py
 M backend/app/models/strategy.py
 M frontend/src/pages/StrategyPage.tsx
?? backend/migrations/versions/f53a1b2c3d4e_phase53_trade_updated_at.py
?? backend/tests/test_phase53_delete_safety.py
?? backend/tests/test_phase53_stale_analysis.py
```

**پیشنهاد commit (پس از تأیید):**
```
git add backend/app/api/analytics.py \
        backend/app/api/strategies.py \
        backend/app/models/strategy.py \
        backend/migrations/versions/f53a1b2c3d4e_phase53_trade_updated_at.py \
        backend/tests/test_phase53_stale_analysis.py \
        backend/tests/test_phase53_delete_safety.py \
        frontend/src/pages/StrategyPage.tsx

git commit -m "Phase 53.1: stale-analysis guard (trade.updated_at) + strategy delete safety (409)"
```

> ⛔ **commit زده نشد** — منتظر تأیید کاربر.

**git log (آخرین ۳):**
```
fd848a8 (HEAD -> main, origin/main) Phase 52: new version ranking formula (expectancy/sample/dd-percent)
59b68f7 Fix: prop_stage_3 calculation + income at received + USD→USDT test updates
c55433c WIP: Add [قابلیت ۱] + fix [باگ ۲] + improve [چیز ۳]
```


