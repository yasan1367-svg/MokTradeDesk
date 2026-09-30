# PHASE 48b — `getAnalysis` با `test_type` (گزارش نهایی)

> وضعیت: ✅ کامل · **commit نشده** (طبق درخواست کاربر)
> دامنه: Frontend فقط (`client.ts` + یک تست جدید) — بک‌اند **هیچ تغییری** لازم نداشت
> HEAD فعلی: `d70f2c1` (Phase 50: README)

---

## ۱) خلاصهٔ اجرایی

پلن 48b می‌گفت: «`getAnalysis()` در `client.ts` مقدار `test_type` نمی‌فرستد ⇒ `AnalysisPage` نمی‌تواند
Forward/Real را ببیند.» بررسی کد نشان داد **نیمهٔ اول درست است و نیمهٔ دوم غلط**:

| ادعای پلن | واقعیت کد |
|---|---|
| `getAnalysis` در `client.ts` `test_type` نمی‌فرستد | ✅ **درست** — `api.get('/api/analytics/'+versionId)` بدون پارامتر |
| `AnalysisPage` از `getAnalysis` استفاده می‌کند | ❌ **غلط** — از `getAnalysisVersion(id, testType)` استفاده می‌کند (از قبل `test_type` می‌فرستد) |
| `AnalysisPage` Forward را نمی‌بیند | ❌ **غلط** — تب «فوروارد» ⇒ `testType='FORWARD'` ⇒ هر دو مسیر (بارگذاری + تحلیل مجدد) پارامتر را پاس می‌دهند |
| بک‌اند باید اصلاح شود | ❌ لازم نبود — `GET /api/analytics/{version_id}?test_type=...` از **فاز 48a.2** پیاده شده و تست دارد |

**نتیجه:** یک باگ واقعی (عدم ارسال `test_type`) + یک باگ هم‌خانواده در همان endpoint (`getVersionAnalysis`)
رفع شد؛ `AnalysisPage` **عمداً دست‌نخورده** ماند (دلیل در بخش ۴) و یک تست فرانت برای جلوگیری از رگرسیون افزوده شد.

| KPI | نتیجه |
|---|---|
| `npx tsc -b --force` | **TSC_EXIT=0** |
| `npx vitest run` | **VITEST_EXIT=0** — ۳ فایل / **۱۴ تست pass** (۹ قبلی + ۵ جدید) |
| `npm run build` | **BUILD_EXIT=0** (`✓ built in 10.17s`) |
| `pytest tests/test_phase48a_get_analysis.py` | **PYTEST_EXIT=0** — ۲ passed (اثبات پشتیبانی بک‌اند از `test_type`) |
| تغییرات | `client.ts`: ۷+ / ۴− · فایل جدید تست: ۶۰ خط · `AnalysisPage`: **۰ خط** |

---

## ۲) گام ۱ — کد قبل از تغییر (گزارش)

### `frontend/src/api/client.ts` (خطوط ۲۵–۲۸)

```typescript
export const analyzeVersion = (versionId: number) =>
  api.post(`/api/analytics/analyze/${versionId}`);
export const getAnalysis = (versionId: number) =>
  api.get(`/api/analytics/${versionId}`);
```

- **چطور `versionId` را می‌فرستد؟** به‌صورت **path param** داخل template string.
- **آیا `test_type` دارد؟** ❌ **نه** (نه در URL، نه در `params`).
- **چطور `api.get` را صدا می‌زند؟** `api.get(url)` — بدون آرگومان دوم (config/params).
- **مصرف‌کننده در فرانت:** 🔴 **صفر** (در هیچ page/component ای import نشده؛ فقط در اسناد فازها ذکر شده).

### یافتهٔ اضافه — دوقلوی همان endpoint (خطوط ۲۶۶–۲۷۰)

```typescript
export const getVersionAnalysis = (versionId: number) =>
  api.get(`/api/analytics/${versionId}`);
```

همان endpoint، همان باگ، **صفر مصرف‌کننده** ⇒ هم‌زمان با `getAnalysis` رفع شد.

### یافتهٔ اضافه — مسیرهای scoped (خطوط ۲۷۸–۲۸۵) که از قبل درست‌اند

```typescript
export const analyzeVersionScoped = (versionId: number, testType?: string) =>
  api.post(`/api/analytics/analyze/version/${versionId}`, null,
    { params: testType ? { test_type: testType } : {} });
export const getAnalysisVersion = (versionId: number, testType?: string) =>
  api.get(`/api/analytics/analysis/version/${versionId}`,
    { params: testType ? { test_type: testType } : {} });
```

### `frontend/src/pages/AnalysisPage.tsx` (گزارش کامل)

- **کجا `getAnalysis` صدا زده می‌شود؟** **هیچ‌جا.** (صفر مصرف‌کننده — تأیید با جست‌وجوی سراسری روی `src`.)
- **کجا تحلیل گرفته می‌شود؟** در `useEffect` بارگذاری (خط ۱۰۵) و در `handleReanalyze` (خط ۱۴۲):

```tsx
const isVersion = scope === 'backtest' || scope === 'forward';
const testType = scope === 'forward' ? 'FORWARD' : scope === 'backtest' ? 'BACKTEST' : undefined;
const res = isVersion ? await getAnalysisVersion(selectedId, testType)   // ← test_type دارد ✅
                      : await getAnalysisProp(selectedId);
```

- **آیا `test_type` دارد؟** ✅ **بله** — از تب فعال مشتق می‌شود و به `getAnalysisVersion` می‌رود.
- **`versionId` از کجا می‌آید؟** از state `selectedId` که با `<select>` نسخه‌ها (خط ۲۰۱–۲۰۵) پر می‌شود.
- **انتخابگر Version دارد؟** ✅ بله (`versions` از `getAllVersions()`؛ فقط در تب‌های بک‌تست/فوروارد).
- **انتخابگر Test Type دارد؟** ✅ بله ولی به شکل **تب** (نه dropdown): `SCOPE_TABS` = بک‌تست / فوروارد / مرحله ۱ / ۲ / ۳
  (خط ۲۵–۳۱، ذخیره در `localStorage` با کلید `analysis_selected_scope`).
- **ساختار کلی صفحه:** کارت تب‌ها → کارت انتخاب نسخه/مرحله + «تحلیل مجدد» + «دانلود PDF» → ۴ متریک اصلی
  (سود خالص/نرخ برد/PF/DD) → ۴ متریک تکمیلی (Net R/اکسپکتانسی/میانگین/باخت متوالی) → Consistency →
  ۵ نمودار → ۴ `AnalysisTable` → جدول معاملات (`getTrades`).
- **آیا `analyzeVersion` (قدیمی) را صدا می‌زند؟** ❌ خیر؛ `analyzeVersionScoped(selectedId, testType)` (خط ۱۴۱).
  `analyzeVersion` هم صفر مصرف‌کننده دارد و مسیر legacy `POST /analytics/analyze/{id}` در بک‌اند اصلاً
  پارامتر `test_type` نمی‌پذیرد ⇒ **عمداً تغییر نکرد** (اضافه‌کردن پارامتری که بک‌اند نادیده می‌گیرد = باگ خاموش جدید).
- **Real:** تحلیل «واقعی» از طریق تب‌های **مرحلهٔ پراپ** (شامل `funded_real`) سرو می‌شود و مسیر
  `GET /api/analytics/analysis/version/{id}` برای `REAL_PERSONAL`/`REAL_PROP` با **400** رد می‌کند:
  «تحلیل نسخه فقط برای BACKTEST یا FORWARD است…» (`backend/app/api/analytics.py:123-124`).

---

## ۳) تغییرات `frontend/src/api/client.ts` (گام ۲)

```diff
+// فاز ۴۸b: `test_type` صریح (پیش‌فرض BACKTEST — همان پیش‌فرض بک‌اند در فاز 48a.2).
+// بدون آن، برای نسخه‌ای که هم تحلیل Backtest و هم Forward دارد، پاسخ نامعین/کهنه می‌شد.
-export const getAnalysis = (versionId: number) =>
-  api.get(`/api/analytics/${versionId}`);
+export const getAnalysis = (versionId: number, testType: string = 'BACKTEST') =>
+  api.get(`/api/analytics/${versionId}?test_type=${testType}`);
```

```diff
+// فاز ۴۸b: همان endpoint بالا ⇒ همان باگ `test_type` (رفع شد برای هم‌خوانی کامل)
-export const getVersionAnalysis = (versionId: number) =>
-  api.get(`/api/analytics/${versionId}`);
+export const getVersionAnalysis = (versionId: number, testType: string = 'BACKTEST') =>
+  api.get(`/api/analytics/${versionId}?test_type=${testType}`);
```

**چرا بی‌خطر است؟** امضا **افزایشی** است (پارامتر دوم optional با پیش‌فرض) ⇒ فراخوانی‌های تک‌آرگومانی
رفتار قبلی را حفظ می‌کنند و پیش‌فرض `'BACKTEST'` دقیقاً برابر پیش‌فرض بک‌اند است
(`test_type: Optional[str] = "BACKTEST"` در `analytics.py:940`) ⇒ **بدون تغییر رفتار خاموش**.

---

## ۴) `AnalysisPage.tsx` — چرا تغییر نکرد (انحراف آگاهانه از گام ۳ پلن)

گام ۳ پلن می‌خواست state + `<select>` با گزینه‌های `BACKTEST/FORWARD/REAL_PERSONAL/REAL_PROP` به صفحه اضافه شود.
در وضعیت فعلی کد این کار **رگرسیون** می‌ساخت:

1. **صفحه از `getAnalysis` استفاده نمی‌کند** ⇒ گام ۳ چیزی را «وصل» نمی‌کرد و کد مرده اضافه می‌شد.
2. **انتخابگر Test Type از قبل وجود دارد** (تب‌های بک‌تست/فوروارد) ⇒ dropdown دوم، **دو منبع حقیقت متناقض**
   برای `testType` می‌ساخت (`scope` در برابر state جدید).
3. **گزینه‌های `REAL_*` روی مسیر نسخه خطای 400 می‌دهند** — بک‌اند صریحاً رد می‌کند
   (`analytics.py:123-124` و همان گارد در GET) ⇒ کاربر «واقعی» را انتخاب می‌کرد و خطا می‌گرفت.
4. **«Real» در این صفحه از مسیر دیگری پوشش داده می‌شود:** تب‌های مرحله ۱/۲/۳ (`funded_real`)
   ⇒ افزودن `REAL_*` به انتخابگر نسخه، قابلیت جدیدی اضافه نمی‌کرد.

آیا هدف واقعی «نمایش حساب شخصی واقعی (`REAL_PERSONAL`) در `AnalysisPage`» است؟ آن یک **قابلیت جدید** است
(نه باگ یک‌خطی) و به تب جدید + `getAnalysisPersonalAccount` + اندپوینت معاملات بر اساس
`personal_trading_account_id` نیاز دارد ⇒ پیشنهاد فاز 48c (بخش ۷).

---

## ۵) تست جدید (گام ۴)

`frontend/src/__tests__/client.analysis.test.ts` (۵ تست) — با `vi.spyOn` روی نمونهٔ axios، **URL/پارامترهای واقعی** بررسی می‌شود:

| تست | انتظار |
|---|---|
| `getAnalysis(7)` | `/api/analytics/7?test_type=BACKTEST` |
| `getAnalysis(12, 'FORWARD')` | `/api/analytics/12?test_type=FORWARD` |
| `getVersionAnalysis(3, 'FORWARD')` | `/api/analytics/3?test_type=FORWARD` |
| `getAnalysisVersion(5, 'FORWARD')` | `/api/analytics/analysis/version/5` + `params:{test_type:'FORWARD'}` (ضد‌رگرسیون) |
| `analyzeVersionScoped(5, 'FORWARD')` | `/api/analytics/analyze/version/5` + `params:{test_type:'FORWARD'}` (ضد‌رگرسیون) |

---

## ۶) نتیجهٔ تست‌ها (خروجی واقعی)

```text
npx tsc -b --force                                      → TSC_EXIT=0
npx vitest run        → Test Files 3 passed (3) | Tests 14 passed (14) | VITEST_EXIT=0
npm run build                                           → ✓ built in 10.17s | BUILD_EXIT=0
python -m pytest tests\test_phase48a_get_analysis.py -q → 2 passed | PYTEST_EXIT=0
```

> نکته: تست‌های فرانت در `tsconfig.app.json` **exclude** شده‌اند (`src/**/*.test.ts`)، پس `tsc -b`
> آن‌ها را type-check نمی‌کند و فقط vitest اجرا می‌کند (فایل جدید: ۵ pass از ۱۴).

---

## ۷) وضعیت Git و پیشنهاد بعدی

```text
$ git status --short
 M frontend/src/api/client.ts
?? frontend/src/__tests__/client.analysis.test.ts

$ git diff --stat
 frontend/src/api/client.ts | 11 +++++++----
 1 file changed, 7 insertions(+), 4 deletions(-)

$ git log --oneline -3
d70f2c1 (HEAD -> main, origin/main, origin/HEAD) Phase 50: README - setup/run/test/backup/troubleshooting
723154f Phase 48a: Add implementation report
f985f91 Phase 48a.6: rewrite ComparisonPage for new compare contract + report
```

✅ **هیچ commit ای زده نشد** (طبق درخواست) — منتظر تأیید کاربر.

### پیشنهاد فاز بعدی (48c) — خارج از دامنهٔ این تسک
1. **REAL_PERSONAL در `AnalysisPage`:** تب «واقعی شخصی» + `getAnalysisPersonalAccount` + معاملات بر اساس
   `personal_trading_account_id` (تب «واقعی پراپ» = استیج `funded_real` که فعلاً در تب «مرحله ۳» است).
2. **پاک‌سازی dead code:** `analyzeVersion` + `getAnalysis`/`getVersionAnalysis` **صفر مصرف‌کننده** دارند؛
   یا حذف شوند یا (بهتر) به‌عنوان wrapper عمومی مسیر scoped باقی بمانند.
3. **پایداری فیلترها در URL** (یادداشت باقی‌ماندهٔ فاز 48a) — refresh = از دست رفتن تب/انتخاب نسخه.

