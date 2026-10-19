# 🧹 PHASE 38.3 — Fix Remaining Issues · REPORT

> **وضعیت:** ✅ کامل (بدون commit — منتظر تأیید)
> **تاریخ:** ۱۴۰۵/۰۷/۰۷
> **دامنه:** فقط فرانت‌اند (۲ فایل) — **بدون تغییر بک‌اند**
> **خروجی:** `tsc -b --force` → **EXIT 0** · `vitest run` → **9 passed (EXIT 0)**
> **پایهٔ کار:** `HEAD = d55803` (Phase 38.2) — worktree در شروع **تمیز** بود؛
> کار دفتر دور ریخته شد و همین‌جا از صفر انجام شد.

---

## ۱. خلاصهٔ اجرایی

دو بدهی فنی که در گزارش `PHASE38_2_FRONTEND_DROPDOWN.md` (بخش ۷ — «یادداشت‌های باقی‌مانده»)
ثبت شده بود، تسویه شد:

| # | مورد | اقدام | نتیجه |
|:--|:---|:---|:---|
| ۱ | `AnalysisPage.tsx:71` — query مردهٔ `getFinanceAccounts({ type: 'broker' })` | حذف کامل query + import + state | ✅ هر بار لود صفحه دیگر `console.error` و درخواست ۴۲۲ ندارد |
| ۲ | `AccountForm.tsx` — ۳ فیلد بی‌اثر (`broker_name`, `prop_firm_name`, `prop_firm_id`) | حذف از Props + state + useEffect + submit + reset + JSX | ✅ فرم دیگر دادهٔ دورریز نمی‌فرستد |

✅ **هیچ تغییری در بک‌اند، DB، یا `client.ts` انجام نشد.**
✅ **هیچ commit ای زده نشد.**

---

## ۲. گام ۱ — گزارش کد (قبل از تغییر)

### ۲.۱ `frontend/src/pages/AnalysisPage.tsx`

**خط ۷۱ — کد کامل:**
```tsx
getFinanceAccounts({ type: 'broker' })
  .then((res) => setBrokerAccounts(res.data))
  .catch((err) => console.error('خطا در دریافت حساب‌های بروکر:', err));
```

**همهٔ نقاط مصرف `getFinanceAccounts` / `brokerAccounts` در این فایل:**

| خط | نقش |
|:--|:---|
| ۱۶ | `getFinanceAccounts` در import از `../api/client` |
| ۵۵ | `const [brokerAccounts, setBrokerAccounts] = useState<BrokerOption[]>([])` |
| ۷۱-۷۳ | خودِ query + `.then(setBrokerAccounts)` + `.catch` |
| ۱۹۸ | مصرف در JSX (فقط داخل شاخهٔ `scope === 'broker'`): `{brokerAccounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}` |

**آیا جای دیگری از `type: 'broker'` استفاده شده؟**
❌ خیر. در کل کدبیس (۲۲۸ فایل) تنها همین یک نقطهٔ کد است؛ بقیهٔ موارد فقط در
اسناد `.md` (`PHASE26_DOMAIN_ARCHITECTURE.md`, `PHASE38_2_FRONTEND_DROPDOWN.md`) هستند.

**آیا `getFinanceAccounts` کلاً مرده است؟** ❌ خیر — سه مصرف سالم دیگر دارد و **دست‌نخورده** ماندند:
- `DashboardPage.tsx:247` → `getFinanceAccounts()` (بدون فیلتر)
- `FinancePage.tsx:203` / `FinancePage.tsx:240` → `getFinanceAccounts()` (بدون فیلتر)

⇒ فقط **call با فیلتر `broker`** مرده بود، نه خودِ تابع.

**زمینه — این query چه می‌خواست بکند؟**
تب «🏦 بروکر» (فاز ۲۰، `scope = 'broker'`) برای تحلیل یک **حساب مالیِ نوع بروکر** ساخته شده بود:
1. `getFinanceAccounts({ type: 'broker' })` لیست حساب‌های بروکر را برای dropdown می‌گرفت؛
2. انتخاب کاربر → `selectedId`؛
3. `getAnalysisBroker(id)` / `analyzeBroker(id)` → `GET/POST /api/analytics/analysis|analyze/broker/{finance_account_id}`؛
4. `getTrades({ finance_account_id: selectedId })` → لیست معاملات.

این طراحی از دورانی می‌آید که `AccountType.BROKER` وجود داشت. **فاز ۲۷/۲۸ حساب‌های معاملاتی را
از `accounts` جدا کرد** (بروکر → `models/trading.py :: PersonalTradingAccount`، پراپ → `models/prop.py :: PropAccount`).
**فاز ۳۸.۲** گزینهٔ `broker` را از dropdown حذف کرد.

⚠️ **اما `AccountType` بک‌اند** مستقل از فرانت اعتبارسنجی می‌کند:
```python
# backend/app/api/finance.py
@router.get("/accounts")
def get_accounts(type: Optional[AccountType] = None, ...):
```
`AccountType` الان فقط `bank/exchange/crypto_wallet/card/cash/trust_wallet` است ⇒ درخواست
`?type=broker` با **۴۲۲ Unprocessable Entity** رد می‌شود ⇒ promise همیشه reject می‌شد ⇒
dropdown همیشه خالی («— حساب بروکری وجود ندارد —») و در **هر بار بارگذاری صفحه** یک
`console.error('خطا در دریافت حساب‌های بروکر:', ...)` تولید می‌شد.
**⇒ «query مرده» تأیید شد.**

### ۲.۲ `frontend/src/components/AccountForm.tsx`

**سه فیلد بی‌اثر (کد قبل):**

| فیلد | Props | state | useEffect | handleSubmit | reset | JSX |
|:---|:--|:--|:--|:--|:--|:--|
| **نام بروکر/صرافی** (`brokerName` → `broker_name`) | خط ۱۴ | ۴۲ | ۵۴ | ۷۰ | ۷۹ | ۱۵۹-۱۶۸ |
| **نام پراپ فرم** (`propFirmName` → `prop_firm_name`) | خط ۱۵ | ۴۳ | ۵۵ | ۷۱ | ۸۰ | ۱۷۰-۱۷۹ |
| **`propFirmId` → `prop_firm_id`** (در JSX رندر نمی‌شد ولی state + ارسال داشت) | خط ۱۶ | ۴۴ | ۵۶ | ۷۲ | ۸۱ | — |

```tsx
// Props
broker_name?: string;
prop_firm_name?: string;
prop_firm_id?: number | null;

// state
const [brokerName, setBrokerName] = useState('');
const [propFirmName, setPropFirmName] = useState('');
const [propFirmId, setPropFirmId] = useState('');

// handleSubmit
broker_name: brokerName || null,
prop_firm_name: propFirmName || null,
prop_firm_id: propFirmId ? parseInt(propFirmId) : null,
```

**آیا `AccountCreate` بک‌اند این فیلدها را قبول می‌کند؟** ❌ **نه.**
```python
# backend/app/api/finance.py:45
class AccountCreate(BaseModel):
    name: str
    type: AccountType
    currency: Currency = Currency.USD
    balance: float = 0.0
    card_number: Optional[str] = None
```
هیچ‌کدام از `broker_name` / `prop_firm_name` / `prop_firm_id` در schema نیستند ⇒ Pydantic
**بی‌صدا** آن‌ها را دور می‌ریزد. علاوه بر آن، مدل `FinancialAccount` هم این ستون‌ها را ندارد
(فاز ۲۸ از `accounts` حذفشان کرد — فقط در migration قدیمی `51ea09b4aa3d` باقی مانده‌اند).
⇒ کاربر مقدار وارد می‌کرد، ذخیره نمی‌شد، و در `mode='edit'` هم فرم خالی/غیرواقعی نشان می‌داد.
**⇒ «بی‌اثر» تأیید شد.**

> 📌 **توضیح شمارش «۳ فیلد»:** صورت مسئله فقط دو برچسب نام برد
> (`نام بروکر/صرافی`, `نام پراپ فرم`)، اما در واقع **سه فیلد بی‌اثر** وجود داشت؛
> فیلد سوم `prop_firm_id` بود که در JSX رندر نمی‌شد ولی در state و payload ارسال می‌شد.
> جهت رعایت کامل قاعدهٔ «حذف فیلدهای بی‌اثر»، **هر سه** حذف شدند.
---

## ۳. گام ۲ — تغییرات `frontend/src/pages/AnalysisPage.tsx`

### ۳.۱ حذف import
```diff
   getAnalysisBroker,
   getAllPropStages,
-  getFinanceAccounts,
 } from '../api/client';
```

### ۳.۲ `brokerAccounts`: از state به آرایهٔ ثابت خالی
```diff
-  const [brokerAccounts, setBrokerAccounts] = useState<BrokerOption[]>([]);
+  // فاز ۳۸.۳ — query مردهٔ `getFinanceAccounts({ type: 'broker' })` حذف شد.
+  // دلیل: `AccountType.BROKER` در فاز ۳۸.۲ حذف شد ⇒ backend با ۴۲۲ پاسخ می‌داد.
+  const brokerAccounts: BrokerOption[] = [];
```
**دلیل انتخاب `const []` به‌جای حذف کامل:** در این زیرفاز دامنهٔ تغییر «حذف query مرده» است و
حذف تب «بروکر» کار **فاز ۳۸.۴** است. با آرایهٔ ثابت خالی، کدِ JSX (خط ۱۹۸) **بدون خطای TS و بدون
تغییر رفتار** کار می‌کند و dropdown تب بروکر همان حالت «خالی» را نشان می‌دهد — ولی این بار
**بدون درخواست شبکه و بدون `console.error`**. `BrokerOption` هنوز مصرف می‌شود ⇒ import آن حفظ شد.

### ۳.۳ حذف خودِ query از `useEffect`
```diff
     getAllPropStages()
       .then((res) => setPropStages(res.data))
       .catch((err) => console.error('خطا در دریافت مراحل پراپ:', err));
-    getFinanceAccounts({ type: 'broker' })
-      .then((res) => setBrokerAccounts(res.data))
-      .catch((err) => console.error('خطا در دریافت حساب‌های بروکر:', err));
   }, []);
```

### ۳.۴ به‌روزرسانی کامنت سرصفحه
```diff
-  // ۱. بارگذاری لیست‌های اولیه (نسخه‌ها / پراپ‌ها / بروکرها)
+  // ۱. بارگذاری لیست‌های اولیه (نسخه‌ها / پراپ‌ها)
+  // فاز ۳۸.۳ — بارگذاری «بروکرها» حذف شد (query مرده)
```

> ✅ **بعد از تغییر:** هیچ import بی‌استفاده، هیچ state بی‌استفاده و هیچ متغیر بی‌مصرفی باقی نمانده
> (`tsc` با `noUnusedLocals` کامپایل می‌شود و EXIT 0 داد).

---

## ۴. گام ۳ — تغییرات `frontend/src/components/AccountForm.tsx`

### ۴.۱ Props — حذف ۳ فیلد از `initialData`
```diff
     balance: number;
     card_number?: string;
-    broker_name?: string;
-    prop_firm_name?: string;
-    prop_firm_id?: number | null;
   };
```
> ⚠️ **سازگاری با فراخوان:** `FinancePage.tsx:389` مقدار `initialData={editAccount ?? undefined}` می‌فرستد و
> `editAccount` از نوع `Account` (خط ۵۵ همان فایل) است که **هنوز** `broker_name`/`prop_firm_name`/`prop_firm_id`
> دارد. چون `editAccount` یک **متغیر** است (نه object literal تازه)، قانون *excess property check*
> تایپ‌اسکریپت اعمال نمی‌شود ⇒ **خطای کامپایل ندارد** (تأییدشده با `TSC_EXIT=0`).
> پاک‌سازی تایپ `Account` در `FinancePage` خارج از دامنهٔ این زیرفاز است (فقط برچسب/تایپ نمایشی).

### ۴.۲ state
```diff
   const [cardNumber, setCardNumber] = useState('');
-  const [brokerName, setBrokerName] = useState('');
-  const [propFirmName, setPropFirmName] = useState('');
-  const [propFirmId, setPropFirmId] = useState('');
+  // فاز ۳۸.۳ — فیلدهای بی‌اثر `broker_name` / `prop_firm_name` / `prop_firm_id` حذف شدند
+  // (در `AccountCreate` بک‌اند وجود ندارند ⇒ Pydantic بی‌صدا دور می‌ریخت)
   const [saving, setSaving] = useState(false);
```

### ۴.۳ `useEffect` (پرکردن فرم در حالت ویرایش)
```diff
       setCardNumber(initialData.card_number || '');
-      setBrokerName(initialData.broker_name || '');
-      setPropFirmName(initialData.prop_firm_name || '');
-      setPropFirmId(initialData.prop_firm_id ? String(initialData.prop_firm_id) : '');
     }
```

### ۴.۴ `handleSubmit` — payload
```diff
         balance: parseFloat(balance) || 0,
         card_number: cardNumber || null,
-        broker_name: brokerName || null,
-        prop_firm_name: propFirmName || null,
-        prop_firm_id: propFirmId ? parseInt(propFirmId) : null,
       });
```
> ✅ payload حالا **دقیقاً** منطبق بر `AccountCreate` است: `{ name, type, currency, balance, card_number }`
> (`card_number` تنها فیلد اختیاری درست‌است و **حفظ شد**).

### ۴.۵ reset پس از ذخیره
```diff
       setCardNumber('');
-      setBrokerName('');
-      setPropFirmName('');
-      setPropFirmId('');
     } finally {
```

### ۴.۶ JSX — حذف دو بلوک ورودی (۲۹ خط)
```diff
-          {/* نام بروکر */}
-          <div>
-            <label ...>نام بروکر/صرافی</label>
-            <input value={brokerName} onChange={...} placeholder="مثلاً Binance" ... />
-          </div>
-
-          {/* نام پراپ */}
-          <div>
-            <label ...>نام پراپ فرم</label>
-            <input value={propFirmName} onChange={...} placeholder="مثلاً FTMO" ... />
-          </div>
         </div>
```
**نتیجه:** گرید فرم حالا ۴ فیلد دارد — `نام حساب` (تمام‌عرض)، `نوع حساب`، `ارز`، `موجودی`، `شماره کارت`.
هیچ کلاس Tailwind یا کامپوننتی هم بی‌استفاده نماند (`GlassCard` / `LoadingButton` هر دو هنوز مصرف می‌شوند).

---

## ۵. گام ۴ — تست و اعتبارسنجی

```text
cd frontend
npx tsc -b --force ....................................... TSC_EXIT=0
npx vitest run ........................................... VITEST_EXIT=0 · 9 passed
```

**جزئیات Vitest:**
```text
 ✓ src/__tests__/utils.test.ts (4 tests)
 ✓ src/__tests__/components.test.tsx (5 tests)

 Test Files  2 passed (2)
      Tests  9 passed (9)
```
> ✅ **قبل از تغییر** هم `TSC_EXIT=0` و `9 passed` بود ⇒ **بدون رگرسیون** (baseline گرفته شد، سپس تست‌ها دوباره اجرا شدند).

### 🔍 اعتبارسنجی Cross-Stack (فرانت ↔ بک‌اند)
```text
backend  AccountCreate (api/finance.py:45) : name, type, currency, balance, card_number
frontend AccountForm  payload              : name, type, currency, balance, card_number
MATCH: True
```

---

## ۶. دامنهٔ تغییرات (بدون commit)

```text
 M frontend/src/components/AccountForm.tsx
 M frontend/src/pages/AnalysisPage.tsx
?? PHASE38_3_FIX_REMAINING.md
```
```text
 frontend/src/components/AccountForm.tsx | 39 ++-------------------------------
 frontend/src/pages/AnalysisPage.tsx     | 11 +++++-----
 2 files changed, 7 insertions(+), 43 deletions(-)
```
> ✅ **بک‌اند، `client.ts`، DB و تست‌های بک‌اند لمس **نشدند**. هیچ `commit` ای زده نشد.
---

## ۷. 🐛 یافته‌های اضافی حین کار (ورودیِ فاز ۳۸.۴)

این‌ها **خارج از دامنهٔ ۳۸.۳** بودند و **دست‌نخورده** ماندند، اما چون مستقیماً به فاز ۳۸.۴ مربوط‌اند
(حذف تب «بروکر»)، اینجا مستند می‌شوند:

### ۷.۱ `AnalysisPage.tsx:116` — باگ **خاموش** داده (همان مورد ذکرشده در بریف)
```tsx
: await getTrades({ finance_account_id: selectedId, limit: 500 });
```
🔍 **پس از verify:** در `backend/app/api/trades.py:210-232` امضای `get_trades` این‌هاست:
`version_id, strategy_id, personal_trading_account_id, prop_stage_id, symbol, test_type, source, direction, status, date_from, date_to, search, pnl_min, pnl_max, page, page_size, limit, offset, sort_by, sort_order`
⇒ **`finance_account_id` وجود ندارد.** نزدیک‌ترین معادل: **`personal_trading_account_id`**.
**چرا خاموش است؟** FastAPI برای query-paramهای *اعلام‌نشده* خطا نمی‌دهد (۴۲۲ فقط برای اعتبارسنجی
پارامترهای اعلام‌شده است) ⇒ فیلتر بی‌صدا نادیده گرفته می‌شود و endpoint **همهٔ معاملات** را برمی‌گرداند،
نه معاملات آن دامنه ⇒ جدول «لیست معاملات» در تب بروکر، داده‌ی کل DB را نشان می‌داد.
✅ **این خط فقط در شاخهٔ `else` (تب بروکر) است** ⇒ با حذف تب در فاز ۳۸.۴ **خودبه‌خود حذف می‌شود**.

### ۷.۲ `analyzeBroker` / `getAnalysisBroker` — endpointهای **ناموجود** (۴۰۴ قطعی)
```ts
// frontend/src/api/client.ts:227-228
export const analyzeBroker = (financeAccountId: number) =>
  api.post(`/api/analytics/analyze/broker/${financeAccountId}`);
// frontend/src/api/client.ts:234-235
export const getAnalysisBroker = (financeAccountId: number) =>
  api.get(`/api/analytics/analysis/broker/${financeAccountId}`);
```
اما در `backend/app/api/analytics.py` این مسیرها **تعریف نشده‌اند**؛ مسیرهای واقعی:
```text
POST /analyze/{version_id}          POST /analyze/version/{version_id}
POST /analyze/prop/{prop_stage_id}  POST /analyze/personal-account/{personal_trading_account_id}
GET  /analysis/version/{version_id} GET  /analysis/prop/{prop_stage_id}
GET  /analysis/personal-account/{personal_trading_account_id}
```
⇒ در تب بروکر، کلیک روی «🔄 تحلیل مجدد» **همیشه ۴۰۴** می‌گرفت (کد فاز ۲۸ نام endpoint را به
`personal-account` تغییر داد ولی فرانت به‌روز نشد) ⇒ حذف آن‌ها در فاز ۳۸.۴ **بدهی مرده** است، نه حذف قابلیت.
> 💡 اگر بعداً تحلیل «حساب معاملاتی شخصی» خواستید، مسیر درست:
> `POST /api/analytics/analyze/personal-account/{personal_trading_account_id}`.

### ۷.۳ بدهی‌های کوچک باقی‌مانده (بی‌خطر، فعلاً حفظ شدند)
| # | مورد | توضیح |
|:--|:---|:---|
| ۱ | `ScopeType` شامل `'broker'` + تب 🏦 (خطوط ۲۴-۳۲) | حذفش کار ۳۸.۴ است |
| ۲ | `backend/app/api/analytics.py:395-404` — `classify()` معاملاتِ `personal_trading_account_id` را `"broker"` برچسب می‌زند و کلید `"broker"` در `by_source` هست | **کلید خروجی API** است ⇒ تغییرش نیازمند بررسی مصرف‌کننده‌هاست (خارج از دامنهٔ ۳۸.۴ پیشنهادی) |
| ۳ | `FinancePage.tsx:76,82` — `ACCOUNT_TYPE_LABELS`/`ACCOUNT_TYPE_NAMES` هنوز `broker`/`prop` دارند | فقط برچسب نمایشی؛ بی‌خطر |
| ۴ | `FinancePage.tsx:55-59` — تایپ `Account` هنوز `broker_name`/`prop_firm_name`/`prop_firm_id` دارد | الان بی‌مصرف است (فرم دیگر نمی‌فرستد/نمی‌خواند) |

---

## ۸. ✅ تأیید نهایی زیرفاز ۳۸.۳

| بررسی | نتیجه |
|:---|:---|
| `AnalysisPage.tsx` — هیچ اثر باقی‌مانده‌ای از `getFinanceAccounts({type:'broker'})` | ✅ صفر (import/state/query همه حذف) |
| `AccountForm.tsx` — هیچ اثر باقی‌مانده‌ای از `brokerName`/`propFirmName`/`propFirmId` | ✅ صفر |
| `getFinanceAccounts` در سه نقطهٔ سالم دیگر (Dashboard/Finance) | ✅ دست‌نخورده |
| payload فرم دقیقاً منطبق بر `AccountCreate` | ✅ `{name, type, currency, balance, card_number}` |
| `npx tsc -b --force` | ✅ `TSC_EXIT=0` |
| `npx vitest run` | ✅ `VITEST_EXIT=0` · **9 passed** |
| رگرسیون | ✅ صفر (baseline قبل از تغییر هم ۰/۹ بود) |
| تغییر بک‌اند / DB / `client.ts` | ✅ صفر |
| commit | ✅ **زده نشد** |

⏸️ **پایان زیرفاز ۳۸.۳ — منتظر تأیید کاربر برای شروع ۳۸.۴ (Clean Break).**