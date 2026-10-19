# PHASE10_REPORT — تکمیل UI معامله دستی (فیلد حساب مالی)

**وضعیت:** ✅ کامل شد

---

## ۱. بررسی وضعیت (قبل از تغییر)

`finance_account_id` در این بخش‌ها استفاده می‌شد:

| فایل | بخش | وضعیت قبل |
|------|-----|-----------|
| `backend/app/api/trades.py` | `ManualTradeCreate` (خط ۷۴)، اعتبارسنجی (۵۱۹)، ذخیره (۵۶۰) | ✅ از فاز ۹ کامل بود |
| `backend/app/api/trades.py` | `TradeUpdate` (۳۴)، سریالایزر (۱۴۲/۱۷۳)، فیلتر (۱۹۶، ۲۲۴-۲۲۵)، ویرایش (۳۴۸-۳۴۹، ۴۰۵-۴۰۶) | ✅ کامل |
| `frontend/src/api/client.ts` | تایپ `createManualTrade` (خط ۳۱۰) | ✅ موجود |
| `frontend/src/pages/TradesPage.tsx` | — | ❌ هیچ استفاده‌ای (نه state، نه UI، نه ارسال) |

**یافته:** بک‌اند نیازی به تغییر نداشت؛ کار اصلی فقط Frontend بود.

---

## ۲. پیاده‌سازی (فقط `TradesPage.tsx`)

| # | تغییر |
|---|-------|
| ۱ | import: `+getFinanceAccounts` از `api/client` |
| ۲ | state جدید: `financeAccounts` |
| ۳ | `loadFilters`: دریافت `getFinanceAccounts()` در `Promise.all` و فیلتر `type !== 'prop'` در سمت کلاینت |
| ۴ | `manualTrade`: افزودن `finance_account_id: ''` (در state اولیه و در reset مودال) |
| ۵ | UI: `select` «حساب مالی» در همان ردیف «نسخه» (گزینه‌ی خالی: «— بدون حساب مالی —») |
| ۶ | `handleCreateManualTrade`: ارسال `finance_account_id` در صورت انتخاب |
| ۷ | اعتبارسنجی UX هم‌راستا با بک‌اند: برای `REAL` باید دقیقاً یکی از حساب مالی/مرحله‌ی پراپ انتخاب شود؛ برای Backtest و Forward هیچ‌کدام نباید انتخاب شود |

بک‌اند: **بدون تغییر** (endpoint `/api/trades/manual` از قبل این فیلد را می‌گیرد و ذخیره می‌کند).

---

## ۳. نتایج تست

| تست | نتیجه |
|-----|-------|
| `npx tsc -b --force` | ✅ Exit 0 |
| `npm run build` | ✅ Exit 0 |
| ساخت معامله دستی (`test_type=real`، `version_id=1`، `finance_account_id=1`) | ✅ `id=19` ساخته شد |
| خواندن مجدد معامله | ✅ `finance_account_id = 1` ذخیره شده بود |
| پاک‌سازی | ✅ معامله‌ی تستی حذف شد؛ دیتابیس به حالت قبل برگشت (`trades = 18`، بدون رکورد دارای `finance_account_id`) |

---

## ۴. نکات

- مقدار `Account.type` در پاسخ API با حروف کوچک است (`bank` / `broker` / `prop`)؛ فیلتر `type !== 'prop'` بر همین اساس است.
- select حساب مالی برای همه‌ی انواع تست نمایش داده می‌شود، اما فقط برای `REAL` قابل استفاده است (اعتبارسنجی UI و بک‌اند).
- فیلد حساب مالی اختیاری است.

---

## ۵. فایل‌های تغییر‌یافته

- `frontend/src/pages/TradesPage.tsx` (تنها فایل کد تغییریافته)
- `PHASE10_REPORT.md` (جدید)
