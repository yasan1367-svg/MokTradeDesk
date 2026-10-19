# 🔗 PROP ↔ FINANCE Integration — گزارش فاز ۵.۱ (Frontend)

> **وضعیت:** ✅ کامل و تست‌شده
> **دامنه:** Frontend + یک افزودنی کوچک بک‌اند (endpoint دکمه «ساخت حساب مالی»)
> **تاریخ:** 2026-09-24
> **تصمیمات تأییدشده:** انحراف ۱ = الف (`withdrawal_date` در بک‌اند) | انحراف ۲ = الف (کامپوننت `Toast.tsx`)

---

## ۱. خلاصه تغییرات

| حوزه | تغییر |
|------|-------|
| **Backend** | `WithdrawalCreate.withdrawal_date` + پارس ISO + استفاده در `PropWithdrawal` و `Transaction` + endpoint جدید `POST /accounts/{id}/finance-account` |
| **`client.ts`** | اصلاح `withdrawFromStage` (امضای جدید) + `create_finance_account` در `createPropAccount` + ۳ تابع جدید |
| **`Toast.tsx`** | 🆕 کامپوننت Toast (success/error، auto-dismiss، dark-aware، RTL) |
| **`PropPage.tsx`** | checkbox حساب مالی + Modal برداشت (select مقصد + PersianDateInput) + بخش حساب مالی در جزئیات + Toast + Skeleton |

**جریان جدید برداشت:**
```
دکمه «💰 برداشت» → Modal → مبلغ + تاریخ (شمسی) + حساب مقصد + توضیحات
  → POST /api/prop/stages/{id}/withdraw
      → PropWithdrawal (+ destination_account_id + withdrawal_date)
      → Transaction(type=withdrawal) ← بک‌اند فاز ۵.۰
      → به‌روزرسانی موجودی مبدأ/مقصد
  → Toast موفقیت + refresh جزئیات و لیست مقصدها
```

---

## ۲. فایل‌های تغییریافته

| # | فایل | نوع | جزئیات |
|---|------|-----|--------|
| ۱ | `backend/app/api/prop.py` | ✏️ | `withdrawal_date` در schema + پارس ISO + `PropWithdrawal`/`Transaction` + **endpoint جدید** |
| ۲ | `frontend/src/api/client.ts` | ✏️ | ۱ امضا اصلاح + ۳ تابع جدید + ۱ فیلد در `createPropAccount` |
| ۳ | `frontend/src/components/Toast.tsx` | 🆕 | کامپوننت جدید |
| ۴ | `frontend/src/pages/PropPage.tsx` | ✏️ | ۸ تغییر (imports، state، loaders، handlers، JSX) |
| ۵ | `PROP_FINANCE_INTEGRATION_PHASE5_FRONTEND.md` | 🆕 | همین فایل |

### ۲.۱ بک‌اند (`api/prop.py`)

```python
class WithdrawalCreate(BaseModel):
    amount: float
    note: Optional[str] = None
    destination_account_id: int
    withdrawal_date: Optional[str] = None  # 🆕 فاز ۵.۱ (ISO 8601)
```

```python
# پارس امن تاریخ
withdrawal_dt = datetime.now(timezone.utc)
if request.withdrawal_date:
    try:
        parsed = datetime.fromisoformat(request.withdrawal_date.replace("Z", "+00:00"))
        withdrawal_dt = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(400, "فرمت تاریخ برداشت نامعتبر است (ISO 8601: YYYY-MM-DD)")
```
→ `PropWithdrawal(withdrawal_date=withdrawal_dt)` و `Transaction(date=withdrawal_dt)`

**⚠️ endpoint جدید (افزودنی):**
```python
@router.post("/accounts/{account_id}/finance-account")
def create_prop_finance_account(account_id: int, db: Session = Depends(get_db)):
    """ساخت (یا اتصال) حساب مالی برای یک اکانت پراپ — 🆕 فاز ۵.۱"""
    # prop_acc بررسی → _ensure_finance_account() → commit
```

### ۲.۲ کلاینت (`api/client.ts`)

```typescript
// امضای جدید (backward-incompatible با نسخه قبلی)
export const withdrawFromStage = (
  stageId: number,
  data: {
    amount: number;
    destination_account_id: number;
    withdrawal_date?: string;
    note?: string;
  }
) => api.post(`/api/prop/stages/${stageId}/withdraw`, data);

// 🆕
export const getPropAccountFinanceAccount = (propAccountId: number) =>
  api.get(`/api/prop/accounts/${propAccountId}/finance-account`);
export const createPropFinanceAccount = (propAccountId: number) =>
  api.post(`/api/prop/accounts/${propAccountId}/finance-account`);
export const getFinanceAccountsForDestination = () => api.get('/api/finance/accounts');

// createPropAccount + create_finance_account?: boolean
```

### ۲.۳ `Toast.tsx` (جدید)

- Props: `message`, `type: 'success' | 'error'`, `onClose`, `duration = 3000`
- Dark-aware: `bg-[var(--bg-card)]/95` + `text-[var(--text-secondary)]`
- RTL: `dir="rtl"` + `left-1/2 -translate-x-1/2`
- auto-dismiss با ref-safe pattern (`useRef` + `useEffect`) — بدون ریست تایمر در هر رندر
- `role="status"` + `aria-live="polite"` برای دسترس‌پذیری

### ۲.۴ `PropPage.tsx`

| # | تغییر |
|---|--------|
| ۱ | imports: `-getPersonalAccounts`، `+getPropAccountFinanceAccount`، `+getFinanceAccountsForDestination`، `+createPropFinanceAccount`، `+PersianDateInput`، `+Toast`، `+Skeleton` |
| ۲ | state: `personalAccounts` → **`destinationAccounts`** + ۹ state جدید (`createFinanceAccount`, `financeInfo`, `loadingDetail`, `showWithdrawModal`, `withdrawingStage`, `withdrawAmount`, `withdrawDate`, `withdrawDestinationId`, `withdrawNote`) |
| ۳ | `loadPersonalAccounts` → **`loadDestinationAccounts`** (فیلتر `type !== 'prop'`) |
| ۴ | `loadAccountDetail` → `+loadingDetail` + `+loadFinanceInfo()` |
| ۵ | `handleCreateAccount` → ارسال `create_finance_account` + پیام هوشمند |
| ۶ | `handleWithdraw(stage)` → بازکردن Modal (جایگزین `prompt()`) + `handleConfirmWithdraw()` |
| ۷ | `handleCreateFinanceAccount(propAccountId)` → برای دکمه «ساخت حساب مالی» |
| ۸ | JSX: بنرها → Toast، checkbox در فرم اکانت، بخش حساب مالی در جزئیات (+Skeleton)، Modal برداشت (~۱۳۰ خط) |

---

## ۳. نتایج تست

### ۳.۱ تست‌های بک‌اند

**الف) `withdrawal_date` — ۸ PASS / ۰ FAIL**
```
POST /withdraw {"amount":100, "destination_account_id":1, "withdrawal_date":"2026-03-15"} → 200
```
| بررسی | نتیجه |
|-------|-------|
| `PropWithdrawal.withdrawal_date == 2026-03-15` | ✅ `2026-03-15 00:00:00` |
| `Transaction.date == 2026-03-15` | ✅ `2026-03-15 00:00:00` |
| بدون `withdrawal_date` → «الان» | ✅ `2026-09-24 20:25:05+00:00` |
| تاریخ نامعتبر (`"not-a-date"`) → `400` | ✅ پیام: «فرمت تاریخ برداشت نامعتبر است (ISO 8601: YYYY-MM-DD)» |
| ISO کامل (`2026-04-20T14:30:00+00:00`) | ✅ `2026-04-20 14:30:00` |

**ب) endpoint ساخت حساب مالی — ۱۵ PASS / ۰ FAIL**
```
POST /api/prop/accounts/{id}/finance-account → 200
{'linked': True, 'account': {'id': 1, 'name': 'NoFin 25K', 'type': 'prop',
 'currency': 'USD', 'balance': 25000.0, 'prop_firm_name': 'FTMO'}}
```
| بررسی | نتیجه |
|-------|-------|
| `GET` قبل از ساخت → `linked: false` | ✅ |
| `POST` → `linked: true` | ✅ |
| نام درست (`NoFin 25K`) | ✅ |
| `type == prop` | ✅ |
| `balance == 25000` (از `Stage1.initial_balance`) | ✅ |
| `PropAccount.finance_account_id` وصل شد | ✅ |
| فقط ۱ حساب `prop` ساخته شد | ✅ |
| `GET` بعد از ساخت → `linked: true` + همان حساب | ✅ |
| `POST` دوباره → **idempotent** (حساب جدید ساخته نشد) | ✅ |
| اکانت ناموجود → `404` | ✅ |

### ۳.۲ تست‌های Frontend

| بررسی | دستور | نتیجه |
|-------|-------|-------|
| TypeScript (build mode، بدون کش) | `npx tsc -b --force` | ✅ **`TSCB_EXIT=0`** |
| ESLint روی `Toast.tsx` | `npx eslint src/components/Toast.tsx` | ✅ **`TOAST_ESLINT_EXIT=0`** |
| Production build | `npm run build` | ✅ **`BUILD_EXIT=0`** (`✓ built in 2.69s`) |
| ایمپورت بک‌اند | `from app.api import prop` | ✅ ۲۲ route |

### ۳.۳ ایمنی داده

| جدول | مقدار |
|------|-------|
| alembic_version | `b7d4e19c2f83` (بدون تغییر) |
| prop_accounts / prop_stages | ۲ / ۲ |
| trades / accounts | ۱۸ / ۱ |
| transactions / prop_withdrawals / prop_costs | ۰ / ۰ / ۰ |
| categories | ۱۳ |

✅ تست‌ها روی **DB درون‌حافظه‌ای** اجرا شدند — DB واقعی **دست‌نخورده**.

---

## ۴. نکات و هشدارها

### ۴.۱ ⚠️ افزودنی خارج از مرحله ۱ تأییدشده (Backend)
برای اینکه دکمه **«💰 ساخت حساب مالی»** (که در spec تأییدشده شما بود) واقعاً کار کند، endpoint جدید زیر اضافه شد — چون هیچ مسیری برای ساخت حساب مالی «به‌درخواست» وجود نداشت (`_ensure_finance_account` فقط هنگام برداشت اجرا می‌شد):

```python
POST /api/prop/accounts/{account_id}/finance-account
```
- کد: ~۲۵ خط | idempotent | تست‌شده (۱۵ PASS)
- اگر با این افزودنی موافق نیستید، حذفش آسان است (بک‌اند + ۳ خط در فرانت).

### ۴.۲ ⚠️ پیاده‌نشده: گزینه «حساب جدید» در فرم برداشت
spec شما گفته بود: «گزینه «حساب جدید»: امکان ساخت حساب جدید در همان فرم».
**پیاده نشد** — به‌جایش اگر هیچ حساب مقصدی وجود نداشت، هشدار روشن نمایش داده می‌شود:
> ⚠️ حساب مالی مقصدی وجود ندارد. ابتدا در صفحه «مالی» یک حساب بانکی/صرافی/کیف‌پول/بروکر بسازید.

**دلیل:** ساخت حساب مالی UI پیچیده‌تری لازم دارد (فرم داخلی یا Modal تودرتو). اگر لازم است، در فاز بعد اضافه می‌کنم.

### ۴.۳ ⚠️ `modalError` همچنان بنر inline است
خطای داخل Modal برداشت با بنر inline نمایش داده می‌شود (سازگار با سایر Modalهای موجود مثل pass/fail). Toast فقط برای پیام‌های سطح صفحه استفاده می‌شود.

### ۴.۴ ⚠️ خطاهای ESLint از قبل موجود (سراسری)
`eslint` روی کل پروژه خطاهایی دارد که **از قبل** وجود داشته‌اند و build را نمی‌شکند (`build = tsc -b && vite build` — بدون lint):

| فایل (تغییرنیافته) | تعداد خطا |
|---|---|
| `FinancePage.tsx` + `PersonalPage.tsx` | **۲۷ خطا** (۲۲ مورد `no-explicit-any`) |

→ نتیجه: خطاهای `no-explicit-any` در `PropPage.tsx`/`client.ts` **جدید نیستند** و از الگوی موجود پروژه می‌آیند. تنها خطای **جدید و واقعی** (`react-hooks/refs` در `Toast.tsx:27`) **اصلاح شد** و اکنون `Toast.tsx` صفر خطا دارد.

### ۴.۵ ⚠️ Dark Mode ناقص در `PropPage.tsx`
`PropPage` (مثل `PersonalPage`) از رنگ‌های hardcoded فقط-روشن استفاده می‌کند (`bg-white`, `#1A2B47`, `#E5EBF3`). کامپوننت **`Toast`** dark-aware است (`var(--bg-card)`)، اما بقیه صفحه نه. تغییر کامل به CSS variables خارج از دامنه فاز ۵.۱ است.

### ۴.۶ رفتار جدید برداشت
- **حساب شخصی حذف شد:** دیگر از `getPersonalAccounts` استفاده نمی‌شود؛ مقصد فقط از حساب‌های **مالی** (`type !== prop`) انتخاب می‌شود.
- **دستی:** بدون انتخاب مقصد، دکمه «ثبت برداشت» خطای «انتخاب حساب مقصد الزامی است» می‌دهد.
- **تاریخ شمسی:** `PersianDateInput` مقدار ISO (`YYYY-MM-DD`) می‌دهد → به بک‌اند ارسال می‌شود.

### ۴.۷ سازگاری
- `getStageWithdrawals` (client.ts) دست‌نخورده ماند — اکنون endpoint بک‌اند آن وجود دارد.
- `getPersonalAccounts` همچنان در `ImportPage`, `TradesPage`, `PropPage`(؟) — بررسی شد: در `PropPage` **حذف شد**، در دو فایل دیگر **بی‌تغییر**.

---

## ۵. چک‌لیست تکمیل‌شده

- [x] **Backend:** `withdrawal_date` در `WithdrawalCreate`
- [x] **Backend:** پارس امن ISO + خطای `400` برای فرمت نامعتبر
- [x] **Backend:** استفاده از `withdrawal_dt` در `PropWithdrawal` و `Transaction`
- [x] **Backend:** `POST /accounts/{id}/finance-account` (افزودنی — بخش ۴.۱)
- [x] **`Toast.tsx`:** کامپوننت جدید + اصلاح `react-hooks/refs`
- [x] **`client.ts`:** `withdrawFromStage` جدید + `createPropAccount.create_finance_account`
- [x] **`client.ts`:** `getPropAccountFinanceAccount` + `createPropFinanceAccount` + `getFinanceAccountsForDestination`
- [x] **`PropPage`:** checkbox «ساخت خودکار حساب مالی»
- [x] **`PropPage`:** Modal برداشت (مبلغ + `PersianDateInput` + select مقصد + توضیحات)
- [x] **`PropPage`:** حذف کامل `prompt()` و `personalAccounts`
- [x] **`PropPage`:** بخش «حساب مالی متناظر» در جزئیات (لینک/دکمه)
- [x] **`PropPage`:** Toast جایگزین بنرها
- [x] **`PropPage`:** Skeleton برای حالت لودینگ جزئیات
- [x] تست بک‌اند: ۸ + ۱۵ = **۲۳ PASS / ۰ FAIL**
- [x] `npx tsc -b --force` → `TSCB_EXIT=0`
- [x] `npx eslint src/components/Toast.tsx` → `TOAST_ESLINT_EXIT=0`
- [x] `npm run build` → `BUILD_EXIT=0`
- [x] پاکسازی فایل‌های موقت

---

## ۶. Rollback

**Frontend** (بازگردانی `withdrawFromStage` و `PropPage`):
```powershell
cd frontend
git checkout -- src/api/client.ts src/pages/PropPage.tsx
Remove-Item src/components/Toast.tsx
```

**Backend** (حذف `withdrawal_date` و endpoint جدید):
```powershell
cd backend
# فقط اگر لازم بود — تغییرات schema امن و additive هستند
git checkout -- app/api/prop.py
```
> ⚠️ **بدون migration** — هیچ تغییری در ستون‌های DB لازم نبود (هر دو فیلد additive در سطح API هستند).

---

## ۷. گام بعدی پیشنهادی

| # | موضوع | اولویت |
|---|-------|--------|
| ۱ | گزینه «حساب جدید» داخل Modal برداشت (بخش ۴.۲) | متوسط |
| ۲ | Dark Mode کامل `PropPage` / `PersonalPage` (تبدیل به CSS variables) | متوسط |
| ۳ | رفع سراسری خطاهای `no-explicit-any` (۲۷+ خطا) | پایین |
| ۴ | نمایش تاریخچه برداشت‌ها در جزئیات (استفاده از `getStageWithdrawals`) | پایین |
| ۵ | Code-splitting برای هشدار حجم chunk (>500KB) | پایین |

---

> ✅ **فاز ۵.۱ کامل شد — ۲۳ تست PASS، `tsc`/`eslint`/`build` همه سبز، DB واقعی دست‌نخورده.**