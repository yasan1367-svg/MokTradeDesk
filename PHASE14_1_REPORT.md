# فاز ۱۴.۱ — رفع باگ‌ها + نمودارهای پایه

**تاریخ:** 1405/07/03 | **وضعیت:** ✅ کامل

---

## ۱. Backend — `backend/app/api/analytics.py` (`GET /dashboard`)

**به `summary` اضافه شد:** `total_trades`, `open_trades`, `closed_trades`, `gross_profit`, `gross_loss`, `avg_win`, `avg_loss`, `largest_win`, `largest_loss`, `expectancy`, `max_consecutive_losses`.

**به `today` اضافه شد:** `winning_trades`, `losing_trades` (به‌همراه `win_rate` موجود).

**سری‌های زمانی جدید:**
- `equity_curve`: `[{date, equity}]` — اکوییتی تجمعی روزانه.
- `pnl_distribution`: `[{range, count}]` — ۸ سطل از `< -500` تا `> 500`.
- `win_loss`: `{wins, losses}`.

## ۲. Frontend — رفع باگ‌ها

- **`ui/StatCard.tsx`**: نرمال‌سازی `sparkData` به بازهٔ ۱۲–۱۰۰٪ (رفع باگ مقیاس اعداد بزرگ) + افزودن prop اختیاری `chart` (نمودار سفارشی جایگزین sparkline).
- **`analytics.py`/`summary.open_trades` و `summary.total_trades`**: حالا واقعاً از بک‌اند می‌آیند (قبلاً خالی رندر می‌شدند).

## ۳. Frontend — نمودارها

**هر کارت آماری نمودار خودش:**
- **سود خالص** → sparkline از `equity_curve`.
- **نرخ برد** → مینی‌نمودار دایره‌ای (`MiniPie`).
- **حداکثر ضرر** → مینی‌نمودار میله‌ای (بزرگ‌ترین ضرر / حداکثر افت).
- **فاکتور سود** → مینی‌نمودار میله‌ای (سود ناخالص / زیان ناخالص).

**ردیف نمودارهای پایه (۳ کارت):**
- `EquityCurveChart` با `data={equity_curve}` (prop جدید `data` اضافه شد — سازگار با `trades` قبلی).
- `WinLossPieChart` با `win_loss`.
- `PnLDistributionChart` با `data={pnl_distribution}` (حالت هیستوگرام اضافه شد — سازگار با حالت قبلی در AnalysisPage).

## ۴. UX
- **Skeleton**: `DashboardSkeleton` موجود استفاده می‌شود.
- **Toast**: خطای بارگذاری + نتیجهٔ دانلود PDF با `useToast`.
- **Dark Mode / RTL**: همهٔ Tooltipها با CSS variables و `direction: rtl`.

## ۵. تست
| بررسی | نتیجه |
|---|---|
| Backend smoke (`/dashboard`) | ✅ کلیدها و سری‌ها درست (equity_curve=۶ روز، pnl_distribution=۸ سطل، win_loss=10/8) |
| `pytest` | ✅ 33 passed |
| `tsc -b --force` | ✅ بدون خطا |
| `vitest` | ✅ 9 passed |
| `npm run build` | ✅ موفق (3.36s) |

## ۶. فایل‌های تغییریافته
- `backend/app/api/analytics.py`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/components/ui/StatCard.tsx`
- `frontend/src/components/charts/EquityCurveChart.tsx`
- `frontend/src/components/charts/PnLDistributionChart.tsx`
- `PHASE14_1_REPORT.md`
