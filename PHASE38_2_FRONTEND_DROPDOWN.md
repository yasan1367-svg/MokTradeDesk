# 🎛️ PHASE 38.2 — Frontend Dropdown · REPORT

> **وضعیت:** ✅ کامل
> **تاریخ:** ۱۴۰۵/۰۷/۰۹
> **دامنه:** فقط فرانت‌اند (۲ فایل) — **بدون تغییر بک‌اند**
> **خروجی:** `tsc -b --force` → EXIT 0 · `vitest run` → 9 passed

---

## ۱. خلاصهٔ اجرایی

به dropdown «نوع حساب مالی» سه گزینهٔ جدید فاز ۳۸ اضافه شد و **دو گزینهٔ نامعتبر حذف شدند**:

| گزینه | مقدار | وضعیت |
|:---|:---|:---|
| 💳 کارت بانکی | `card` | ✅ جدید |
| 💵 پول نقد | `cash` | ✅ جدید |
| 🤝 کیف پول Trust | `trust_wallet` | ✅ جدید |
| 📊 بروکر | `broker` | ❌ **حذف شد** (نامعتبر) |
| 🏢 پراپ | `prop` | ❌ **حذف شد** (نامعتبر) |

---

## ۲. گام ۱ — کد قبلی

**فایل واقعی dropdown:** `frontend/src/components/AccountForm.tsx` (نه `FinancePage.tsx`)

```tsx
const ACCOUNT_TYPES = [
  { value: 'bank', label: '🏦 بانک' },
  { value: 'exchange', label: '🔄 صرافی' },
  { value: 'crypto_wallet', label: '₿ کیف‌پول ارز دیجیتال' },
  { value: 'broker', label: '📊 بروکر' },      // ← نامعتبر
  { value: 'prop', label: '🏢 پراپ' },          // ← نامعتبر
];
```
> `FinancePage.tsx` فقط این فرم را `<AccountForm ... />` صدا می‌زند و برچسب‌های نمایشی
> (`ACCOUNT_TYPE_LABELS` / `ACCOUNT_TYPE_NAMES`) را نگه می‌دارد.

---

## ۳. گام ۲ — تغییرات

### ۳.۱ `frontend/src/components/AccountForm.tsx`
```tsx
const ACCOUNT_TYPES = [
  { value: 'bank', label: '🏦 بانک' },
  { value: 'exchange', label: '🔄 صرافی' },
  { value: 'crypto_wallet', label: '₿ کیف‌پول ارز دیجیتال' },
  { value: 'card', label: '💳 کارت بانکی' },           // فاز ۳۸.۲
  { value: 'cash', label: '💵 پول نقد' },               // فاز ۳۸.۲
  { value: 'trust_wallet', label: '🤝 کیف پول Trust' }, // فاز ۳۸.۲
];
```

### ۳.۲ `frontend/src/pages/FinancePage.tsx` (برچسب‌های نمایشی)
```tsx
const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  bank: '🏦', exchange: '🔄', crypto_wallet: '₿', broker: '📊', prop: '🏢',
  card: '💳', cash: '💵', trust_wallet: '🤝',   // فاز ۳۸.۲
};

const ACCOUNT_TYPE_NAMES: Record<string, string> = {
  bank: 'بانک', exchange: 'صرافی', crypto_wallet: 'کیف‌پول دیجیتال',
  broker: 'بروکر', prop: 'پراپ',
  card: 'کارت بانکی', cash: 'پول نقد', trust_wallet: 'کیف پول Trust',  // فاز ۳۸.۲
};
```
> `crypto_wallet` از «تراست ولت» به **«کیف‌پول دیجیتال»** تغییر یافت تا با `trust_wallet`
> جدید اشتباه نشود. برچسب‌های `broker`/`prop` حفظ شدند (برای دادهٔ قدیمی در صورت وجود).

---

## ۴. 🐛 باگ از قبل موجود که رفع شد

در `backend/app/api/finance.py`:
```python
class AccountCreate(BaseModel):
    type: AccountType      # ← اعتبارسنجی Pydantic
```
از فاز ۲۷/۲۸، `AccountType` فقط شامل `BANK/EXCHANGE/CRYPTO_WALLET` است (بروکر → `Broker` و
پراپ → `PropAccount` منتقل شدند). بنابراین گزینه‌های `broker`/`prop` در dropdown ⇒
**خطای ۴۲۲ در زمان ثبت حساب** می‌دادند. حذف شدند.

---

## ۵. گام ۳ — تست و اعتبارسنجی

```text
cd frontend
npx tsc -b --force ....................................... TSC_EXIT=0
npx vitest run ........................................... 9 passed (VITEST_EXIT=0)
```

> ⚠️ دستور درخواستی `pnpm tsc --noEmit` بود؛ اما این پروژه **pnpm ندارد**
> (`package.json` + `node_modules` با npm) و اسکریپت رسمی `tsc -b` است. بنابراین از
> `npx tsc -b --force` استفاده شد (همان روش فاز ۳۶–۳۸).

### اعتبارسنجی Cross-Stack (script موقت، سپس حذف)
```
frontend: ['bank', 'card', 'cash', 'crypto_wallet', 'exchange', 'trust_wallet']
backend : ['bank', 'card', 'cash', 'crypto_wallet', 'exchange', 'trust_wallet']
MATCH: True
```
✅ مقادیر dropdown دقیقاً با `AccountType` بک‌اند مطابق‌اند.

---

## ۶. دامنهٔ تغییرات
```
 M frontend/src/components/AccountForm.tsx
 M frontend/src/pages/FinancePage.tsx
```
(فاز ۳۸ بک‌اند کامیت شده: `c40d512`)

---

## ۷. یادداشت‌های باقی‌مانده (خارج از دامنه)

1. **فیلدهای بی‌اثر در فرم:** `نام بروکر/صرافی` و `نام پراپ فرم` همچنان در `AccountForm`
   نمایش داده می‌شوند اما فیلدهای `AccountCreate` نیستند (فاز ۲۸ حذف شدند) ⇒ بی‌اثرند.
   پیشنهاد: حذف در یک فاز تمیزکاری فرانت.
2. **`AnalysisPage.tsx:71`** از `getFinanceAccounts({ type: 'broker' })` استفاده می‌کند —
   با حذف `AccountType.BROKER` این فیلتر احتمالاً همیشه خالی برمی‌گردد (نیازمند بررسی در فاز بعد).
