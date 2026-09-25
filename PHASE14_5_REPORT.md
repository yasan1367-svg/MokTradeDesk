# فاز ۱۴.۵ — Empty State، Refresh، Quick Actions

**تاریخ:** 1405/07/03 | **وضعیت:** ✅ کامل

---

## ۱. Empty State (بهبود)
- **کارت‌های آماری**: اگر معامله‌ای ثبت نشده باشد (`total_trades = 0`) → `EmptyState` با دکمهٔ **«افزودن معامله»**.
- **نمودارها**: پیام مناسب خودکار (منحنی سرمایه/برد-باخت/توزیع).
- **جدول‌ها**: «آخرین معاملات» → EmptyState با دکمهٔ **«ثبت معامله»**؛ «معاملات باز» → EmptyState.
- **آمار ریسک**: EmptyState موجود برای دادهٔ ناکافی.

## ۲. دکمهٔ Refresh
- در هدر داشبورد، با **آیکون چرخان** (`animate-spin`) در حین بارگذاری و غیرفعال‌سازی دکمه.
- **همهٔ ویجت‌ها** با یک `loadDashboard()` همگام به‌روزرسانی می‌شوند (dash، yesterday، finance، risk، trades، alerts).
- **Toast** موفقیت: «داشبورد به‌روزرسانی شد».

## ۳. Quick Actions (هدر)
| دکمه | عملکرد |
|---|---|
| ➕ | معاملهٔ جدید (`Ctrl+N`) — ناوبری + dispatch رویداد |
| 💳 | تراکنش مالی (ناوبری به مالی) |
| 🏦 | حساب مالی جدید (ناوبری به مالی) |
| 🔍 | جستجوی سریع (`Ctrl+K` — dispatch) |
| 🔄 | Refresh |
| 📄 گزارش PDF | خروجی PDF |

همه با **Tooltip** توضیحی.

## ۴. بهبودهای UX
- **Toast**: موفقیت Refresh و خطاها.
- **Skeleton**: `DashboardSkeleton` برای بارگذاری اولیه.
- **Error Boundary مستقل برای هر ویجت** (۶ مورد): کارت‌های آماری، نمودارها، پراپ و اهداف، آمار ریسک، ویجت مالی، معاملات — خطای یک ویجت بقیه را از کار نمی‌اندازد.
- خطای Refresh دیگر کل صفحه را پنهان نمی‌کند (`error && !data`).

## ۵. تست
| بررسی | نتیجه |
|---|---|
| تعادل ErrorBoundary | ✅ ۶ باز / ۶ بسته |
| `tsc -b --force` | ✅ بدون خطا |
| `vitest` | ✅ 9 passed |
| `pytest` | ✅ 33 passed |
| `npm run build` | ✅ موفق (11.66s) |

## ۶. فایل‌های تغییریافته
- `frontend/src/pages/DashboardPage.tsx` (Refresh، Quick Actions، EmptyState، ۶ ErrorBoundary، `loadDashboard`)
- `PHASE14_5_REPORT.md`
