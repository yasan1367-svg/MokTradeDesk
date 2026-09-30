# PHASE 47a — فقط حیاتی (Prop DD ساده + Fail-closed)

> تاریخ: 2026-09-30 · وضعیت: ✅ کامل — **بدون commit** (منتظر تأیید کاربر)
> دامنه: تک‌نفره/شخصی · پراپ‌فرم **Static + Balance** · همه محاسبات روی **تریدهای بسته**

---

## ۱) خلاصهٔ اجرایی

کاربر Phase 47 کامل را کنار گذاشت و فقط ۳ چیز حیاتی خواست:

1. **DD ساده** — فقط `static + balance`، حذف `trailing` و `dd_basis`.
2. **Fail-closed** — نبودِ حد (`max_daily_dd` / `max_total_dd` / `profit_target`) ⇒ `unconfigured` و **هرگز** «آمادهٔ پاس».
3. تست نهایی + گزارش.

هدف: «موتور فقط اشتباه محاسباتی نداشته باشد».

نتیجه: **۳۵۷ passed** · **ruff: All checks passed** · بدون migration جدید.

---

## ۲) تسک‌ها

### 47a.0 — بکاپ ✅
```
C:\Backup\trading_desk.db.before_phase47a   (417,792 bytes)
```

### 47a.1 — ساده‌سازی: فقط static + balance ✅
فایل: `backend/app/services/prop_rule_engine.py`

- **حذف `dd_basis`** — همیشه فقط تریدهای بستهٔ نهایی‌شده:
  ```python
  closed_trades = [t for t in trades if t.close_time is not None]
  ```
- **حذف `dd_mode`/`trailing`** — همیشه static (گزینهٔ trailing کنار گذاشته شد).
- **تابع `_total_drawdown` ساده شد** → `(total_dd, equity_floor, violated)`:
  ```python
  equity = initial; min_equity = initial
  for trade in ordered_trades:
      equity += metrics.net_pnl(trade)
      min_equity = min(min_equity, equity)
  total_dd     = max(0, initial - min_equity)
  equity_floor = initial - max_dd_limit
  violated     = min_equity < equity_floor
  ```
- **Model** (`backend/app/models/prop.py`): ستون `dd_basis` کامنت شد (migration زده نشد؛ ستون DB دست‌نخورده و نادیده گرفته می‌شود). `dd_mode` حفظ شد ولی موتور آن را نادیده می‌گیرد.
- خروجی موتور: حذف `dd_mode`/`dd_basis`/`peak_equity`؛ افزودن `unconfigured` (و نگه‌داشتن `equity_floor`).

**نکتهٔ محاسباتی مهم:** `min_equity` شامل نقطهٔ شروع است. مثال `10000 → 10500 → 10200 → 10800` ⇒ `min = 10000` (نه 10200) ⇒ **DD = 0**؛ چون حساب هرگز زیر موجودی اولیه نرفته است.

### 47a.2 — Fail-closed ✅
- نبودِ هر حد پیام هشدار در `violations` می‌گذارد و `unconfigured = True` می‌کند.
- در حالت unconfigured: `ready_to_pass = False` و `suggested_status = "unconfigured"`.
- سایر فیلدها (max_daily_loss/trading_days/…) همچنان محاسبه و بازگردانده می‌شوند تا مصرف‌کننده‌ها نشکنند.

> انحراف جزئی از اسنیپت پلن: به‌جای بازنویسی `"status"` (که وضعیت واقعی مرحله است)، از `suggested_status` + فیلد جدید `unconfigured` استفاده شد تا معنای `status` خراب نشود.

### 47a.3 — تست نهایی + گزارش ✅
```
pytest -q           →  357 passed in 19.53s
ruff check .        →  All checks passed!  (exit 0)
```

---

## ۳) تست‌ها

**جدید در `tests/test_phase47_prop_rules.py`:**
| تست | بررسی |
|---|---|
| `test_static_dd_simple` | مثال ۳-تریدی؛ `min_equity=10000` ⇒ DD=0، floor=9000 |
| `test_static_dd_violated` | افت ۱۲۰۰ زیر کف ۹۰۰۰ ⇒ `total_dd_violated=True`، `failed_total_dd` |
| `test_static_dd_no_violation` | افت ۸۰۰ در محدوده ⇒ بدون نقض |
| `test_unconfigured_stage_not_ready_to_pass` | بدون حد + سود بزرگ ⇒ `ready_to_pass=False`، `unconfigured` |
| `test_stage_with_no_limits_warns` | ۳ پیام هشدار در `violations` |

**حفظ‌شده:** `test_group_daily_pnl_respects_offset`، `test_daily_dd_uses_day_boundary`، `test_prop_stage_default_dd_mode_static`، `test_prop_stage_default_day_boundary_utc`.

**حذف‌شده (منسوخ با حذف trailing/dd_basis):**
- `test_prop_stage_default_dd_basis_balance`
- `test_trailing_vs_static_dd_differs`
- `test_daily_dd_trailing`

**به‌روزرسانی `tests/test_phase43_unified_metrics.py`:**
- `_seed` دیگر `dd_mode="trailing"` پین نمی‌کند.
- `test_max_drawdown_consistent`: انتظار موتور = **static** (`max(0, initial − min_equity)`)؛ AnalysisService همچنان trailing را به‌عنوان متریک نمایشی گزارش می‌کند.
- `test_max_total_dd_static`: `equity_floor == 9000`، `max_total_dd == 0`، بدون نقض.

---

## ۴) شمارش تست‌ها
```
355 (پس از 47.2)  − ۳ حذف‌شده  + ۵ جدید  =  357 passed
```

---

## ۵) آماده برای Phase 48
- موتور DD اکنون **یک تعریف واحد** و fail-closed دارد ⇒ تصمیم «آمادهٔ پاس» دیگر fail-open نیست.
- محدودیت‌های آگاهانه (خارج از دامنهٔ 47a): `initial_balance or 10000.0` هنوز هست، `PropEquitySnapshot`/Reconcile، `pass_stage` atomic، CostType، `/payouts/stats` و … کنار گذاشته شدند.

---

## ۶) وضعیت Git (بدون commit)
```
M backend/app/models/prop.py                    (+9/-... )
M backend/app/services/prop_rule_engine.py      (+104/-...)
M backend/tests/test_phase43_unified_metrics.py (+27/-...)
M backend/tests/test_phase47_prop_rules.py      (+194/-...)
HEAD = 3d4f149 (Phase 47.1)
```
⛔ commit انجام نشد — منتظر تأیید کاربر.
