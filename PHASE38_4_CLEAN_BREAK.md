# 🧨 PHASE 38.4 — Clean Break · REPORT

> **وضعیت:** ✅ کامل (بدون commit — منتظر تأیید)
> **تاریخ:** ۱۴۰۵/۰۷/۰۷
> **دامنه:** بک‌اند (۵ فایل اپ + ۶ فایل تست) · فرانت‌اند (۵ فایل) · **ریست DB**
> **خروجی تست‌ها:** `pytest` → **188 passed (EXIT 0)** · `tsc -b --force` → **EXIT 0** · `vitest run` → **9 passed (EXIT 0)**
> **پیش‌نیاز:** Phase 38.3 ✅ (همان worktree، commit نشده)

---

## ۱. خلاصهٔ اجرایی

پنج کارِ «Clean Break» که از فازهای ۲۷/۲۸/۳۷ به‌عنوان بدهی باقی مانده بود، یک‌جا بسته شد:

| # | کار | نتیجه |
|:--|:---|:---|
| ۱ | **حذف aliasها** (`Account = FinancialAccount`, `Transaction = FinancialTransaction`) | ✅ صفر مصرف‌کننده باقی ماند (۹ فایل به‌روز شد) |
| ۲ | **حذف تب «بروکر»** از `AnalysisPage` (تب + state + JSX + شاخه‌های داده) | ✅ تب به ۵ تب رسید (بک‌تست/فوروارد/۱/۲/۳) |
| ۳ | **حذف `analyzeBroker` / `getAnalysisBroker`** از `client.ts` | ✅ صفر مرجع باقی ماند |
| ۴ | **حذف `EXCHANGE`** از `TransactionType` و `CategoryType` | ✅ ۱۰ نقطهٔ مصرف → `TRANSFER`/`CONVERSION` |
| ۵ | **حذف فیلدهای منسوخ `client.ts`** | ✅ `broker_name`/`prop_firm_name`/`prop_firm_id` + `finance_account_id` در `getTrades` |
| ۶ | **ریست DB** | ✅ ۳۰ جدول خالی، `alembic stamp head` = `c9d0e1f2a3b4` |

**🐛 دو باگ خاموش (silent) در همین مسیر بسته شد:**
1. `AnalysisPage:116` — `getTrades({ finance_account_id })` که بک‌اند نادیده می‌گرفت ⇒ جدول معاملات تب بروکر **کل DB** را نشان می‌داد.
2. `analyzeBroker`/`getAnalysisBroker` به مسیرهای **ناموجود** بک‌اند می‌زدند ⇒ «تحلیل مجدد» در تب بروکر **همیشه ۴۰۴**.

✅ **هیچ commit ای زده نشد.** ✅ **بدون رگرسیون** (baseline: ۱۸۸ تست بک‌اند / ۹ تست فرانت).

---

## ۲. بخش ۱ — حذف aliasها

### ۲.۱ `backend/app/models/finance.py`
```diff
-# ═════════════════════════════════════════════
-# فاز ۳۷ — aliasهای سازگاری (Backward Compatibility)
-# ═════════════════════════════════════════════
-# نام‌های قدیمی همچنان کار می‌کنند تا importهای موجود نشکنند.
-# حذف تدریجی: پس از به‌روزرسانی همهٔ مصرف‌کننده‌ها در فازهای بعدی.
-Account = FinancialAccount
-Transaction = FinancialTransaction
```
دو docstring کلاس هم به‌روز شد (اشاره به «alias باقی می‌ماند» → «alias حذف شد»).

### ۲.۲ فهرست کامل مصرف‌کننده‌ها (قبل از تغییر) و اقدام
دستور کشف:
```powershell
Get-ChildItem -Recurse -Path app, tests, benchmarks -Filter *.py |
  Select-String -Pattern "from.*finance import.*\bAccount\b"
```
| فایل | خطوط | اقدام |
|:---|:---|:---|
| `app/models/finance.py` | 152-153 | ✅ **حذف alias** + docstring |
| `app/api/finance.py` | — | ✅ از قبل `FinancialAccount` بود |
| `app/api/broker.py` | 15 | ✅ از قبل `FinancialAccount` بود |
| `app/api/analytics.py` | 270, 369, 449, 555 | ✅ از قبل `FinancialAccount as ...` بود (فقط یک کامنت به‌روز شد) |
| `app/api/prop.py`, `trading.py`, `models/prop.py`, `models/trading.py` | — | ✅ فقط `Currency` (بی‌ربط) |
| `app/services/payout_service.py` | 25-30 | ✅ از قبل `FinancialAccount`/`FinancialTransaction` |
| `app/services/finance_sync_service.py` | 4, 13, 27 | ✅ **docstring/کامنت** به نام جدید به‌روز شد |
| `tests/test_finance.py` | 197 | ✅ `Account→FinancialAccount`, `Transaction→FinancialTransaction` |
| `tests/test_import_engine.py` | 15, 373, 376 | ✅ import + دو `query(Account)` |
| `tests/test_phase33_withdrawal.py` | 18, 69, 97, 142, 150, 165, 176, 187, 225, 247, 261 | ✅ ۱۲ نقطه (import + `Account(...)` + ۹× `query(Transaction)`) |
| `tests/test_phase36_performance.py` | 13 | ✅ `Account,`/`Transaction,` از import **حذف** شد (استفاده‌ای نداشتند) |
| `tests/test_phase37_finance_rename.py` | 11, 18, 27, 28 | ✅ **تست بازنویسی شد** (پایین‌تر) |
| `tests/test_soft_delete_filters.py` | 235 | ✅ docstring به‌روز شد |

> 🔧 جایگزینی با regex مرزبند (`(?<![A-Za-z_])Account(?![A-Za-z_])`) انجام شد تا
> `FinancialAccount` / `PropAccount` / `PersonalTradingAccount` / `AccountType` / `AccountCreate`
> هرگز اشتباهاً تغییر نکنند.

### ۲.۳ تست فاز ۳۷ بازنویسی شد (از «تأیید alias» به «تأیید حذف alias»)
```python
# بعد از فاز ۳۸.۴
def test_legacy_aliases_are_removed():
    """فاز ۳۸.۴: `Account`/`Transaction` دیگر در `models.finance` وجود ندارند."""
    assert not hasattr(finance_module, "Account")
    assert not hasattr(finance_module, "Transaction")
    assert finance_module.FinancialAccount is FinancialAccount
    assert finance_module.FinancialTransaction is FinancialTransaction
```
> 🛡️ این تست اکنون **رگرسیون‌گیر** است: اگر کسی alias را برگرداند، تست شکست می‌خورد.

### ۲.۴ تأیید نهایی
اسکن پس از تغییر (`app`, `tests`, `benchmarks`) ⇒ **صفر** ارجاع کد به `Account`/`Transaction` تنها؛
تنها اشاره‌های باقی‌مانده «متن تاریخی» هستند:
`models/finance.py:63,118` (docstring «از Account به FinancialAccount تغییر نام یافت») و
`models/trading.py:42` (عبارت انگلیسی `Personal Trading Account`).
---

## ۳. بخش ۲ — حذف تب «بروکر» از `AnalysisPage.tsx`

### ۳.۱ `type ScopeType` و آرایهٔ تب‌ها
```diff
-type ScopeType = 'backtest' | 'forward' | 'prop_stage_1' | 'prop_stage_2' | 'prop_stage_3' | 'broker';
+// فاز ۳۸.۴ (Clean Break) — تب «بروکر» حذف شد: حساب مالیِ نوع «بروکر» وجود ندارد
+// (حساب‌های معاملاتی → `PersonalTradingAccount` در بک‌اند) و endpointهای تحلیل بروکر هم نیستند.
+type ScopeType = 'backtest' | 'forward' | 'prop_stage_1' | 'prop_stage_2' | 'prop_stage_3';
  const SCOPE_TABS = [ ... ۵ تب ... ];
-  { key: 'broker', icon: '🏦', label: 'بروکر' },
-];
```

### ۳.۲ حذف state و interface
```diff
-interface BrokerOption { id: number; name: string; type: string; }
...
-  // فاز ۳۸.۳ — query مردهٔ `getFinanceAccounts({ type: 'broker' })` حذف شد.
-  // دلیل: `AccountType.BROKER` در فاز ۳۸.۲ حذف شد ⇒ backend با ۴۲۲ پاسخ می‌داد.
-  const brokerAccounts: BrokerOption[] = [];
```
✅ در نتیجه، **هیچ اثری از فاز ۳۸.۳ باقی نماند** (تمام تایپ/آرایه/کامنت حذف شد).

### ۳.۳ 🛡️ گارد `localStorage` (نکتهٔ مهمی که در بریف نبود)
مقدار `analysis_selected_scope` در مرورگر ممکن است `"broker"` باشد ⇒ بعد از حذف تب،
`scope` مقدار **نامعتبر** می‌گرفت و شرط‌های `startsWith('prop_stage_')` می‌شکست.
برای همین اعتبارسنجی اضافه شد:
```tsx
const VALID_SCOPES: ScopeType[] = SCOPE_TABS.map((t) => t.key);

/** مقدار ذخیره‌شده در localStorage را اعتبارسنجی می‌کند (scopeهای حذف‌شده مثل 'broker') */
function readStoredScope(): ScopeType {
  if (typeof window === 'undefined') return 'backtest';
  try {
    const stored = JSON.parse(localStorage.getItem(SCOPE_KEY) || '"backtest"') as ScopeType;
    return VALID_SCOPES.includes(stored) ? stored : 'backtest';
  } catch {
    return 'backtest';
  }
}
...
const [scope, setScope] = useState<ScopeType>(readStoredScope);
```
⇒ کاربری که قبلاً «بروکر» را انتخاب کرده بود، به‌جای صفحهٔ خراب، به «بک‌تست» برمی‌گردد.

### ۳.۴ شاخه‌های داده (تحلیل + معاملات)
```diff
-          const res = isVersion
-            ? await getAnalysisVersion(selectedId, testType)
-            : scope.startsWith('prop_stage_')
-              ? await getAnalysisProp(selectedId)
-              : await getAnalysisBroker(selectedId);      // ← endpoint ناموجود (۴۰۴)
+          // فاز ۳۸.۴: تب «بروکر» حذف شد ⇒ فقط نسخه (backtest/forward) و مرحله پراپ
+          const res = isVersion
+            ? await getAnalysisVersion(selectedId, testType)
+            : await getAnalysisProp(selectedId);
```
```diff
-          const tradesRes = isVersionScope
-            ? await getTrades({ version_id: selectedId, test_type: tt, limit: 500 })
-            : scope.startsWith('prop_stage_')
-              ? await getTrades({ prop_stage_id: selectedId, limit: 500 })
-              : await getTrades({ finance_account_id: selectedId, limit: 500 });  // ← پارامتر ناموجود
+          const tradesRes = isVersionScope
+            ? await getTrades({ version_id: selectedId, test_type: tt, limit: 500 })
+            : await getTrades({ prop_stage_id: selectedId, limit: 500 });
```
✅ **باگ خاموش دادهٔ خط ۱۱۶ خودبه‌خود حذف شد** (چون کل شاخهٔ `else` حذف شد).

### ۳.۵ `handleReanalyze`
```diff
-      } else if (scope.startsWith('prop_stage_')) {
-        await analyzePropStage(selectedId);
-        const res = await getAnalysisProp(selectedId);
-        setAnalysis(res.data);
-      } else {
-        await analyzeBroker(selectedId);
-        const res = await getAnalysisBroker(selectedId);
-        setAnalysis(res.data);
-      }
+      } else {
+        // فاز ۳۸.۴: تب «بروکر» حذف شد ⇒ باقی موارد مرحله پراپ است
+        await analyzePropStage(selectedId);
+        const res = await getAnalysisProp(selectedId);
+        setAnalysis(res.data);
+      }
```
### ۳.۶ JSX انتخابگر
```diff
-              {scope === 'broker' ? 'انتخاب حساب بروکر' :
-               scope.startsWith('prop_stage_') ? 'انتخاب مرحله پراپ' : 'انتخاب نسخه'}
+              {scope.startsWith('prop_stage_') ? 'انتخاب مرحله پراپ' : 'انتخاب نسخه'}
             </label>
-            {scope === 'broker' ? (
-              <select ...>
-                <option value="">— حساب بروکری وجود ندارد —</option>
-                {brokerAccounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
-              </select>
-            ) : scope.startsWith('prop_stage_') ? (
+            {scope.startsWith('prop_stage_') ? (
```

### ۳.۷ importها
```diff
   analyzeVersionScoped,
   analyzePropStage,
-  analyzeBroker,
   getAnalysisVersion,
   getAnalysisProp,
-  getAnalysisBroker,
   getAllPropStages,
```
> ⚠️ `getTrades` همچنان مصرف می‌شود (تب نسخه/پراپ) ⇒ import آن حفظ شد.

---

## ۴. بخش ۳ — حذف از `client.ts`
```diff
 export const analyzePropStage = (propStageId: number) =>
   api.post(`/api/analytics/analyze/prop/${propStageId}`);
-export const analyzeBroker = (financeAccountId: number) =>
-  api.post(`/api/analytics/analyze/broker/${financeAccountId}`);
 export const getAnalysisVersion = ...
 export const getAnalysisProp = (propStageId: number) =>
   api.get(`/api/analytics/analysis/prop/${propStageId}`);
-export const getAnalysisBroker = (financeAccountId: number) =>
-  api.get(`/api/analytics/analysis/broker/${financeAccountId}`);
+// فاز ۳۸.۴ (Clean Break): `analyzeBroker`/`getAnalysisBroker` حذف شدند
+// (مسیرهای `/analyze|analysis/broker/{id}` در بک‌اند وجود ندارند؛ معادل آن‌ها
+//  `/analyze|analysis/personal-account/{personal_trading_account_id}` است).
```
**شاهد از بک‌اند** (`app/api/analytics.py` — فهرست واقعی مسیرها):
```text
POST /analyze/{version_id}   POST /analyze/version/{id}   POST /analyze/prop/{id}
POST /analyze/personal-account/{id}
GET  /analysis/version/{id}  GET  /analysis/prop/{id}      GET  /analysis/personal-account/{id}
```
⇒ هیچ مسیر `broker` وجود ندارد ⇒ حذف این دو تابع = **حذف کد مرده**، نه حذف قابلیت.
---

## ۵. بخش ۴ — حذف `EXCHANGE` از Enumها

### ۵.۱ ⚠️ نکتهٔ حیاتی: دو `EXCHANGE` متفاوت وجود داشت
| Enum | مقدار | سرنوشت |
|:---|:---|:---|
| `AccountType.EXCHANGE` (`"exchange"` = «صرافی») | نوع **حساب مالی** | ✅ **دست‌نخورده ماند** (صرافی یک حساب مالی معتبر است) |
| `TransactionType.EXCHANGE` | نوع **تراکنش** | ❌ **حذف شد** |
| `CategoryType.EXCHANGE` | نوع **دسته‌بندی** | ❌ **حذف شد** |

### ۵.۲ کشف قبل از حذف (طبق بریف)
```powershell
Get-ChildItem -Recurse -Path app, tests -Filter *.py | Select-String -Pattern "EXCHANGE"
```
نتیجهٔ اولیه (PowerShell بدون `-CaseSensitive`) خالی برگشت؛ با اسکن دقیق Python
(`(?<![A-Za-z_])EXCHANGE(?![A-Za-z_])`) **۱۰ نقطهٔ مصرف در ۵ فایل** پیدا شد:

| فایل:خط | کد قبل | اقدام |
|:---|:---|:---|
| `models/finance.py:41` | `CategoryType.EXCHANGE = "exchange"` | ✅ **حذف** |
| `models/finance.py:48` | `TransactionType.EXCHANGE = "exchange"` | ✅ **حذف** |
| `app/api/finance.py:387` | `total_transfers` ← `type == TransactionType.EXCHANGE` | ✅ → `TRANSFER` |
| `app/api/finance.py:1256` | `flow_types = [... DEPOSIT, WITHDRAWAL, EXCHANGE]` | ✅ → `TRANSFER` |
| `app/api/finance.py:1348` | `exchanges = _total([TransactionType.EXCHANGE])` | ✅ → `TRANSFER` |
| `app/api/finance.py:1484` | `exchange-rates` ← `type == TransactionType.EXCHANGE` | ✅ → `TRANSFER` |
| `app/api/finance.py:1527` | seed: `{"تبدیل ارز", CategoryType.EXCHANGE}` | ✅ → `CONVERSION` |
| `app/services/payout_service.py:250` | `type=TransactionType.EXCHANGE` (انتقال پراپ) | ✅ → `TRANSFER` |
| `tests/test_phase33_withdrawal.py:226` | `Transaction.type == TransactionType.EXCHANGE` | ✅ → `TRANSFER` |
| `tests/test_phase37_finance_rename.py:50,59` | assertion «exchange در Enumها هست» | ✅ → assertion «**نیست**» |

> 📌 **چرا `TRANSFER` و نه `CONVERSION`؟** در `TransactionType` مقدار `CONVERSION` **وجود ندارد**
> (فقط در `CategoryType`). کامنت خودِ `payout_service` می‌گفت «نوع `EXCHANGE` ⇒ به‌عنوان **انتقال**
> شمرده می‌شود، نه درآمد» ⇒ جانشین طبیعی `TRANSFER` بود. برای `CategoryType` (که `CONVERSION` دارد)
> طبق بریف دقیقاً `CONVERSION` گذاشته شد.

### ۵.۳ حفظ سازگاری JSON API
| کلید JSON | وضعیت |
|:---|:---|
| `finance/summary.total_transfers` | ✅ نام و معنایش حفظ شد (الان روی `TRANSFER` حساب می‌شود) |
| `finance/money-cycle.total_exchanges` | ✅ **نام کلید حفظ شد** (فرانت مصرف می‌کند)؛ مقدارش از `TRANSFER` می‌آید + کامنت توضیحی |
| `finance/money-cycle.total_transfers` | ✅ بدون تغییر (فیلتر `from_account_id`/`to_account_id` غیرتهی) |
| `finance/exchange-rates` | ✅ نام endpoint و keyها بدون تغییر |

**اثبات بدون‌رگرسیون بودن تست `test_money_cycle`:**
```python
# قبل: tx3 type=exchange(3000), tx4 type=exchange(4000, from/to)
# بعد:  tx3 type=transfer(3000), tx4 type=transfer(4000, from/to)
assert body["total_exchanges"] == 7000   # ← _total([TRANSFER]) = 3000+4000 ✅
assert body["total_transfers"] == 4000   # ← فیلتر from/to = 4000 ✅
```

### ۵.۴ فرانت‌اند — `exchange` به‌عنوان نوع **تراکنش/دسته** (نه حساب)
بدون این تغییر، ارسال `"exchange"` از UI باعث **۴۲۲** می‌شد.
| فایل:خط | قبل | بعد |
|:---|:---|:---|
| `components/TransactionForm.tsx:35` | `{ value: 'exchange', label: '🔄 تبدیل' }` | `{ value: 'transfer', label: '🔄 انتقال/تبدیل' }` |
| `components/TransactionForm.tsx:70` | `type === 'exchange' \|\| type === 'transfer'` | `type === 'transfer'` |
| `components/TransactionForm.tsx:196` | کامنت `exchange/transfer` | کامنت به‌روز شد |
| `components/CategoryForm.tsx:21` | `{ value: 'exchange', label: '💱 تبدیل' }` | `{ value: 'conversion', label: '💱 تبدیل' }` |
| `pages/FinancePage.tsx:496` | `<option value="exchange">🔄 تبدیل</option>` | `<option value="transfer">🔄 انتقال/تبدیل</option>` |
| `pages/FinancePage.tsx:89` | `exchange:` در `TRANSACTION_TYPE_STYLES` | `transfer:` |
| `pages/FinancePage.tsx:98` | `exchange: 'تبدیل'` | `transfer: 'انتقال/تبدیل'` |
| `pages/FinancePage.tsx:103` | `exchange: '#8b5cf6'` | `transfer: '#8b5cf6'` |

✅ **دست‌نخورده (درست بود):** `AccountForm.tsx:21`, `DashboardPage.tsx:643`, `FinancePage.tsx:76,81,1134`
— همه `['exchange', '🔄 صرافی']` برای **نوع حساب** هستند.

### ۵.۵ تأیید نهایی
پس از تغییر، `EXCHANGE` در `app`/`tests`/`benchmarks` فقط در این موارد دیده می‌شود:
`AccountType.EXCHANGE` (صرافی — درست) و کامنت‌های توضیحی «EXCHANGE حذف شد».
---

## ۶. (تکمیلی از بریف قبلی) — حذف فیلدهای منسوخ `client.ts`

### ۶.۱ `createFinanceAccount` — سه فیلد بی‌اثر (تکمیل فاز ۳۸.۳)
```diff
 export const createFinanceAccount = (data: {
   name: string;
   type: string;
   currency?: string;
   balance?: number;
   card_number?: string;
-  broker_name?: string;
-  prop_firm_name?: string;
-  prop_firm_id?: number | null;
 }) => api.post('/api/finance/accounts', data);
```
✅ حالا تایپ دقیقاً = `AccountCreate` بک‌اند: `{ name, type, currency, balance, card_number }`.

### ۶.۲ `getTrades` — `finance_account_id` → `personal_trading_account_id`
```diff
 export const getTrades = (params?: {
   version_id?: number;
   prop_stage_id?: number;
-  finance_account_id?: number;
+  personal_trading_account_id?: number;  // فاز ۳۸.۴: جایگزین منسوخ `finance_account_id`
```
✅ **امن بود:** تنها مصرف‌کنندهٔ قبلی همان شاخهٔ «بروکر» در `AnalysisPage` بود که حذف شد؛
فیلد جدید با `backend/app/api/trades.py:213` مطابقت دارد.

### ۶.۳ ⚠️ `createManualTrade.finance_account_id` — **عمداً دست‌نخورده ماند**
```ts
  // ⚠️ فاز ۳۸.۴ — این فیلد در بک‌اند وجود ندارد (نام درست: `personal_trading_account_id`).
  // عمداً دست‌نخورده ماند تا `TradesPage` نشکند؛ مهاجرت کامل آن به یک فاز جدا نیاز دارد.
  finance_account_id?: number;
```
**دلیل (تصمیم آگاهانه):** تنها مصرف‌کنندهٔ این فیلد، مودال «معامله دستی» در `TradesPage` است
(`lines 82, 314, 331, 346, 367, 987-988`). دو گزینه وجود داشت:
- ❌ **تغییر نام صرف در `client.ts`** ⇒ خطای TS در `TradesPage` می‌داد (excess property).
- ❌ **تغییر نام در `TradesPage` بدون تغییر منبع داده** ⇒ بدتر می‌شد: dropdown از
  `getFinanceAccounts()` پر می‌شود، یعنی **ID حساب مالی** به فیلد `personal_trading_account_id`
  فرستاده می‌شد ⇒ **آلودگی داده** (به‌جای no-op فعلی).
- ✅ **رها کردن به‌عنوان بدهی مستند** + کامنت هشدار در کد (انتخاب شد) — چون اصلاح واقعی نیازمند
  افزودن `getPersonalTradingAccounts` به `client.ts` (که امروز **وجود ندارد**) و بازنویسی آن مودال است.

> 🔎 برای ثبت: این هم یک **باگ خاموش** است — انتخاب «حساب مالی» در ثبت معاملهٔ دستی امروز
> هیچ اثری ندارد (بک‌اند فیلد را نادیده می‌گیرد) و کلاسیفیکیشن معاملهٔ REAL
> به حساب معاملاتی شخصی **کار نمی‌کند**.

---

## ۷. بخش ۶+۷ — تست‌ها

### ۷.۱ Baseline (قبل از تغییرات این زیرفاز)
```text
venv\Scripts\python.exe -m pytest -q -p no:warnings  →  188 passed  (PYTEST_EXIT=0)
npx tsc -b --force                                   →  TSC_EXIT=0
npx vitest run                                       →  9 passed   (VITEST_EXIT=0)
```

### ۷.۲ بک‌اند (بعد از تغییرات + ریست DB)
```text
cd backend
venv\Scripts\python.exe -m pytest -q -p no:warnings
........................................................................ [ 38%]
........................................................................ [ 76%]
............................................                             [100%]
PYTEST_EXIT=0        →  188 passed
```
✅ **۱۸۸ = ۱۸۸** ⇒ صفر رگرسیون، صفر تست حذف‌شده
(دو تست فاز ۳۷ فقط **بازنویسی** شدند، نه حذف: `test_aliases_are_identical` → `test_legacy_aliases_are_removed`).

### ۷.۳ فرانت‌اند
```text
cd frontend
npx tsc -b --force   →  TSC_EXIT=0   (بدون هیچ خطا)
npx vitest run       →  VITEST_EXIT=0
  ✓ src/__tests__/utils.test.ts (4 tests)
  ✓ src/__tests__/components.test.tsx (5 tests)
  Test Files  2 passed (2)      Tests  9 passed (9)
```
---

## ۸. بخش ۵ (DB) — ریست دیتابیس

### ۸.۱ مراحل اجراشده
```powershell
cd backend
Copy-Item trading_desk.db trading_desk.db.bak_before_cleanbreak   # بکاپ امن
Remove-Item trading_desk.db                                       # حذف
venv\Scripts\python.exe -c "from app.core.database import Base, engine; import app.models...; Base.metadata.create_all(bind=engine)"
venv\Scripts\python.exe -m alembic stamp head
venv\Scripts\python.exe -m alembic current
```
> ⚠️ در تلاش اول، دستورات PowerShell (`Copy-Item`/`Remove-Item`) داخل `cmd /c` اجرا شدند و
> **نامعتبر** بودند ⇒ DB حذف **نشد**. با اجرای درست PowerShell تکرار شد:
> `deleted: True` ✅

### ۸.۲ وضعیت DB پس از ریست
```text
alembic current ................................ c9d0e1f2a3b4 (head)   ✅
tables ......................................... 30                    ✅
row count در همهٔ جدول‌ها ....................... 0                     ✅ (DB تمیز)
SIZE ........................................... 409,600 bytes
```
**۳۰ جدول:** `accounts, alembic_version, analysis_results, analysis_runs, analysis_scopes,
brokers, categories, custom_time_intervals, import_batch_rows, import_batches, import_identities,
import_profiles, journal_reviews, personal_trading_accounts, prop_accounts, prop_alerts, prop_costs,
prop_firm_default_rules, prop_firms, prop_stages, prop_withdrawals, rule_violations, screenshots,
strategies, strategy_versions, symbol_mappings, time_points, trades, transactions, user_settings`

### ۸.۳ اعتبارسنجی اسکیمای جدید (مقایسه با DB قبلی)
برای اطمینان از اینکه `create_all` + `stamp` چیزی را از دست نداده، اسکیمای DB جدید با
**بکاپ DB قبلی** (که با زنجیرهٔ migrationها ساخته شده بود) مقایسه شد:
```text
TABLES  old=30  new=30     only in OLD: []       only in NEW: []     ✅
INDEXES old=59  new=59     only in OLD: []       only in NEW: []     ✅
COLUMN DIFFS .....................................  هیچ ستونی تفاوت ندارد  ✅
```
✅ **صفر drift.** اسکیمای جدید **دقیقاً** منطبق با اسکیمای migration-ساخته است
(شامل ۷ ستون `accounts`: `id, name, type, currency, balance, card_number, created_at` —
یعنی `broker_name`/`prop_firm_name`/`prop_firm_id` که فاز ۲۸ حذفشان کرد، در هیچ‌کدام نیست).

### ۸.۴ 🐛 باگ کشف‌شدهٔ مهم: زنجیرهٔ migration روی DB خالی **بالا نمی‌آید**
در جریان اعتبارسنجی، `alembic upgrade head` روی یک DB **خالی و تازه** اجرا شد و شکست خورد:
```text
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError)
index ix_trades_is_deleted already exists
[SQL: CREATE INDEX ix_trades_is_deleted ON trades (is_deleted)]
```
**تشخیص:** migration فاز ۲۵ (`f1a2b3c4d5e6_add_is_deleted_to_trades`) ایندکس
`ix_trades_is_deleted` را می‌سازد و migration فاز ۳۶ (`…_performance_indexes`) دوباره
همان ایندکس را روی DB خالی می‌سازد ⇒ **تضاد**.
این باگ **از قبل وجود داشت** (فاز ۳۶ یا قبل‌تر) و فقط روی **DB تازه** ظاهر می‌شود؛ روی DB
موجود به‌دلیل ترتیب اجرا مشکلی نمی‌سازد.
⇒ همین موضوع دلیلِ نیاز به `create_all` + `stamp head` است (روش بریف) و
**در گزارش ثبت شد** (پایین‌تر، بدهی ۱).
> ✅ خوشبختانه `app/main.py` در startup هم `alembic upgrade head` می‌زند؛ چون DB ما
> **stamp شده روی head** است، این فراخوانی no-op می‌شود و اپ بدون خطا بالا می‌آید.
---

## ۹. لیست فایل‌های تغییر یافته (۱۷ فایل + ۲ گزارش)

```text
 backend/app/api/analytics.py                 |  2 +-
 backend/app/api/finance.py                   | 13 +++---
 backend/app/models/finance.py                | 26 +++++-------
 backend/app/services/finance_sync_service.py |  6 ++--
 backend/app/services/payout_service.py       |  8 ++--
 backend/tests/test_finance.py                | 12 +++---
 backend/tests/test_import_engine.py          |  6 ++--
 backend/tests/test_phase33_withdrawal.py     | 24 +++++------
 backend/tests/test_phase36_performance.py    |  2 +-
 backend/tests/test_phase37_finance_rename.py | 26 +++++++-----
 backend/tests/test_soft_delete_filters.py    |  2 +-
 frontend/src/api/client.ts                   | 14 +++----
 frontend/src/components/AccountForm.tsx      | 39 +----------------
 frontend/src/components/CategoryForm.tsx     |  2 +-
 frontend/src/components/TransactionForm.tsx  |  6 ++--
 frontend/src/pages/AnalysisPage.tsx          | 62 ++++++++++++++----------------
 frontend/src/pages/FinancePage.tsx           |  8 ++--
 17 files changed, 107 insertions(+), 151 deletions(-)
```
> `AccountForm.tsx` (۳۹ خط) بخشی از **فاز ۳۸.۳** است که هنوز commit نشده ⇒ در همین diff دیده می‌شود.

**فایل‌های جدید (بدون commit):**
```text
?? PHASE38_3_FIX_REMAINING.md
?? PHASE38_4_CLEAN_BREAK.md
```
**DB (در git نیست — `.gitignore`):**
```text
   trading_desk.db                        (جدید، ۳۰ جدول خالی)
   trading_desk.db.bak_before_cleanbreak  (بکاپ قبل از ریست)
```

### دسته‌بندی بر اساس کار
| بخش | فایل‌ها |
|:---|:---|
| ۱. aliasها | `models/finance.py`, `services/finance_sync_service.py`, ۶ فایل تست |
| ۲. تب بروکر | `pages/AnalysisPage.tsx` |
| ۳. توابع بروکر | `api/client.ts` |
| ۴. EXCHANGE | `models/finance.py`, `api/finance.py`, `services/payout_service.py`, `api/analytics.py` (کامنت), `TransactionForm.tsx`, `CategoryForm.tsx`, `FinancePage.tsx`, ۲ فایل تست |
| ۵. فیلدهای منسوخ | `api/client.ts` |
| ۶. ریست DB | `trading_desk.db` (بیرون از git) |

---

## ۱۰. بدهی‌های باقی‌مانده و یافته‌ها

| # | بدهی / یافته | شدت | جزئیات و راه‌حل پیشنهادی |
|:--|:---|:--|:---|
| ۱ | **زنجیرهٔ migration روی DB خالی شکست می‌خورد** | 🔴 بالا | `ix_trades_is_deleted` دوبار ساخته می‌شود (فاز ۲۵ + فاز ۳۶) ⇒ `alembic upgrade head` روی DB خالی خطا. راه‌حل: در migration فاز ۳۶ قبل از ساخت ایندکس، وجودش چک شود (یا `IF NOT EXISTS`). الان با `create_all`+`stamp` دور زده می‌شود. |
| ۲ | **`TradesPage` — ثبت معاملهٔ دستی: «حساب مالی» بی‌اثر** | 🔴 بالا | `finance_account_id` در payload (`TradesPage:367`) در بک‌اند وجود ندارد و نادیده گرفته می‌شود. معنایش: کلاسیفیکیشن REAL-personal کار نمی‌کند + dropdown از منبع اشتباه (`getFinanceAccounts`) پر می‌شود + `a.broker_name` نمایش داده می‌شود (فیلد حذف‌شده). راه‌حل: افزودن `getPersonalTradingAccounts` به `client.ts` + تغییر منبع dropdown + تغییر نام فیلد به `personal_trading_account_id`. |
| ۳ | **`analytics.py:395-404` — `classify()`** | 🟡 متوسط | معاملاتِ `personal_trading_account_id` را هنوز `"broker"` برچسب می‌زند و کلید `"broker"` در `by_source` هست. چون **کلید خروجی JSON** است، تغییرش نیازمند بررسی مصرف‌کننده‌ها (داشبورد) در یک فاز جدا. |
| ۴ | **`PropPage.tsx:300` — `res.data?.finance_account_id`** | 🟡 متوسط | خواندن فیلدی که `PropAccount` از فاز ۲۸ ندارد ⇒ همیشه falsy. کد مرده. |
| ۵ | **برچسب‌های `broker`/`prop` در `FinancePage.tsx:76,81`** | 🟢 کم | `ACCOUNT_TYPE_LABELS`/`ACCOUNT_TYPE_NAMES` برای `AccountType`هایی که وجود ندارند (فقط نمایشی). |
| ۶ | **تایپ `Account` در `FinancePage.tsx:55-59`** | 🟢 کم | هنوز `broker_name?`/`prop_firm_name?`/`prop_firm_id?` دارد (بی‌مصرف بعد از فاز ۳۸.۳). |
| ۷ | **تب جدید «حساب معاملاتی شخصی» در تحلیل** | 🟢 کم | بک‌اند مسیرهای `/analyze|analysis/personal-account/{id}` را **دارد** ولی فرانت وصل نشده. اگر خواستید، جایگزین تب بروکر همین است (نه `finance_account_id`). |
| ۸ | **`services/finance_sync_service.py`** | 🟢 کم | هنوز no-op است (از فاز ۲۸) — نیازمند تصمیم طراحی مستقل. |
| ۹ | **کامنت منسوخ در `models/finance.py:63,118`** | ⚪ ناچیز | «کلاس از `Account` به `FinancialAccount` تغییر نام یافت» — متن **تاریخی** است و عمداً حفظ شد. |
---

## ۱۱. ✅ تأیید نهایی زیرفاز ۳۸.۴

| بررسی | نتیجه |
|:---|:---|
| alias `Account`/`Transaction` در `models.finance` | ✅ حذف شد (`not hasattr` تست شد) |
| ارجاع کد به alias در `app`/`tests`/`benchmarks` | ✅ **صفر** |
| تب «بروکر» در `AnalysisPage` (تب/state/JSX/داده) | ✅ **صفر** اثر باقی‌مانده |
| گارد `localStorage` برای scope حذف‌شده `'broker'` | ✅ افزوده شد |
| `analyzeBroker`/`getAnalysisBroker` در `client.ts` | ✅ حذف شد |
| `getTrades({ finance_account_id })` (باگ خاموش) | ✅ با حذف تب از بین رفت |
| `TransactionType.EXCHANGE` / `CategoryType.EXCHANGE` | ✅ حذف شد |
| نقاط مصرف EXCHANGE (۱۰ مورد) | ✅ همه به `TRANSFER`/`CONVERSION` منتقل شد |
| `AccountType.EXCHANGE` (صرافی) | ✅ **دست‌نخورده** (نباید حذف می‌شد) |
| فیلدهای منسوخ `createFinanceAccount` | ✅ حذف شد |
| `client.ts` ↔ `AccountCreate` بک‌اند | ✅ **MATCH کامل** |
| `client.ts` ↔ `get_trades` بک‌اند | ✅ `personal_trading_account_id` منطبق |
| `pytest` | ✅ **188 passed · EXIT 0** (baseline هم ۱۸۸) |
| `tsc -b --force` | ✅ **EXIT 0** |
| `vitest run` | ✅ **9 passed · EXIT 0** |
| ریست DB | ✅ ۳۰ جدول، صفر ردیف، stamped = `c9d0e1f2a3b4 (head)` |
| drift اسکیمای جدید vs قدیم | ✅ صفر تفاوت (جدول/ایندکس/ستون) |
| commit | ✅ **زده نشد** |

### خلاصهٔ یک‌خطی
> فاز ۳۸.۴ چهار بدهی «Clean Break» (aliasها، تب بروکر، EXCHANGE، فیلدهای منسوخ) را بست،
> **۲ باگ خاموش** را حذف کرد، DB را از صفر ساخت (بدون drift)، و ۱۸۸+۹ تست سبز ماند —
> **بدون هیچ commit**.

### 🔜 پیشنهاد گام بعدی (به‌ترتیب اولویت)
1. **رفع باگ migration** (بدهی ۱) — کوچک و مهم برای هر DB تازه.
2. **مهاجرت `TradesPage` به `personal_trading_account_id`** (بدهی ۲) + افزودن API حساب‌های معاملاتی شخصی.
3. **افزودن تب «حساب معاملاتی شخصی» به `AnalysisPage`** (بدهی ۷) به‌عنوان جانشین واقعی تب بروکر.
4. سپس **commit** فازهای ۳۸.۳ + ۳۸.۴.

⏸️ **پایان زیرفاز ۳۸.۴ — منتظر تأیید کاربر برای commit.**