# 📋 گزارش فاز ۱۹ — جداسازی معاملات REAL از تحلیل استراتژی

> **تاریخ:** ۱۴۰۵/۰۷/۰۴ (2026-09-25) · **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ کامل — ✅ ۴۹ تست پاس · ✅ تست پذیرش (Backtest + Real) · ✅ تست زنده روی دیتابیس واقعی

**فایل‌های تغییر‌یافته:**
- **جدید:** `backend/app/utils/trade_scope.py` — helper مشترک `analysis_trades_filter()`
- `backend/app/services/analysis_service.py` — `analyze_version` · `compare_versions` · پاک‌سازی تحلیل کهنه
- `backend/app/api/strategies.py` — `get_strategy_stats`
- `backend/app/api/export.py` — جدول معاملات در PDF تحلیل
- `backend/app/api/analytics.py` — گارد سازگاری `GET /{version_id}`
- **جدید:** `backend/tests/test_analysis_scope.py` — ۱۱ تست
- **جدید:** `PHASE19_REPORT.md`

---

## ۱. مشکل

تحلیل نسخه‌ی استراتژی باید فقط روی معاملات **Backtest / Forward** انجام شود، اما معاملات **REAL**
(که با Import MT4 روی همان نسخه ذخیره می‌شوند) در متریک‌ها شمرده می‌شدند و نتیجه را خراب می‌کردند.

### شاهد از دیتابیس واقعی (قبل از فاز ۱۹)

| جدول | مقدار |
|---|---|
| `trades` | ۲۱ معامله — **همه `test_type = 'REAL'`** و همه با `version_id = 1` |
| `analysis_results` | `[(version_id=1, total_trades=21, win_rate=57.14, net_pnl=101.96)]` ← **۱۰۰٪ از معاملات واقعی** |
| `analysis_runs` | `[(version_id=1, total_trades=21)]` |

⇒ تحلیل نسخه ۱ کاملاً از معاملات واقعی محاسبه شده بود.

---

## ۲. ریشه — ۴ نقطه‌ی کوئری که `test_type` را فیلتر نمی‌کردند

| # | فایل: خط | تابع | فیلتر قبلی |
|---|---|---|---|
| ۱ | `analysis_service.py:21` | `analyze_version` | فقط `version_id` |
| ۲ | `analysis_service.py:143` | `compare_versions` (نمادها) | فقط `version_id` |
| ۳ | `strategies.py:319` | `get_strategy_stats` | فقط `version_id` |
| ۴ | `export.py:338` | جدول معاملات PDF تحلیل | فقط `version_id` |

### نکته‌ی فنی مهم

مقدار enum در SQLite به‌صورت **NAME** ذخیره می‌شود (`'REAL'`) نه value (`'real'`).
این با تست تجربی تأیید شد؛ SQL تولیدشده در هر سه حالت `!= 'REAL'` بود.

---

## ۳. تغییرات

### ۳.۱ helper مشترک — `backend/app/utils/trade_scope.py` (جدید)

```python
def analysis_trades_filter() -> ColumnElement:
    """شرط SQL: فقط معاملات غیر-REAL (یعنی BACKTEST و FORWARD)."""
    return or_(Trade.test_type.is_(None), Trade.test_type != TestType.REAL)
```

**SQL:** `WHERE trades.test_type IS NULL OR trades.test_type != 'REAL'`

> ستون `test_type` در مدل `nullable` است؛ ردیف‌های legacy با NULL به‌عنوان «غیر-REAL» **حفظ** می‌شوند
> تا ناخواسته از تحلیل حذف نشوند (بدون regression).

### ۳.۲ لایه ۱ — ریشه (اولویت بالا)

```python
# ❌ قبل (analysis_service.py:21):
trades = self.db.query(Trade).filter(Trade.version_id == version_id).all()

# ✅ بعد:
trades = (
    self.db.query(Trade)
    .filter(Trade.version_id == version_id, analysis_trades_filter())
    .all()
)
```

همین تغییر در `compare_versions` (خط ۱۵۵)، `get_strategy_stats` (`strategies.py:322`)
و جدول PDF (`export.py:342`) اعمال شد.

### ۳.۳ آیتم ۴ — گارد سازگاری `GET /api/analytics/{version_id}`

این endpoint **معاملات را کوئری نمی‌کند**؛ فقط snapshot ذخیره‌شده‌ی `AnalysisResult` را می‌خواند.
بنابراین «فیلتر شود» به‌صورت **گارد سازگاری** پیاده شد:

```python
# ── گارد سازگاری (فاز ۱۹) ──
analyzable_trades = (
    db.query(Trade)
    .filter(Trade.version_id == version_id, analysis_trades_filter())
    .count()
)

if analyzable_trades == 0:
    raise HTTPException(404, "این نسخه معامله‌ی Backtest/Forward ندارد "
                             "(معاملات REAL در تحلیل نسخه شمرده نمی‌شوند)")

if result.total_trades != analyzable_trades:
    raise HTTPException(404, f"تحلیل ذخیره‌شده کهنه است ({result.total_trades} معامله در تحلیل "
                             f"در برابر {analyzable_trades} معامله‌ی قابل‌تحلیل فعلی). "
                             f"دوباره «تحلیل مجدد» را بزنید.")
```

> فرانت‌اند (`AnalysisPage.tsx:61-66`) پاسخ ۴۰۴ را graceful مدیریت می‌کند (حالت خالی + پیام)،
> پس این گارد UI را نمی‌شکند.

### ۳.۴ پاک‌سازی خودکار تحلیل کهنه (Self-healing)

تحلیلی که **پیش از فاز ۱۹** محاسبه شده، آلوده است و دیگر قابل بازتولید نیست؛
پس هنگام «تحلیل مجدد» پاک می‌شود تا در هیچ endpoint سرو نشود:

```python
if not trades:
    stale = self.db.query(AnalysisResult).filter(
        AnalysisResult.version_id == version_id
    ).first()
    if stale:
        self.db.delete(stale)
        self.db.commit()
    raise ValueError(
        "هیچ معامله‌ای برای تحلیل این نسخه یافت نشد "
        "(معاملات REAL در تحلیل Backtest/Forward شمرده نمی‌شوند)"
    )
```

> `analysis_runs` (تاریخچه/audit log) **دست‌نخورده** می‌ماند.

---

## ۴. لایه ۲ — عمداً بی‌تغییر (نمای کلی)

طبق تصمیم فاز، این endpointهای گلوبال **فیلتر نمی‌شوند** چون نمای کلی دسک هستند
و حذف REAL از آن‌ها یعنی پنهان‌شدن سود واقعی:

| endpoint | فایل: خط |
|---|---|
| `GET /dashboard` | `analytics.py:96` |
| `GET /yesterday` | `analytics.py:303` |
| `GET /risk-metrics` | `analytics.py:378` |
| `GET /risk-advanced` | `analytics.py:486` |
| `GET /calendar` | `analytics.py:648` |

همچنین عمداً بی‌تغییر ماندند:
- `strategies.py:30` (`_trades_count_by_version`) — شمارش نمایشی «معاملات متصل به نسخه»
- `strategies.py:223` — گارد `delete_version` (جلوگیری از حذف نسخه‌ی دارای معامله)
- `strategies.py:269` — `GET /versions/{id}/trades` (لیست خام؛ هر آیتم `test_type` دارد)

---

## ۵. تست پذیرش — نسخه با Backtest + Real

**سناریو:** یک نسخه با **۲ معامله Backtest** (+100 و +100) و **۳ معامله REAL** (−500 هرکدام).

```
معاملات نسخه: 5 کل  |  2 قابل‌تحلیل (Backtest/Forward)
              (۳ معامله REAL با مجموع −1500$ نادیده گرفته می‌شود)

POST /api/analytics/analyze/1  → HTTP 200
GET  /api/analytics/1          → HTTP 200
     total_trades = 2      (انتظار: 2)
     net_pnl      = 200.0  (انتظار: 200.0 — نه -1300.0)
     win_rate     = 100.0  (انتظار: 100.0)
GET  /api/strategies/1/stats   → HTTP 200
     total_trades = 2      (انتظار: 2)
     net_pnl      = 200.0  (انتظار: 200.0)

نسخه‌ی فقط-REAL:
POST /api/analytics/analyze/2  → HTTP 404
     هیچ معامله‌ای برای تحلیل این نسخه یافت نشد (معاملات REAL در تحلیل Backtest/Forward شمرده نمی‌شوند)
```

**نتیجه: ✅ فقط Backtest/Forward شمرده می‌شود.**

### تست‌های خودکار — `backend/tests/test_analysis_scope.py` (۱۱ تست)

| تست | تضمین |
|---|---|
| `test_analysis_filter_keeps_everything_except_real` | BACKTEST/FORWARD/NULL می‌مانند، REAL حذف می‌شود |
| `test_analyze_version_ignores_real_trades` | ۳ Backtest + ۵ REAL → `total_trades=3`, `net_pnl=300` |
| `test_analyze_version_counts_forward_trades` | FORWARD هم جزو تحلیل است |
| `test_analyze_version_real_only_raises` | نسخه‌ی فقط-REAL → `ValueError` با ذکر REAL |
| `test_analyze_endpoint_real_only_returns_404` | `POST /analyze/{id}` → ۴۰۴ |
| `test_analyze_endpoint_metrics_are_clean` | `GET /{id}` → `total_trades=1`, `net_pnl=100` |
| `test_strategy_stats_ignores_real_trades` | `/stats` → `total_trades=2`, `net_pnl=200` |
| `test_get_analysis_real_only_version_returns_404` | گارد: تحلیل کهنه روی نسخه‌ی فقط-REAL سرو نمی‌شود |
| `test_get_analysis_stale_snapshot_returns_404` | گارد: snapshot ناهم‌خوان → ۴۰۴ «کهنه» |
| `test_get_analysis_outdated_after_new_backtest_trade` | افزودن معامله‌ی جدید، تحلیل قبلی را کهنه می‌کند |
| `test_reanalyze_cleans_stale_result_when_no_analyzable_trades` | پاک‌سازی خودکار رکورد کهنه |

**اثبات اینکه تست‌ها باگ را می‌گیرند** (با `git stash` موقت روی کد اصلاح‌شده):

| وضعیت کد | نتیجه |
|---|---|
| کد باگ‌دار | **`6 failed, 1 passed`** — از جمله `assert 5 == 2` (۵ = ۲ Backtest + ۳ REAL) |
| کد اصلاح‌شده | **`11 passed`** |

---

## ۶. تست زنده روی دیتابیس واقعی

| درخواست | قبل از فاز ۱۹ | بعد از فاز ۱۹ |
|---|---|---|
| `GET /api/analytics/1` | `200` با ۲۱ معامله‌ی REAL (win_rate 57.14) | ✅ **`404`** «این نسخه معامله‌ی Backtest/Forward ندارد…» |
| `GET /api/strategies/1/stats` | `total_trades: 21` | ✅ `total_trades: 0` |
| `POST /api/analytics/analyze/1` | متریک آلوده | ✅ `404` + پیام شفاف (و رکورد کهنه پاک شد) |
| `GET /api/analytics/1` (پس از پاک‌سازی) | — | ✅ `404` «تحلیلی برای این نسخه یافت نشد…» |

### وضعیت دیتابیس قبل/بعد

| جدول | قبل | بعد |
|---|---|---|
| `analysis_results` | `[(1, 21)]` ← آلوده | **`[]`** ← پاک شد ✅ |
| `analysis_runs` | `[(1, 21)]` | `[(1, 21)]` (تاریخچه حفظ شد) |
| `trades` | ۲۱ | ۲۱ (هیچ داده‌ای حذف نشد) |

---

## ۷. تأیید نهایی

| بررسی | نتیجه |
|---|---|
| `pytest -q` (کل مجموعه) | ✅ **`49 passed`** |
| `py_compile` فایل‌های تغییریافته | ✅ `exit=0` |
| تست پذیرش (Backtest + Real) | ✅ فقط Backtest/Forward شمرده شد |
| تست زنده (uvicorn + دیتابیس واقعی) | ✅ ۴ درخواست، همه پاسخ صحیح (بدون ۵۰۰) |
| اسکریپت‌های موقت | ✅ پاک شدند |

---

## ۸. نکات و محدودیت‌ها

1. **تغییر رفتار (طبق تصمیم فاز):** `GET /api/analytics/{version_id}` اگر تحلیل ذخیره‌شده با معاملات
   قابل‌تحلیل فعلی هم‌خوان نباشد `404` می‌دهد (با پیام «کهنه»). در جریان عادی UI
   (`POST analyze` → `GET`) همیشه fresh است، پس گارد فعال نمی‌شود.
2. **ناهماهنگی ظاهری مجاز:** لیست نسخه‌ها (`_trades_count_by_version`) همچنان «۲۱ معامله» نشان می‌دهد
   (معاملات واقعاً متصل‌اند)، در حالی که تحلیل ۰ است. این درست است — پیام خطای جدید همین را توضیح می‌دهد.
3. **`analysis_runs` (تاریخچه) پاک نمی‌شود:** رکوردهای تاریخی که پیش از فاز ۱۹ ثبت شده‌اند همچنان
   اعداد آلوده دارند (audit log). اگر لازم است، پاک‌سازی جداگانه لازم دارد.
4. **`GET /{version_id}/history`** گارد ندارد (تاریخچه است، نه snapshot جاری) — خارج از دامنه‌ی فاز.
5. **`compare_versions`** تحلیل ذخیره‌شده‌ی هر نسخه را می‌خواند؛ با پاک‌سازی/تحلیل مجدد (بند ۳.۴)
   رکوردهای آلوده حذف می‌شوند. اگر گارد سخت‌گیرانه روی `/compare` لازم است، در فاز بعد اضافه می‌شود.

*گزارش فاز ۱۹ — تهیه‌شده در ۱۴۰۵/۰۷/۰۴.*

