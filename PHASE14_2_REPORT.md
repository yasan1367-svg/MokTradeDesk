# فاز ۱۴.۲ — ترتیب جدید + کارت روز گذشته + ویجت مالی

**تاریخ:** 1405/07/03 | **وضعیت:** ✅ کامل

---

## ۱. Backend — endpoint جدید

**`GET /api/analytics/yesterday`** در `backend/app/api/analytics.py`:
```jsonc
{
  "date": "1405/07/02",        // شمسی
  "day_of_week": "پنج‌شنبه",
  "total_trades": 0,
  "winning_trades": 0,
  "losing_trades": 0,
  "win_rate": 0.0,
  "net_pnl": 0.0,
  "by_source": {
    "prop":     { "trades": 0, "winning": 0, "losing": 0, "pnl": 0.0 },
    "broker":   { "trades": 0, "winning": 0, "losing": 0, "pnl": 0.0 },
    "personal": { "trades": 0, "winning": 0, "losing": 0, "pnl": 0.0 }
  }
}
```
- بر اساس `close_time` روز گذشته (UTC).
- تفکیک منبع: `prop_stage_id` → prop؛ نوع حساب مالی `PROP` → prop، `BROKER` → broker؛ در غیر این صورت personal.
- تاریخ شمسی از `finance._gregorian_to_jalali`، روز هفته با نام فارسی.

## ۲. Frontend — ترتیب جدید داشبورد

**ترتیب نهایی (تأیید شد):**
1. هدر (تاریخ شمسی، روز هفته، ساعت زنده، سلام/احوالپرسی)
2. کارت «وضعیت امروز» (بالای همه)
3. کارت «روز گذشته» ← جدید
4. ۴ کارت آماری
5. نمودارها (منحنی سرمایه، برد/باخت، توزیع PnL)
6. کارت «وضعیت پراپ»
7. کارت «پیشرفت اهداف»
8. ویجت مالی ← جدید
9. هشدارهای پراپ (در صورت وجود)

## ۳. هدر جدید
- **تاریخ شمسی** امروز (`jalaliDate`), **روز هفته** فارسی, **ساعت زنده** (هر ثانیه), و **احوالپرسی** بر اساس ساعت (صبح/وقت/عصر/شب بخیر).
- دکمهٔ «دانلود گزارش PDF» حفظ شد.

## ۴. کارت «روز گذشته»
تاریخ + روز هفته، سود/زیان، Win Rate، برد/باخت، تفکیک منبع (پراپ/بروکر/شخصی) و **مینی‌نمودار میله‌ای** بر اساس `by_source`.

## ۵. ویجت مالی
- **موجودی کل** (خالص به تفکیک ارز) از `getFinanceSummary`.
- **جریان نقدی** (۶ ماه اخیر، نمودار میله‌ای درآمد/هزینه) از `getFinanceCashflow`.
- **تفکیک حساب‌ها** (۶ حساب اول با موجودی) از `getFinanceAccounts`.

## ۶. UX
- **Skeleton**: `DashboardSkeleton` موجود.
- **Toast**: خطاها/موفقیت‌ها (بارگذاری، دانلود PDF).
- **Dark Mode / RTL**: CSS variables + RTL + Tooltipهای RTL.

## ۷. تست
| بررسی | نتیجه |
|---|---|
| Backend smoke (`/yesterday`) | ✅ date=1405/07/02، day=پنج‌شنبه، by_source={prop,broker,personal} |
| `pytest` | ✅ 33 passed |
| `tsc -b --force` | ✅ بدون خطا |
| `vitest` | ✅ 9 passed |
| `npm run build` | ✅ موفق (3.11s) |

## ۸. فایل‌های تغییریافته
- `backend/app/api/analytics.py` (endpoint جدید `yesterday` + `timedelta`)
- `frontend/src/api/client.ts` (`getYesterdayData`)
- `frontend/src/pages/DashboardPage.tsx` (هدر جدید، ترتیب جدید، کارت روز گذشته، ویجت مالی)
- `PHASE14_2_REPORT.md`
