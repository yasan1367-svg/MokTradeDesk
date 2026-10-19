# PHASE 52 — Strategy Ranking (New Formula)

> **تاریخ:** ۱۴۰۵/۰۷/۱۱ (2026-10-02) · **وضعیت:** ✅ پیاده‌شده · ⛔ آمادهٔ commit (منتظر تأیید کاربر)

---

## ۱) خلاصهٔ اجرایی

فرمول `calculate_version_score` از یک امتیاز **دلاری‌محور و ناقص** (فاز 48a) به یک
امتیاز **کیفیت‌محور با آگاهی از نمونه** (فاز ۵۲) بازنویسی شد. خروجی تابع از `float`
به `dict` تغییر کرد تا علاوه بر `score`، **وضعیت نمونه**، **هشدارها** و **اجزای امتیاز**
در اختیار UI قرار گیرند.

- **Backend:** ۳ فایل تغییر + ۱ فایل تست جدید + ۲ فایل تست به‌روزرسانی.
- **Frontend:** ۲ فایل تغییر (نشان وضعیت نمونه + هشدارها + اجزای امتیاز در جدول/Drawer).
- **تست‌ها:** `400 passed + 1 xfailed` (backend) · `29 passed` (vitest) · TSC=0 · BUILD=0.

---

## ۲) فرمول قدیم vs جدید

### فرمول قدیم (فاز 48a) — `float`
```python
win_score  = min(win_rate, 100)
pf_score   = min(profit_factor * 20, 100)
pnl_score  = min(max(net_pnl / 10, 0), 100)
dd_penalty = min(max_dd / 10, 50)
score = win*0.35 + pf*0.35 + pnl*0.30 − dd_penalty*0.20     # کلمپ 0..100
```

**ایرادها:** PnL دلاری (سقف سریع) · بی‌توجه به اندازهٔ حساب · بدون درصد بازده ·
بدون ریسک هر معامله · بی‌توجه به تعداد معاملات · DD جریمهٔ محدود · Win Rate تنها معیار کیفیت.

### فرمول جدید (فاز ۵۲) — `dict`
```python
expectancy_score = clamp(expectancy_r / 1.0, 0, 1) * 100      # وزن ۴۰٪  (مهم‌ترین)
win_rate_score   = clamp(win_rate, 0, 100)                    # وزن ۲۰٪
pf_score         = clamp(profit_factor / 5 * 100, 0, 100)      # وزن ۲۰٪
dd_score         = clamp(100 - dd_percent * 5, 0, 100)         # وزن ۲۰٪  (کمتر بهتر)

score = (Σ وزن‌دار) − sample_penalty                            # کلمپ 0..100

sample_status:  n<10 ⇒ «خیلی کم» (−۳۰) | n<30 ⇒ «ناکافی» (−۱۵) | n≥30 ⇒ «کافی» (۰)
dd_percent   = max_dd_percent  یا  max_dd / ASSUMED_ACCOUNT_SIZE(10000) * 100
```

**خروجی:**
```json
{
  "score": 74.0,
  "sample_status": "کافی",
  "warnings": [],
  "components": {
    "expectancy_score": 100.0, "win_rate_score": 50.0,
    "pf_score": 20.0, "dd_score": 100.0, "sample_penalty": 0.0
  }
}
```

### نمونهٔ عددی (win_rate=50٪ · PF=2 · expectancy_r=0.4 · max_dd=1000 · n=40)
| فرمول | محاسبه | Score |
|---|---|---|
| قدیم | 17.5 + 14 + (net) − 10 | وابسته به PnL دلاری |
| جدید | 16 + 10 + 8 + 10 | **۴۴.۰** |

---

## ۳) تغییرات فایل‌به‌فایل

### Backend
| فایل | تغییر |
|---|---|
| `app/services/version_score.py` | بازنویسی کامل: `calculate_version_score → dict` + `ASSUMED_ACCOUNT_SIZE=10000` + `sample_status`/`warnings`/`components` + `_dd_percent()` |
| `app/services/analysis_service.py` | `compare_versions()`: مصرف `["score"]` + افزودن `sample_status`/`warnings`/`components` به هر item |
| `tests/test_phase48a_score.py` | آپدیت ۴ تست قدیمی برای خروجی dict |
| `tests/test_phase48a_comparison.py` | آپدیت `test_compare_score_calculation` (`["score"]` + سه فیلد جدید) |
| `tests/test_phase52_score_v2.py` | 🆕 ۱۰ تست جدید |

### Frontend
| فایل | تغییر |
|---|---|
| `src/api/client.ts` | `VersionComparisonItem` + `sample_status?` / `warnings?` / `components?` |
| `src/pages/ComparisonPage.tsx` | ستون «وضعیت نمونه» (Badge رنگی) + نشان هشدار (tooltip) + نمایش هشدارها/اجزای امتیاز در Drawer |


---

## ۴) تست‌ها

### ۱۰ تست جدید — `tests/test_phase52_score_v2.py`
| # | تست | انتظار |
|:--|:--|:--|
| ۱ | `test_score_v2_perfect_metrics` | ۱۰۰ + «کافی» + بدون هشدار |
| ۲ | `test_score_v2_low_sample_penalty` | n=15 ⇒ ۸۵ (جریمهٔ ۱۵) + «ناکافی» |
| ۳ | `test_score_v2_high_dd_penalty` | DD=20% ⇒ dd_score=0 و score=۸۰ |
| ۴ | `test_score_v2_expectancy_priority` | Expectancy بر Win Rate غالب است (۷۴ > ۴۸) |
| ۵ | `test_sample_status_very_low` | n=5 ⇒ «خیلی کم» |
| ۶ | `test_sample_status_low` | n=20 ⇒ «ناکافی» |
| ۷ | `test_sample_status_enough` | n=30 ⇒ «کافی» |
| ۸ | `test_warnings_high_dd` | هشدار «Drawdown بالا» |
| ۹ | `test_warnings_low_expectancy` | هشدار «Expectancy ضعیف» |
| ۱۰ | `test_score_clamped_0_100` | کلمپ ۰..۱۰۰ |

### ۵ تست قدیمی آپدیت‌شده
`test_phase48a_score.py` (۴ تست) + `test_phase48a_comparison.py::test_compare_score_calculation` (۱ تست).

### نتیجهٔ اجرا
```
Backend : 400 passed, 1 xfailed in 27.91s   (قبل: 391 · +10 جدید، ۱ xfail همان /wallets/convert)
Frontend: TSC_EXIT=0 · vitest 29 passed · BUILD_EXIT=0
```

---

## ۵) نکات طراحی / تصمیم‌ها

1. **مبنای Drawdown درصدی (گام ۲ — گزینهٔ الف):** اندازهٔ حساب در DB نیست ⇒ از ثابت
   `ASSUMED_ACCOUNT_SIZE = 10000 USDT` استفاده شد. اگر متریک `max_dd_percent` موجود
   باشد، همان اولویت دارد (قابل‌توسعه در آینده).
2. **پاداش نبودِ Drawdown:** هر نسخهٔ بدون افت (max_dd=0) به‌صورت ساختاری ۲۰ امتیاز
   از مؤلفهٔ DD می‌گیرد. این رفتار مطابق فرمول پیشنهادی است و در
   `test_score_zero_metrics` مستند شده است.
3. **سازگاری:** فیلد `score` در item همان `float` باقی ماند (فقط از `["score"]` استخراج
   می‌شود) ⇒ `RankResponse`/`CompareResponse`/چارت‌ها دست‌نخورده.
4. `net_pnl` دیگر در فرمول امتیاز دخالت ندارد (طبق طرح) ولی همچنان در `metrics` و UI نمایش داده می‌شود.

---

## ۶) آماده‌بودن برای commit

### فایل‌های مرتبط با فاز ۵۲ (این کار)
```
 M backend/app/services/version_score.py
 M backend/app/services/analysis_service.py
 M backend/tests/test_phase48a_score.py
 M backend/tests/test_phase48a_comparison.py
?? backend/tests/test_phase52_score_v2.py
 M frontend/src/api/client.ts
 M frontend/src/pages/ComparisonPage.tsx
```

### فایل‌های نامرتبط (از کار قبلی «Fix Test Failures» — همچنان uncommitted)
```
 M backend/app/api/finance.py
 M backend/app/services/financial_reporting.py
 M backend/app/services/payout_service.py
 M backend/tests/test_finance.py
 M backend/tests/test_phase33_withdrawal.py
 M backend/tests/test_phase38_personal_finance.py
 M backend/tests/test_phase39_wallet.py
 M backend/tests/test_phase44_currency.py
 M backend/tests/test_phase45_ledger_integrity.py
```

**پیشنهاد commit (پس از تأیید):**
```
git add backend/app/services/version_score.py \
        backend/app/services/analysis_service.py \
        backend/tests/test_phase48a_score.py \
        backend/tests/test_phase48a_comparison.py \
        backend/tests/test_phase52_score_v2.py \
        frontend/src/api/client.ts \
        frontend/src/pages/ComparisonPage.tsx

git commit -m "Phase 52: new version ranking formula (expectancy/sample/dd-percent)"
```

> ⛔ **commit زده نشد** — منتظر تأیید کاربر.

**git log (آخرین ۳):**
```
c55433c (HEAD -> main, origin/main) WIP: Add [قابلیت ۱] + fix [باگ ۲] + improve [چیز ۳]
1e50245 Phase 48c: REAL_PERSONAL tab in Analysis + URL persistence in Comparison + 15 tests
937ab28 Phase 48b: Fix getAnalysis/getVersionAnalysis to send test_type + 5 tests
```
