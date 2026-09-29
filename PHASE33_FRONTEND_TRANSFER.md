# 🔄 PHASE 33 — FRONTEND TRANSFER (Payout Transfer Form)

> **وضعیت:** ✅ کامل — فرم UI ثبت انتقال بین‌حسابی
> **تاریخ:** ۱۴۰۵/۰۷/۰۹
> **دامنه:** `frontend/src/pages/PayoutHistoryPage.tsx` (+ استفاده از `createPropPayoutTransfer` که در `client.ts` آماده بود)
> **خروجی:** `tsc -b --force` → EXIT 0 · `vitest run` → EXIT 0

---

## ۱. هدف

فراهم کردن UI برای ثبت پرش‌های انتقال پس از دریافت برداشت:

```text
Prop ─► Trust Wallet ─► Exchange ─► IRR ─► Bank Card
         (درآمد)          (انتقال)     (انتقال)   (انتقال)
```

طبق قانون فاز ۳۳: **تنها پرش «Prop → Trust Wallet» (نقطهٔ دریافت) درآمد است**؛ بقیهٔ پرش‌ها
انتقال (`type=exchange`) هستند و در `finance/summary.total_transfers` می‌آیند، نه `total_income`.

---

## ۲. تغییرات — `frontend/src/pages/PayoutHistoryPage.tsx`

### ۲.۱ Import و State
- افزودن `createPropPayoutTransfer` به importها.
- State جدید:

```tsx
const [transferRow, setTransferRow] = useState<any | null>(null);
const [transferSaving, setTransferSaving] = useState(false);
const [transferForm, setTransferForm] = useState({
  from_account_id: '', to_account_id: '', amount: '', currency: '', date: '', note: '',
});
```

### ۲.۲ Handlerها
- `openTransfer(row)`: فرم را باز می‌کند و **حساب مبدأ را به‌صورت پیش‌فرض = حساب مقصد همان برداشت**
  و مبلغ/ارز را از خود برداشت پیش‌پر می‌کند.
- `handleTransferSubmit()`:
  - اعتبارسنجی: مقصد و مبلغ الزامی، مبدأ ≠ مقصد.
  - فراخوانی `createPropPayoutTransfer(id, {...})`.
  - پیام موفقیت: «انتقال ثبت شد (درآمد نیست)» + بارگذاری مجدد.

```tsx
await createPropPayoutTransfer(transferRow.id, {
  to_account_id: Number(transferForm.to_account_id),
  from_account_id: transferForm.from_account_id ? Number(transferForm.from_account_id) : undefined,
  amount: Number(transferForm.amount),
  currency: transferForm.currency || undefined,
  date: transferForm.date || undefined,
  note: transferForm.note || undefined,
});
```

### ۲.۳ دکمهٔ «🔄» در جدول
- در ستون عملیات، **فقط برای برداشت‌های `received`** نمایش داده می‌شود (چون پول در آن نقطه
  وارد حساب مقصد شده و انتقال بعدی معنا دارد).
- رنگ ایندگو (`#6366f1`) برای تمایز از تغییر وضعیت.

### ۲.۴ Modal انتقال
- Overlay تمام‌صفحه + کارت (RTL، تم پروژه)؛ بستن با کلیک روی backdrop یا «انصراف».
- فیلدها:

| فیلد | توضیح |
|:---|:---|
| 📤 حساب مبدأ | پیش‌فرض «حساب مقصد همان برداشت» |
| 📥 حساب مقصد | انتخاب از حساب‌های مالی (`type !== 'prop'`) |
| 💵 مبلغ | پیش‌پر از مبلغ برداشت |
| 💱 ارز | USD / IRR |
| 📅 تاریخ (شمسی) | `PersianDateInput` |
| 📝 توضیحات | اختیاری |

- بنر راهنما: «زنجیرهٔ نمونه: Prop → Trust Wallet → Exchange → IRR → Bank Card» + تأکید
  «این انتقال درآمد نیست».
- فهرست حساب‌ها از `transferAccounts` (فیلتر `type !== 'prop'`) که قبلاً در صفحه بارگذاری می‌شود.

---

## ۳. جریان کاربری

```text
۱) ثبت برداشت              ⇒ status = REQUESTED (بدون پول)
۲) تأیید → پردازش → دریافت  ⇒ ثبت درآمد در حساب مقصد (Trust Wallet)
۳) دکمهٔ 🔄 روی همان ردیف   ⇒ ثبت انتقال Trust Wallet → Exchange
۴) تکرار 🔄 برای پرش بعدی   ⇒ Exchange → IRR → Bank Card
   (هیچ‌کدام از پرش‌های ۳ و ۴ درآمد نیستند)
```

---

## ۴. اعتبارسنجی

```text
cd frontend && npx tsc -b --force ....... TSC_EXIT=0 (بدون خطا)
cd frontend && npx vitest run ........... VITEST_EXIT=0 (9 passed)
```

پوشش بک‌اند این قابلیت از قبل توسط `test_transfer_is_not_income` تضمین شده است
(`total_income` ثابت، `total_transfers` افزایش، موجودی مبدأ کم/مقصد زیاد).

---

## ۵. یادداشت‌ها

1. **اعتبارسنجی سمت سرور:** endpoint همچنین وجود حساب‌ها و «مبدأ ≠ مقصد» را بررسی و خطای
   فارسی برمی‌گرداند؛ UI همان پیام را نمایش می‌دهد.
2. **بدون Double Counting:** انتقال‌ها `Transaction.type=EXCHANGE` هستند و در محاسبهٔ درآمد
   (`DEPOSIT`/`PROFIT`) شمرده نمی‌شوند.
3. **پیش‌شرط نمایش دکمه:** وضعیت `received` — برای جلوگیری از ثبت انتقال پیش از ورود واقعی پول.
