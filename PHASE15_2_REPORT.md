# 📋 گزارش فاز ۱۵.۲ — رفع N+1 Queryها + Rate Limiting

> **تاریخ:** ۱۴۰۵/۰۷/۰۳ (2026-09-25)
> **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ ۶ محل N+1 رفع شد — ✅ Rate Limiting فعال شد — ✅ ۳۳/۳۳ تست پاس
> **فایل‌های تغییر‌یافته:** `prop.py` · `personal.py` · `strategies.py` · `imports.py` · `export.py` · `main.py` · `requirements.txt` · **جدید:** `core/rate_limit.py`

---

## بخش الف — رفع N+1 Queryها

### ۱. `prop.py` — `get_firms` (N+1 اصلی)

#### قبل
```python
def get_firms(db: Session = Depends(get_db)):
    firms = db.query(PropFirm).all()
    result = []
    for f in firms:
        accounts = db.query(PropAccount).filter(PropAccount.prop_firm_id == f.id).all()  # ← N+1
        ...
            "accounts_count": len(accounts),
```
**هزینه:** `1 + N` کوئری (N = تعداد شرکت‌ها).

#### بعد
```python
def get_firms(db: Session = Depends(get_db)):
    # selectinload: شمارش اکانت‌ها در یک کوئری (رفع N+1 — فاز ۱۵.۲)
    firms = db.query(PropFirm).options(selectinload(PropFirm.accounts)).all()
    result = []
    for f in firms:
        result.append({... "accounts_count": len(f.accounts)})
```
**هزینه:** `2` کوئری ثابت. ✅

---

### ۲. `prop.py` — `get_accounts` (N+1 اضافه که در بررسی پیدا شد)

#### قبل
```python
    accounts = db.query(PropAccount).all()
    for a in accounts:
        firm = db.query(PropFirm).filter(PropFirm.id == a.prop_firm_id).first()        # ← N+1
        stages = db.query(PropStage).filter(PropStage.prop_account_id == a.id).all()    # ← N+1
```
**هزینه:** `1 + 2N`.

#### بعد
```python
    # selectinload: firm و stages هر کدام در یک کوئری (رفع N+1 — فاز ۱۵.۲)
    accounts = (
        db.query(PropAccount)
        .options(selectinload(PropAccount.firm), selectinload(PropAccount.stages))
        .all()
    )
    for a in accounts:
        firm = a.firm
        result.append({... "firm_name": firm.name if firm else "نامشخص", "stages_count": len(a.stages)})
```
**هزینه:** `3` کوئری ثابت. ✅

---

### ۳. `personal.py` — `get_reviews` (N+1 اصلی)

#### قبل
```python
    reviews = db.query(JournalReview).order_by(JournalReview.created_at.desc()).all()
    for r in reviews:
        trade = db.query(Trade).filter(Trade.id == r.trade_id).first()          # ← N+1
        screenshots = db.query(Screenshot).filter(                            # ← N+1
            Screenshot.entity_type == "review",
            Screenshot.entity_id == r.id,
        ).all()
```
**هزینه:** `1 + 2N`.

#### بعد
```python
    # selectinload: trade و screenshots هر کدام در یک کوئری (رفع N+1 — فاز ۱۵.۲)
    reviews = (
        db.query(JournalReview)
        .options(selectinload(JournalReview.trade), selectinload(JournalReview.screenshots))
        .order_by(JournalReview.created_at.desc())
        .all()
    )
    for r in reviews:
        trade = r.trade
        result.append({... "screenshots_count": len(r.screenshots)})
```
**هزینه:** `3` کوئری ثابت. ✅

---

### ۴. `personal.py` — `get_prop_accounts_for_ledger` (N+1 اضافه)

#### قبل
```python
    accounts = db.query(PropAccount).all()
    for a in accounts:
        firm = db.query(PropFirm).filter(PropFirm.id == a.prop_firm_id).first()   # ← N+1
```

#### بعد
```python
    # selectinload: firm در یک کوئری (رفع N+1 — فاز ۱۵.۲)
    accounts = db.query(PropAccount).options(selectinload(PropAccount.firm)).all()
    for a in accounts:
        firm = a.firm
```
**هزینه:** `2` کوئری ثابت. ✅

---

### ۵. `strategies.py` — سه محل N+1 (مورد سوم درخواست)

#### ۵.۱ `get_strategies` (`GET /api/strategies/`)
**قبل:** `1 + N` (یک کوئری شمارش نسخه‌ها برای هر استراتژی)
```python
    strategies = db.query(Strategy).all()
    for s in strategies:
        versions = db.query(StrategyVersion).filter(StrategyVersion.strategy_id == s.id).all()  # ← N+1
```
**بعد:** `2` کوئری ثابت
```python
    strategies = db.query(Strategy).options(selectinload(Strategy.versions)).all()
    for s in strategies:
        result.append({... "versions_count": len(s.versions)})
```

#### ۵.۲ `get_all_versions` (`GET /api/strategies/versions/all`)
**قبل:** `1 + 2N` (یک کوئری برای نام استراتژی + یک `count()` برای هر نسخه)
```python
    versions = db.query(StrategyVersion).all()
    for v in versions:
        strategy = db.query(Strategy).filter(Strategy.id == v.strategy_id).first()          # ← N+1
        trades_count = db.query(Trade).filter(Trade.version_id == v.id).count()            # ← N+1
```
**بعد:** `3` کوئری ثابت
```python
    versions = db.query(StrategyVersion).options(selectinload(StrategyVersion.strategy)).all()
    counts = _trades_count_by_version(db, [v.id for v in versions])
    for v in versions:
        strategy = v.strategy
        result.append({... "trades_count": counts.get(v.id, 0)})
```

#### ۵.۳ `get_strategy_versions` (`GET /api/strategies/{id}/versions`)
**قبل:** `1 + N`
```python
    for v in versions:
        trades_count = db.query(Trade).filter(Trade.version_id == v.id).count()   # ← N+1
```
**بعد:** `2` کوئری ثابت
```python
    counts = _trades_count_by_version(db, [v.id for v in versions])
    for v in versions:
        result.append({... "trades_count": counts.get(v.id, 0)})
```

#### Helper جدید (یک کوئری گروهی به‌جای N تا `count()`)
```python
def _trades_count_by_version(db: Session, version_ids: List[int]) -> dict:
    """شمارش معاملات هر نسخه در یک کوئری گروهی (رفع N+1 — فاز ۱۵.۲)"""
    if not version_ids:
        return {}
    rows = (
        db.query(Trade.version_id, func.count(Trade.id))
        .filter(Trade.version_id.in_(version_ids))
        .group_by(Trade.version_id)
        .all()
    )
    return {version_id: count for version_id, count in rows}
```

---

## بخش ب — Rate Limiting

### ۶. ماژول مشترک جدید: `app/core/rate_limit.py`
```python
"""Rate Limiting مشترک پروژه (فاز ۱۵.۲) — مبتنی بر slowapi."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)          # کلید: IP درخواست‌کننده

IMPORT_RATE_LIMIT = "10/minute"   # آپلود و پردازش فایل (Soft4X / MT4)
EXPORT_RATE_LIMIT = "20/minute"   # ساخت CSV/PDF (بار سنگین CPU/حافظه)
```

### ۶.۱ `main.py` — ثبت Limiter
```python
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from .core.rate_limit import limiter
...
# ═════════════════════════════════════════════
# Rate Limiting (فاز ۱۵.۲)
# ═════════════════════════════════════════════
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

### ۶.۲ `imports.py` — محدودسازی ۲ endpoint (۱۰ درخواست/دقیقه)
```python
@router.post("/soft4x")
@limiter.limit(IMPORT_RATE_LIMIT)
async def import_soft4x(
    request: Request,          # ← لازم برای slowapi
    file: UploadFile = File(...),
    ...
```
```python
@router.post("/mt4")
@limiter.limit(IMPORT_RATE_LIMIT)
async def import_mt4(request: Request, file: UploadFile = File(...), ...):
```

### ۶.۳ `export.py` — محدودسازی ۴ endpoint (۲۰ درخواست/دقیقه)
```python
@router.get("/trades/csv")
@limiter.limit(EXPORT_RATE_LIMIT)
def export_trades_csv(request: Request, version_id: Optional[int] = None, ...):
```
اعمال‌شده روی: `/trades/csv` · `/trades/pdf` · `/analysis/pdf` · `/dashboard/pdf`.

### ۶.۴ `requirements.txt`
```diff
 pydantic-settings
+slowapi
```
> **نصب‌شده در venv:** `slowapi-0.1.10` (+ `limits-5.8.0`, `deprecated-1.3.1`, `wrapt-2.4.1`)


---

## 🧪 اعتبارسنجی

### شمارش کوئری‌های SELECT (اثبات رفع N+1)
با یک `event.listens_for(engine, "before_cursor_execute")` تعداد SELECTها شمرده شد:

| Endpoint | قبل (تخمینی) | بعد (اندازه‌گیری‌شده) | ثابت با رشد داده؟ |
|---|---|---|---|
| `GET /api/prop/firms` | `1 + N` | **2** | ✅ (۱ firm → ۴ firm: همان ۲) |
| `GET /api/prop/accounts` | `1 + 2N` | **3** | ✅ |
| `GET /api/strategies/` | `1 + N` | **2** | ✅ |
| `GET /api/strategies/versions/all` | `1 + 2N` | **3** | ✅ |
| `GET /api/personal/journal/reviews` | `1 + 2N` | **3** | ✅ |
| `GET /api/personal/prop-accounts-list` | `1 + N` | **2** | ✅ |

**اثبات کلیدی:** پس از افزودن ۳ شرکت پراپ جدید (rows: ۱ → ۴)، تعداد SELECTهای `GET /api/prop/firms` **ثابت روی ۲** ماند ⇒ N+1 واقعاً برطرف شده است.

### تست Rate Limiting
۱۲ درخواست پی‌درپی به `POST /api/imports/soft4x` (سقف ۱۰/دقیقه):
```
status codes: [500, 500, 500, 500, 500, 500, 500, 500, 500, 500, 429, 429]
```
- ۱۰ درخواست اول پردازش شدند (کد ۵۰۰ به‌دلیل فایل xlsx جعلی — مورد انتظار).
- از درخواست یازدهم به بعد → **429 Too Many Requests** ✅

### تست سلامت سایر بخش‌ها
| مورد | نتیجه |
|---|---|
| `python -m py_compile` (۷ فایل) | ✅ OK |
| `app.openapi()` | ✅ ۷۸ مسیر (بدون تغییر) |
| `limiter` ثبت‌شده | ✅ `app.state.limiter` |
| `GET /api/export/trades/csv` | ✅ `200` · `text/csv` |
| `pytest -q` | ✅ **۳۳ passed** |
| پاک‌سازی دادهٔ تست | ✅ ۹ ردیف (۳ firm + ۳ account + ۳ stage) حذف شد |

---

## ✅ نتیجه‌گیری فاز ۱۵.۲

**بخش الف — N+1 (۶ محل):**
1. ✅ `prop.py:get_firms` — `selectinload` (مورد درخواستی)
2. ✅ `prop.py:get_accounts` — `selectinload` (اضافه)
3. ✅ `personal.py:get_reviews` — `selectinload` (مورد درخواستی)
4. ✅ `personal.py:get_prop_accounts_for_ledger` — `selectinload` (اضافه)
5. ✅ `strategies.py:get_strategies` — `selectinload` (مورد سوم)
6. ✅ `strategies.py:get_all_versions` + `get_strategy_versions` — `selectinload` + کوئری گروهی `GROUP BY`

**بخش ب — Rate Limiting:**
7. ✅ ماژول `core/rate_limit.py` + ثبت در `main.py`
8. ✅ ۲ endpoint import → `10/minute`
9. ✅ ۴ endpoint export → `20/minute`
10. ✅ `slowapi` به `requirements.txt` اضافه و نصب شد

### 📌 نکات برای فاز بعدی
- **تنظیم سقف‌ها:** مقادیر `10/min` و `20/min` در `core/rate_limit.py` قابل تنظیم‌اند. برای محیط production ممکن است نیاز به سقف بالاتر یا کلید Redis باشد.
- **وابستگی‌های گم‌شده در `requirements.txt`:** هنگام بررسی مشخص شد `reportlab`، `jdatetime`، `arabic-reshaper` و `python-bidi` (که `export.py` استفاده می‌کند) در `requirements.txt` **ثبت نشده‌اند** — پیشنهاد می‌شود در فاز بعدی اضافه شوند.
- **پیشنهاد فاز ۱۵.۳ (P1 باقی‌مانده):** `BE-07` بازآرایی محاسبات داشبورد به SQL Aggregation، و `FE-01` Code Splitting صفحات.

*گزارش فاز ۱۵.۲ — تهیه‌شده در ۱۴۰۵/۰۷/۰۳.*

