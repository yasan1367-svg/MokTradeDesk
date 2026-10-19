# 📋 گزارش فاز ۱۵.۴ — Bundle Splitting (Frontend)

> **تاریخ:** ۱۴۰۵/۰۷/۰۳ (2026-09-25)
> **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ Code Splitting پیاده شد — ✅ ۲۶ chunk ساخته شد — ✅ `tsc` و `vite build` و `vitest` همه پاس
> **فایل‌های تغییر‌یافته:** فقط `frontend/src/App.tsx` و `frontend/src/main.tsx` (+63 / −28)

---

## ۱. مشکل

همهٔ ۱۲ صفحه با `import` استاتیک در `App.tsx` وارد می‌شدند ⇒ **یک bundle واحد ۱٬۰۷۱٫۲۰ kB** که **پیش از اولین رندر** باید لود شود.

```tsx
// App.tsx (قبل)
import AnalysisPage from './pages/AnalysisPage';
import ComparisonPage from './pages/ComparisonPage';
import StrategyPage from './pages/StrategyPage';
import TradesPage from './pages/TradesPage';
import JournalPage from './pages/JournalPage';
import PropPage from './pages/PropPage';
import RiskManagementPage from './pages/RiskManagementPage';
import ImportPage from './pages/ImportPage';
import DashboardPage from './pages/DashboardPage';
import SettingsPage from './pages/SettingsPage';
import CalendarPage from './pages/CalendarPage';
import FinancePage from './pages/FinancePage';
```

---

## ۲. تغییرات

### ۲.۱ `App.tsx` — تبدیل به `React.lazy`
```tsx
import { useMemo, useState, useEffect, lazy, Suspense } from 'react';
...
// ── فاز ۱۵.۴: Code Splitting — هر صفحه یک chunk جداگانه ──
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const AnalysisPage = lazy(() => import('./pages/AnalysisPage'));
const ComparisonPage = lazy(() => import('./pages/ComparisonPage'));
const StrategyPage = lazy(() => import('./pages/StrategyPage'));
const TradesPage = lazy(() => import('./pages/TradesPage'));
const JournalPage = lazy(() => import('./pages/JournalPage'));
const PropPage = lazy(() => import('./pages/PropPage'));
const CalendarPage = lazy(() => import('./pages/CalendarPage'));
const RiskManagementPage = lazy(() => import('./pages/RiskManagementPage'));
const ImportPage = lazy(() => import('./pages/ImportPage'));
const FinancePage = lazy(() => import('./pages/FinancePage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));

// preload صفحهٔ پیش‌فرض (Dashboard) — فاز ۱۵.۴
const preloadDashboard = () => { void import('./pages/DashboardPage'); };
```
**۱۲ lazy import** — تأیید شد که هیچ `import` استاتیکی از `./pages/*` باقی نمانده است.

### ۲.۲ `App.tsx` — fallback آگاه از Dark Mode
```tsx
// ── فاز ۱۵.۴: fallback آگاه از Dark Mode (با CSS Variables) ──
function PageLoading() {
  return (
    <div className="flex items-center justify-center min-h-[320px] h-full w-full">
      <div className="flex flex-col items-center gap-3 text-[var(--text-secondary)]">
        <div className="w-9 h-9 rounded-full border-2 border-[var(--border-subtle)] border-t-[var(--accent)] animate-spin" />
        <span className="text-xs">در حال بارگذاری…</span>
      </div>
    </div>
  );
}
```
> از توکن‌های `var(--*)` استفاده می‌کند ⇒ در **هر دو حالت روشن و تاریک** درست نمایش داده می‌شود.

### ۲.۳ `App.tsx` — `Suspense` + حفظ `ErrorBoundary` هر صفحه
```tsx
<div className="flex-1 overflow-y-auto p-7">
  <Suspense fallback={<PageLoading />}>
    {page === 'dashboard' && <ErrorBoundary label="داشبورد"><DashboardPage onNavigate={...} /></ErrorBoundary>}
    {page === 'analysis' && <ErrorBoundary label="تحلیل"><AnalysisPage /></ErrorBoundary>}
    {/* ... بقیهٔ ۱۰ صفحه با ErrorBoundary اختصاصی خودشان */}
  </Suspense>
</div>
```
- ✅ `ErrorBoundary` **برای هر صفحه حفظ شد** (طبق درخواست).
- ✅ یک `Suspense` مشترک، کل ناحیهٔ محتوا را پوشش می‌دهد.

### ۲.۴ `App.tsx` — Preload صفحهٔ پیش‌فرض
```tsx
  const { theme, toggleTheme } = useTheme();
  const toast = useToast();

  // ── preload صفحهٔ پیش‌فرض (فاز ۱۵.۴) ──
  useEffect(() => { preloadDashboard(); }, []);
```
> Dashboard همچنان یک chunk جداگانه است، اما در اولین فرصت fetch می‌شود تا کاربر تأخیری احساس نکند.

### ۲.۵ `main.tsx` — `Suspense` سراسری (دفاعی)
```tsx
import React, { Suspense } from 'react'
...
// ── فاز ۱۵.۴: fallback سراسری آگاه از Dark Mode ──
function RootFallback() {
  return (
    <div className="flex items-center justify-center h-screen bg-[var(--bg-base)] text-[var(--text-secondary)]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-9 h-9 rounded-full border-2 border-[var(--border-subtle)] border-t-[var(--accent)] animate-spin" />
        <span className="text-xs">در حال بارگذاری…</span>
      </div>
    </div>
  )
}

ReactDOM.createRoot(...).render(
  <React.StrictMode>
    <ToastProvider>
      <ErrorBoundary fullScreen label="اپلیکیشن">
        <Suspense fallback={<RootFallback />}>
          <App />
        </Suspense>
      </ErrorBoundary>
    </ToastProvider>
  </React.StrictMode>,
)
```
> لایهٔ دفاعی: اگر روزی خود `App` یا هر کامپوننت سطح‌بالا lazy شود، بدون خطا مدیریت می‌شود.

### ۲.۶ `vite.config.ts` — **تغییر نکرد**
`manualChunks` دستی اضافه نشد چون **rolldown (Vite 8) به‌صورت خودکار** recharts و کامپوننت‌های مشترک را به chunkهای جدا تقسیم کرد (خروجی زیر). افزودن تنظیم دستی، ریسک ناسازگاری با rolldown را داشت.

---

## ۳. نتیجهٔ Build

### ۳.۱ مقایسهٔ حجم **بارگذاری اولیه (blocking)**

`dist/index.html` فقط این‌ها را لود می‌کند (بقیه dynamic هستند):

| | قبل | بعد | کاهش |
|---|---|---|---|
| JS اولیه | **1,071.20 kB** | **241.56 kB** | **−829.64 kB (۷۷٫۴٪)** |
| JS اولیه (gzip) | 273.28 kB | **75.68 kB** | **−197.60 kB (۷۲٫۳٪)** |
| CSS | 47.05 kB | 47.15 kB | — |

**ترکیب JS اولیه (بعد):** `index-D8t3x5Xn.js` (240.85 kB) + `rolldown-runtime-hePW80VL.js` (0.71 kB)

### ۳.۲ تعداد chunkها
- **۲۶ فایل JS** (قبل: ۱ فایل) — مجموع `1,059.3 kB`
- **۱ فایل CSS** (بدون تغییر)
- ⏱ زمان build: **3.06s**

> نکته: مجموع کل حجم تقریباً ثابت می‌ماند (۱٬۰۷۱ → ۱٬۰۵۹ kB) چون Splitting حجم را کم نمی‌کند؛ بلکه **بایت‌ها را از مسیر بحرانی رندر اولیه بیرون می‌برد**.

### ۳.۳ chunk هر صفحه (به تفکیک)

| صفحه (chunk) | حجم | gzip |
|---|---|---|
| `PropPage` | 68.32 kB | 10.72 kB |
| `FinancePage` | 56.43 kB | 9.53 kB |
| `ComparisonPage` | 56.20 kB | 12.55 kB |
| `DashboardPage` | 38.57 kB | 9.96 kB |
| `TradesPage` | 29.11 kB | 5.85 kB |
| `StrategyPage` | 25.92 kB | 5.57 kB |
| `ImportPage` | 21.44 kB | 4.33 kB |
| `AnalysisPage` | 15.98 kB | 4.27 kB |
| `JournalPage` | 12.84 kB | 3.40 kB |
| `RiskManagementPage` | 11.45 kB | 2.43 kB |
| `SettingsPage` | 8.58 kB | 2.04 kB |
| `CalendarPage` | 7.98 kB | 2.76 kB |

**۱۲ صفحه = ۱۲ chunk مستقل** ✅ — هرکدام فقط هنگام مراجعهٔ کاربر لود می‌شوند.

### ۳.۴ chunkهای مشترک (خودکار توسط rolldown)
| chunk | حجم | توضیح |
|---|---|---|
| `BarChart` | 359.51 kB | هستهٔ recharts (فقط با صفحات نموداردار لود می‌شود) |
| `index` | 240.85 kB | entry: React + App + Sidebar + ErrorBoundary + CommandPalette + Toast |
| `client` | 55.73 kB | API client مشترک |
| `PolarChart` | 18.08 kB | recharts |
| `PnLDistributionChart` | 18.82 kB | مشترک |
| `PieChart` | 13.70 kB | recharts |
| `LineChart` | 11.94 kB | recharts |
| `ActivePoints` | 4.97 kB | recharts |
| `jalali` | 2.58 kB | util مشترک |
| `Skeleton` | 2.46 kB | مشترک |
| `PersianDateInput` | 1.99 kB | مشترک |
| `GlassCard` / `getRadiusAndStrokeWidthFromDot` | 0.17 / 0.25 kB | مشترک |
| `rolldown-runtime` | 0.71 kB | runtime |

---

## 🧪 اعتبارسنجی

| مورد | نتیجه |
|---|---|
| `npx tsc -b --force` | ✅ `TSC_EXIT=0` |
| `npx vite build` | ✅ `VITE_EXIT=0` · 688 modules · built in 8.31s |
| `npm run build` (tsc + vite) | ✅ `exit=0` · built in 3.06s |
| `npx vitest run` | ✅ **Test Files 2 passed · Tests 9 passed** |
| import استاتیک صفحه در `App.tsx` | ✅ **صفر** |
| تعداد `lazy(() => import('./pages/...'))` | ✅ **۱۲** |
| فایل‌های تغییر‌یافته | ✅ فقط `App.tsx` و `main.tsx` |

---

## ✅ نتیجه‌گیری فاز ۱۵.۴

1. ✅ هر ۱۲ صفحه با `React.lazy` به chunk مستقل تبدیل شدند.
2. ✅ `Suspense` + fallback **آگاه از Dark Mode** (با `var(--*)`) اضافه شد.
3. ✅ `ErrorBoundary` اختصاصی هر صفحه **حفظ شد**.
4. ✅ Preload برای Dashboard (صفحهٔ پیش‌فرض) پیاده شد.
5. ✅ `main.tsx` با `Suspense` سراسری (لایهٔ دفاعی) به‌روزرسانی شد.
6. ✅ **بارگذاری اولیه ۷۷٪ (gzip: ۷۲٪) کاهش یافت** — از 1,071 kB به 241 kB.
7. ✅ ۲۶ chunk ساخته شد (قبل: ۱).
8. ✅ همهٔ تست‌ها، type-check و build موفق.

### 📌 یادداشت‌ها و موارد خارج از دامنه
- **`PersonalPage` وجود ندارد:** در فهرست درخواستی ذکر شده بود، اما در `frontend/src/pages/` چنین فایلی نیست. صفحات واقعی **۱۲ مورد** بودند (بدون PersonalPage). صفحهٔ مربوط به ژورنال (`JournalPage`) و پراپ (`PropPage`) موجودند.
- **`vite.config.ts` تغییر نکرد:** تقسیم خودکار rolldown کافی بود. اگر در آینده نیاز به chunk ثابت vendor (برای کش بهتر) بود، می‌توان `build.rolldownOptions.output.codeSplitting` را بررسی کرد — اما با rolldown ریسک ناسازگاری دارد.
- **بزرگ‌ترین chunk باقی‌مانده `BarChart` (359 kB)** است که هستهٔ recharts است؛ چون Dashboard و چند صفحهٔ دیگر نمودار دارند، نمی‌توان آن را از مسیر داشبورد حذف کرد. در صورت نیاز، در فاز بعد می‌توان نمودارهای صفحات غیرِ داشبورد را به `IntersectionObserver`/lazy جداگانه منتقل کرد.
- **تست runtime مرورگر:** در این محیط امکان اجرای مرورگر نبود؛ اعتبارسنجی با `tsc` + `vite build` + `vitest` انجام شد. رفتار `Suspense`/lazy در production build استاندارد React است.

*گزارش فاز ۱۵.۴ — تهیه‌شده در ۱۴۰۵/۰۷/۰۳.*

