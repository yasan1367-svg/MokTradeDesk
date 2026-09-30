# PHASE 48c — تب «واقعی شخصی» (REAL_PERSONAL) + ماندگاری فیلترها در URL (گزارش نهایی)

> وضعیت: ✅ کامل · **commit نشده** (طبق درخواست کاربر — منتظر تأیید)
> دامنه: Frontend فقط — **هیچ فایل بک‌اندی تغییر نکرد** (endpointهای `personal-account` از فاز ۲۰/۲۳ وجود داشتند و تست دارند)
> HEAD فعلی: `937ab28` (Phase 48b)

---

## ۱) خلاصهٔ اجرایی

| هدف پلن | نتیجه |
|---|---|
| تب «واقعی شخصی» (`REAL_PERSONAL`) در `AnalysisPage` | ✅ افزوده شد (تب 💼) + انتخابگر حساب + تحلیل/معاملات همان دامنه |
| ماندگاری فیلترهای `ComparisonPage` در URL | ✅ افزوده شد (`?versions=1,2&test_type=FORWARD&symbol=...`) |

| KPI | نتیجه |
|---|---|
| `npx tsc -b --force` | **TSC_EXIT=0** |
| `npx vitest run` | **VITEST_EXIT=0** — **۴ فایل / ۲۹ تست pass** (۱۴ قبلی + **۱۵ جدید**) |
| `npm run build` | **BUILD_EXIT=0** (`✓ built in 3.47s`) |
| `pytest -q` (بک‌اند، بدون تغییر) | **PYTEST_EXIT=0** — **۳۷۳ تست pass، ۰ خطا** (count دقیق با شمارش نشانگرهای پیشرفت) |
| `ruff check .` | ⚠️ **قابل اجرا نبود** — `ruff` در venv نصب نیست (`No module named ruff`؛ `pip list` فقط `pytest`/`pytest-cov` دارد). چون **هیچ فایل بک‌اندی تغییر نکرد**، وضعیت lint نسبت به baseline بدون تغییر است. |
| تغییرات | ۴ فایل ویرایش + ۳ فایل جدید (۲ util + ۱ تست) · ۱۵۲+ / ۳۰− |

### دو انحراف آگاهانه از پلن (با دلیل)

| # | پلن می‌گفت | واقعیت کد | کاری که انجام شد |
|---|---|---|---|
| ۱ | `useSearchParams` از `react-router-dom` | ❌ **`react-router-dom` نصب نیست** (صفر نتیجه در ۳۳۷ فایل؛ ناوبری با `useState` در `App.tsx`) | ماژول مشترک `utils/urlState.ts` روی **History API خام** (`replaceState`) |
| ۲ | فقط فیلترهای `ComparisonPage` در URL | ❌ صفحهٔ فعال در URL نبود ⇒ **refresh همیشه داشبورد را نشان می‌داد** و فیلترهای ذخیره‌شده بی‌اثر می‌شدند | نگهداری صفحه هم در URL (`?page=comparison`) — گام **48c.2b** |
| ۳ | state جداگانهٔ `selectedPersonalAccount` | `selectedId` از قبل «دامنهٔ انتخاب‌شده» است (نسخه/مرحله) | از **همان `selectedId`** استفاده شد (منبع واحد حقیقت + reset خودکار در `handleScopeChange`) |

---

## ۲) بخش ۱ — تب «واقعی شخصی» (REAL_PERSONAL)

### ۲.۱ گزارش گام ۱.۱ — کد قبل از تغییر (`AnalysisPage.tsx`)

| پرسش | پاسخ |
|---|---|
| `SCOPE_TABS` چیست؟ | ۵ تب: `backtest` 📊 / `forward` 📈 / `prop_stage_1` 🏁 / `prop_stage_2` 🔍 / `prop_stage_3` 💰 — هر آیتم `{key, icon, label}` |
| `scope` state چطور است؟ | `useState<ScopeType>(readStoredScope)` + ماندگاری در `localStorage['analysis_selected_scope']` با گارد `VALID_SCOPES` (scopeهای حذف‌شده مثل `'broker'` ⇒ fallback به `backtest`) |
| `selectedId` چطور انتخاب می‌شود؟ | یک state مشترک؛ با `<select>` نسخه‌ها یا `<select>` مراحل پراپ پر می‌شود؛ برای تب‌های پراپ **اولین مرحلهٔ همان نوع** خودکار انتخاب می‌شود (`STAGE_TYPE_BY_SCOPE`) |
| endpointها | بارگذاری: `getAnalysisVersion(id, testType)` / `getAnalysisProp(id)` · تحلیل مجدد: `analyzeVersionScoped(id, testType)` / `analyzePropStage(id)` · معاملات: `getTrades({version_id\|prop_stage_id, test_type, limit:500})` |
| رندر تب‌ها | کارت اول صفحه: `SCOPE_TABS.map(...)` → `<button onClick={() => handleScopeChange(t.key)}>` |
| ساختار کلی | تب‌ها → انتخابگر دامنه + «تحلیل مجدد» + «دانلود PDF» → ۴ متریک اصلی → ۴ متریک تکمیلی → Consistency → ۵ نمودار → ۴ `AnalysisTable` → جدول معاملات |

⚠️ نکتهٔ مهم: **هیچ‌کدام از توابع `analyzePersonalAccount` / `getAnalysisPersonalAccount` در `client.ts` وجود نداشت** ⇒ باید اضافه می‌شدند (برخلاف فرض پلن).

### ۲.۲ گزارش گام ۱.۲ — بررسی بک‌اند (بدون تغییر)

```python
# backend/app/api/analytics.py
@router.post("/analyze/personal-account/{personal_trading_account_id}")   # خط ۱۴۵
@router.get ("/analysis/personal-account/{personal_trading_account_id}")  # خط ۸۵۷
```

| پرسش | پاسخ |
|---|---|
| endpoint چیست؟ | `POST /api/analytics/analyze/personal-account/{id}` (اجرای تحلیل) + `GET /api/analytics/analysis/personal-account/{id}` (خواندن تحلیل ذخیره‌شده) |
| ورودی چیست؟ | فقط `personal_trading_account_id` (path param) — **بدون `test_type`** (نوع تست از خود دامنه معلوم است: REAL_PERSONAL) |
| خروجی POST | `{message, analysis_id, run_id, personal_trading_account_id}` · در نبود معامله ⇒ **404** «هیچ معامله‌ای برای این دامنه یافت نشد» |
| خروجی GET | `_analysis_response(result)`: `total_trades, win_rate, profit_factor, net_pnl, net_r, max_dd, expectancy, expectancy_r, avg_win, avg_loss, largest_win, largest_loss, max_consecutive_losses, consistency_analysis, session_analysis, weekday_analysis, hour_analysis, custom_time_analysis, created_at` |
| دامنه/کلید ذخیره | `scope=PERSONAL_ACCOUNT`, `scope_key=str(personal_trading_account_id)` (در `AnalysisService.analyze_personal_account`؛ معاملات `is_deleted == False`) |
| گارد سازگاری | `_guard_analyzable(...)`: اگر تعداد معاملات فعلی ≠ `result.total_trades` ⇒ **404 «تحلیل کهنه است… دوباره تحلیل کنید»** |
| منبع لیست حساب‌ها | `GET /api/trading/accounts` ⇒ آیتم‌ها: `{id, broker_name, account_number, account_label, currency, initial_balance, ...}` (`backend/app/api/trading.py:125`) — همان منبعی که `TradesPage` استفاده می‌کند |
| تست‌های موجود | `tests/test_analysis_phase23.py:229-230` و `tests/test_phase40_full_regression.py:313,611` (POST+GET حساب شخصی) ⇒ مسیر بک‌اند تست‌شده است |

### ۲.۳ تغییرات اعمال‌شده

**الف) `frontend/src/api/client.ts` (+۲ تابع):**
```ts
// فاز ۴۸c — تحلیل حساب معاملاتی شخصی (دامنهٔ REAL_PERSONAL، scope=PERSONAL_ACCOUNT)
export const analyzePersonalAccount = (personalTradingAccountId: number) =>
  api.post(`/api/analytics/analyze/personal-account/${personalTradingAccountId}`);
// فاز ۴۸c — خواندن تحلیل ذخیره‌شدهٔ حساب معاملاتی شخصی
export const getAnalysisPersonalAccount = (personalTradingAccountId: number) =>
  api.get(`/api/analytics/analysis/personal-account/${personalTradingAccountId}`);
```

**ب) `frontend/src/pages/AnalysisPage.tsx`:**

```diff
-type ScopeType = 'backtest' | 'forward' | 'prop_stage_1' | 'prop_stage_2' | 'prop_stage_3';
-const SCOPE_TABS: { key: ScopeType; icon: string; label: string }[] = [
+type ScopeType = 'backtest' | 'forward' | 'real_personal' | 'prop_stage_1' | ...;
+const SCOPE_TABS: { key: ScopeType; icon: string; label: string; testType?: string }[] = [
   { key: 'forward', icon: '📈', label: 'فوروارد', testType: 'FORWARD' },
+  { key: 'real_personal', icon: '💼', label: 'واقعی شخصی', testType: 'REAL_PERSONAL' },
```
```diff
+const testTypeOfScope = (scope: ScopeType): string | undefined =>
+  SCOPE_TABS.find((t) => t.key === scope)?.testType;      // منبع واحد test_type
+const [personalAccounts, setPersonalAccounts] = useState<PersonalAccountOption[]>([]);
```
```diff
-const testType = scope === 'forward' ? 'FORWARD' : scope === 'backtest' ? 'BACKTEST' : undefined;
+const testType = testTypeOfScope(scope);
 const res = isVersion
   ? await getAnalysisVersion(selectedId, testType)
-  : await getAnalysisProp(selectedId);
+  : scope === 'real_personal'
+    ? await getAnalysisPersonalAccount(selectedId)
+    : await getAnalysisProp(selectedId);
```
```diff
+} else if (scope === 'real_personal') {
+  await analyzePersonalAccount(selectedId);
+  const res = await getAnalysisPersonalAccount(selectedId);
+  setAnalysis(res.data);
 } else {
```
- **معاملات:** `scope === 'real_personal'` ⇒ `getTrades({ personal_trading_account_id: selectedId, limit: 500 })`
- **انتخاب خودکار:** در effect موجود، اگر `scope === 'real_personal'` ⇒ اولین حساب شخصی انتخاب می‌شود
- **انتخابگر:** `<select>` سوم برای حساب‌های شخصی (برچسب: `account_label || account_number || #id` + `— broker_name`)
- **برچسب نوع تست در جدول معاملات:** `رییل شخصی` / `رییل پراپ` (به‌جای «رییل» برای همه)
- **متن حالت خالی:** «یک دامنه (نسخه / حساب شخصی / مرحله پراپ) انتخاب کنید…»
- 🔒 **دکمهٔ PDF نسخه‌محور ماند** (اندپوینت `export/analysis/pdf` فقط `version_id` می‌پذیرد)

---

## ۳) بخش ۲ — ماندگاری فیلترها در URL

### ۳.۱ گزارش گام ۲.۱ — کد قبل از تغییر (`ComparisonPage.tsx`)

| پرسش | پاسخ |
|---|---|
| stateها | `versions`, `strategies` · `selectedIds`, `filterStrategy`, `searchQuery`, `testType='BACKTEST'`, `symbol`, `dateFrom`, `dateTo` · `result`, `loading`, `drawerVersion` |
| `selectedIds` چطور مدیریت می‌شود؟ | `toggleVersion(id)` — افزودن/حذف با سقف `MAX_SELECT = 5` (Toast هشدار) |
| ارسال به API | `compareVersions({ version_ids: selectedIds, test_type: testType, symbol: symbol.trim() || undefined, date_from, date_to })` در `handleCompare` |
| `react-router-dom` نصب است؟ | ❌ **نه** — در `package.json` فقط `axios, lucide-react, react, react-dom, recharts, zustand`؛ جست‌وجوی `react-router|useSearchParams|BrowserRouter` ⇒ **صفر نتیجه** در ۳۳۷ فایل. ناوبری: `App.tsx` با `useState<Page>` |
| ذخیرهٔ وضعیت | فقط `localStorage` (تب تحلیل) — **هیچ فیلتری در URL نبود** ⇒ refresh = پاک شدن همه‌چیز |

### ۳.۲ تغییرات اعمال‌شده

**الف) فایل جدید `frontend/src/utils/urlState.ts`** (ابزار مشترک، بدون وابستگی جدید):
```ts
buildSearch(currentSearch, patch)  // خالص: کلیدهای دیگر حفظ، null/undefined/'' ⇒ حذف کلید
readParam(key, currentSearch?)     // خواندن یک پارامتر
writeSearch(patch)                 // history.replaceState (بدون آلوده‌کردن تاریخچه)
```

**ب) فایل جدید `frontend/src/utils/comparisonUrl.ts`** (اعتبارسنجی ورودی کاربر):
- `COMPARISON_TEST_TYPES = ['BACKTEST','FORWARD','REAL_PERSONAL','REAL_PROP']` (whitelist — جایگزین آرایهٔ تکراری داخل صفحه)
- `MAX_COMPARE_SELECT = 5`, `DEFAULT_COMPARISON_TEST_TYPE = 'BACKTEST'`
- `parseComparisonFilters(search)`: idهای معتبر (`>0`, صحیح) · حذف تکراری · **سقف ۵** · `test_type` فقط از whitelist · `symbol` trim و حداکثر ۲۰ کاراکتر · تاریخ‌ها فقط `YYYY-MM-DD`
- `buildComparisonPatch(filters)`: مقادیر پیش‌فرض/خالی حذف می‌شوند (URL تمیز؛ `test_type` پیش‌فرض `BACKTEST` نوشته نمی‌شود)
- `buildComparisonSearch(currentSearch, filters)`: خروجی نهایی (خالص، برای تست)

**ج) `ComparisonPage.tsx`:**
```diff
-const [selectedIds, setSelectedIds] = useState<number[]>([]);
-const [testType, setTestType] = useState<string>('BACKTEST');
+const initialFilters = useMemo(() => parseComparisonFilters(window.location.search), []);
+const [selectedIds, setSelectedIds] = useState<number[]>(initialFilters.versionIds);
+const [testType, setTestType] = useState<string>(initialFilters.testType ?? DEFAULT_COMPARISON_TEST_TYPE);
+const [symbol, setSymbol] = useState(initialFilters.symbol ?? '');
+const [dateFrom, setDateFrom] = useState(initialFilters.dateFrom ?? '');
+const [dateTo, setDateTo] = useState(initialFilters.dateTo ?? '');
```
```diff
+const updateUrl = () => writeSearch(buildComparisonPatch({ versionIds: selectedIds, testType, symbol, dateFrom, dateTo }));
+useEffect(() => {                       // sync خودکار با debounce ۵۰۰ms
+  const timer = setTimeout(updateUrl, URL_SYNC_DEBOUNCE_MS);
+  return () => clearTimeout(timer);
+}, [selectedIds, testType, symbol, dateFrom, dateTo]);
```
```diff
 const handleCompare = async () => {
   if (selectedIds.length < 2) { ... }
+  updateUrl();   // تثبیت فوری در URL قبل از فراخوانی API
   setLoading(true);
```

**د) `App.tsx` (گام 48c.2b — بدون این، refresh فیلترها را بی‌اثر می‌کرد):**
```diff
+function readPageFromUrl(): Page {           // اعتبارسنجی با PAGE_TITLES
+  const raw = new URLSearchParams(window.location.search).get('page');
+  return raw && PAGE_KEYS.includes(raw) ? raw as Page : 'dashboard';
+}
-const [page, setPage] = useState<Page>('dashboard');
+const [page, setPage] = useState<Page>(readPageFromUrl);
+useEffect(() => { writeSearch({ page: page === 'dashboard' ? null : page }); }, [page]);
```

**نتیجهٔ عملی:** لینک/refresh مثل `?page=comparison&versions=12,15&test_type=FORWARD&symbol=XAUUSD&date_from=2025-01-01`
همان صفحه و همان فیلترها را بازمی‌گرداند (نتیجهٔ مقایسه عمداً اجرا نمی‌شود؛ کاربر یک‌بار «مقایسه» می‌زند).
ℹ️ `URLSearchParams` کاما را `%2C` کد می‌کند (`versions=12%2C15`) که در parse دقیقاً معادل `,` است.

---

## ۴) تست‌ها

### ۴.۱ فایل جدید `frontend/src/__tests__/urlState.test.ts` (۱۵ تست)

| گروه | پوشش |
|---|---|
| `buildSearch` | افزودن کلید + حفظ کلیدهای دیگر · حذف با `null`/`undefined`/`''` · patch خالی = بدون تغییر |
| `readParam` | خواندن مقدار · `null` برای کلید ناموجود |
| `writeSearch` (jsdom) | آپدیت `window.location.search` · پاک‌کردن پارامتر با `null` |
| `parseComparisonFilters` | idهای نامعتبر/منفی/صفر/تکراری دور ریخته می‌شوند · **سقف ۵** · whitelist `test_type` (`HACK;DROP` ⇒ `null`) · اعتبارسنجی تاریخ · search خالی |
| `buildComparisonPatch/Search` | حذف پیش‌فرض‌ها · نوشتن نوع تست/نماد/تاریخ · حذف `versions` خالی · **round-trip** (build ⇒ parse) |

### ۴.۲ خروجی واقعی اجراها

```text
npx tsc -b --force                     → TSC_EXIT=0
npx vitest run                         → Test Files 4 passed (4) | Tests 29 passed (29) | VITEST_EXIT=0
npm run build                          → ✓ built in 3.47s | BUILD_EXIT=0
python -m pytest -q -p no:warnings     → PYTEST_EXIT=0 | 373 dots | 0 نشانگر F/E
ruff check .                           → ⚠️ قابل اجرا نبود (ruff در venv نصب نیست)
```

تفکیک تست‌های فرانت: `utils.test.ts` ۴ · `components.test.tsx` ۵ · `client.analysis.test.ts` ۵ · **`urlState.test.ts` ۱۵**

---

## ۵) فایل‌های تغییر یافته

| فایل | نوع | تغییر |
|---|---|---|
| `frontend/src/api/client.ts` | ویرایش | +`analyzePersonalAccount` · +`getAnalysisPersonalAccount` (۶ خط) |
| `frontend/src/pages/AnalysisPage.tsx` | ویرایش | تب `real_personal` · `testType` در `SCOPE_TABS` + `testTypeOfScope` · state `personalAccounts` + fetch · انتخاب خودکار · شاخه‌های تحلیل/معاملات/تحلیل مجدد · انتخابگر حساب · برچسب‌ها (+۸۷/−…) |
| `frontend/src/utils/urlState.ts` | **جدید** | ابزار query-string (History API؛ بدون react-router) |
| `frontend/src/utils/comparisonUrl.ts` | **جدید** | parse/build فیلترهای مقایسه + whitelist + سقف انتخاب |
| `frontend/src/pages/ComparisonPage.tsx` | ویرایش | init از URL · `updateUrl` · sync با debounce ۵۰۰ms · `test_type` از whitelist مشترک |
| `frontend/src/App.tsx` | ویرایش | `?page=` خواندن/نوشتن (گام 48c.2b) |
| `frontend/src/__tests__/urlState.test.ts` | **جدید** | ۱۵ تست |

✅ **بک‌اند: صفر تغییر** (هیچ فایل `backend/**` لمس نشد).

---

## ۶) وضعیت Git (⛔ بدون commit)

```text
$ git status --short
 M frontend/src/App.tsx
 M frontend/src/api/client.ts
 M frontend/src/pages/AnalysisPage.tsx
 M frontend/src/pages/ComparisonPage.tsx
?? PHASE48C_IMPL_REPORT.md
?? frontend/src/__tests__/urlState.test.ts
?? frontend/src/utils/comparisonUrl.ts
?? frontend/src/utils/urlState.ts

$ git diff --stat
 frontend/src/App.tsx                  | 21 ++++++++-
 frontend/src/api/client.ts            |  6 +++
 frontend/src/pages/AnalysisPage.tsx   | 87 ++++++++++++++++++++++++++++-------
 frontend/src/pages/ComparisonPage.tsx | 68 +++++++++++++++++++++++------
 4 files changed, 152 insertions(+), 30 deletions(-)

$ git log --oneline -3
937ab28 (HEAD -> main, origin/main, origin/HEAD) Phase 48b: Fix getAnalysis/getVersionAnalysis to send test_type + 5 tests
d70f2c1 Phase 50: README - setup/run/test/backup/troubleshooting (pnpm + auto-migration corrected)
723154f Phase 48a: Add implementation report
```

---

## ۷) یادداشت‌ها / کارهای باقی‌مانده

1. **نتیجهٔ مقایسه در URL نمی‌آید** (فقط فیلترها) ⇒ در refresh، کاربر باید یک‌بار «مقایسه» بزند. (اگر بخواهید، اجرای خودکار با `≥2` نسخه در URL کار ۵ دقیقه‌ای است.)
2. **`filterStrategy` و `searchQuery` (فیلترهای سمت کلاینت لیست نسخه‌ها) در URL ذخیره نشدند** — پلن هم آن‌ها را نخواسته بود.
3. **تب تحلیل همچنان در `localStorage` است** (`analysis_selected_scope`) نه در URL؛ می‌توان در فاز بعد به `?page=analysis&scope=real_personal` منتقل کرد.
4. **`analyzeVersion` / `getAnalysis` / `getVersionAnalysis`** در `client.ts` همچنان **صفر مصرف‌کننده** دارند (بدهی مستندشدهٔ 48b).
5. **`ruff` در venv نصب نیست** ⇒ برای اجرای lint بک‌اند باید `pip install ruff` شود (پیش‌نیاز پلن‌های بعدی).
6. **PDF تحلیل** فقط برای نسخه‌ها فعال است (اندپوینت بک‌اند `version_id`-محور) ⇒ برای حساب شخصی/پراپ نیاز به توسعهٔ اندپوینت export دارد.