# 📋 گزارش فاز ۱۵.۳ — پرفرمنس Dashboard با SQL Aggregation

> **تاریخ:** ۱۴۰۵/۰۷/۰۳ (2026-09-25)
> **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ ۵ endpoint بهینه شد — ✅ خروجی **کاملاً یکسان** (تأییدشده) — ✅ ۳۳/۳۳ تست پاس
> **فایل‌های تغییر‌یافته:** `backend/app/api/analytics.py` · `backend/app/api/strategies.py` · `backend/requirements.txt`

---

## ۱. مشکل اصلی

```python
# analytics.py (قبل)
all_trades = db.query(Trade).all()          # ← کل جدول + هیدراته‌کردن ORM
for _t in all_trades:
    _t.close_time = _ensure_utc(_t.close_time)
# ... فیلتر بازه و همهٔ محاسبات در Python روی لیست کامل
```

- **هزینه:** لود همهٔ ردیف‌ها به‌صورت **ORM object کامل** (۲۰+ ستون + identity map + lazy loads).
- **فیلتر تاریخ:** بعد از لود، در Python ⇒ حتی وقتی کاربر یک بازهٔ کوچک انتخاب می‌کند، کل جدول خوانده می‌شود.
- **با ۱۰٬۰۰۰+ معامله:** پاسخ چند ثانیه‌ای.

---

## ۲. راه‌حل — Helpers مشترک جدید

در `analytics.py` (بالای فایل) سه helper اضافه شد:

```python
def _net_expr():
    """عبارت SQL سود/زیان خالص: pnl + commission + swap (با COALESCE)"""
    return (
        func.coalesce(Trade.pnl, 0.0)
        + func.coalesce(Trade.commission, 0.0)
        + func.coalesce(Trade.swap, 0.0)
    )

def _parse_bound(value: Optional[str], end: bool = False):
    """تبدیل رشتهٔ ISO به datetime آگاه از timezone (UTC)"""   # مشترک بین endpointها
    ...

def _scope_filter(query, df_bound, dt_bound):
    """اعمال فیلتر بازه در سطح SQL به‌جای فیلتر در Python"""
    if df_bound or dt_bound:
        query = query.filter(Trade.close_time.isnot(None))
    if df_bound:
        query = query.filter(Trade.close_time >= df_bound)
    if dt_bound:
        query = query.filter(Trade.close_time <= dt_bound)
    return query
```
به‌همراه importهای جدید: `from sqlalchemy import func, case, and_` و `from ..models.strategy import Trade` در سطح ماژول.

---

## ۳. `GET /api/analytics/dashboard`

### قبل (خلاصه)
```python
all_trades = db.query(Trade).all()
# فیلتر بازه در Python (حلقه روی همه)
closed_trades = [t for t in all_trades if t.close_time is not None]
wins = [t for t in closed_trades if net_pnl(t) > 0]
losses = [t for t in closed_trades if net_pnl(t) < 0]
gp = sum(net_pnl(t) for t in wins) ...
st = sorted(closed_trades, key=lambda t: t.close_time)     # برای DD/streak/sparkline
_vals = [net_pnl(t) for t in closed_trades]                # برای buckets
# + محاسبهٔ دوره‌ها با فیلتر Python
```

### بعد — آمار کلی در **یک کوئری SQL**
```python
agg = scope.with_entities(
    func.count(Trade.id),
    func.sum(case((is_closed, 1), else_=0)),                       # closed_count
    func.sum(net),                                                 # net_pnl (scope)
    func.sum(case((win_cond, net), else_=0.0)),                    # gross_profit
    func.sum(case((loss_cond, net), else_=0.0)),                   # gross_loss
    func.sum(case((win_cond, 1), else_=0)),                        # wins
    func.sum(case((loss_cond, 1), else_=0)),                       # losses
    func.max(case((win_cond, net), else_=0.0)),                    # largest_win
    func.min(case((loss_cond, net), else_=0.0)),                   # largest_loss
).one()
```

### بعد — توزیع PnL در **یک کوئری GROUP BY**
```python
_bucket_case = case(*[(cond, label) for label, cond in _bucket_defs], else_="> 500")
_bmap = {label: int(cnt) for label, cnt in
         closed_scope.with_entities(_bucket_case, func.count(Trade.id))
         .group_by(_bucket_case).all()}
pnl_distribution = [{"range": label, "count": _bmap.get(label, 0)} for label, _ in _bucket_defs]
```

### بعد — دوره‌ها + امروز در **یک کوئری**
```python
per = closed_scope.with_entities(
    func.sum(case((Trade.close_time >= ts, net), else_=0.0)),                                   # today pnl
    func.sum(case((Trade.close_time >= ts, 1), else_=0)),                                       # today count
    func.sum(case((and_(Trade.close_time >= ts, net > 0), 1), else_=0)),                        # today wins
    func.sum(case((Trade.close_time >= cm, net), else_=0.0)),                                   # month
    func.sum(case((and_(Trade.close_time >= pms, Trade.close_time < cm), net), else_=0.0)),     # prev month
    func.sum(case((Trade.close_time >= cq, net), else_=0.0)),                                   # quarter
    func.sum(case((Trade.close_time >= ys, net), else_=0.0)),                                   # year
).one()
```

### بعد — سکانس مرتب با **فقط ۲ ستون** (بدون ORM) برای DD/streak/اکوییتی
```python
narrow = (
    closed_scope.with_entities(Trade.close_time, net.label("net"), Trade.id)
    .order_by(Trade.close_time.asc(), Trade.id.asc())
    .all()
)
# equity_curve (تجمیع روزانه)، sparkline، max_dd، max_consecutive_losses
```
**هزینه:** `5 → 8` کوئری ثابت (مستقل از حجم داده)، اما هیچ ردیف کامل ORM لود نمی‌شود.

---

## ۴. `GET /api/analytics/risk-advanced`

### قبل
```python
all_trades = db.query(Trade).all()
for _t in all_trades: _t.close_time = _ensure_utc(_t.close_time)
closed = []
for t in all_trades:                        # ← فیلتر بازه در Python
    if t.close_time is None: continue
    if df_bound and t.close_time < df_bound: continue
    if dt_bound and t.close_time > dt_bound: continue
    closed.append(t)
closed.sort(key=lambda t: t.close_time)
returns = [net_pnl(t) for t in closed]
```

### بعد
```python
# فاز ۱۵.۳: فیلتر بازه در SQL + واکشی فقط ۳ ستون (بدون لود ORM)
_rows = (
    _scope_filter(db.query(Trade), df_bound, dt_bound)
    .filter(Trade.close_time.isnot(None))
    .with_entities(Trade.close_time, _net.label("net"), Trade.r_multiple)
    .order_by(Trade.close_time.asc(), Trade.id.asc())
    .all()
)
closed = [{"close_time": _ct, "net": float(_n or 0.0), "r_multiple": _r} for _ct, _n, _r in _rows]
returns = [c["net"] for c in closed]
```
> **نکته:** محاسبات پیچیده (Sharpe، Sortino، VaR/CVaR، Ulcer، Calmar) طبق درخواست **در Python باقی ماندند** چون به سری کامل مقادیر نیاز دارند؛ اما ورودی آن‌ها دیگر یک پروجکشن ۳ ستونی است، نه ORM کامل.

---

## ۵. `GET /api/analytics/risk-metrics` (بهینه‌سازی اضافه)

### قبل
```python
all_trades = db.query(Trade).all()
closed_trades = [t for t in all_trades if t.close_time is not None]
open_trades = [t for t in all_trades if t.close_time is None]
oe = sum(abs(t.pnl or 0) for t in open_trades)          # ← حلقه روی open trades
rv = [t.r_multiple for t in closed_trades if ...]
```

### بعد
```python
# ۵ ستون لازم، به ترتیب id (معادل ترتیب قبلی .all())
_rows = (db.query(Trade).filter(Trade.close_time.isnot(None))
         .with_entities(Trade.close_time, _net.label("net"), Trade.r_multiple, Trade.sl, Trade.open_price)
         .order_by(Trade.id.asc()).all())
closed_trades = [{...}, ...]
# exposure معاملات باز → یک کوئری SQL
oe = float(db.query(func.sum(func.abs(func.coalesce(Trade.pnl, 0.0))))
           .filter(Trade.close_time.is_(None)).scalar() or 0.0)
```
> **دقت:** ترتیب `closed_trades` عمداً با `ORDER BY id` حفظ شد چون `streak` در این endpoint روی ترتیب خام (نه مرتب‌شده بر اساس تاریخ) محاسبه می‌شود.

---

## ۶. `GET /api/analytics/calendar`

### قبل
```python
trades = query.order_by(Trade.close_time).all()      # ← ORM کامل
for t in trades:
    days[t.close_time.strftime("%Y-%m-%d")].append(t)
```

### بعد
```python
trades = (query.with_entities(
            Trade.id, Trade.symbol, Trade.direction, Trade.size,
            Trade.pnl, Trade.close_time, _net.label("net"))
          .order_by(Trade.close_time.asc()).all())
```

---

## ۷. `GET /api/strategies/{id}/stats`

### قبل
```python
all_trades = db.query(Trade).filter(Trade.version_id.in_(version_ids)).all()   # ← ORM کامل
def _net_pnl(t): return (t.pnl or 0) + (t.commission or 0) + (t.swap or 0)
```

### بعد
```python
# فاز ۱۵.۳: فقط ۳ ستون لازم (بدون لود ORM)
_rows = (db.query(Trade).filter(Trade.version_id.in_(version_ids))
         .with_entities(Trade.close_time, Trade.open_time, _net.label("net"))
         .order_by(Trade.id.asc()).all())
all_trades = [(ct, ot, float(n or 0.0)) for ct, ot, n in _rows]
```
> در `strategies.py` نیز یک `_net_expr()` محلی اضافه شد (چون helper اصلی در `analytics.py` است و import متقابل وابستگی ایجاد می‌کرد).

---

## ۸. وابستگی‌های گم‌شده (اضافه‌شده به `requirements.txt`)

```diff
 pydantic-settings
 slowapi
+
+# Export / PDF (فاز ۱۵.۳ — وابستگی‌های گم‌شده که export.py استفاده می‌کند)
+reportlab
+jdatetime
+arabic-reshaper
+python-bidi
```
**نسخه‌های نصب‌شده در venv:** `reportlab 5.0.1` · `jdatetime 6.1.0` · `arabic-reshaper 3.0.1` · `python-bidi 0.6.11`

---

## 🧪 اعتبارسنجی — اثبات «خروجی یکسان»

روش: **قبل از هر تغییری**، پاسخ ۶ endpoint با ۲۰۰۰ معاملهٔ ساختگی (`note="PHASE153_SEED"`) در JSON ذخیره شد (baseline)، سپس پس از refactor دوباره گرفته و **مقایسهٔ عمیق** (dict/list/عدد با دقت ۱e-6) انجام شد.

| Endpoint | خروجی | کوئری | زمان (قبل → بعد) | سرعت |
|---|---|---|---|---|
| `GET /api/analytics/dashboard` | ✅ IDENTICAL | 5 → 8 | 188.77 → **69.91** ms | **2.70×** |
| `GET /api/analytics/dashboard?date_from=…&date_to=…` | ✅ IDENTICAL | 5 → 8 | 166.04 → **75.45** ms | **2.20×** |
| `GET /api/analytics/risk-advanced` | ✅ IDENTICAL | 2 → 2 | 212.74 → **102.48** ms | **2.08×** |
| `GET /api/analytics/risk-metrics` | ✅ IDENTICAL | 2 → 3 | 160.06 → **46.74** ms | **3.42×** |
| `GET /api/strategies/{id}/stats` | ✅ IDENTICAL | 3 → 3 | 148.49 → **33.43** ms | **4.44×** |
| `GET /api/analytics/calendar` | ✅ IDENTICAL | 1 → 1 | 32.91 → **28.41** ms | 1.16× |
| | **ALL IDENTICAL: True** | | | |

> زمان‌ها = best-of-3 با ۲۰۰۰ معامله. `calendar` چون فقط معاملات یک ماه شمسی را برمی‌گرداند، مجموعه‌دادهٔ کوچکی دارد و عمدتاً نویز اندازه‌گیری است.

### تست‌های دیگر
| مورد | نتیجه |
|---|---|
| `python -m py_compile` (analytics + strategies) | ✅ OK |
| `pytest -q` | ✅ **۳۳ passed** |
| سلامت endpointها با دادهٔ واقعی (۱۸ معامله) | ✅ هر ۵ → `200` |
| پاک‌سازی دادهٔ تست | ✅ ۲۰۰۰ ردیف حذف شد (بازگشت به ۱۸) |
| فایل‌های موقت | ✅ همه پاک شدند |

---

## ✅ نتیجه‌گیری فاز ۱۵.۳

**دستاورد:**
1. ✅ حذف `db.query(Trade).all()` از **۵ endpoint** (dashboard، risk-advanced، risk-metrics، calendar، strategy_stats).
2. ✅ محاسبات تجمیعی (sum/count/max/min/group_by/case) به **SQL** منتقل شدند.
3. ✅ فیلتر بازهٔ تاریخ به **SQL** منتقل شد (قبلاً پس از لود کامل انجام می‌شد).
4. ✅ واکشی‌ها به **پروجکشن ۲–۷ ستونی** تبدیل شدند (به‌جای ORM کامل).
5. ✅ **خروجی هیچ endpoint تغییر نکرد** — اثبات‌شده با مقایسهٔ عمیق JSON.
6. ✅ ۴ وابستگی گم‌شده به `requirements.txt` اضافه شد.
7. ✅ سرعت: **۲ تا ۴.۴ برابر** روی ۲۰۰۰ معامله (و نسبت بهبود با رشد داده بیشتر می‌شود).

### 📌 تصمیم مهندسی دربارهٔ Window Functions
درخواست «استفاده از window functions برای streak و drawdown» بررسی شد، اما:
- **`max_consecutive_losses`**: کد اصلی `net == 0` را **شفاف** می‌بیند (streak را reset نمی‌کند). بازتولید دقیق این رفتار با window function در SQLite نیازمند CTE پیچیده و پرریسک است.
- **`max_dd` / `sparkline` / `equity_curve`**: به همان سکانس نیاز دارند که اکنون با **پروجکشن ۲ ستونی** خوانده می‌شود (سبک و سریع).

بنابراین برای **تضمین یکسان‌بودن خروجی**، این سه مورد روی لیست ۲ ستونی در Python محاسبه می‌شوند — گلوگاه واقعی (هیدراته‌کردن ORM) از بین رفت. این یک trade-off آگاهانه است و در صورت نیاز، نسخهٔ window-function در فاز بعد قابل افزودن است.

### 📌 آیتم باقی‌مانده برای فاز بعد
- `GET /api/analytics/yesterday` (`analytics.py:266`) هنوز `db.query(Trade).filter(...).all()` دارد. عمداً در این فاز دست نخورد چون **baseline برای مقایسه در دسترس نبود** و مقایسهٔ تاریخ در SQL با ذخیره‌سازی naive/aware در SQLite ریسک subtle دارد. پیشنهاد: در فاز ۱۵.۴ با تست اختصاصی.

*گزارش فاز ۱۵.۳ — تهیه‌شده در ۱۴۰۵/۰۷/۰۳.*

