# 🌙 فاز ۶ — رفع Dark Mode در PersonalPage و PropPage

> **وضعیت:** ✅ کامل و تست‌شده
> **دامنه:** فقط `PersonalPage.tsx` + `PropPage.tsx` (طبق تصمیم گزینه ۲)
> **تاریخ:** 2026-09-24

---

## ۱. خلاصه تغییرات

| فایل | نوع تغییر | حجم تغییر |
|------|-----------|-----------|
| `frontend/src/index.css` | ✏️ افزودن **۵ متغیر جدید** (روشن + تاریک) | +۱۰ خط |
| `frontend/src/pages/PersonalPage.tsx` | ✏️ جایگزینی رنگ‌ها | **۲۲۴ جایگزینی** |
| `frontend/src/pages/PropPage.tsx` | ✏️ جایگزینی رنگ‌ها | **۴۴۹ جایگزینی** |
| **جمع** | | **۶۷۳ جایگزینی** |

**قبل از فاز ۶:** هر دو صفحه **صفر استفاده از `dark:`** داشتند و از رنگ‌های hardcoded فقط-روشن استفاده می‌کردند.
**بعد از فاز ۶:** همه سطوح/متن/حاشیه‌ها از CSS variables استفاده می‌کنند → با سوییچ تم کاملاً dark-aware.

### 🆕 متغیرهای جدید (`index.css`)

```css
:root {
  --purple-soft: #F1ECFF;
  --warning-soft: #FFF5DB;
  --warning-soft-alt: #FFF8E5;
  --purple-border: #D5C8F5;
  --warning-border: #F0DBA6;
}

.dark {
  --purple-soft: #2A1F4A;
  --warning-soft: #3D2F1A;
  --warning-soft-alt: #3D2F1A;
  --purple-border: #4A3A6A;
  --warning-border: #5A4A2A;
}
```

---

## ۲. جدول Mapping اجراشده

### گروه A — سطوح (Surface)
| از | به | Personal | Prop |
|---|---|---|---|
| `bg-white` | `bg-[var(--bg-card)]` | 28 | 42 |
| `bg-[#F8FAFF]` | `bg-[var(--bg-input)]` | 19 | 40 |
| `bg-[#F5F7FB]` | `bg-[var(--bg-elevated)]` | 1 | 5 |
| `bg-[#E5EBF3]` | `bg-[var(--border-subtle)]` | – | 1 |

### گروه B — متن
| از | به | Personal | Prop |
|---|---|---|---|
| `text-[#1A2B47]` | `text-[var(--text-primary)]` | 40 | 78 |
| `text-[#6B7A94]` | `text-[var(--text-secondary)]` | 31 | 68 |
| `text-[#9AA8BF]` | `text-[var(--text-muted)]` | 5 | 5 |

### گروه C — حاشیه
| از | به | Personal | Prop |
|---|---|---|---|
| `border-[#E5EBF3]` | `border-[var(--border-subtle)]` | 39 | 72 |
| `border-[#A9C1FA]` | `border-[var(--border-accent)]` | 7 | 13 |

### گروه D — Semantic
| از | به | Personal | Prop |
|---|---|---|---|
| `bg-[#EDF3FF]` | `bg-[var(--accent-soft)]` | 4 | 10 |
| `ring-[#EDF3FF]` | `ring-[var(--accent-soft)]` | 5 | 1 |
| `bg-[#E5F8F1]` | `bg-[var(--profit-soft)]` | 3 | 8 |
| `bg-[#FFEDF0]` | `bg-[var(--loss-soft)]` | 5 | 9 |
| `text-[#E45D72]` | `text-[var(--loss)]` | 12 | 28 |
| `text-[#13AE81]` | `text-[var(--profit)]` | 5 | 18 |
| `text-[#3F7CFF]` | `text-[var(--accent)]` | 2 | 8 |
| `border-[#3F7CFF]` | `border-[var(--accent)]` | 15 | 7 |
| `border-[#13AE81]` | `border-[var(--profit)]` | – | 17 |
| `border-[#7959D6]` | `border-[var(--purple)]` | – | 8 |
| `border-[#E45D72]` | `border-[var(--loss)]` | – | 2 |
| `text-[#7959D6]` | `text-[var(--purple)]` | – | 2 |
| `text-[#D99B25]` | `text-[var(--warning)]` | – | 2 |
| `bg-[#F1ECFF]` | `bg-[var(--purple-soft)]` | 2 | 1 |
| `bg-[#FFF5DB]` | `bg-[var(--warning-soft)]` | 1 | – |
| `bg-[#FFF8E5]` | `bg-[var(--warning-soft-alt)]` | – | 2 |
| `border-[#D5C8F5]` | `border-[var(--purple-border)]` | – | 1 |
| `border-[#F0DBA6]` | `border-[var(--warning-border)]` | – | 1 |

### گروه E — 🚫 دست‌نخورده (عمداً)
| الگو | باقیمانده در Personal | در Prop | دلیل |
|---|---|---|---|
| `text-white` | 8 | 26 | متن روی دکمه‌های گرادیانی |
| `border-[#A8E6CF]` | 3 | 7 | حاشیه همرنگ semantic |
| `border-[#F0A6B2]` | 3 | 7 | حاشیه همرنگ semantic |
| `from-[#3F7CFF]` / `to-[#5B8DEF]` | – | 6 / 6 | گرادیان برند |
| `from-[#E45D72]` / `to-[#F0A6B2]` | – | 4 / 4 | گرادیان danger |
| `from-[#13AE81]` / `to-[#4DD9A9]` | – | 2 / 2 | گرادیان success |
| `bg-[#3F7CFF]` | – | 2 | دکمه solid |
| `bg-[#E45D72]` | – | 1 | badge solid |
| `bg-[#D99B25]` | – | 1 | دکمه solid |
| `accent-[#13AE81]` | – | 1 | checkbox accent |
| `bg-black/60` | – | 5 | overlay مودال |

**نتیجه residual:** PersonalPage=**۶** | PropPage=**۴۳** — **۱۰۰٪ مطابق گروه E** ✅

---

## ۳. نتایج تست

| # | بررسی | دستور/روش | نتیجه |
|---|-------|-----------|-------|
| ۱ | TypeScript (build mode، بدون کش) | `npx tsc -b --force` | ✅ **`TSCB_EXIT=0`** |
| ۲ | Production build | `npm run build` | ✅ **`BUILD_EXIT=0`** (`✓ built in 2.56s`) |
| ۳ | نبود `bg-white` باقیمانده | regex count | ✅ Personal=**0**، Prop=**0** |
| ۴ | حفظ `text-white` (گروه E) | regex count | ✅ Personal=**8**، Prop=**26** |
| ۵ | **صفر typo در متغیرها** | cross-check ۲۱ var استفاده‌شده vs ۲۷ تعریف‌شده | ✅ **`NONE - all vars defined OK`** |
| ۶ | **JIT: تولید کلاس‌ها در CSS نهایی** | بررسی ۴۳ کلاس var در `dist/assets/*.css` | ✅ **۱۰۰٪ موجود (صفر missing)** |
| ۷ | اعتبار مقادیر `border-[var(...)]` | بازرسی declaration | ✅ `border-color:var(--x)` (نه width — gotcha رخ نداد) |
| ۸ | لینت: خطای جدید منطقی | eslint مقایسه با `.bak` | ✅ **صفر خطای جدید** (۴ خطای موجود در کد بایت‌به‌بایت یکسان) |
| ۹ | زنجیره فعال‌سازی تم | `App.tsx:102-108` → `html.dark` → `.dark{...}` | ✅ تأیید شد |

### نمونه diff (کارت‌های جریان نقدی — PersonalPage)

```diff
- <div className="bg-white border-2 border-[#A8E6CF] rounded-[22px] p-6 shadow-md ...">
+ <div className="bg-[var(--bg-card)] border-2 border-[#A8E6CF] rounded-[22px] p-6 shadow-md ...">

- <div className="w-12 h-12 rounded-[14px] bg-[#EDF3FF] flex items-center justify-center text-2xl">
+ <div className="w-12 h-12 rounded-[14px] bg-[var(--profit-soft)] flex items-center justify-center text-2xl">

- <div className="text-[13px] text-[#6B7A94] font-bold">کل ورودی</div>
+ <div className="text-[13px] text-[var(--text-secondary)] font-bold">کل ورودی</div>

- <div className="text-[32px] font-extrabold text-[#13AE81]">+${cashflow.total_in}</div>
+ <div className="text-[32px] font-extrabold text-[var(--profit)]">+${cashflow.total_in}</div>

  <div style={{ background: 'linear-gradient(90deg, #13AE81, #4DD9A9)' }} />   ← دست‌نخورده (گرادیان)
```

---

## ۴. نکات و هشدارها

### ۴.۱ ⚠️ تصحیح mapping: `--bg-secondary` وجود ندارد
spec شما گفت `bg-[#F8FAFF]` → `var(--bg-secondary)`، اما این متغیر در `index.css` **تعریف نشده**. متغیر صحیح **`--bg-input`** است (روشن `#F8FAFF` — دقیقاً همان رنگ؛ تاریک `#1E2F41`). از `--bg-input` استفاده شد.

### ۴.۲ ⚠️ کاوئت بصری: حاشیه‌های semantic روی پس‌زمینه‌های soft
طبق گروه E، `border-[#A8E6CF]` و `border-[#F0A6B2]` تغییر نکردند. اما این‌ها کنار `bg-[var(--profit-soft)]` / `bg-[var(--loss-soft)]` قرار می‌گیرند که در تاریک **تیره** می‌شوند:

| حالت | پس‌زمینه | حاشیه | نتیجه |
|------|----------|-------|-------|
| روشن | `#E5F8F1` (سبز روشن) | `#A8E6CF` | هماهنگ ✅ |
| تاریک | `#0D2E22` (سبز تیره) | `#A8E6CF` (سبز روشن) | حاشیه **روشن** می‌ماند ⚠️ |

**تعداد تحت تأثیر:** ~۶ در Personal + ~۱۴ در Prop. **رفع پیشنهادی:** افزودن `--profit-border` / `--loss-border` (مثل کاری که برای purple/warning شد). خارج از دامنه تأییدشده — در فاز بعدی قابل انجام است.

### ۴.۳ ℹ️ `border-[var(--loss)]` تنها با prefix تولید می‌شود
در CSS نهایی `.border-\[var\(--loss\)\]` (بدون prefix) **وجود ندارد** — چون در سورس فقط به‌صورت `focus:border-[var(--loss)]` استفاده شده و Tailwind همان را ساخته: `.focus\:border-\[var\(--loss\)\]` ✅
→ **هیچ کلاس بدون تولید (missing) وجود ندارد.**

### ۴.۴ ℹ️ خطاهای ESLint از قبل موجود (بدون تغییر)
| خط | پیام | وضعیت |
|----|------|-------|
| `PersonalPage.tsx:115`, `:122` | `Calling setState synchronously within an effect...` | ✅ از قبل موجود — کد **بایت‌به‌بایت** مثل `.bak` |
| `PropPage.tsx:166`, `:167` | `Cannot access variable before it is declared` | ✅ از قبل موجود (فقط نام تابع عوض شد) |
| `no-explicit-any` | ۳۱ مورد | ✅ از قبل موجود در کل پروژه |

> **اثبات:** خطوط ۱۱۳-۱۲۳ `PersonalPage.tsx` بین نسخه جدید و `.bak` **یکسان** هستند (مقایسه شد). تغییرات فاز ۶ فقط رشته‌های `className` بودند و نمی‌توانند خطای hook/logic ایجاد کنند.

### ۴.۵ ℹ️ بکاپ‌ها
فایل‌های `.bak` **حفظ شده‌اند** (طبق درخواست شما):
```
frontend/src/pages/PersonalPage.tsx.bak   (41,617 bytes)
frontend/src/pages/PropPage.tsx.bak       (89,513 bytes)
```
Tailwind این فایل‌ها را نمی‌بیند (`content: ["./src/**/*.{js,ts,jsx,tsx}"]` — پسوند `.bak` مطابقت ندارد). در صورت اطمینان می‌توانید حذفشان کنید.

### ۴.۶ ℹ️ خارج از دامنه (فازهای بعدی)
| فایل | مسئله | تعداد |
|------|-------|-------|
| `PropAnalytics.tsx` (فرزند PropPage) | رنگ hardcoded | ۱۲ |
| `PersianDateInput.tsx` (فرزند هر دو) | کلاس‌های **نامدار** غیر-dark-aware (`bg-card`, `border-card-border`, `text-text-primary`, `text-text-secondary`, `border-accent`) | ۵ |
| `TradesPage.tsx` | کلاس‌های نامدار | ۱۷۲ |
| `AnalysisPage.tsx` | کلاس‌های نامدار | ۴۲ |
| `AnalysisTable.tsx` | – | ۱۵ |
| `StatCard.tsx` / `MetricCard.tsx` | – | ۶ / ۶ |
| charts (۵ فایل) | – | ۱ هر کدام |

> **⚠️ مهم:** `tailwind.config.js` رنگ‌های **نامدار** (`card`, `card-border`, `text-primary`, `accent`, ...) را با hex ثابت تعریف کرده و **بدون dark variant** هستند. هر فایلی که از این کلاس‌ها استفاده کند در تاریک روشن می‌ماند. رفع نیازمند تبدیلشان به `var()` است.

---

## ۵. گام بعدی پیشنهادی

| # | فاز | موضوع |
|---|-----|-------|
| ۱ | **۶.۱** | `PropAnalytics.tsx` (۱۲) + `PersianDateInput.tsx` (۵ کلاس نامدار) |
| ۲ | **۶.۲** | افزودن `--profit-border` / `--loss-border` برای رفع کاوئت ۴.۲ |
| ۳ | **۷** | `TradesPage` (۱۷۲) + `AnalysisPage` (۴۲) + بقیه |

---

## ۶. Rollback

```powershell
cd frontend
Copy-Item src\pages\PersonalPage.tsx.bak src\pages\PersonalPage.tsx -Force
Copy-Item src\pages\PropPage.tsx.bak     src\pages\PropPage.tsx -Force
# متغیرهای index.css افزودنی و بی‌ضرر هستند (بدون rollback)
```

---

> ✅ **فاز ۶ کامل شد** — ۶۷۳ جایگزینی، `tsc`/`build` سبز، صفر typo، ۱۰۰٪ کلاس‌ها در CSS نهایی، صفر خطای جدید.