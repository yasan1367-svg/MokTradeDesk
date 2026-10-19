# 🌙 فاز ۷.۱ + ۷ — Dark Mode کامل پروژه + حذف App.css

> **وضعیت:** ✅ کامل و تست‌شده
> **دامنه:** حذف `App.css` + ۵ فایل با کلاس نامدار + ۷ فایل charts
> **تاریخ:** 2026-09-24
> **تصمیم:** گزینه ۱ (سبک A کامل، سبک B فقط grid/axis)

---

## ۱. خلاصه تغییرات

### فاز ۷.۱ — حذف `src/App.css`
| بررسی | نتیجه |
|-------|-------|
| import در `src/**` | ✅ هیچ‌کجا |
| ارجاع در `index.html` / `vite.config` | ✅ ندارد |
| محتوا | قالب پیش‌فرض Vite (`.counter`, `.hero`, `.base`, `.framework`, `.vite`, `#next-steps`, `.ticks`) |
| سینتکس تودرتو (`&:hover`) | ⚠️ نیازمند `postcss-nesting` که **نصب نیست** → حتی اگر import می‌شد، CSS نامعتبر بود |
| **اقدام** | `Move-Item src\App.css src\App.css.pre71` (حذف + حفظ محتوا) |
| **نتیجه** | `src/index.css` تنها CSS پروژه؛ ۶ متغیر «گمشده» برطرف شد |

### فاز ۷ — Dark Mode بقیه فایل‌ها
| مرحله | فایل | تغییرات | alpha (حفظ) |
|-------|------|---------|-------------|
| ۷.۰ | `TradesPage.tsx` | **۱۵۴** | ۱۸ |
| ۷.۱ | `AnalysisPage.tsx` | **۳۶** | ۶ |
| ۷.۲ | `AnalysisTable.tsx` | **۱۳** | ۲ |
| ۷.۳ | `StatCard.tsx` | **۶** | ۰ |
| ۷.۴ | `MetricCard.tsx` | **۶** | ۰ |
| ۷.۵ | `ComparisonBarChart.tsx` (سبک A) | **۸** | ۰ |
| ۷.۵ | `ComparisonRadarChart.tsx` (سبک A) | **۷** | ۰ |
| ۷.۶ | `EquityCurveChart.tsx` (سبک B) | **۶** | ۰ |
| ۷.۶ | `WinLossPieChart.tsx` (سبک B) | **۱** | ۰ |
| ۷.۶ | `WeekdayBarChart.tsx` (سبک B) | **۶** | ۰ |
| ۷.۶ | `SessionBarChart.tsx` (سبک B) | **۶** | ۰ |
| ۷.۶ | `PnLDistributionChart.tsx` (سبک B) | **۱** | ۰ |
| | **جمع** | **۲۵۰** | **۲۶** |

> **چرا ۱۵۴ نه ۱۷۲؟** ۱۷۲ − ۱۸ alpha = **۱۵۴** ✅ (alpha ها عمداً دست‌نخورده)
> **چرا ۳۶ نه ۴۲؟** ۴۲ − ۶ = **۳۶** ✅ | **۱۳ نه ۱۵؟** ۱۵ − ۲ = **۱۳** ✅

---

## ۲. 🔥 چالش فنی: `bg-card` زیرمجموعه `bg-card-border`

| الگو | TradesPage |
|---|---|
| `bg-card-border` | 4 |
| `bg-card` | 26 |

**خطر:** جایگزینی ساده `bg-card` → `bg-card-border` را خراب می‌کرد: `bg-[var(--bg-card)]-border` ❌

**راه‌حل — regex با lookaround دوطرفه:**
```regex
(?<![a-zA-Z0-9-])  bg-card  (?![a-zA-Z0-9/-])
```
| بخش | محافظت از |
|-----|-----------|
| `(?<![a-zA-Z0-9-])` | `var(--bg-card)` (قبلش `-` است) و توکن‌های بلندتر |
| `(?![a-zA-Z0-9/-])` | `bg-card-border` (بعدش `-`) و `bg-card/50` (بعدش `/`) |

**ترتیب اجرا:** بلندترها اول (`bg-card-border` قبل از `bg-card`) — هرچند lookaround مستقل از ترتیب کار می‌کند.

---

## ۳. جدول Mapping — کلاس‌های نامدار (۱۴ الگو)

| از | به | Trades | Analysis | AnalysisTable | Stat | Metric |
|---|---|---|---|---|---|---|
| `bg-card-border` | `bg-[var(--border-subtle)]` | 2 | – | – | – | – |
| `border-card-border` | `border-[var(--border-subtle)]` | 28 | 2 | 1 | – | – |
| `text-text-primary` | `text-[var(--text-primary)]` | 35 | 15 | 5 | 1 | 1 |
| `text-text-secondary` | `text-[var(--text-secondary)]` | 46 | 10 | 2 | 2 | 2 |
| `bg-card` | `bg-[var(--bg-card)]` | 25 | 1 | – | – | – |
| `bg-accent` | `bg-[var(--accent)]` | 3 | 1 | – | – | – |
| `text-accent` | `text-[var(--accent)]` | 2 | 1 | 1 | 1 | 1 |
| `border-accent` | `border-[var(--accent)]` | – | 1 | – | – | – |
| `bg-profit` | `bg-[var(--profit)]` | 2 | – | – | – | – |
| `text-profit` | `text-[var(--profit)]` | 5 | 2 | 2 | 1 | 1 |
| `border-profit` | `border-[var(--profit)]` | – | – | – | – | – |
| `bg-loss` | `bg-[var(--loss)]` | 1 | – | – | – | – |
| `text-loss` | `text-[var(--loss)]` | 5 | 3 | 2 | 1 | 1 |
| `border-loss` | `border-[var(--loss)]` | – | – | – | – | – |
| **جمع** | | **154** | **36** | **13** | **6** | **6** |

> ⚠️ **ویژگی مهم:** `bg-accent` و `hover:bg-accent/80` روی **یک خط** هستند → lookahead `(?![a-zA-Z0-9/-])` از alpha محافظت کرد ✅

---

## ۴. جدول Mapping — Charts

### سبک A — مبتنی بر روشن (دقیقاً مثل PropAnalytics گروه ۲)
| از | به | ComparisonBar | ComparisonRadar |
|---|---|---|---|
| `#FFFFFF` | `var(--bg-card)` | 1 | 1 |
| `#E5EBF3` | `var(--border-subtle)` | 2 | 2 |
| `#1A2B47` | `var(--text-primary)` | 2 | 3 |
| `#9AA8BF` | `var(--text-muted)` | – | 1 |
| `#6B7A94` | `var(--text-secondary)` | 3 | – |
| **جمع** | | **8** | **7** |

### سبک B — grid/axis فقط (tooltip/legend تاریک حفظ شد)
| از | به | Equity | WinLoss | Weekday | Session | PnLDist |
|---|---|---|---|---|---|---|
| `text-text-secondary` | `text-[var(--text-secondary)]` | 1 | 1 | 1 | 1 | 1 |
| `stroke="#2A2A3A"` | `stroke="var(--border-subtle)"` | 1 | – | 1 | 1 | – |
| `stroke="#8888A0"` | `stroke="var(--text-muted)"` | – | – | 2 | 2 | – |
| `stroke="#6B7A94"` | `stroke="var(--text-secondary)"` | 2 | – | – | – | – |
| `fill: '#8888A0'` | `fill: 'var(--text-muted)'` | – | – | 2 | 2 | – |
| `fill: '#6B7A94'` | `fill: 'var(--text-secondary)'` | 2 | – | – | – | – |
| **جمع** | | **6** | **1** | **6** | **6** | **1** |

### 🚫 Group E — دست‌نخورده (عمداً)
| مورد | توضیح |
|------|-------|
| `backgroundColor: '#14141E'` | Tooltip تاریک — طراحی عمدی ۵ فایل |
| `border: '1px solid #2A2A3A'` | Tooltip border تاریک |
| `color: '#F0F0F5'` | Tooltip/Legend text روشن (روی تاریک) |
| `#00D4AA`, `#FF4D6D`, `#6C63FF`, `#FFB84D`, `#4DA6FF`, `#B84DFF` | پالت سری‌های داده |
| `#3F7CFF`, `#7959D6`, `#13AE81`, `#D99B25`, `#E45D72` | پالت سبک A |

### 🔒 ۲۶ alpha modifier — حفظ شد
```
18  TradesPage.tsx
 6  AnalysisPage.tsx
 2  AnalysisTable.tsx
```
نمونه: `bg-accent/20`, `hover:bg-accent/80`, `bg-loss/10`, `bg-loss/80`, `hover:bg-card/50`, `hover:bg-card-border/80`, `border-loss/30`, `border-profit/30`, `border-card-border/50`, `text-text-secondary/50`, `hover:bg-profit/80`, `hover:bg-loss/80`

---

## ۵. نتایج تست

| # | بررسی | روش | نتیجه |
|---|-------|-----|-------|
| ۱ | فاز ۷.۱: `tsc -b --force` | pipe | ✅ **`TSCB_EXIT=0`** |
| ۲ | فاز ۷.۱: `npm run build` | pipe | ✅ **`BUILD_EXIT=0`** |
| ۳ | فاز ۷.۱: var cross-check | اسکن | ✅ **`NONE`** (۶ متغیر گمشده App.css برطرف شد) |
| ۴ | فاز ۷: `tsc -b --force` | pipe | ✅ **`TSCB_EXIT=0`** |
| ۵ | فاز ۷: `npm run build` | pipe | ✅ **`BUILD_EXIT=0`** |
| ۶ | **جایگزینی کلاس نامدار** | اسکریپت | ✅ **۲۱۵** = ۲۴۱−۲۶ (دقیقاً) |
| ۷ | **alpha modifier حفظ‌شده** | اسکن پروژه‌گستر | ✅ **۲۶** (۱۸+۶+۲) |
| ۸ | **Residual کلاس نامدار** | اسکن پروژه‌گستر | ✅ **`TOTAL: 0`** |
| ۹ | سبک A | اسکریپت | ✅ **۱۵** (۸+۷) — residual = پالت فقط |
| ۱۰ | سبک B | اسکریپت | ✅ **۲۰** (۶+۱+۶+۶+۱) |
| ۱۱ | **tooltip/legend تاریک حفظ** | اسکن ۵ فایل | ✅ هر ۵ فایل: tooltipBg=1, tooltipBorder=1, `#F0F0F5` موجود |
| ۱۲ | Residual grid/axis سبک B | اسکن | ✅ **`NONE`** |
| ۱۳ | **JIT: تولید کلاس‌ها در CSS نهایی** | ۵۱ کلاس var | ✅ **`checked=51  missing=0`** |
| ۱۴ | **JIT: alpha classes** | ۱۴ کلاس alpha | ✅ **`MISSING: 0 / 14`** (شامل `hover:` prefix) |
| ۱۵ | var cross-check نهایی | اسکن | ✅ **`NONE - all vars defined OK`** |
| ۱۶ | خطوط تغییر | diff با `.pre7` | Trades 97 · Analysis 30 · AnalysisTable 11 · Stat 6 · Metric 6 = **۱۵۰ خط** |
| ۱۷ | خطاهای لینت جدید | eslint + diff proof | ✅ **صفر** (۷ خطای غیر-`any` در کد **دست‌نخورده**) |

### 🔒 اثبات خطاهای ESLint (۷ مورد)
خطاهای گزارش‌شده در `TradesPage.tsx`: خطوط **53, 64, 71, 77, 103, 108, 112**

```
--- TradesPage.tsx: changed lines = 97 ---
    ✅ NO OVERLAP - all error lines are UNCHANGED code
    ✅ ALL changed lines contain className/var()
```
| بررسی | نتیجه |
|-------|-------|
| همپوشانی خطوط خطا با خطوط تغییر | ✅ **صفر** |
| همه ۹۷ خط تغییر شامل `className`/`var()` | ✅ **بله** |
| ماهیت خطاها | `setState in effect`, `unused 'e'/'err'`, `access before declared` — همه از قبل |

### 📝 نمونه diff (AnalysisTable.tsx)
```diff
- <h3 className="text-text-primary font-bold mb-4">
+ <h3 className="text-[var(--text-primary)] font-bold mb-4">

- <tr className="text-text-secondary border-b border-card-border">
+ <tr className="text-[var(--text-secondary)] border-b border-[var(--border-subtle)]">

- <td className={`py-2 font-bold ${value.net_pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
+ <td className={`py-2 font-bold ${value.net_pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
```
> ✅ حالت **template-literal** (داخل `${}`) هم درست تبدیل شد.

---

## ۶. نکات و هشدارها

### ۶.۱ ⚠️ ۲۶ alpha modifier — همچنان غیر-theme-aware
طبق تصمیم شما حفظ شدند. **پیامد:** در Dark Mode، این ۲۶ مورد با رنگ‌های **روشن config** رندر می‌شوند:
| کلاس | رنگ config | در Dark Mode |
|------|-----------|--------------|
| `hover:bg-card/50`, `bg-card/50` | `#FFFFFF` 50% | overlay **روشن** ⚠️ |
| `hover:bg-card-border/80`, `bg-card-border/80` | `#E5EBF3` 80% | روشن ⚠️ |
| `border-card-border/50` | `#E5EBF3` 50% | روشن ⚠️ |
| `bg-accent/*`, `bg-profit/*`, `bg-loss/*` | یکسان در هر دو تم | ✅ بی‌مشکل |

**رفع ریشه‌ای (فاز ۷.۲ پیشنهادی):** تبدیل `tailwind.config.js` به RGB triplet:
```css
:root { --bg-card-rgb: 255 255 255; }   .dark { --bg-card-rgb: 26 39 54; }
```
```js
colors: { card: 'rgb(var(--bg-card-rgb) / <alpha-value>)' }
```
→ نیازمند ~۱۵ متغیر `-rgb` جدید + ۱۵ ورودی config.

### ۶.۲ ℹ️ tooltip های سبک B — طراحی عمدی تاریک
۵ فایل chart tooltip/legend با `#14141E` / `#2A2A3A` / `#F0F0F5` دارند که **در هر دو تم تاریک** می‌مانند — انتخاب طراحی که **دست‌نخورده** ماند.
> در مقابل، سبک A (`ComparisonBarChart`, `ComparisonRadarChart`) tooltip روشن داشتند که به `var()` تبدیل شدند.

### ۶.۳ ℹ️ `src/App.css` — حذف شد (با بکاپ)
`App.css.pre71` (۲٫۸۹۱ بایت) حفظ شد. اکنون `src/index.css` تنها CSS پروژه است.

### ۶.۴ ℹ️ تعداد بکاپ‌ها
| پسوند | فاز | تعداد |
|-------|-----|-------|
| `.bak` | ۶ | ۲ |
| `.pre61` | ۶.۱ | ۱۳ |
| `.pre7` | ۷ | ۱۲ |
| `.pre71` | ۷.۱ | ۱ |
| **جمع** | | **۲۸** |

> همه با پسوند غیر-`.tsx`/`.css` → Tailwind و tsc نادیده می‌گیرند ✅

### ۶.۵ ℹ️ وضعیت نهایی Dark Mode پروژه
| گروه | وضعیت |
|------|-------|
| `FinancePage` | ✅ از ابتدا dark-aware |
| `PersonalPage`, `PropPage` | ✅ فاز ۶ (۶۷۳ جایگزینی) |
| `PropAnalytics`, `PersianDateInput` | ✅ فاز ۶.۱ |
| `TradesPage`, `AnalysisPage`, `AnalysisTable`, `StatCard`, `MetricCard` | ✅ فاز ۷ (۲۱۵) |
| ۷ فایل chart | ✅ فاز ۷ (۳۵) |
| `AccountForm`, `TransactionForm`, `CategoryForm`, `Toast`, `Skeleton` | ✅ از قبل |
| **کلاس نامدار باقیمانده** | ✅ **صفر** |
| **alpha modifier غیر-theme-aware** | ⚠️ **۲۶** (فاز ۷.۲) |

### ۶.۶ خارج از دامنه — صفحات باقیمانده
سایر صفحات (`ImportPage`, `JournalPage`, `StrategyPage`, `DashboardPage`, `RiskManagementPage`, `SettingsPage`, `ComparisonPage`, `CalendarPage`) از **هگز hardcoded** استفاده می‌کنند (نه کلاس نامدار) — مشابه وضعیت `PersonalPage` قبل از فاز ۶. در صورت تمایل در فاز ۸ قابل رفع است.

---

## ۷. Rollback

```powershell
cd frontend

# فاز ۷.۱ — بازگردانی App.css
Copy-Item src\App.css.pre71 src\App.css -Force

# فاز ۷ — ۵ فایل کلاس نامدار
Copy-Item src\pages\TradesPage.tsx.pre7              src\pages\TradesPage.tsx -Force
Copy-Item src\pages\AnalysisPage.tsx.pre7            src\pages\AnalysisPage.tsx -Force
Copy-Item src\components\AnalysisTable.tsx.pre7      src\components\AnalysisTable.tsx -Force
Copy-Item src\components\StatCard.tsx.pre7           src\components\StatCard.tsx -Force
Copy-Item src\components\MetricCard.tsx.pre7         src\components\MetricCard.tsx -Force

# فاز ۷ — ۷ فایل chart
Copy-Item src\components\charts\ComparisonBarChart.tsx.pre7    src\components\charts\ComparisonBarChart.tsx -Force
Copy-Item src\components\charts\ComparisonRadarChart.tsx.pre7  src\components\charts\ComparisonRadarChart.tsx -Force
Copy-Item src\components\charts\EquityCurveChart.tsx.pre7      src\components\charts\EquityCurveChart.tsx -Force
Copy-Item src\components\charts\WinLossPieChart.tsx.pre7       src\components\charts\WinLossPieChart.tsx -Force
Copy-Item src\components\charts\WeekdayBarChart.tsx.pre7       src\components\charts\WeekdayBarChart.tsx -Force
Copy-Item src\components\charts\SessionBarChart.tsx.pre7       src\components\charts\SessionBarChart.tsx -Force
Copy-Item src\components\charts\PnLDistributionChart.tsx.pre7  src\components\charts\PnLDistributionChart.tsx -Force
```

---

## ۸. گام بعدی پیشنهادی

| # | فاز | موضوع | حجم |
|---|-----|-------|-----|
| ۱ | **۷.۲** | رفاکتور `tailwind.config.js` → RGB triplet + `<alpha-value>` (رفع ۲۶ alpha) | ~۳۰ |
| ۲ | **۸** | هگزهای hardcoded صفحات باقیمانده (Import/Journal/Strategy/Dashboard/RiskManagement/Settings/Comparison/Calendar) | ~؟ |
| ۳ | ۸.۱ | حذف ۲۸ فایل بکاپ (پس از اطمینان) | ۲۸ |

---

> ✅ **فاز ۷.۱ + ۷ کامل شد** — ۲۵۰ تغییر در ۱۲ فایل + حذف App.css، `tsc`/`build` سبز، **صفر کلاس نامدار باقیمانده**، ۲۶ alpha محفوظ، ۵۱/۵۱ کلاس و ۱۴/۱۴ alpha در CSS نهایی، صفر خطای جدید.