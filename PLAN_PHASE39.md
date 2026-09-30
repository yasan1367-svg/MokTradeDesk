# 📋 PLAN_PHASE39.md — Phase 39: Wallet & Money Flow

> **نوع سند:** Plan + نتیجهٔ آدیت کد واقعی (این سند **پیش از** شروع اجرا نوشته شده است)
> **تاریخ:** ۱۴۰۵/۰۷/۰۹
> **پایه:** `HEAD = 78d8e4e` (Phase 38.5 — push شده)
> **پیش‌نیاز:** `PHASE38_IMPL_REPORT.md`, `PHASE38_AUDIT.md`, `PHASE22_REPORT.md`, `PLAN_PHASE37.md`
> **وضعیت:** ⛔ **اجرا نشده** — منتظر قفل‌کردن دامنه (بخش ۴)
> **یادداشت:** بخش «📋 هدف Phase 39» در درخواست کاربر **خالی/بریده** رسید؛ بنابراین دامنه بر پایهٔ
> آدیت کد + عنوان فاز + بدهی‌های صریح مستندشدهٔ فاز ۳۸ استخراج شده است.

---

## ۱. خلاصهٔ اجرایی

| محور | وضعیت فعلی | هدف فاز ۳۹ |
|:---|:---|:---|
| «کیف‌پول» | `FinancialAccount` (`accounts`) با `balance` ذخیره‌شدهٔ `Float` | یک **نویسندهٔ واحد** برای موجودی (`WalletService`) |
| «دفتر» | `FinancialTransaction` **تک‌سطری** (single-entry) با `account_id` اجباری | همان جدول + اثر جهت‌دار مستند و قابل ماشین‌خوان |
| تبدیل ارز | **غیرقابل مدل‌سازی** (یک `amount` + یک `currency`) | ستون‌های `counter_amount` / `counter_currency` / `fx_rate` |
| کارمزد انتقال | فیلد ندارد (`FEE` = ردیف دوم دستی) | `fee_amount` / `fee_currency` |
| گزارش جریان پول | فقط **نوع** حساب (`bank`/`exchange`)، بدون id/name | افزودن id/name + حفظ کلیدهای فعلی |
| `spendable-assets` | 🔴 **باگ**: `trust_wallet` از `CRYPTO_WALLET` پر می‌شود؛ `CARD`/`CASH` غایب؛ `total.irr` هاردکد | رفع کامل + تفکیک بر پایهٔ ارز |
| API کیف‌پول‌محور | وجود ندارد | `/wallets`، `/wallets/{id}/ledger`، `/wallets/{id}/reconciliation`، `/wallets/summary`، `/wallets/{id}/adjust` |
| جدول جدید | — | ❌ **لازم نیست** (گزینهٔ B متعادل) |
| Migration | head = `c9d0e1f2a3b4` | ✅ ۱ فایل افزودنی (فقط `add_column` nullable) |

**قرارداد طلایی این فاز:** هر تغییری در `FinancialAccount.balance` **فقط** از مسیر `WalletService`
انجام می‌شود. هیچ‌جای دیگری `balance` مستقیماً دست‌کاری نمی‌شود.

---

## ۲. وضعیت فعلی (As-Is Audit) — با شاهد کد

### ۲.۱ موجودیت‌ها
| موجودیت | محل | وضعیت |
|:---|:---|:---|
| `FinancialAccount` (`__tablename__="accounts"`) | `app/models/finance.py:60-97` | ✅ `balance=Float`، `card_number`، ۳ relationship (`entries`/`transactions_out`/`transactions_in`) |
| `FinancialTransaction` (`__tablename__="transactions"`) | `app/models/finance.py:115-147` | ⚠️ `account_id` **NOT NULL** + `from_account_id`/`to_account_id` اختیاری |
| `Category` | `app/models/finance.py:100-112` | ✅ `CategoryType` (INCOME/EXPENSE/TRANSFER/CONVERSION) |
| `PropWithdrawal` | `app/models/prop.py:189-218` | ✅ `destination_account_id` + `transaction_id` (idempotency فاز ۳۳) |

### ۲.۲ Enumها
```python
class AccountType(str, enum.Enum):      # models/finance.py:14-29
    BANK = "bank"; EXCHANGE = "exchange"; CRYPTO_WALLET = "crypto_wallet"
    CARD = "card"; CASH = "cash"; TRUST_WALLET = "trust_wallet"

class Currency(str, enum.Enum):         # models/finance.py:32-34
    IRR = "IRR"; USD = "USD"

class TransactionType(str, enum.Enum):  # models/finance.py:45-54
    DEPOSIT; WITHDRAWAL; PROFIT; LOSS; FEE; PURCHASE; TRANSFER; ADJUSTMENT
```
> قرارداد ذخیره‌سازی پروژه: **NAME** ذخیره می‌شود (`Enum(Currency)` ⇒ `'USD'`/`'IRR'` چون NAME == value).
> تنها استثنا: `PropCost.cost_type` با `values_callable=_enum_values` (lowercase) — `models/prop.py:46-48`.

### ۲.۳ Endpointهای موجود مرتبط با جریان پول
| Endpoint | خط | خروجی |
|:---|:---|:---|
| `GET /finance/summary` | `api/finance.py:355` | `assets_by_currency`, `total_income/expense/transfers`, `transaction_count` |
| `GET /finance/accounts/{id}/stats` | `api/finance.py:404` | موجودی + درآمد/هزینه + آخرین تراکنش |
| `GET /finance/spendable-assets` | `api/finance.py:1203` | `prop_stage_3`/`broker`/`exchange`/`trust_wallet`/`bank` + `total` |
| `GET /finance/money-flow` | `api/finance.py:1250` | `{flows:[{from,to,amount,currency,type,date}]}` — `from`/`to` = **نوع** حساب |
| `GET /finance/money-cycle` | `api/finance.py:1335` | `total_deposits/withdrawals/exchanges/transfers` + `current_balance` |
| `GET /finance/asset-trend` | `api/finance.py:1427` | روند تجمعی USD/IRR روزانه |
| `GET /finance/exchange-rates` | `api/finance.py:1476` | نرخ **ضمنی** IRR→USD (ΣIRR/ΣUSD همان روز) |
| `POST /finance/sync/trades` | `api/finance.py:455` | ⚠️ **no-op** — `FinanceSyncService` از فاز ۲۸ غیرفعال است (`services/finance_sync_service.py:20-28`) |

### ۲.۴ چه کسی `balance` را تغییر می‌دهد؟ (تنها ۵ نقطه — همه خارج از یک سرویس مشترک)
```
services/payout_service.py:200   dest.balance = (dest.balance or 0.0) + amount     # _post_income (RECEIVED)
services/payout_service.py:258   src.balance  = (src.balance  or 0.0) - amount     # record_transfer
services/payout_service.py:259   dst.balance  = (dst.balance  or 0.0) + amount     # record_transfer
services/payout_service.py:313   dest.balance = (dest.balance or 0.0) + delta      # update
services/payout_service.py:338   dest.balance = (dest.balance or 0.0) - amount     # delete_and_reverse
api/prop.py:1162                 payer.balance = (payer.balance or 0.0) - cost.amount  # create_cost
```


---

## ۳. شکاف‌های شناسایی‌شده (Gap Analysis) — ۱۲ مورد

| # | شکاف | شاهد کد | شدت |
|:--|:---|:---|:---:|
| **G1** | **دو منبع حقیقت برای موجودی** — `POST/PATCH/DELETE /finance/transactions` **هیچ اثری روی `balance` ندارند** در حالی که مسیرهای پراپ اثر دارند ⇒ drift اجتناب‌ناپذیر. 또한 `POST /finance/accounts` مقدار `balance` را به‌عنوان «موجودی افتتاحیه» می‌پذیرد **بدون** تراکنش متناظر. | `api/finance.py:315-349`, `:151-162` | 🔴 |
| **G2** | **تک‌سطری بودن دفتر** — `TRANSFER` فقط **یک ردیف** با `account_id = مقصد` می‌سازد؛ کوئری «همهٔ اثرات روی کیف‌پول X» نیازمند union سه relationship جداست (`entries` ∪ `transactions_out` ∪ `transactions_in`). | `models/finance.py:80-97`, `:142-144`; `payout_service.py:243-254` | 🟠 |
| **G3** | **تبدیل ارز غیرقابل مدل‌سازی** — انتقال/تبدیل بین کیف‌پول IRR و USD فقط **یک** `amount` + یک `currency` دارد ⇒ مبلغ سمت مقابل و نرخ گم می‌شود. `/exchange-rates` نرخ را **ضمنی** از نسبت ΣIRR/ΣUSD همان روز حدس می‌زند (محدودیت مستندشده). | `api/finance.py:1476-1509`; `PHASE22_REPORT.md:116,139` | 🔴 |
| **G4** | **کارمزد انتقال/تبدیل وجود ندارد** — `TransactionType.FEE` هست ولی برای «انتقال + کارمزد» باید ردیف دوم دستی ساخت. | `models/finance.py:50` | 🟡 |
| **G5** | **هویت کیف‌پول در گزارش گم است** — `/money-flow` فقط **نوع** حساب را برمی‌گرداند (`from="bank"`)، نه id/name ⇒ فرانت نمی‌تواند بگوید «کدام صرافی». | `api/finance.py:1279-1286`; `frontend/src/api/client.ts:655-658`; `FinancePage.tsx:1173` | 🟠 |
| **G6** | 🔴 **باگ واقعی `spendable-assets`** — (الف) سبد `trust_wallet` از `AccountType.CRYPTO_WALLET` پر می‌شود (فاز ۳۸ `TRUST_WALLET` را اضافه کرد ولی این endpoint آپدیت نشد)؛ (ب) `CARD`/`CASH`/`CRYPTO_WALLET` کلاً در خروجی نیستند؛ (ج) `total.irr` هاردکد = سبد `bank` ⇒ IRRهای صرافی/نقد/کارت از جمع IRR حذف می‌شوند. | `api/finance.py:1213-1224` | 🔴 |
| **G7** | **بدون endpoint کیف‌پول‌محور** — نه لیست کیف‌پول با موجودی دفتری، نه صورت حساب، نه مغایرت‌یابی. | — | 🟠 |
| **G8** | **دقت پول = `Float`** — همهٔ ستون‌های مالی `Float` و `round(x, 2)` پراکنده در ~۳۰ نقطه. | `models/finance.py:75,129`; `api/finance.py:869-878` | 🟡 |
| **G9** | **بدون محافظ موجودی (overdraft)** — `src.balance` می‌تواند بی‌صدا منفی شود؛ هیچ سیاستی وجود ندارد. | `payout_service.py:258` | 🟠 |
| **G10** | **ابهام معنایی `TRANSFER`** — هم «زنجیرهٔ انتقال پراپ» (`Prop → Trust → Exchange → IRR → Bank Card`) و هم «تبدیل ارز» با یک مقدار enum ثبت می‌شوند؛ `/exchange-rates` هر `TRANSFER` را تبدیل فرض می‌کند. | `api/finance.py:1487`; `payout_service.py:250` | 🟡 |
| **G11** | **حذف تراکنش، موجودی را برنمی‌گرداند** — `delete_transaction` فقط `is_deleted=True` می‌کند. (در مقابل، `PayoutService.delete_and_reverse` درست عمل می‌کند ⇒ رفتار ناهمگون.) | `api/finance.py:341-349` vs `payout_service.py:330-344` | 🔴 |
| **G12** | **بدون idempotency/audit برای تغییر موجودی** — فقط `PropWithdrawal.transaction_id` وجود دارد؛ انتقال‌ها کلید idempotency ندارند. | `models/prop.py:213` | 🟡 |

### ۳.۱ جمع‌بندی شدت
```
🔴 بحرانی (۴): G1، G3، G6، G11      → در گزینهٔ B همه رفع می‌شوند
🟠 متوسط  (۴): G2، G5، G7، G9       → G5/G7/G9 در B رفع؛ G2 در فاز ۴۰ (دفتر دوطرفه)
🟡 کم     (۴): G4، G8، G10، G12     → G4 در B؛ G8 در فاز ۴۰ (Numeric)
```

---

## ۴. گزینه‌های دامنه (نیازمند تصمیم کاربر)

| گزینه | محتوا | Migration | ریسک | تخمین |
|:---|:---|:---:|:---:|:---:|
| **A — گزارش‌محور** | فقط ۳۹.۴ (رفع G5/G6) + endpointهای **خواندنی** کیف‌پول (۳۹.۳) | ❌ | 🟢 | ~۴ ساعت |
| **B — متعادل** ⭐ پیشنهاد | ۳۹.۱ + ۳۹.۲ + ۳۹.۳ + ۳۹.۴ + ۳۹.۵ + ۳۹.۶ | ✅ ۱ فایل | 🟡 | ~۱۲ ساعت |
| **C — کامل** | B + دفتر دوطرفهٔ `wallet_entries` (G2) + `Float → Numeric(18,2)` (G8) | ✅ ۲ فایل | 🔴 | ~۲۴ ساعت |

> **توصیه: گزینهٔ B.** دلایل:
> ۱) هر ۴ شکاف 🔴 را می‌بندد، بدون جدول جدید ⇒ ریسک مهاجرت حداقلی.
> ۲) گزینهٔ C نیازمند بازنویسی تمام `float(t.amount)` و تبدیل `Decimal → float` در JSON است
>    (~۳۰ نقطه) و تست‌های موجود را با ریسک بالا مواجه می‌کند ⇒ بهتر است فاز ۴۰ باشد.
> ۳) گزینهٔ A فقط «کیف‌پول» را می‌خواند و باگ‌های G1/G11 (drift موجودی) باقی می‌مانند.

---

## ۵. نقشهٔ اجرا — فازهای فرعی (بر پایهٔ گزینهٔ B)

### ۵.۱ فاز ۳۹.۱ — `WalletService`: تنها نویسندهٔ موجودی  ⟵ رفع G1، G9، G11، G12

**فایل جدید:** `backend/app/services/wallet_service.py`

```python
"""فاز ۳۹ — سرویس کیف‌پول: تنها نقطهٔ تغییر FinancialAccount.balance.

قرارداد جهت‌دار (direction contract):
  DEPOSIT / PROFIT                   ⇒ account_id  +
  WITHDRAWAL / LOSS / FEE / PURCHASE ⇒ account_id  −
  TRANSFER                           ⇒ from_account_id − , to_account_id + , account_id = مقصد
  ADJUSTMENT                         ⇒ account_id  ±  (علامت از فراخوان)
"""

BALANCE_DIRECTION: dict[TransactionType, str] = {
    TransactionType.DEPOSIT: "+",
    TransactionType.PROFIT: "+",
    TransactionType.WITHDRAWAL: "-",
    TransactionType.LOSS: "-",
    TransactionType.FEE: "-",
    TransactionType.PURCHASE: "-",
    TransactionType.TRANSFER: "move",      # دو طرفه
    TransactionType.ADJUSTMENT: "signed",  # علامت در payload
}


class WalletService:
    @staticmethod
    def post(db, *, account_id, type, amount, currency=None, date=None, category_id=None,
             from_account_id=None, to_account_id=None,
             counter_amount=None, counter_currency=None, fx_rate=None,
             fee_amount=None, fee_currency=None,
             description=None, related_trade_id=None, related_prop_account_id=None,
             signed_amount=None, allow_overdraft=False, commit=True) -> FinancialTransaction: ...

    @staticmethod
    def reverse(db, tx: FinancialTransaction, *, commit=True) -> None: ...

    @staticmethod
    def reconcile(db, account_id: int) -> dict: ...
    # → {"account_id","stored","ledger","delta","is_balanced","entry_count"}

    @staticmethod
    def ledger(db, account_id: int, *, limit=None, offset=0) -> list[dict]: ...
    # union سه رابطه + direction / signed_amount / running_balance
```

**نکات پیاده‌سازی الزامی:**
1. `post()` **همیشه** `db.flush()` می‌زند تا `tx.id` در دسترس باشد (نیاز `PayoutService._post_income`).
2. اعتبارسنجی: `amount > 0` برای همهٔ انواع به‌جز `ADJUSTMENT` (که از `signed_amount` استفاده می‌کند).
3. `TRANSFER`: `from_account_id != to_account_id` (منطق موجود در `payout_service.py:227` منتقل می‌شود).
4. `allow_overdraft=False` ⇒ بررسی `balance >= amount` روی کیف‌پول مبدأ و پرتاب `ValueError`
   با پیام فارسی (`"موجودی کیف‌پول مبدأ کافی نیست"`) که لایهٔ API آن را به `HTTPException(400)` تبدیل می‌کند.
5. `reverse()` = عکس دقیق اثر + `is_deleted = True` (اسکلت از `payout_service.py:331-350`).

**مهاجرت فراخوانی‌ها (Grep تأییدی در پایان اجباری است):**
| فایل | خط | اقدام |
|:---|:---|:---|
| `api/finance.py::create_transaction` | ۳۱۵ | `WalletService.post(...)` |
| `api/finance.py::update_transaction` | ۳۲۸ | اثر قدیمی `reverse` → اعمال مجدد (بازمحاسبه) |
| `api/finance.py::delete_transaction` | ۳۴۱ | `WalletService.reverse(tx)` |
| `services/payout_service.py::_post_income` | ۱۵۸ | `WalletService.post` |
| `services/payout_service.py::record_transfer` | ۲۰۷ | `WalletService.post(type=TRANSFER, ...)` + فیلدهای FX/کارمزد |
| `services/payout_service.py::update` | ۲۶۹ | مسیر delta → `WalletService.post(ADJUSTMENT)` |
| `services/payout_service.py::delete_and_reverse` | ۳۳۰ | `WalletService.reverse(tx)` |
| `api/prop.py::create_cost` | ~۱۱۶۲ | `WalletService.post(type=PURCHASE, account_id=payer_id, ...)` |


### ۵.۲ فاز ۳۹.۲ — مدل‌سازی FX و کارمزد  ⟵ رفع G3، G4، G10

**ستون‌های جدید (nullable) روی `FinancialTransaction` — `models/finance.py`:**
```python
# ── فاز ۳۹: مدل‌سازی تبدیل ارز + کارمزد انتقال ──
counter_amount      = Column(Float, nullable=True)            # مبلغ سمت مقابل
counter_currency    = Column(Enum(Currency), nullable=True)    # ارز سمت مقابل
fx_rate             = Column(Float, nullable=True)             # counter_amount / amount
fee_amount          = Column(Float, nullable=True)             # کارمزد انتقال/تبدیل
fee_currency        = Column(Enum(Currency), nullable=True)
transfer_group_id   = Column(String, nullable=True, index=True)  # گروه‌بندی زنجیرهٔ چند-پرشی
```
> **قاعدهٔ سازگاری:** اگر `counter_currency is None` ⇒ `counter_currency = currency`،
> `counter_amount = amount`، `fx_rate = 1.0`. برای `TRANSFER` بین دو ارز متفاوت:
> `currency` = ارز مبدأ و `counter_currency` = ارز مقصد.

**قاعدهٔ محاسبهٔ خودکار در `WalletService.post`:**
```
amount    = مبلغ سمت مبدأ (همیشه مثبت — به‌جز ADJUSTMENT)
fx_rate   = fx_rate or (counter_amount / amount if counter_amount else 1.0)
واریز به مقصد = counter_amount if counter_amount else amount
```
**سازگاری با `test_finance.py:304-318`:** چون همهٔ فیلدها nullable و پیش‌فرض‌دار هستند،
`POST /finance/transactions` فعلی (که فیلدهای FX نمی‌فرستد) دست‌نخورده کار می‌کند.

### ۵.۳ فاز ۳۹.۳ — API کیف‌پول‌محور  ⟵ رفع G7

| Endpoint جدید | پارامترها | خروجی |
|:---|:---|:---|
| `GET /finance/wallets` | `type?`, `currency?` | `[{id, name, type, currency, stored_balance, ledger_balance, delta, is_balanced, entry_count, last_activity_at}]` |
| `GET /finance/wallets/{id}/ledger` | `limit?`(≤۵۰۰), `offset?`, `date_from?`, `date_to?` | `{account, entries:[{id, date, type, direction, amount, signed_amount, currency, counter_amount, counter_currency, fx_rate, fee_amount, description, category_name, peer_account_id, peer_account_name, running_balance}]}` |
| `GET /finance/wallets/{id}/reconciliation` | — | `{account_id, stored, ledger, delta, is_balanced, entry_count, last_entry_at}` |
| `GET /finance/wallets/summary` | — | `{by_type:{bank:{IRR,USD,accounts},…}, by_currency:{IRR,USD}, total_accounts, unbalanced_count}` |
| `POST /finance/wallets/{id}/adjust` | `{amount, currency?, description, date?}` | ثبت `ADJUSTMENT` از مسیر `WalletService` + `{transaction_id, stored_balance}` |

**نکات:**
- `ledger_balance` = `opening_balance + Σeffect`. برای **پرهیز از هرگونه migration داده‌ای**،
  `opening_balance` به‌صورت `stored_balance − Σeffect` محاسبه می‌شود ⇒ کیف‌پول‌هایی که با
  `balance` افتتاحیهٔ مستقیم ساخته شده‌اند (`POST /finance/accounts` با `balance=1000`)
  همیشه `delta == 0` و `is_balanced == true` می‌گیرند.
- همهٔ endpointها فقط کیف‌پول‌های **مالی** (`FinancialAccount`) را می‌بینند — بروکر/پراپ همچنان از
  `PersonalTradingAccount` / `PropAccount` می‌آیند (قرارداد فاز ۲۷/۲۸، `PHASE38_5_FIX_DEBT.md`).

### ۵.۴ فاز ۳۹.۴ — رفع گزارش‌های موجود  ⟵ رفع G5، G6، G10

**الف) `/finance/spendable-assets` — `api/finance.py:1203-1225` (🔴 باگ فعلی):**
```python
# قبل (باگ):
trust_wallet = _balance_sum(db, AccountType.CRYPTO_WALLET)   # ← نادرست
bank = _balance_sum(db, AccountType.BANK)
total_usd = prop_stage_3 + broker + exchange + trust_wallet
"total": {"usd": total_usd, "irr": bank}                     # ← هاردکد؛ IRR بقیه گم می‌شود

# بعد (فاز ۳۹):
trust_wallet  = _balance_sum(db, AccountType.TRUST_WALLET)   # ← رفع
crypto_wallet = _balance_sum(db, AccountType.CRYPTO_WALLET)  # ← جدید
card = _balance_sum(db, AccountType.CARD)                    # ← جدید
cash = _balance_sum(db, AccountType.CASH)                    # ← جدید
usd_total = prop_stage_3 + broker + exchange + trust_wallet + crypto_wallet
irr_total = Σ balance همهٔ کیف‌پول‌های IRR (نه فقط bank)
```
> کلیدهای فعلی (`prop_stage_3`, `broker`, `exchange`, `trust_wallet`, `bank`, `total.usd`, `total.irr`)
> **حفظ می‌شوند** و فقط کلیدهای جدید افزوده می‌شوند ⇒ `test_finance.py:219-240` نمی‌شکند.

**ب) `/finance/money-flow` — `api/finance.py:1279-1286`:** افزودن `from_account_id`،
`from_account_name`، `to_account_id`، `to_account_name` + `counter_amount`/`counter_currency`/`fx_rate`.
کلیدهای `from`/`to` (نوع حساب) **عیناً حفظ می‌شوند** ⇒ `test_finance.py:314-315` نمی‌شکند.

**ج) `/finance/exchange-rates` — `api/finance.py:1476-1509`:** اگر `fx_rate` روی تراکنش موجود
باشد از آن استفاده شود؛ وگرنه fallback به نرخ ضمنی فعلی (ΣIRR/ΣUSD). (رفع G10 در حد گزارش.)

**د) `/finance/money-cycle` — `api/finance.py:1335-1371`:** افزودن `current_balance_by_currency`
(`{"USD": x, "IRR": y}`) و حفظ `current_balance` فعلی.


### ۵.۵ فاز ۳۹.۵ — Migration (۱ فایل، افزودنی، idempotent)

**فایل:** `backend/migrations/versions/e39f0a1b2c3d_phase39_wallet_money_flow.py`
```python
revision: str = "e39f0a1b2c3d"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"   # head فعلی
```
**عمل‌ها:** فقط `op.add_column("transactions", sa.Column(...))` برای ۶ ستون nullable
(+ ایندکس `ix_transactions_transfer_group_id`).

**الگوی idempotent (به سبک فاز ۳۸.۵ — `c9d0e1f2a3b4_phase36_indexes.py:58-76`):**
```python
from sqlalchemy import inspect

def _existing_columns(table: str) -> set:
    return {c["name"] for c in inspect(op.get_bind()).get_columns(table)}

def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if column.name in _existing_columns(table):
        return
    op.add_column(table, column)
```

**چرا بدون backfill؟** هر ۶ ستون nullable هستند و کد مصرف‌کننده در نبود مقدار، پیش‌فرض
(`counter_amount = amount`, `fx_rate = 1.0`) را اعمال می‌کند ⇒ صفر ریسک دادهٔ موجود.

**بدون جدول جدید** ⇒ هیچ rebuild/FK-churn روی SQLite لازم نیست.

### ۵.۶ فاز ۳۹.۶ — تست‌ها

**فایل جدید:** `backend/tests/test_phase39_wallet_money_flow.py` (~۱۸ تست)

| تست | پوشش |
|:---|:---|
| `test_manual_transaction_updates_balance` | G1 — `POST /finance/transactions` حالا موجودی را تغییر می‌دهد |
| `test_manual_delete_reverses_balance` | G11 — حذف نرم، موجودی را برمی‌گرداند |
| `test_manual_update_reapplies_balance` | G1 — ویرایش مبلغ ⇒ بازمحاسبهٔ اثر |
| `test_transfer_moves_both_balances` | G1/G2 — مبدأ − ، مقصد + |
| `test_transfer_same_account_rejected` | `400` |
| `test_overdraft_blocked` | G9 — `400` با پیام فارسی |
| `test_adjustment_signed_effect` | `ADJUSTMENT` مثبت/منفی |
| `test_fx_transfer_stores_rate` | G3 — `counter_amount`/`counter_currency`/`fx_rate` در DB |
| `test_fee_recorded_on_transfer` | G4 — `fee_amount`/`fee_currency` |
| `test_wallet_ledger_running_balance` | G7 — `running_balance` انتها = `stored_balance` |
| `test_reconciliation_balanced` | G7 — `delta == 0` برای کیف‌پول افتتاحیه‌ای |
| `test_wallets_summary_by_currency` | G7 |
| `test_spendable_assets_trust_wallet` | G6 — سبد `trust_wallet` از `TRUST_WALLET` |
| `test_spendable_assets_irr_total` | G6 — `total.irr` شامل IRR صرافی/نقد/کارت |
| `test_money_flow_has_account_ids` | G5 — id/name + حفظ `from`/`to` نوعی |
| `test_exchange_rate_prefers_fx_field` | G3 — نرخ واقعی بر نرخ ضمنی اولویت دارد |
| `test_payout_received_still_posts_income` | ♻️ رگرسیون فاز ۳۳ — `PROFIT` + موجودی مقصد |
| `test_prop_cost_still_decreases_payer` | ♻️ رگرسیون فاز ۵/۳۸ — `PURCHASE` |

**فایل‌های موجود که تحت نظارت قرار می‌گیرند (نباید بشکنند):**
`tests/test_finance.py` (۲۳ تست، بخصوص `test_money_flow:304` و `test_spendable_assets:227`)،
`tests/test_phase33_withdrawal.py`، `tests/test_phase37_finance_rename.py`،
`tests/test_phase38_personal_finance.py`، `tests/test_soft_delete_filters.py`.

### ۵.۷ فاز ۳۹.۷ — Frontend (سبک — فقط افزودنی)

| فایل | تغییر |
|:---|:---|
| `frontend/src/api/client.ts` | تایپ‌های `Wallet`, `WalletLedgerEntry`, `WalletSummary` + ۵ تابع (`getWallets`, `getWalletLedger`, `getWalletReconciliation`, `getWalletsSummary`, `adjustWallet`) + افزودن فیلدهای FX به `MoneyFlow` (اختیاری) |
| `frontend/src/pages/FinancePage.tsx` | تب جدید `👛 کیف‌پول‌ها` (`{ key: 'wallets' }` در `TABS:318-330`) + جدول + نشانگر مغایرت (`delta != 0` → 🟠) + drawer صورت حساب |
| `frontend/src/components/AccountForm.tsx` | «موجودی اولیه» → ثبت خودکار از مسیر `POST /finance/wallets/{id}/adjust` (رفع G1 در سطح UI) |

**قرارداد:** تمام تغییرات فرانت **افزودنی** است؛ هیچ تب/فیلد موجودی حذف نمی‌شود
⇒ `npx tsc -b --force` باید `EXIT 0` و `vitest run` باید `9 passed` بماند.


---

## ۶. فایل‌به‌فایل — دامنهٔ تغییر (گزینهٔ B)

| فایل | نوع | محتوا |
|:---|:---:|:---|
| `backend/app/services/wallet_service.py` | 🆕 جدید | `WalletService` — تنها نویسندهٔ موجودی |
| `backend/migrations/versions/e39f0a1b2c3d_phase39_wallet_money_flow.py` | 🆕 جدید | ۶ ستون nullable + ۱ ایندکس |
| `backend/tests/test_phase39_wallet_money_flow.py` | 🆕 جدید | ~۱۸ تست |
| `PLAN_PHASE39.md` | 🆕 جدید | همین سند |
| `backend/app/models/finance.py` | ✏️ | ۶ ستون جدید روی `FinancialTransaction` |
| `backend/app/api/finance.py` | ✏️ | ۷ فراخوانی → `WalletService` · ۵ endpoint کیف‌پول · رفع `spendable-assets` · غنی‌سازی `money-flow`/`exchange-rates`/`money-cycle` |
| `backend/app/services/payout_service.py` | ✏️ | ۴ فراخوانی → `WalletService` (حفظ قرارداد فاز ۳۳) |
| `backend/app/api/prop.py` | ✏️ | `create_cost` → `WalletService` |
| `frontend/src/api/client.ts` | ✏️ | ۵ تابع + تایپ‌ها (افزودنی) |
| `frontend/src/pages/FinancePage.tsx` | ✏️ | تب «کیف‌پول‌ها» |
| `frontend/src/components/AccountForm.tsx` | ✏️ | موجودی اولیه → `ADJUSTMENT` |

**فایل‌های «ممنوع‌اللمس» در این فاز:**
`backend/app/api/analytics.py` · `backend/app/api/broker.py` · `backend/app/api/trading.py`
· `frontend/src/pages/PropPage.tsx` · `models/prop.py` (به‌جز هیچ) — چون قرارداد فاز ۲۷/۲۸/۳۸.۵
این‌ها را تثبیت کرده و تغییرشان خارج از دامنهٔ «Wallet & Money Flow» است.

---

## ۷. جدول ریسک و کاهش

| ریسک | احتمال | تأثیر | راه کاهش |
|:---|:---:|:---:|:---|
| **دو بار اعمال شدن اثر موجودی** (سرویس جدید + کد قدیمیِ فراموش‌شده) | متوسط | 🔴 | مهاجرت هر ۷ فراخوانی + `grep -rn "balance = ("` در پایان باید **صفر** نتیجه در `api/`/`services/` بدهد |
| drift موجودی موجود در DB فعلی | بالا | 🟠 | endpoint `/reconciliation` + گزارش `unbalanced_count` در `/wallets/summary` (اصلاح دستی با `POST /adjust`) |
| شکستن `test_money_flow` (`from`/`to` نوعدار) | کم | 🟡 | کلیدهای فعلی حفظ می‌شوند؛ فقط کلید جدید افزوده می‌شود |
| شکستن `test_spendable_assets` | کم | 🟡 | `trust_wallet` از `CRYPTO_WALLET` به `TRUST_WALLET` اصلاح می‌شود؛ در تست فعلی کیف‌پول `trust_wallet` ساخته نمی‌شود ⇒ مقدار قبل و بعد `0` است |
| شکستن جریان برداشت پراپ (فاز ۳۳) | متوسط | 🔴 | `test_phase33_withdrawal.py` + ۲ تست رگرسیون اختصاصی در ۳۹.۶ |
| migration روی DB موجود | کم | 🟡 | فقط `add_column` nullable + helper `inspect`-محور (الگوی فاز ۳۸.۵) |
| افت کارایی `/money-flow` (بدون فیلتر تاریخ) | متوسط | 🟡 | افزودن `date_from`/`date_to` اختیاری + `limit` (الگوی فاز ۳۶) |
| رشد اندازهٔ `finance.py` (۱۵۵۶+ خط) | متوسط | 🟡 | منطق جدید در `wallet_service.py`؛ endpointها فقط لایهٔ نازک باقی می‌مانند |

---

## ۸. سؤالات باز (نیازمند تصمیم پیش از اجرا)

| # | سؤال | پیشنهاد |
|:--|:---|:---|
| ۱ | سیاست overdraft: آیا `TRANSFER` با موجودی ناکافی مسدود شود؟ | ✅ بله برای `TRANSFER`/`WITHDRAWAL`، ❌ خیر برای `ADJUSTMENT` |
| ۲ | موجودی افتتاحیه: فیلد مستقیم `balance` یا تراکنش `ADJUSTMENT`؟ | تراکنش `ADJUSTMENT` (رفع کامل G1) — با حفظ فیلد فعلی برای سازگاری |
| ۳ | `Float → Numeric(18,2)` در ۳۹ یا ۴۰؟ | فاز ۴۰ (ریسک `Decimal`/JSON بالا) |
| ۴ | دفتر دوطرفهٔ `wallet_entries` در ۳۹ یا ۴۰؟ | فاز ۴۰ (نیازمند rebuild جدول + مهاجرت داده) |
| ۵ | آیا `/finance/sync/trades` (no-op از فاز ۲۸) حذف/مستند شود؟ | خارج از دامنه؛ فقط یادآوری در گزارش |
| ۶ | آیا `TransactionType.TRANSFER` باید به `TRANSFER` + `CONVERSION` تفکیک شود؟ | فاز ۴۰ (`CategoryType.CONVERSION` از قبل هست؛ کلید `money-cycle.total_exchanges` باید حفظ شود) |

---

## ۹. اعتبارسنجی (پس از اجرا)

```shell
cd i:\trade\MokTradeDesk\backend

# ۱) سلامت import
venv\Scripts\python.exe -c "import app.main; from app.services.wallet_service import WalletService; print('OK')"

# ۲) تست کامل — باید 192 + ~18 = ~210 passed باشد
venv\Scripts\python.exe -m pytest -q -p no:warnings

# ۳) تأیید head جدید
venv\Scripts\python.exe -m alembic heads          # باید e39f0a1b2c3d

# ۴) idempotency مهاجرت (روی DB موجود و DB خالی)
venv\Scripts\python.exe -m alembic upgrade head
venv\Scripts\python.exe -m alembic upgrade head   # بار دوم: بی‌اثر

# ۵) تأیید «تنها نویسندهٔ موجودی»
#    هیچ نتیجه‌ای نباید برگردد (به‌جز خود wallet_service.py):
#    grep -rn "\.balance = " app/api app/services | grep -v wallet_service.py

cd ..\frontend
npx tsc -b --force                                 # EXIT 0
npx vitest run                                     # 9 passed
npm run build                                      # EXIT 0
```

---

## ۱۰. تخمین زمانی (گزینهٔ B)

| فاز فرعی | تخمین |
|:---|:---:|
| ۳۹.۱ `WalletService` + مهاجرت ۷ فراخوانی | ۳ ساعت |
| ۳۹.۲ مدل FX/کارمزد + migration | ۱.۵ ساعت |
| ۳۹.۳ پنج endpoint کیف‌پول | ۳ ساعت |
| ۳۹.۴ رفع گزارش‌ها (G5/G6/G10) | ۱.۵ ساعت |
| ۳۹.۵/۳۹.۶ تست‌ها (~۱۸) | ۲ ساعت |
| ۳۹.۷ فرانت‌اند | ۱ ساعت |
| **جمع** | **~۱۲ ساعت** |

---

## ⛔ پایان Plan — اجرا فقط پس از قفل‌کردن دامنه (گزینهٔ A/B/C) و تأیید صریح کاربر

