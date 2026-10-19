# PHASE 45 — Financial Ledger Integrity — گزارش پیاده‌سازی

> هدف فاز: **بستن دور زدن دفتر کل + یکپارچگی مالی**.
> مبنا: آنالیز خارجی باگ #۵ (هفت مورد: PATCH balance، cascade حذف، PATCH تراکنش حذف‌شده،
> نبود چک ارز، سه نسخهٔ `_to_currency`، برگشتِ منفی‌ساز، `running_balance` غلط).
> وضعیت: ✅ همهٔ تسک‌ها انجام شد · **۳۳۱ تست بک‌اند** · `ruff` سبز ·
> frontend (`tsc`/`vitest`/`build`) سبز · migration روی DB واقعی اعمال شد · commit **زده نشده**.

---

## ۱) خلاصهٔ اجرایی

| # | باگ | وضعیت | راه‌حل |
|---|---|---|---|
| ۴۵.۱ | `PATCH /accounts` فیلد `balance` را می‌پذیرفت (نقض «تنها نویسنده») | ✅ | `balance` از `AccountUpdate` حذف؛ موجودی اولیه در `POST` از مسیر `ADJUSTMENT` |
| ۴۵.۲ | تغییر ارز حسابِ دارای تراکنش | ✅ | چک تراکنش‌های سه‌گانه ⇒ `409` |
| ۴۵.۳ | `DELETE /accounts` سخت + cascade تراکنش طرف مقابل | ✅ | حذف نرم (`is_archived`) + حذف `cascade` از سه relationship + migration |
| ۴۵.۴ | `PATCH /transactions` بدون فیلتر حذف + نبود هم‌گامی TRANSFER | ✅ | فیلتر `is_deleted==False` + `account_id = to_account_id` + گارد مبدأ≠مقصد |
| ۴۵.۵ | `WalletService.post` بدون چک ارز | ✅ | چک ارز برای غیر-TRANSFER + گارد cross-currency در TRANSFER + endpoint `wallets/convert` |
| ۴۵.۶ | سه نسخهٔ `_to_currency` | ✅ | `app/utils/currency.py::to_currency` + جایگزینی در سه فایل |
| ۴۵.۷ | `reverse()` روی واریزِ خرج‌شده (موجودی منفی) | ✅ | چک بدهیِ برگشت ⇒ `WalletError` |
| ۴۵.۸ | `ledger.running_balance` با offset/date_from غلط | ✅ | موجودی آغازین (`_opening_balance`) + پنجره‌بُری نمایش |
| ۴۵.۹ | نبود endpoint مغایرت‌یابی | ✅ | `GET /accounts/{id}/reconcile` + هشدار 🟠 در UI |
| ۴۵.۱۰ | نبود تست Property | ✅ | `test_phase45_hypothesis.py` (Hypothesis) |

**پایه:** ۳۰۹ (پایان فاز ۴۴) → **۳۳۱ تست** (+۲۲).

---

## ۲) تسک‌ها

### ۴۵.۰ — بکاپ اولیه ✅
`C:\Backup\trading_desk.db.before_phase45` (۴۱۳٬۶۹۶ بایت).

### ۴۵.۱ — حذف `balance` از AccountUpdate ✅
- `AccountUpdate` دیگر `balance` ندارد (Pydantic آن را نادیده می‌گیرد ⇒ دور زدن ممکن نیست).
- `create_account`: ستون با `balance=0` ساخته می‌شود؛ اگر مقدار اولیه داده شود،
  `WalletService.post(type=ADJUSTMENT, description="موجودی اولیه")` ثبت می‌کند.
- نتیجه: از همان لحظهٔ ساخت، `reconcile.delta == 0`.

### ۴۵.۲ — تغییر ارز فقط بدون تراکنش ✅
- اگر حساب حتی یک تراکنش (account/from/to) داشته باشد ⇒ `409`.

### ۴۵.۳ — حذف نرم حساب + حذف cascade ✅
- مدل: `FinancialAccount.is_archived` (Boolean, indexed, server_default 0).
- حذف `cascade="all, delete-orphan"` از `entries` / `transactions_out` / `transactions_in`.
- Migration جدید `a45c0de1f2a3` (idempotent، افزودنی) — روی DB واقعی اعمال شد
  (`f39a1b2c3d4e → a45c0de1f2a3`).
- `DELETE /accounts/{id}`: فقط بدون تراکنش و با موجودی صفر ⇒ `is_archived=True`، وگرنه `409`.
- `GET /accounts`: حساب‌های آرشیوشده پنهان می‌شوند.

### ۴۵.۴ — PATCH تراکنش ✅
- فیلتر `is_deleted == False` (روی تراکنش حذف‌شده ⇒ `404`).
- برای `TRANSFER`: `account_id = to_account_id` و گارد `from != to`.

### ۴۵.۵ — چک ارز + تبدیل ✅
- `WalletService.post(..., allow_cross_currency=False)`:
  - غیر-TRANSFER: اگر ارز تراکنش با ارز حساب نخواند ⇒ `WalletError`.
  - TRANSFER دوطرفه: طرفین باید هم‌ارز باشند (مگر `allow_cross_currency`).
- endpoint جدید `POST /finance/wallets/convert` (دو تراکنش `ADJUSTMENT` خروج/ورود + کنترل موجودی مبدأ).

### ۴۵.۶ — یکی‌کردن `_to_currency` ✅
- `app/utils/currency.py::to_currency(value, default=None)`:
  `None → default` · `Currency → همان` · رشتهٔ معتبر (case-insensitive) · نامعتبر ⇒ اگر
  `default` باشد همان، وگرنه `ValueError`.
- جایگزینی در `wallet_service.py` (None-aware)، `payout_service.py` و `api/prop.py` (fallback USD).

### ۴۵.۷ — رد برگشتِ منفی‌ساز ✅
- `reverse(..., allow_overdraft=False)`: بدهیِ برگشت (منفیِ دلتاهای مثبت) بررسی می‌شود؛
  اگر موجودی کافی نباشد ⇒ `WalletError` («حذف این تراکنش موجودی را منفی می‌کند»).

### ۴۵.۸ — running_balance درست ✅
- `_opening_balance(db, account_id, before=date_from)` = مجموع اثر تراکنش‌های مؤثر قبل از بازه.
- `ledger` ابتدا کل بازه را پیمایش و running را از opening محاسبه می‌کند، سپس
  `offset/limit` را فقط روی خروجی اعمال می‌کند (پنجرهٔ نمایش).

### ۴۵.۹ — endpoint مغایرت‌یابی ✅
- `GET /finance/accounts/{id}/reconcile` → `WalletService.reconcile`.
- UI: در تب حساب‌ها، آیکن 🟠 + tooltip وقتی `delta != 0`؛ خطای حذف (۴۰۹) هم با toast نمایش داده می‌شود.

### ۴۵.۱۰ — تست Hypothesis ✅
- `hypothesis` به `requirements.txt` اضافه و نصب شد.
- `test_random_operations_keep_balance_consistent`: دنبالهٔ تصادفی (۱۰–۶۰ عملیات) روی ۳ حساب؛
  در پایان برای هر حساب `reconcile.delta == 0`.

---

## ۳) تست‌ها

| فایل | تعداد | پوشش |
|---|---|---|
| `tests/test_phase45_ledger_integrity.py` | ۲۰ | ۴۵.۱ تا ۴۵.۹ (balance/cascade/currency/convert/reverse/ledger/reconcile) |
| `tests/test_phase45_hypothesis.py` | ۱ | Property: دنبالهٔ تصادفی ⇒ تراز همیشگی |
| `tests/test_finance.py` | (به‌روزرسانی) | `test_money_flow` (ارز exchange → IRR) |
| `tests/test_phase38_personal_finance.py` | (به‌روزرسانی) | موجودی اولیه حالا ADJUSTMENT هم می‌سازد |
| **جمع جدید** | **۲۱** | |
| **کل بک‌اند** | **۳۳۱ passed** (۱۶٫۹s) | `ruff check app tests` → All checks passed |
| **فرانت‌اند** | ۹ vitest · tsc/build ✅ | |

---

## ۴) فایل‌های تغییر‌یافته

**کد جدید:** `backend/app/utils/currency.py` · `backend/migrations/versions/a45c0de1f2a3_phase45_accounts_is_archived.py`
**کد ویرایش‌شده:** `backend/app/api/finance.py` · `backend/app/api/prop.py` ·
`backend/app/models/finance.py` · `backend/app/services/wallet_service.py` ·
`backend/app/services/payout_service.py` · `backend/requirements.txt`
**تست جدید:** `test_phase45_ledger_integrity.py` · `test_phase45_hypothesis.py`
**تست ویرایش‌شده:** `test_finance.py` · `test_phase38_personal_finance.py`
**فرانت‌اند:** `src/api/client.ts` · `src/pages/FinancePage.tsx`
**مستند:** `PHASE45_IMPL_REPORT.md` · اعمال migration روی DB واقعی (`a45c0de1f2a3` = head)

---

## ۵) کشف‌ها

- **ناسازگاری دادهٔ تستی، واقعی بود:** `test_money_flow` یک برداشت IRR روی حساب USD ثبت
  می‌کرد — دقیقاً همان باگ #۵. با چک ارز، این حالت حالا رد می‌شود و تست به دادهٔ درست
  (حساب IRR) منتقل شد.
- **موجودی اولیه، منبع اصلی drift بود:** با مسیر جدید `ADJUSTMENT`، حساب‌ها از ابتدا ترازند.
  حساب‌های قدیمی موجود در DB واقعی ممکن است `delta != 0` داشته باشند و اکنون در UI با 🟠
  دیده می‌شوند (رفتار مطلوب — قابل شناسایی و اصلاح).
- **حذف cascade خطرناک بود:** با `cascade=all,delete-orphan` حذف یک حساب، تراکنش‌های انتقالِ
  طرف مقابل را هم پاک می‌کرد ⇒ دفتر طرف مقابل ناقص می‌شد. حذف cascade + آرشیو، این را می‌بندد.

---

## ۶) آماده برای Phase 46

- `FinancialAccount.balance` اکنون واقعاً فقط از `WalletService` تغییر می‌کند (مسیر ورودی بسته شد).
- دفتر کل تراز است و ابزار مغایرت‌یابی (API + UI) برای حساب‌های قدیمی در دسترس است.
- تبدیل ارز مسیر رسمی (`/wallets/convert`) دارد و انتقال بین‌ارزی رد می‌شود.
- تست Property تضمین می‌کند هر تغییر آینده در WalletService، تراز را نشکند.

## ۷) گام Git

```
git status        → 10 فایل تغییر‌یافته + 4 فایل جدید (currency.py، migration، 2 تست) + PHASE45_IMPL_REPORT.md
git log --oneline -3 → b02238b (HEAD) Phase 44 ...
```

⛔ **commit زده نشده — منتظر تأیید کاربر.**

