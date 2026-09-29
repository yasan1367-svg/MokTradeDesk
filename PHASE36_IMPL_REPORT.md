# ⚡ PHASE 36 — Performance & Query Optimization · IMPLEMENTATION REPORT

> **وضعیت:** ✅ کامل (Indexes + N+1 fix + Aggregation + Pagination + Benchmark)
> **تاریخ:** ۱۴۰۵/۰۷/۰۹
> **Revision:** `b8c9d0e1f2a3` → **`c9d0e1f2a3b4`** (head جدید)
> **خروجی تست:** `167 passed` · بنچمارک ۱K/۱۰K/۱۰۰K/۵۰۰K اجرا شد

---

## ۱. خلاصهٔ اجرایی

| هدف | اقدام |
|:---|:---|
| ایندکس‌های مناسب | ✅ ۷ ایندکس (۴ روی `trades` + ۳ روی `transactions`) — مدل + migration |
| جلوگیری از N+1 | ✅ داشبورد (ارزیابی گروهی پراپ) + `GET /finance/transactions` (`joinedload`) |
| Aggregation در DB | ✅ آمار داشبورد/مالی از قبل SQL بود؛ N+1 پراپ حذف شد (۲ کوئری ثابت) |
| Pagination | ✅ `GET /finance/transactions` و `GET /prop/payouts` صاحب `limit/offset` شدند (Trade List از قبل داشت) |
| جلوگیری از Load همهٔ Trades | ✅ لیست‌ها صفحه‌بندی‌شده؛ داشبورد فقط ۳ ستون لازم را می‌خواند؛ موتور پراپ bulk |
| داشبورد سریع با حجم بالا | ✅ اندازه‌گیری و گزارش گلوگاه‌ها |

---

## ۲. تغییرات فایل‌به‌فایل

### ۲.۱ ایندکس‌ها
- `models/strategy.py` → `Trade`:
  - `prop_stage_id` ⇒ `index=True` (جدید)
  - `close_time` ⇒ `index=True` (جدید)
  - `personal_trading_account_id` / `is_deleted` از قبل `index=True` بودند اما **ایندکس‌شان در DB ساخته نشده بود** ⇒ در migration ساخته شد.
- `models/finance.py` → `Transaction`:
  - `account_id`، `date`، `type` ⇒ `index=True` (جدید)
- `migrations/versions/c9d0e1f2a3b4_phase36_indexes.py` (جدید):
  `ix_trades_{prop_stage_id, personal_trading_account_id, is_deleted, close_time}` و
  `ix_transactions_{account_id, date, type}` + downgrade کامل.
- ✅ روی `trading_desk.db` اجرا شد (بکاپ `trading_desk.db.bak_phase36_pre`): هر ۷ ایندکس تأیید شد.

### ۲.۲ رفع N+1 در موتور پراپ — `services/prop_rule_engine.py`
- استخراج محاسبهٔ ارزیابی به `_evaluate_stage_with_trades(stage, trades)`.
- `evaluate_stage(db, stage_id)` حالا همان تابع را صدا می‌زند (رفتار بدون تغییر).
- **جدید:** `evaluate_stages(db, stage_ids)` — همهٔ مراحل و همهٔ معاملات‌شان با **۲ کوئری**
  (به‌جای `1 + 2N`).

### ۲.۳ داشبورد — `api/analytics.py`
```python
stage_ids = [s.id for s in active_stages]
bulk_eval = PropRuleEngine.evaluate_stages(db, stage_ids)   # ← ۲ کوئری برای همهٔ مراحل
for stage in active_stages:
    result = bulk_eval.get(stage.id) or PropRuleEngine.evaluate_stage(db, stage.id)
```

### ۲.۴ تراکنش‌های مالی — `api/finance.py`
- `joinedload(Transaction.account)`, `joinedload(Transaction.category)` ⇒ رفع N+1 در `account_name`/`category_name`.
- افزودن `limit` (۱..۲۰۰۰) و `offset` — **پیش‌فرض `limit=None` ⇒ سازگاری کامل با رفتار قبلی و فرانت‌اند موجود**.

### ۲.۵ برداشت‌های پراپ — `api/prop.py`
- افزودن `limit`/`offset` به `GET /api/prop/payouts` + مرتب‌سازی پایدار (`withdrawal_date DESC, id DESC`).

---

## ۳. بنچمارک — `backend/benchmarks/bench_phase36.py`

اجرا: `venv\Scripts\python.exe benchmarks\bench_phase36.py [--sizes ...] [--skip-analysis] [--index-impact]`

### ۳.۱ نتایج (ms)

| ناحیه | ۱K | ۱۰K | ۱۰۰K | ۵۰۰K |
|:---|---:|---:|---:|---:|
| Dashboard `/api/analytics/dashboard` | ۱۰۲ | ۲۸۲ | ۲,۷۵۹ | **۱۰,۳۳۸** |
| Trade List (page=1, size=50) | ۶۲ | ۴۱ | ۶۰ | ۲۷ |
| Trade List (`prop_stage_id=…`) | ۲۲ | ۱۴ | ۱۸۹ | ۲۷۶ |
| Analysis `analyze_version` | ۱۵۳ | ۶۸۹ | ۸,۰۸۶ | **۳۱,۳۵۰** |
| Prop `evaluate_stage` (تکی) | ۶ | ۱۰۰ | ۱۹۳ | ۱,۱۷۳ |
| Prop `evaluate_stages` (bulk) | ۴ | ۳۷ | ۳۲۱ | ۱,۲۶۲ |
| Finance `summary` | ۶.۵ | ۸.۸ | ۳۴ | ۶.۳ |
| Finance `money-cycle` | ۳.۶ | ۵.۹ | ۱۷ | ۳.۶ |
| Finance `transactions` (l=100) | ۶.۶ | ۱۰.۳ | ۱۶ | ۸.۵ |
| Prop `payouts` (l=100) | ۳۴.۶ | ۸.۷ | ۱۴ | ۵.۱ |

| سربار راه‌اندازی | ۱K | ۱۰K | ۱۰۰K | ۵۰۰K |
|:---|---:|---:|---:|---:|
| seed (درج) | ۰.۴s | ۱.۳s | ۱۰.۴s | ۵۶.۸s |
| ساخت ۷ ایندکس | ۷۵ms | ۹۶ms | ~۷۰۰ms | ۲.۹۶s |

### ۳.۲ اثر ایندکس‌ها (`--index-impact` روی ۱۰۰K)

| کوئری | بدون ایندکس | با ایندکس | تسریع |
|:---|---:|---:|---:|
| فیلتر `prop_stage_id` | ۲۱۳.۵ ms | ۸۴.۸ ms | **×۲.۵** |
| مرتب‌سازی `close_time` (recent closed) | ۳۲۵.۷ ms | ۱۵۳.۴ ms | **×۲.۱** |
| شمارش `is_deleted = 0` | ۷۳.۵ ms | ۴.۱ ms | **×۱۸.۰** |

### ۳.۳ یافته‌ها (شکل‌دهندهٔ فازهای بعدی)
1. **Dashboard در ۵۰۰K = ~۱۰s** — گلوگاه اصلی: خواندن دنبالهٔ مرتب ۵۰۰K ردیفی
   (`close_time`, `net`) برای محاسبهٔ دقیق Max-DD / Longest-Loss-Streak / Equity-Curve.
   ایندکس `close_time` کمک کرد اما حذف کامل نیازمند پنجره‌ای‌کردن (Window Functions) یا
   Snapshot افزایشی است ⇒ **پیشنهاد برای فاز Performance بعدی**.
2. **Analysis در ۵۰۰K = ~۳۱s** — ذاتاً همهٔ معاملات را لازم دارد (آمار دقیق) ⇒ کاندید
   Snapshot/Incremental در فاز بعد.
3. **لیست‌ها و گزارش‌های مالی** با Pagination/joinedload در همهٔ اندازه‌ها زیر ~۳۰۰ms ماندند ✅

---

## ۴. تست‌ها — `backend/tests/test_phase36_performance.py` (جدید · ۸ تست)

| تست | پوشش |
|:---|:---|
| `test_phase36_indexes_exist` | وجود ۷ ایندکس درخواستی |
| `test_bulk_evaluate_matches_single` | برابری کامل bulk با تک‌تک (`evaluate_stages` ≡ `evaluate_stage`) |
| `test_bulk_evaluate_constant_query_count` | تعداد کوئری ثابت (≤۳) برای ۵ مرحله ⇒ رفع N+1 |
| `test_bulk_evaluate_handles_missing_stage` | مرحلهٔ ناموجود در bulk |
| `test_bulk_evaluate_empty_ids` | ورودی خالی |
| `test_transactions_list_has_no_n_plus_one` | `joinedload` ⇒ تعداد کوئری مستقل از تعداد ردیف |
| `test_transactions_pagination` | `limit`/`offset` + سازگاری حالت بدون limit |
| `test_payouts_pagination` | Pagination برداشت‌های پراپ |

---

## ۵. اعتبارسنجی

```text
pytest (کل مجموعه) ....................................... 167 passed
alembic upgrade head ..................................... c9d0e1f2a3b4 ✓
trades indexes .......... ix_trades_{prop_stage_id, personal_trading_account_id, is_deleted, close_time} ✓
transactions indexes .... ix_transactions_{account_id, date, type} ✓
benchmark ............... 1K / 10K / 100K / 500K اجرا و ثبت شد
```

---

## ۶. گام بعدی
**Phase 37 (یکسان‌سازی FINANCE)** — `Account` ⇒ `FinancialAccount`، `Transaction` ⇒
`FinancialTransaction`، افزودن `TRANSFER/CONVERSION/ADJUSTMENT` به Enumها (بدون جدول جدید)،
سپس migration/تست/`PHASE37_IMPL_REPORT.md`. (منتظر شروع فاز ۳۷ — چون تغییر نام‌ها دامنه‌ی
گسترده‌ای دارد و کد قبل از هر تغییر ارائه می‌شود.)

> ⏳ Phase 38/39 طبق توافق: **صبر برای متن کامل**.

