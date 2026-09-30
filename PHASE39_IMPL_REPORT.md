# 💰 PHASE 39 — Fix Financial Bugs + Screenshot · IMPLEMENTATION REPORT

> **وضعیت:** ✅ کامل (۳۹.۱ + ۳۹.۲ + ۳۹.۳ + ۳۹.۴)
> **تاریخ:** ۱۴۰۵/۰۷/۰۹
> **پایه:** `HEAD = 78d8e4e` (Phase 38.5 — push شده)
> **خروجی تست:** `232 passed · ۰ failed` (EXIT=0) · `tsc EXIT=0` · `vitest 9 passed` · `build EXIT=0`
> **Migration:** `f39a1b2c3d4e` (head جدید — قبلی: `c9d0e1f2a3b4`)
> **commit:** ⛔ **زده نشد** (کاربر صبح push می‌کند)

---

## ۱. خلاصهٔ اجرایی

فاز ۳۹ سه بدهی بحرانی مالی/داده‌ای را بست: **G1** (تراکنش‌ها موجودی را تغییر نمی‌دادند ⇒ دو منبع
حقیقت)، **G6** (باگ `spendable-assets`: سبد تراست‌ولت از نوع اشتباه پر می‌شد و `total.irr` هاردکد بود)،
**G9** (بدون محافظ موجودی) و **G11** (حذف تراکنش موجودی را برنمی‌گرداند) — به‌همراه رفع
**«Screenshot دوگانه»**.

معماری حاصل: **یک نقطهٔ واحد** برای تغییر `FinancialAccount.balance` و **یک نقطهٔ واحد** برای ساخت
`FinancialTransaction` (`WalletService`)؛ ۸ فراخوانی پراکندهٔ قبلی (در `payout_service` و `prop.py`)
به آن مهاجرت کردند. `Trade.screenshot_path` (ستون مرده — هیچ‌گاه خوانده/نشده) حذف شد تا تنها منبع
اسکرین‌شات، جدول `screenshots` باشد.

**هیچ‌کدام از موارد درخواستی Skip انجام نشد:** FX، کارمزد، `Numeric`، دفتر دوطرفه،
endpointهای کیف‌پول و Reconciliation همه خارج از دامنه ماندند (فقط `reconcile()`/`ledger()` به‌عنوان
متدهای داخلی ساخته شدند و تست دارند، ولی endpoint عمومی ندارند).

| متریک | قبل | بعد |
|:---|:---:|:---:|
| تست‌های backend | ۱۹۲ | **۲۳۲** (+۴۰) |
| نقاط نویسندهٔ `balance` | ۵ پراکنده | **۱** (`wallet_service.py`) |
| نقاط ساخت `FinancialTransaction` | ۵ | **۱** (`wallet_service.py`) |
| منبع حقیقت اسکرین‌شات | ۲ | **۱** |
| باگ‌های باز G1/G6/G9/G11 | ۴ | **۰** |

---

## ۲. زیرفازها

### ۳۹.۱ — `WalletService` (رفع G1، G9، G11)

**فایل جدید:** `backend/app/services/wallet_service.py` (۴۹۵ خط)

قرارداد جهت‌دار (`BALANCE_DIRECTION`):

| نوع | اثر |
|:---|:---|
| `DEPOSIT` / `PROFIT` | `account_id` **+** |
| `WITHDRAWAL` / `LOSS` / `FEE` / `PURCHASE` | `account_id` **−** |
| `TRANSFER` (دوطرفه) | `from_account_id` **−** · `to_account_id` **+** · `account_id` = مقصد |
| `TRANSFER` (یک‌طرفه) | ثبت می‌شود، **بدون اثر** روی موجودی (تبدیل بیرون از نرم‌افزار) |
| `ADJUSTMENT` | `account_id` **±** (علامت از `amount` یا `signed_amount`) |

**متدها:** `post()` · `reverse()` · `reconcile()` · `ledger()` · `validate_amount()`
**خطا:** `WalletError(ValueError)` با پیام فارسی (سازگار با `except ValueError` موجود ⇒ `400`).

**قوانین پیاده‌شده:**
- `post()` همیشه `db.flush()` می‌زند ⇒ `tx.id` بلافاصله در دسترس (نیاز `_post_income` فاز ۳۳)
- اعتبارسنجی **قبل از** `db.add` ⇒ هیچ حالت جزئی باقی نمی‌ماند
- `amount > 0` برای همهٔ انواع به‌جز `ADJUSTMENT`
- `TRANSFER` دوطرفه: `from != to`
- `allow_overdraft=False` (پیش‌فرض) ⇒ پیام `«موجودی کیف‌پول «X» کافی نیست (موجودی: …، مورد نیاز: …)»`
- `reverse()` idempotent + `is_deleted = True`
- `ADJUSTMENT` از محافظ موجودی **مستثنا** است (اصلاح دستی آگاهانه)

**مهاجرت ۸ فراخوانی:**
| فایل | تابع | اقدام |
|:---|:---|:---|
| `api/finance.py:319` | `create_transaction` | `WalletService.post` (`allow_overdraft=True`) |
| `api/finance.py:347` | `update_transaction` | برگشت اثر → تغییر → اعمال مجدد (+`validate_amount`) |
| `api/finance.py:369` | `delete_transaction` | `WalletService.reverse` |
| `services/payout_service.py:187` | `_post_income` | `WalletService.post(PROFIT, commit=False)` |
| `services/payout_service.py:246` | `record_transfer` | `WalletService.post(TRANSFER)`, سختگیر |
| `services/payout_service.py:302` | `update` | برگشت + اعمال مجدد روی **همان ردیف** |
| `services/payout_service.py:335` | `delete_and_reverse` | `WalletService.reverse(commit=False)` |
| `api/prop.py:1150` | `create_cost` | `WalletService.post(PURCHASE)`, سختگیر |

### ۳۹.۲ — رفع G6 + مهاجرت برداشت بروکر

**الف) `GET /finance/spendable-assets` — سه باگ رفع شد:**

| # | باگ | قبل | بعد |
|:--|:---|:---|:---|
| ۱ | سبد `trust_wallet` از نوع **اشتباه** | `_balance_sum(CRYPTO_WALLET)` | `_balance_sum(TRUST_WALLET)` |
| ۲ | `crypto_wallet`/`card`/`cash` **غایب** | — | ۳ سبد جدید |
| ۳ | `total.irr` **هاردکد** = سبد `bank` | `"irr": bank` | `Σ` موجودی همهٔ کیف‌پول‌های IRR (`_balance_sum_currency` جدید) |

> **تأثیر واقعی:** کیف‌پول `trust_wallet` (مقصد اصلی برداشت پراپ) در «دارایی قابل برداشت»
> **صفر** دیده می‌شد. ✅ هر ۷ کلید قدیمی حفظ شد؛ فقط ۳ کلید افزوده شد.

**ب) مهاجرت `/finance/withdrawals` (برداشت بروکر) — گزینهٔ الف تأییدشدهٔ کاربر:**
| هندلر | قبل | بعد |
|:---|:---|:---|
| `POST` | ساخت مستقیم، **بدون اثر روی موجودی** | `WalletService.post(WITHDRAWAL, allow_overdraft=True)` |
| `PUT/PATCH` | `setattr` — **بدون اثر** | برگشت → تغییر → اعمال مجدد |
| `DELETE` | `is_deleted=True` — **بدون برگشت** | `WalletService.reverse` |

> فرانت‌اند فقط `GET /finance/withdrawals/stats` را صدا می‌زند (تب بروکر در فاز ۳۸.۵ حذف شد)
> ⇒ مهاجرت **صفر ریسک رگرسیون UI** دارد ولی قرارداد مالی را اصلاح می‌کند.

### ۳۹.۳ — رفع «Screenshot دوگانه»

| مورد | نتیجه |
|:---|:---|
| `Trade.screenshot_path` | 🗑️ حذف از مدل + `DROP COLUMN` |
| `api/trades.py` | ✅ **بدون تغییر** — از قبل فقط از جدول `screenshots` می‌خواند |
| Frontend | ✅ **بدون تغییر** — صفر ارجاع |
| نوع ستون | **ستون مرده** — در هیچ کد runtime خوانده/نوشته نمی‌شد |

> جزئیات کامل در `PHASE39_3_SCREENSHOT_FIX.md`.

### ۳۹.۴ — تست نهایی

| بررسی | نتیجه |
|:---|:---|
| `pytest` (کل) | **۲۳۲ passed · ۰ failed** (EXIT=0) |
| `npx tsc -b --force` | **EXIT=0** |
| `npx vitest run` | **EXIT=0** — ۹ passed |
| `npm run build` | **EXIT=0** — `built in 8.21s` |
| `alembic current` | `f39a1b2c3d4e (head)` |
| `alembic heads` | `f39a1b2c3d4e` |


---

## ۳. دستاوردها

### ۳.۱ معماری تمیز — «یک نویسنده»

تأیید نهایی با grep روی `app/api` + `app/services`:

```text
۱) نویسندهٔ balance:
   wallet_service.py:216        ← فقط ۱ نتیجه

۲) ساخت FinancialTransaction:
   wallet_service.py:322        ← فقط ۱ نتیجه (broker.py:6 فقط docstring است)

۳) screenshot_path در app/ + frontend/src/:
   (خالی)                       ← صفر نتیجه
```

### ۳.۲ باگ‌های رفع‌شده

| # | باگ | شرح | گواه |
|:--|:---|:---|:---|
| **G1** | دو منبع حقیقت موجودی | `POST/PATCH/DELETE /finance/transactions` و `/finance/withdrawals` هیچ اثری روی `balance` نداشتند | ۸ تست API |
| **G6** | باگ `spendable-assets` | سبد `trust_wallet` از `CRYPTO_WALLET` پر می‌شد؛ `card`/`cash`/`crypto_wallet` غایب؛ `total.irr` هاردکد | `test_spendable_assets_trust_wallet` · `test_spendable_assets_irr_total` |
| **G9** | بدون محافظ موجودی | برداشت/خرید بیش از موجودی بی‌صدا منفی می‌شد | `test_overdraft_blocked` · `test_prop_cost_overdraft_blocked` |
| **G11** | حذف تراکنش اثر را برنمی‌گرداند | `delete_transaction` فقط `is_deleted=True` می‌کرد | `test_api_delete_transaction_reverses_balance` · `test_reverse_restores_balance` |
| **Screenshot** | دو منبع حقیقت | `Trade.screenshot_path` (مرده) + جدول `screenshots` | `test_screenshot_path_removed` |

### ۳.۳ تست‌ها — ۴۰ تست جدید

| فایل | تعداد | خطوط |
|:---|:---:|:---:|
| `backend/tests/test_phase39_wallet.py` | **۳۴** | ۷۰۳ |
| `backend/tests/test_phase39_screenshot.py` | **۶** | ۱۴۹ |

**۸ تست نام‌برده‌شده در اسپک زیرفاز ۳۹.۱ — همه موجود:**
`test_post_deposit_increases_balance` · `test_post_withdrawal_decreases_balance` ·
`test_post_transfer_moves_both` · `test_transfer_same_account_rejected` · `test_overdraft_blocked` ·
`test_adjustment_signed` · `test_reverse_restores_balance` · `test_payout_still_works` (رگرسیون فاز ۳۳)

**پوشش‌های کلیدی:** محافظ موجودی · rollback · `reconcile` (۴) · `ledger` · نرخ/جهت انتقال ·
`allow_overdraft` · مهاجرت ۶ endpoint (`POST`/`PATCH`/`DELETE` × `transactions`/`withdrawals`) ·
رگرسیون برداشت پراپ (فاز ۳۳) · رگرسیون خرید پراپ (فاز ۵/۳۸) · `money-cycle` جدید ·
سازگاری کلیدهای `spendable-assets` · جداسازی اسکرین‌شات بین معاملات

### ۳.۴ ⚠️ تغییرات در ۲ تست موجود (هر دو تأییدشده توسط کاربر)

| فایل | تغییر | دلیل |
|:---|:---|:---|
| `tests/test_finance.py::test_money_cycle` | `current_balance` ۳۰۰۰ → **۶۰۰۰** | مقدار قبلی فقط چون هیچ تراکنشی موجودی را تغییر نمی‌داد درست بود = خودِ باگ G1 |
| `tests/test_finance.py::test_spendable_assets` | `trust_wallet` ۱۰۰ → **۰** + افزودن `crypto_wallet == 100` | تست قبلی باگ G6 را قفل می‌کرد |

---

## ۴. فایل‌های تغییر یافته

### فایل‌های جدید (۵)
| فایل | خطوط |
|:---|:---:|
| `backend/app/services/wallet_service.py` | ۴۹۵ |
| `backend/tests/test_phase39_wallet.py` | ۷۰۳ |
| `backend/tests/test_phase39_screenshot.py` | ۱۴۹ |
| `backend/migrations/versions/f39a1b2c3d4e_phase39_drop_trade_screenshot_path.py` | ۵۲ |
| `PHASE39_3_SCREENSHOT_FIX.md` + `PHASE39_IMPL_REPORT.md` | اسناد |

### فایل‌های ویرایش‌شده (۵) — `+193 / −92`
```text
 backend/app/api/finance.py             | 160 +++++++++++++++++++++++++--------
 backend/app/api/prop.py                |  38 ++++----
 backend/app/models/strategy.py         |   5 +-
 backend/app/services/payout_service.py |  70 ++++++--------
 backend/tests/test_finance.py          |  12 ++-
```

**✅ صفر تغییر در فرانت‌اند** (`frontend/src/**` دست‌نخورده).

---

## ۵. Migration

**یگانه migration فاز ۳۹:** `f39a1b2c3d4e_phase39_drop_trade_screenshot_path.py`
```python
revision      = "f39a1b2c3d4e"
down_revision = "c9d0e1f2a3b4"   # head قبلی (phase36 indexes)
```
- فقط `op.drop_column("trades", "screenshot_path")` — idempotent (`inspect`-محور، الگوی فاز ۳۸.۵)
- `downgrade()` ستون nullable را بازمی‌گرداند

**اعتبارسنجی تجربی (۴ سناریو):**
| سناریو | نتیجه |
|:---|:---|
| DB خالی (زنجیرهٔ کامل ۱۷ migration) | ✅ `f39a1b2c3d4e` · ستون حذف · **۸ ایندکس سالم** |
| اجرای دوباره (idempotency) | ✅ بدون خطا |
| DB موجود (کپی از DB واقعی، از `c9d0e1f2a3b4`) | ✅ upgrade افزایشی · ستون حذف · ایندکس‌ها سالم |
| `downgrade -1` سپس `upgrade head` | ✅ برگشت‌پذیر |

> **DB واقعی (`backend/trading_desk.db`):** در حال حاضر روی `f39a1b2c3d4e (head)` است
> (migration اعمال شده) و `screenshot_path` ندارد. محتوای آن **صفر رکورد** در
> `trades`/`screenshots`/`accounts`/`transactions` است ⇒ صفر ریسک داده.
> علت اعمال خودکار: `main.py:118` هنگام بالا آمدن برنامه `alembic upgrade head` می‌زند
> و این هوک در اجرای تست‌ها هم فعال می‌شود (رفتار pre-existing — پایین‌تر به‌عنوان بدهی ثبت شد).


---

## ۶. بدهی‌های باقی‌مانده (ثبت‌شده — خارج از دامنهٔ تأییدشده)

| # | مورد | شدت | یادداشت |
|:--|:---|:---:|:---|
| ۱ | **`pytest` فایل `backend/trading_desk.db` واقعی را migrate می‌کند** | 🟠 | `conftest.py` ماژول `app.main` را import می‌کند و هوک startup آن `alembic upgrade head` را روی DB **واقعی** اجرا می‌کند (نه DB تست). pre-existing از قبل از فاز ۳۹. پیشنهاد: در تست‌ها هوک را no-op کنید یا `DATABASE_URL` را override کنید. |
| ۲ | سبدهای per-type در `spendable-assets` **ارز-ناشناس** هستند (`bank` همهٔ ارزها را جمع می‌زند) در حالی که `total` ارز-دقیق است | 🟡 | pre-existing؛ رفع کامل = تفکیک `bank_irr`/`bank_usd` (تغییر قرارداد فرانت) |
| ۳ | `WalletService.reconcile()` و `ledger()` ساخته و تست شده‌اند ولی **endpoint عمومی ندارند** | 🟢 | طبق دستور ۳۹.۱ (۵ endpoint کیف‌پول skip). هر زمان لازم شد فقط لایهٔ API لازم است. ⇒ ابزار تشخیص drift موجود است. |
| ۴ | `Screenshot` **FK واقعی** به `trades` ندارد (polymorphic: `entity_type`+`entity_id`) | 🟡 | عمدی (پشتیبانی `trade`+`review`)، ولی حذف معامله اسکرین‌شات‌هایش را cascade پاک نمی‌کند ⇒ فایل یتیم |
| ۵ | `POST /api/trades/{id}/screenshots` فایل را قبل از commit دیتابیس روی دیسک می‌نویسد | 🟢 | در صورت خطای DB، فایل باقی می‌ماند (pre-existing، ریسک کم) |
| ۶ | `/finance/withdrawals` از `allow_overdraft=True` استفاده می‌کند | 🟢 | مطابق اصل تأییدشدهٔ #۳ (مسیر دستی/انعطاف‌پذیر). در صورت تصمیم برای سختگیری، یک خط تغییر + یک تست. |
| ۷ | اسناد تاریخی هنوز `screenshot_path` را در جدول `Trade` لیست می‌کنند (`FINAL_BLUEPRINT.md:579`, `BASELINE_REPORT.md:154/165/232/245/539`, `MokTradeDesk-*.md`) | 🟢 | مستندات تاریخی — بازنویسی نشدند |
| ۸ | ستون حذف‌شده در migration اولیهٔ `c4838cd01bbd` باقی است | 🟢 | الگوی استاندارد Alembic (migrationهای تاریخی دست‌نخورده می‌مانند) |
| ۹ | FX (`counter_*`/`fx_rate`)، کارمزد (`fee_*`)، `Float→Numeric`، دفتر دوطرفه | — | طبق دستور صریح **skip** شدند. `PLAN_PHASE39.md` گزینهٔ C این‌ها را برای فاز ۴۰ پیش‌بینی کرده بود. |

---

## ۷. گام بعدی پیشنهادی

| اولویت | پیشنهاد | تخمین |
|:---:|:---|:---:|
| 🔴 P0 | **رفع بدهی #۱** — جلوگیری از migrate شدن DB واقعی در تست‌ها (override کردن `DATABASE_URL` در `conftest.py` یا غیرفعال کردن هوک startup در تست) | ۳۰ دقیقه |
| 🟠 P1 | **بازیابی drift موجودی موجود** — استفاده از `WalletService.reconcile()` روی کیف‌پول‌های واقعی و اصلاح با `ADJUSTMENT` (در صورت وجود داده) | ۱ ساعت |
| 🟠 P1 | **نمای «کیف‌پول‌ها» در فرانت + `AccountForm`** — نمایش `stored`/`ledger`/`delta` و ثبت «موجودی اولیه» به‌صورت `ADJUSTMENT` (رفع کامل G1 در UI) | ۳ ساعت |
| 🟡 P2 | **افزودن endpointهای `reconcile` و `ledger`** (کد آماده است) | ۱ ساعت |
| 🟡 P2 | **تفکیک ارزی سبدهای `spendable-assets`** (بدهی #۲) | ۲ ساعت |
| 🟢 P3 | **Phase 40 (گزینهٔ C پلن):** `Float → Numeric(18,2)` با `TypeDecorator` + دفتر دوطرفه + FX/کارمزد | ۱۲–۲۰ ساعت |
| 🟢 P3 | **Cascade اسکرین‌شات‌ها** هنگام حذف معامله (بدهی #۴) | ۲ ساعت |

---

## ۸. تأیید نهایی — چک‌لیست

```text
[✅] pytest (کل مجموعه) ................. 232 passed · 0 failed (EXIT=0)
[✅] npx tsc -b --force ................. EXIT=0
[✅] npx vitest run ..................... EXIT=0 (9 passed)
[✅] npm run build ...................... EXIT=0
[✅] alembic heads ...................... f39a1b2c3d4e
[✅] alembic current .................... f39a1b2c3d4e (head)
[✅] writer of balance .................. فقط wallet_service.py:216
[✅] constructor of FinancialTransaction  فقط wallet_service.py:322
[✅] screenshot_path در app+frontend/src  صفر نتیجه
[✅] frontend/src تغییر نکرده ............ صفر فایل
[⛔] commit ............................. زده نشد (منتظر کاربر)
```

---

## ۹. وضعیت Git (بدون commit)

```text
HEAD -> main = 78d8e4e (Phase 38.5)   ← origin/main هم همین

 M backend/app/api/finance.py
 M backend/app/api/prop.py
 M backend/app/models/strategy.py
 M backend/app/services/payout_service.py
 M backend/tests/test_finance.py
?? PLAN_PHASE39.md
?? PHASE39_3_SCREENSHOT_FIX.md
?? PHASE39_IMPL_REPORT.md
?? backend/app/services/wallet_service.py
?? backend/migrations/versions/f39a1b2c3d4e_phase39_drop_trade_screenshot_path.py
?? backend/tests/test_phase39_screenshot.py
?? backend/tests/test_phase39_wallet.py

5 files changed, 193 insertions(+), 92 deletions(-)
```

**پیام commit پیشنهادی:**
```text
Phase 39: WalletService (single balance writer) + G1/G6/G9/G11 fixes + drop legacy Trade.screenshot_path
```

---

## ⛔ پایان Phase 39 — commit نزده شد؛ کاربر صبح push می‌کند.

