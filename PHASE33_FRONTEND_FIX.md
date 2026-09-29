# 💸 PHASE 33 — FRONTEND FIX (Payout Status) 

> **وضعیت:** ✅ کامل — دکمهٔ تغییر وضعیت برداشت
> **تاریخ:** ۱۴۰۵/۰۷/۰۹
> **دامنه:** `frontend/src/api/client.ts` + `frontend/src/pages/PayoutHistoryPage.tsx`
> **خروجی:** `tsc -b --force` → EXIT 0 · `vitest run` → 9 passed

---

## ۱. هدف

به‌روزرسانی صفحهٔ تاریخچهٔ برداشت تا چرخهٔ عمر فاز ۳۳ را پشتیبانی کند:

```text
REQUESTED ─► APPROVED ─► PROCESSING ─► RECEIVED   (اینجا درآمد ثبت می‌شود)
      └──────────┴───────────┴────────► CANCELLED
```

---

## ۲. تغییرات

### ۲.۱ `frontend/src/api/client.ts`
- توسعهٔ تایپ `createPropPayout` با `currency?`/`reference?`/`status?`.
- توابع جدید:

```ts
export const updatePropPayoutStatus = (id: number, status: string, reference?: string) =>
  api.post(`/api/prop/payouts/${id}/status`, { status, reference });

export const createPropPayoutTransfer = (id: number, data: {
  to_account_id: number; amount: number; from_account_id?: number;
  currency?: string; note?: string; date?: string;
}) => api.post(`/api/prop/payouts/${id}/transfer`, data);
```

### ۲.۲ `frontend/src/pages/PayoutHistoryPage.tsx`
- **برچسب وضعیت (Badge):** `STATUS_META` با ۵ وضعیت (رنگ/آیکن/برچسب فارسی) و کامپوننت
  `StatusBadge`.
- **ستون «وضعیت»** به جدول پراپ اضافه شد.
- **دکمه‌های تغییر وضعیت:** فقط انتقال‌های مجاز که از بک‌اند می‌آید
  (`allowed_transitions`) نمایش داده می‌شوند؛ بنابراین نباید بتوان انتقال نامعتبر زد:
  - `REQUESTED` ⇒ «تأیید» + «لغو»
  - `APPROVED` ⇒ «پردازش» + «لغو»
  - `PROCESSING` ⇒ «دریافت» + «لغو»
  - `RECEIVED`/`CANCELLED` ⇒ فقط «حذف» (terminal)
- **تأیید دریافت:** کلیک روی «دریافت» یک `confirm` نشان می‌دهد (چون درآمد وارد FINANCE می‌شود).
- **حالت اجرا:** `busyId` برای غیرفعال‌کردن دکمه‌ها حین درخواست.
- **راهنما در فرم:** «وضعیت اولیه: درخواست‌شده — با دکمه‌های جدول → تأیید → پردازش → دریافت».
- رنگ دکمهٔ «دریافت» سبز (profit)، «لغو» قرمز (loss)، بقیه accent.

---

## ۳. نکتهٔ رفتاری مهم (هم‌راستا با بک‌اند فاز ۳۳)

| قبل | بعد |
|:---|:---|
| ثبت برداشت ⇒ فوراً پول و درآمد ثبت می‌شد | ثبت برداشت ⇒ `REQUESTED` (بدون پول) |
| — | رسیدن به `RECEIVED` ⇒ ثبت `FinancialTransaction(type=PROFIT)` + افزایش موجودی |
| — | `CANCELLED` ⇒ بدون هیچ اثر مالی |

> تا زمانی که برداشت به `RECEIVED` نرسد، **هیچ مبلغی در FINANCE ثبت نمی‌شود** و
> `withdrawable_profit` کاهش نمی‌یابد.

---

## ۴. اعتبارسنجی

```text
cd frontend && npx tsc -b --force ......... EXIT 0 (بدون خطا)
cd frontend && npx vitest run ............. 9 passed
```

---

## ۵. گام بعدی (اختیاری)

- افزودن دکمهٔ «🔄 انتقال» برای ثبت پرش‌های `Trust Wallet → Exchange → IRR → Bank Card`
  (تابع `createPropPayoutTransfer` آماده است؛ فقط فرم UI لازم دارد).
