# 🌙 فاز ۶.۱ — Dark Mode کامپوننت‌های فرزند + حاشیه‌های semantic

> **وضعیت:** ✅ کامل و تست‌شده
> **دامنه:** `PropAnalytics` + `PersianDateInput` + `--profit-border`/`--loss-border` (پروژه‌گستر)
> **تاریخ:** 2026-09-24
> **تصمیم:** گزینه ۱ (تأیید کامل)

---

## ۱. خلاصه تغییرات

| # | فایل | نوع | حجم |
|---|------|-----|-----|
| ۱ | `frontend/src/index.css` | ✏️ افزودن **۲ متغیر** (روشن + تاریک) | +۴ خط |
| ۲ | `frontend/src/components/charts/PropAnalytics.tsx` | ✏️ ۱۴ کلاس + ۱۲ inline | **۲۶ تغییر / ۲۳ خط** |
| ۳ | `frontend/src/components/PersianDateInput.tsx` | ✏️ ۵ کلاس نامدار → `var()` | **۵ تغییر / ۲ خط** |
| ۴ | **۱۰ فایل** (border ها) | ✏️ جایگزینی پروژه‌گستر | **۴۵ تغییر** |
| | **جمع** | | **۷۶ تغییر** |

### 🆕 متغیرهای جدید (`index.css`)
```css
:root {
  --profit-border: #A8E6CF;   /* 🆕 فاز ۶.۱ */
  --loss-border: #F0A6B2;
}
.dark {
  --profit-border: #1E5945;
  --loss-border: #5C2A34;
}
```
> مقادیر روشن **دقیقاً همان hexهای قبلی** هستند → **صفر تغییر بصری در Light Mode** ✅

---

## ۲. `PropAnalytics.tsx` — دو گروه رنگ

### گروه ۱: کلاس‌های Tailwind (۱۴)
| از | به | تعداد |
|---|---|---|
| `bg-white` | `bg-[var(--bg-card)]` | 2 |
| `border-[#E5EBF3]` | `border-[var(--border-subtle)]` | 4 |
| `bg-[#FFEDF0]` | `bg-[var(--loss-soft)]` | 1 |
| `bg-[#EDF3FF]` | `bg-[var(--accent-soft)]` | 1 |
| `text-[#1A2B47]` | `text-[var(--text-primary)]` | 2 |
| `text-[#6B7A94]` | `text-[var(--text-secondary)]` | 2 |
| `text-[#9AA8BF]` | `text-[var(--text-muted)]` | 2 |

### گروه ۲: 🔥 مقادیر inline / props recharts (۱۲) — **کلاس نبودند**
| از | به | تعداد |
|---|---|---|
| `backgroundColor: '#FFFFFF'` | `backgroundColor: 'var(--bg-card)'` | 2 |
| `border: '2px solid #E5EBF3'` | `border: '2px solid var(--border-subtle)'` | 2 |
| `color: '#1A2B47'` (Tooltip ×2 + Legend ×2) | `color: 'var(--text-primary)'` | 4 |
| `stroke="#E5EBF3"` (CartesianGrid) | `stroke="var(--border-subtle)"` | 1 |
| `stroke="#6B7A94"` (XAxis/YAxis) | `stroke="var(--text-secondary)"` | 2 |

> ✅ `var()` در inline style و SVG `stroke` توسط مرورگر resolve می‌شود (متغیرها روی `:root`/`.dark` تعریف شده‌اند).

### 🚫 گروه E (دست‌نخورده)
`FAILURE_COLORS` (پالت ۷ رنگه) + `Bar fill="#13AE81"`/`"#3F7CFF"`/`"#E45D72"`
→ **باقیمانده بررسی شد: `NONE` غیر-GroupE** ✅

---

## ۳. `PersianDateInput.tsx` — ۵ کلاس نامدار

**diff دقیق (فقط ۲ خط):**
```diff
line 65:
- <label className="text-text-secondary text-xs block mb-1">{label}</label>
+ <label className="text-[var(--text-secondary)] text-xs block mb-1">{label}</label>

line 73:
- className="w-full bg-card border border-card-border rounded-xl px-4 py-2 text-text-primary text-center focus:border-accent focus:outline-none font-mono"
+ className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-2 text-[var(--text-primary)] text-center focus:border-[var(--accent)] focus:outline-none font-mono"
```

| کلاس نامدار config | مقدار ثابت config | → به |
|---|---|---|
| `text-text-secondary` | `#6B7A94` | `text-[var(--text-secondary)]` |
| `bg-card` | `#FFFFFF` | `bg-[var(--bg-card)]` |
| `border-card-border` | `#E5EBF3` | `border-[var(--border-subtle)]` |
| `text-text-primary` | `#1A2B47` | `text-[var(--text-primary)]` |
| `focus:border-accent` | `#3F7CFF` | `focus:border-[var(--accent)]` |

### ⚠️ چرا گزینه `tailwind.config.js` انتخاب نشد
**۲۶ مورد alpha modifier** روی رنگ‌های نامدار در پروژه استفاده می‌شود:
```
4 bg-accent/80    3 bg-accent/20    3 border-card-border/50   3 bg-card/50
2 bg-profit/80    2 bg-loss/80      2 bg-card-border/80       2 bg-loss/10
2 border-loss/30  1 bg-profit/10    1 text-text-secondary/50  1 border-profit/30
```
Tailwind 3 نمی‌تواند به `var(--x)` ساده alpha اعمال کند → این ۲۶ مورد **شفافیت خود را از دست می‌دادند**. رفع درست نیازمند RGB triplet (`rgb(var(--bg-card-rgb) / <alpha-value>)`) است = رفاکتور بزرگ‌تر. لذا `var()` مستقیم انتخاب شد.

---

## ۴. حاشیه‌های semantic — ۴۵ جایگزینی در ۱۰ فایل

| فایل | `border-[#A8E6CF]` → `--profit-border` | `border-[#F0A6B2]` → `--loss-border` | جمع |
|---|---|---|---|
| `PropPage.tsx` | 7 | 7 | 14 |
| `StrategyPage.tsx` | 4 | 4 | 8 |
| `PersonalPage.tsx` | 3 | 3 | 6 |
| `ImportPage.tsx` | 2 | 2 | 4 |
| `JournalPage.tsx` | 1 | 2 | 3 |
| `components/Toast.tsx` | 1 | 1 | 2 |
| `ComparisonPage.tsx` | 1 | 1 | 2 |
| `DashboardPage.tsx` | 1 | 1 | 2 |
| `RiskManagementPage.tsx` | 1 | 1 | 2 |
| `SettingsPage.tsx` | 1 | 1 | 2 |
| **جمع** | **۲۲** | **۲۳** | **۴۵** |

### ✅ ایمنی گرادیان‌ها
وارد کردن `border-` فقط الگوی `border-[#F0A6B2]` را هدف گرفت → گرادیان‌های `to-[#F0A6B2]` **دست‌نخورده**:
```
1  ProgressBar.tsx      2  StatCard.tsx      4  PropPage.tsx       (جمع ۷)
```

---

## ۵. نتایج تست

| # | بررسی | روش | نتیجه |
|---|-------|-----|-------|
| ۱ | TypeScript (build mode، بدون کش) | `npx tsc -b --force` | ✅ **`TSCB_EXIT=0`** |
| ۲ | Production build | `npm run build` | ✅ **`BUILD_EXIT=0`** |
| ۳ | Residual `border-[#A8E6CF]`/`[#F0A6B2]` | regex سراسری | ✅ **`NONE`** |
| ۴ | جراند توتال جایگزینی | اسکریپت | ✅ **۴۵** (دقیقاً ۲۲+۲۳) |
| ۵ | ریسidual PropAnalytics غیر-GroupE | مقایسه با پالت | ✅ **`NONE`** — فقط Group E |
| ۶ | تغییرات `PersianDateInput` | diff با `.pre61` | ✅ **فقط خطوط ۶۵ و ۷۳** |
| ۷ | تغییرات `PropAnalytics` | diff با `.pre61` | ✅ **۲۳ خط** (مطابق انتظار) |
| ۸ | **صفر typo متغیر** | cross-check | ✅ همه varهای کد تعریف شده |
| ۹ | **JIT: تولید در CSS نهایی** | بازرسی `dist/assets/*.css` | ✅ **۱۰/۱۰ کلاس** (شامل `border-[var(--profit-border)]` و `border-[var(--loss-border)]`) |
| ۱۰ | حفظ گرادیان‌ها | regex `to-[#F0A6B2]` | ✅ **۷ مورد دست‌نخورده** |
| ۱۱ | خطای جدید منطقی | eslint روی ۳ فایل | ✅ **صفر** (۳ خطا در کد دست‌نخورده = از قبل موجود) |

### 📝 توضیح خطاهای ESLint (۳ مورد)
| خط | فایل | پیام | وضعیت |
|----|------|------|-------|
| 31:9 | `PersianDateInput.tsx` | `Calling setState synchronously within an effect` | ✅ از قبل — خط ۳۱ **تغییر نکرده** (diff اثبات کرد) |
| 32:16 | `PersianDateInput.tsx` | `'e' is defined but never used` | ✅ از قبل |
| 55:18 | `PersianDateInput.tsx` | `'e' is defined but never used` | ✅ از قبل |
| — | `PropAnalytics.tsx` | `no-explicit-any` (۳ مورد) | ✅ از قبل |

> **اثبات:** diff خط‌به‌خط `PersianDateInput.tsx.post61` با `.pre61` نشان داد **فقط خطوط ۶۵ و ۷۳** تغییر کرده‌اند. پس خطاهای ۳۱/۳۲/۵۵ در کد دست‌نخورده هستند.

---

## ۶. نکات و هشدارها

### ۶.۱ ℹ️ `src/App.css` — کد مرده (خارج از دامنه)
بررسی cross-check متغیرها، ۶ متغیر «گمشده» گزارش کرد: `--accent-bg`, `--accent-border`, `--border`, `--text-h`, `--social-bg`, `--shadow`.
**منشأ:** فایل `src/App.css` — باقیمانده قالب Vite که **در هیچ‌جا import نمی‌شود** (تأیید شد: فقط `main.tsx` → `import './index.css'`).
→ **کد مرده و بی‌اثر**؛ نیازی به اقدام نیست (در صورت تمایل در فاز بعد حذف شود).

### ۶.۲ ℹ️ بکاپ‌ها
**۱۳ فایل `.pre61`** ساخته شد (پسوند `.pre61` → Tailwind و tsc نادیده می‌گیرند چون الگوی `*.tsx`/`*.css` مطابقت ندارد):
```
index.css.pre61, PersianDateInput.tsx.pre61, Toast.tsx.pre61, PropAnalytics.tsx.pre61,
ComparisonPage.tsx.pre61, DashboardPage.tsx.pre61, ImportPage.tsx.pre61, JournalPage.tsx.pre61,
PersonalPage.tsx.pre61, PropPage.tsx.pre61, RiskManagementPage.tsx.pre61,
SettingsPage.tsx.pre61, StrategyPage.tsx.pre61
```
> نکته: بکاپ‌های فاز ۶ (`PersonalPage.tsx.bak`, `PropPage.tsx.bak`) **دست‌نخورده حفظ شدند** (پسوند متفاوت انتخاب شد تا rollback فاز ۶ از بین نرود).

### ۶.۳ ⚠️ باقیمانده Dark Mode (فاز ۷)
| فایل | مسئله | تعداد |
|------|-------|-------|
| `TradesPage.tsx` | کلاس‌های نامدار config | ۱۷۲ |
| `AnalysisPage.tsx` | کلاس‌های نامدار config | ۴۲ |
| `AnalysisTable.tsx` | کلاس‌های نامدار config | ۱۵ |
| `StatCard.tsx` / `MetricCard.tsx` | کلاس‌های نامدار config | ۶ / ۶ |
| charts (۵ فایل) | ۱ هر کدام | ۵ |
| `App.css` | کد مرده (۶ var گمشده) | ۱۱ |

> همچنین `border-[#A8E6CF]`/`[#F0A6B2]` اکنون **صفر** باقیمانده در کل پروژه ✅

### ۶.۴ ℹ️ رفتار recharts با `var()`
`Tooltip contentStyle`, `Legend wrapperStyle`, `CartesianGrid stroke`, `XAxis/YAxis stroke` همه `var()` را می‌پذیرند چون مقادیر به‌صورت CSS اعمال می‌شوند و متغیرها روی `documentElement` تعریف شده‌اند → در Dark Mode **بلافاصله** به‌روز می‌شوند (بدون نیاز به re-render).

---

## ۷. گام بعدی پیشنهادی

| # | فاز | موضوع | حجم |
|---|-----|-------|-----|
| ۱ | **۷** | `TradesPage` (۱۷۲) + `AnalysisPage` (۴۲) + `AnalysisTable` (۱۵) + `StatCard`/`MetricCard` (۱۲) + charts (۵) | ~۲۴۶ |
| ۲ | ۷.۱ | حذف `src/App.css` (کد مرده) | ۱ فایل |
| ۳ | ۷.۲ | رفاکتور `tailwind.config.js` به RGB triplet + `<alpha-value>` (رفع ریشه‌ای ۲۶ alpha modifier) | ~۳۰ تغییر |

---

## ۸. Rollback

```powershell
cd frontend
# فایل‌های اصلی فاز ۶.۱
Copy-Item src\index.css.pre61                            src\index.css -Force
Copy-Item src\components\charts\PropAnalytics.tsx.pre61   src\components\charts\PropAnalytics.tsx -Force
Copy-Item src\components\PersianDateInput.tsx.pre61       src\components\PersianDateInput.tsx -Force

# ۱۰ فایل border
Copy-Item src\components\Toast.tsx.pre61         src\components\Toast.tsx -Force
Copy-Item src\pages\PropPage.tsx.pre61           src\pages\PropPage.tsx -Force
Copy-Item src\pages\StrategyPage.tsx.pre61       src\pages\StrategyPage.tsx -Force
Copy-Item src\pages\PersonalPage.tsx.pre61       src\pages\PersonalPage.tsx -Force
Copy-Item src\pages\ImportPage.tsx.pre61         src\pages\ImportPage.tsx -Force
Copy-Item src\pages\JournalPage.tsx.pre61        src\pages\JournalPage.tsx -Force
Copy-Item src\pages\ComparisonPage.tsx.pre61     src\pages\ComparisonPage.tsx -Force
Copy-Item src\pages\DashboardPage.tsx.pre61      src\pages\DashboardPage.tsx -Force
Copy-Item src\pages\RiskManagementPage.tsx.pre61 src\pages\RiskManagementPage.tsx -Force
Copy-Item src\pages\SettingsPage.tsx.pre61       src\pages\SettingsPage.tsx -Force
```

---

> ✅ **فاز ۶.۱ کامل شد** — ۷۶ تغییر، `tsc`/`build` سبز، صفر typo، ۱۰/۱۰ کلاس در CSS نهایی، صفر خطای جدید، گرادیان‌ها دست‌نخورده.