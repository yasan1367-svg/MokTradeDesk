# PHASE 53.2 — Sharpe/Sortino + Risk Metrics Scope

> **تاریخ:** ۱۴۰۵/۰۷/۱۱ (2026-10-02) · **وضعیت:** ✅ پیاده‌شده · ⛔ آمادهٔ commit (منتظر تأیید کاربر)
> **مبنا:** Phase 53.1 = `d5004b7` · **Alembic head:** `f53a1b2c3d4e` (بدون migration جدید)

---

## ۱) خلاصهٔ اجرایی

دو باگ آماری که Audit ChatGPT کشف کرد، در **هر دو** endpoint ریسک (`/risk-metrics` و `/risk-advanced`) رفع شد:

| تسک | باگ | راه‌حل |
|:--|:--|:--|
| **53.2.1** (A-04) | Sharpe/Sortino روی **سود دلاری هر معامله** با ضریب سالانه‌سازی `√252` (ضریب دادهٔ روزانه) | بازده **دورانهٔ روزانه** (`_daily_returns`) + حذف `√252` |
| **53.2.2** (A-03) | `avg_b` از **همهٔ** حساب‌های شخصی (بی‌قید به scope/ارز) | `avg_b` scope-aware: backtest/forward⇒۱۰۰۰۰ · real⇒حساب‌های مرتبط (fallback ۱۰۰۰۰) · all⇒همه (fallback ۱۰۰۰۰) |

- **Backend:** فقط `app/api/analytics.py` (۳ helper جدید + ۲ endpoint).
- **Frontend:** بدون تغییر (نام کلیدها ثابت ماند).
- **تست‌ها:** `410 passed + 1 xfailed` (قبلاً ۴۰۶ ⇒ **+۴**).

---

## ۲) تسک 53.2.1 — Sharpe/Sortino بدون سالانه‌سازی

### قبل (در هر دو endpoint)
```python
returns = [c["net"] for c in closed]          # PnL دلاری هر معامله
std = (sum((r - mean) ** 2 for r in returns) / len(returns)) ** 0.5
sharpe  = (mean / std) * math.sqrt(252)       # ← √252
sortino = (mean / ddev) * math.sqrt(252)      # ← √252
```

### بعد
```python
def _daily_returns(closed) -> list:
    """جمع net_pnl به تفکیک روزِ بسته‌شدن (بازده دوره‌ای روزانه)."""
    daily = {}
    for c in closed:
        day = c["close_time"].date()
        daily[day] = daily.get(day, 0.0) + float(c.get("net", 0.0) or 0.0)
    return [daily[d] for d in sorted(daily)]

def _sharpe_sortino(series) -> tuple:
    """Sharpe/Sortino روی بازده دوره‌ای — بدون سالانه‌سازی."""
    n = len(series)
    if n < 2:
        return 0.0, 0.0
    mean = sum(series) / n
    std = (sum((x - mean) ** 2 for x in series) / n) ** 0.5
    sharpe = (mean / std) if std > 0 else 0.0
    neg = [x for x in series if x < 0]
    if not neg:
        return sharpe, 0.0
    ddev = (sum(x ** 2 for x in neg) / n) ** 0.5
    return sharpe, (mean / ddev) if ddev > 0 else 0.0
```

مصرف (هر دو endpoint):
```python
sharpe, sortino = _sharpe_sortino(_daily_returns(closed_trades))
```

### نکات مهم
1. **`ar`/`mean_ret` دست‌نخورده ماندند** چون `expectancy` و `expectancy_r` از آن‌ها استفاده می‌کنند (میانگین هر معامله). فقط محاسبهٔ Sharpe/Sortino به سری روزانه منتقل شد.
2. سری روزانه = **جمع PnL همهٔ معاملاتِ یک روز** ⇒ تعداد دوره‌ها = تعداد روزهای معاملاتی (نه تعداد معاملات).
3. `import math` (که فقط برای `sqrt(252)` بود) از هر دو تابع حذف شد.
4. **مثال مرجع** (روزها: `[100, -100, 300]`): `mean=100`, `std≈163.3`, `ddev≈57.7` ⇒ Sharpe≈**0.61**، Sortino≈**1.73** (قبلاً با √252: ≈9.7 و ≈27.5).

### 🟡 خارج از دامنه (Skip شد طبق تأیید)
`strategies.py:465`: `sharpe_ratio = mean / std * sqrt(total)` (برای `StrategyPage`) — طبق تأیید کاربر تغییر نکرد.



---

## ۳) تسک 53.2.2 — مبنای سرمایهٔ scope-aware

### قبل (هر دو endpoint)
```python
from ..models.trading import PersonalTradingAccount as _PTA
_accts = db.query(_PTA).all()                       # ← همهٔ حساب‌ها، بی‌قید
avg_b = sum(a.current_balance or 0 for a in _accts) / len(_accts) if _accts else 10000
```
⇒ با انتخاب scope بک‌تست/فوروارد یا چند‌حسابی، سرمایهٔ مبنا و مشتقاتش
(`position_sizing`, `open_risk_percent`, `risk_of_ruin`) بی‌معنا می‌شد.

### بعد
```python
def _scope_avg_balance(db, scope, account_ids) -> float:
    if scope in ("backtest", "forward"):        # حساب واقعی ندارد
        return ASSUMED_BALANCE                  # 10000
    if scope == "real":
        ids = [i for i in (account_ids or []) if i is not None]
        if not ids:
            return ASSUMED_BALANCE              # 0 گمراه‌کننده بود (RoR=100٪)
        avg = db.query(func.avg(PersonalTradingAccount.current_balance)) \
                .filter(PersonalTradingAccount.id.in_(ids)).scalar()
        return float(avg) if avg else ASSUMED_BALANCE
    accts = db.query(PersonalTradingAccount).all()   # all
    return (sum(a.current_balance or 0 for a in accts) / len(accts)) if accts else ASSUMED_BALANCE
```
- برای `real`، `account_ids` از ستون جدیدِ انتخابیِ `_rows` (`Trade.personal_trading_account_id`) جمع می‌شود.
- `ASSUMED_BALANCE = 10000.0` (طبق تصمیم شما: `0` ⇒ `risk_of_ruin = 100%` ⇒ گمراه‌کننده).

### مصرف `avg_b`
| endpoint | مصرف |
|:--|:--|
| `get_risk_metrics` | `position_sizing` · `risk_of_ruin` · `open_risk_percent` · خروجی `avg_balance` |
| `get_risk_advanced` | `risk_of_ruin` (`units = avg_b / avg_loss`) |

| scope | مبنا |
|:--|:--|
| `backtest` / `forward` | ۱۰۰۰۰ (فرضی) |
| `real` | میانگین موجودی حساب‌های شخصیِ ارجاع‌شده (fallback: ۱۰۰۰۰) |
| `all` | میانگین همهٔ حساب‌ها (fallback: ۱۰۰۰۰) |

---

## ۴) تست‌ها — `tests/test_phase53_risk_metrics.py` (۴ تست)

| تست | سناریو |
|:--|:--|
| `test_sharpe_no_annualization` | سری روزانهٔ `[100,-100,300]` ⇒ Sharpe≈۰.۶۱ (بدون √252) — **هر دو endpoint** |
| `test_sortino_no_annualization` | همان سری ⇒ Sortino≈۱.۷۳ — **هر دو endpoint** |
| `test_risk_metrics_uses_scope` | scope=real ⇒ `avg_balance=20000` (فقط حساب مرتبط، نه ۱۰۵۰۰ میانگین همه) |
| `test_risk_metrics_backtest_assumed_balance` | scope=backtest ⇒ `avg_balance=10000` (نه ۲۰۰۰۰ حساب موجود) |

### نتیجهٔ اجرا
```
Backend : 410 passed, 1 xfailed in 32.66s   (قبل: 406 · +4)
Frontend: بدون تغییر ⇒ نیازی به tsc/vitest نبود
```

---

## ۵) آماده‌بودن برای commit

```
 M backend/app/api/analytics.py
?? backend/tests/test_phase53_risk_metrics.py
```

**پیشنهاد commit (پس از تأیید):**
```
git add backend/app/api/analytics.py \
        backend/tests/test_phase53_risk_metrics.py

git commit -m "Phase 53.2: daily-return Sharpe/Sortino (no annualization) + scope-aware risk capital"
```

> ⛔ **commit زده نشد** — منتظر تأیید کاربر.

**git log (آخرین ۳):**
```
d5004b7 (HEAD -> main, origin/main) Phase 53.1: stale-analysis guard (trade.updated_at) + strategy delete safety (409)
fd848a8 Phase 52: new version ranking formula (expectancy/sample/dd-percent)
59b68f7 Fix: prop_stage_3 calculation + income at received + USD→USDT test updates
```

