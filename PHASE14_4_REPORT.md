# فاز ۱۴.۴ — آمار ریسک پیشرفته

**تاریخ:** 1405/07/03 | **وضعیت:** ✅ کامل

---

## ۱. Backend — endpoint جدید

**`GET /api/analytics/risk-advanced?date_from=&date_to=`** (`analytics.py`)

خروجی:
```jsonc
{
  "has_enough_data": true,
  "total_trades": 18,
  "sharpe_ratio": 3.609,
  "sortino_ratio": 9.552,
  "calmar_ratio": 87.233,
  "risk_of_ruin": 0.0,
  "var_95": -13.72,
  "cvar_95": -14.3,
  "max_consecutive_losses": 2,
  "max_consecutive_wins": 6,
  "avg_r_multiple": 0.282,
  "expectancy_r": 0.415,
  "kelly_criterion": 0.2684,
  "recovery_factor": 2.15,
  "ulcer_index": 8.52,
  "max_drawdown": 40.94,
  "r_multiple_distribution": [{ "range": "< -2R", "count": 0 }, ...],  // ۷ سطل
  "drawdown_curve": [{ "index": 1, "date": "...", "drawdown": 0, "drawdown_pct": 0 }, ...]
}
```
- فیلتر بازهٔ اختیاری (سازگار با داشبورد ۱۴.۳).
- درصدک بدون `numpy` (`_percentile`).
- Calmar سالیانه بر پایهٔ بازهٔ زمانی واقعی معاملات.

## ۲. Frontend — کارت «آمار ریسک پیشرفته» (جدید در داشبورد)
۱۴ شاخص با **Tooltip توضیحی** روی هرکدام:
- **Sharpe** (رنگ‌بندی: سبز >۱، زرد >۰.۵، قرمز ≤۰.۵)، **Sortino**، **Calmar**
- **Risk of Ruin** (سبز <۰.۰۵، زرد <۰.۱، قرمز ≥۰.۱)
- **VaR 95%** و **CVaR 95%**
- **Max Consecutive Losses/Wins**، **Avg R-Multiple**، **Expectancy (R)**، **Kelly**، **Recovery Factor**، **Ulcer Index**، **Max Drawdown**

## ۳. نمودارها
- **توزیع R-Multiple**: هیستوگرام ۷ سطل (رنگ سبز/قرمز).
- **منحنی Drawdown**: نمودار Area با گرادیان.

## ۴. UX
- **Dark Mode / RTL**: CSS variables + RTL.
- **Skeleton**: `DashboardSkeleton` موجود + حالت «در حال بارگذاری…» برای کارت.
- **Tooltip**: توضیح هر شاخص.
- **EmptyState**: وقتی `has_enough_data=false` (کمتر از دو معاملهٔ بسته).

## ۵. تست
| بررسی | نتیجه |
|---|---|
| Backend smoke (`/risk-advanced`) | ✅ همهٔ ۱۸ کلید؛ مقادیر معتبر (Sh=3.609, So=9.552, RoR=0, VaR=-13.72, Ulcer=8.52) |
| `pytest` | ✅ 33 passed |
| `tsc -b --force` | ✅ بدون خطا |
| `vitest` | ✅ 9 passed |
| `npm run build` | ✅ موفق (3.08s) |

## ۶. فایل‌های تغییریافته
- `backend/app/api/analytics.py` (endpoint `risk-advanced` + `_percentile`)
- `frontend/src/api/client.ts` (`getRiskAdvanced`)
- `frontend/src/pages/DashboardPage.tsx` (کارت آمار ریسک + دو نمودار + `RiskStat`)
- `PHASE14_4_REPORT.md`
