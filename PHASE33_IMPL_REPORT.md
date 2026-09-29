# 💸 PHASE 33 — Prop Withdrawal · IMPLEMENTATION REPORT

> **وضعیت:** ✅ کامل (Model + Migration + PayoutService + API + Tests)
> **تاریخ:** ۱۴۰۵/۰۷/۰۹
> **Revision:** `f6a7b8c9d0e1` → **`a7b8c9d0e1f2`** (head جدید)
> **خروجی تست:** `149 passed` (کل مجموعه) · `10 passed` (Phase 33)

---

## ۱. خلاصهٔ اجرایی

| نیازمندی | پیاده‌سازی |
|:---|:---|
| `PropWithdrawal` با `currency`/`status`/`reference`/`created_at` | ✅ |
| `WithdrawalStatus` (REQUESTED/APPROVED/PROCESSING/RECEIVED/CANCELLED) | ✅ |
| `destination_account_id` اجباری (`NOT NULL`) | ✅ (DB + ORM) |
| `PropWithdrawal ← FinancialTransaction` | ✅ از طریق `transaction_id` (FK) |
| **Income در نقطهٔ دریافت** | ✅ فقط در انتقال به `RECEIVED` |
| **انتقال = درآمد نیست** | ✅ `type=EXCHANGE` ⇒ در `total_transfers` نه `total_income` |
| سناریو `Prop → Trust Wallet → Exchange → IRR → Bank Card` | ✅ با `record_transfer` + endpoint |

جریان وضعیت:

```text
REQUESTED ─► APPROVED ─► PROCESSING ─► RECEIVED   (اینجا FinancialTransaction/PROFIT ثبت می‌شود)
      └──────────┴───────────┴────────► CANCELLED (بدون هیچ اثر مالی)
```

---

## ۲. تغییرات فایل‌به‌فایل

### ۲.۱ `backend/app/models/prop.py`
- افزودن `WithdrawalStatus` + جدول انتقال‌های مجاز `WITHDRAWAL_TRANSITIONS`.
- بازنویسی `PropWithdrawal`:

```python
class PropWithdrawal(Base):
    __tablename__ = "prop_withdrawals"
    id                     = Column(Integer, primary_key=True, index=True)
    prop_stage_id          = Column(Integer, ForeignKey("prop_stages.id"), nullable=False)
    amount                 = Column(Float, nullable=False)
    currency               = Column(Enum(Currency), nullable=False, default=Currency.USD)
    withdrawal_date        = Column(DateTime(timezone=True), nullable=False, default=...)
    destination_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    status                 = Column(Enum(WithdrawalStatus), nullable=False,
                                    default=WithdrawalStatus.REQUESTED, index=True)
    reference              = Column(String, nullable=True)
    note                   = Column(Text, nullable=True)
    transaction_id         = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    created_at             = Column(DateTime(timezone=True), server_default=func.now())

    stage                 = relationship("PropStage", back_populates="withdrawals")
    destination_account   = relationship("Account", foreign_keys=[destination_account_id])
    financial_transaction = relationship("Transaction", foreign_keys=[transaction_id])
```

> **افزودهٔ `transaction_id`:** قرارداد شما جهت اتصال را «PropWithdrawal ← FinancialTransaction»
> تعریف کرده بود؛ این ستون همان لینک یک‌به‌یک است (مطابق `M3` سند Audit: `transaction_id`).
> `Currency` از `models.finance` ایمپورت می‌شود (بدون چرخه — finance به prop وابسته نیست).

### ۲.۲ `backend/migrations/versions/a7b8c9d0e1f2_phase33_prop_withdrawal.py` (جدید)
- `batch_alter_table` → افزودن ۵ ستون + FK به `transactions.id`.
- **Backfill:** رکوردهای تاریخی ⇒ `status='RECEIVED'` (چون رفتار قبلی، دریافت فوری էր) و
  `currency` از حساب مقصد / پیش‌فرض USD.
- NOT NULL کردن `withdrawal_date`/`destination_account_id`/`currency`/`status`
  **فقط در صورت نبود NULL** (گارد ایمن برای DB کاربر).
- ایندکس `ix_prop_withdrawals_status`.
- ✅ روی `trading_desk.db` اجرا شد (پس از بکاپ `trading_desk.db.bak_phase33_pre`):
  هر ۳ FK (شامل FK اصلی `prop_stages`) و ایندکس سالم ماندند.

### ۲.۳ `backend/app/services/payout_service.py` (جدید)
`PayoutService`:

| متد | نقش |
|:---|:---|
| `create(...)` | ساخت برداشت با وضعیت **REQUESTED**، بدون تراکنش مالی |
| `set_status(...)` | انتقال مجاز وضعیت؛ در `RECEIVED` ⇒ `_post_income` |
| `_post_income(...)` | ثبت `Transaction(type=PROFIT)` + افزایش موجودی مقصد + `total_withdrawn` (idempotent) |
| `record_transfer(...)` | ثبت پرش انتقال با `type=EXCHANGE` + `from/to` ⇒ **درآمد نیست** |
| `update(...)` | ویرایش + ترمیم هم‌زمان تراکنش/موجودی/`total_withdrawn` |
| `delete_and_reverse(...)` | حذف + برگشت کامل اثر مالی (soft-delete تراکنش) |
| `allowed_transitions(...)` | لیست انتقال‌های مجاز برای UI |

### ۲.۴ `backend/app/api/prop.py`
- Schemas: `PayoutStatusUpdate`, `TransferCreate`؛ افزودن `currency/reference/status` به
  `WithdrawalCreate`/`PayoutCreate`/`PayoutUpdate`.
- `_create_payout_record` بازنویسی شد (اعتبارسنجی مرحله + `PropRuleEngine.validate_withdrawal`
  + ساخت با `PayoutService`).
- endpointهای جدید:
  - `POST /api/prop/payouts/{id}/status` — تغییر وضعیت (درآمد در RECEIVED).
  - `POST /api/prop/payouts/{id}/transfer` — ثبت انتقال بین‌حسابی (بدون درآمد).
- `PUT/PATCH/DELETE /payouts/{id}` اکنون از `PayoutService` (یکپارچگی کامل).
- `_serialize_payout` اکنون `status`, `reference`, `transaction_id`, `allowed_transitions`,
  `currency`, `created_at` را هم برمی‌گرداند.

---

## ۳. تصمیم مالی کلیدی — تغییر رفتار نسبت به قبل

| مورد | قبل (فاز ۵/۱۶) | بعد (فاز ۳۳) |
|:---|:---|:---|
| ساخت برداشت | فوری `Transaction(type=WITHDRAWAL)` + افزایش موجودی | `REQUESTED`، **بدون** تراکنش |
| نوع تراکنش درآمد | `WITHDRAWAL` (⇒ در `total_expense`) | `PROFIT` (⇒ در `total_income`) |
| نقطهٔ ثبت درآمد | لحظهٔ ساخت | لحظهٔ `RECEIVED` |
| حذف برداشت | فقط `total_withdrawn` اصلاح می‌شد | برگشت تراکنش + موجودی + `total_withdrawn` |

> ⚠️ **اثر روی مصرف‌کننده‌ها:** از این پس برای اینکه پول واقعاً وارد FINANCE شود، باید برداشت به
> `RECEIVED` برسد (یا در لحظهٔ ساخت `status="received"` داده شود). فرانت‌اند `PayoutHistoryPage`
> برای نمایش دکمهٔ «تغییر وضعیت» به‌روزرسانی لازم دارد (خارج از دامنهٔ این فاز؛ در گزارش
> ذکر شد).

---

## ۴. تست‌ها — `backend/tests/test_phase33_withdrawal.py` (جدید · ۱۰ تست)

| تست | پوشش |
|:---|:---|
| `test_create_withdrawal_default_requested_no_income` | ساخت ⇒ REQUESTED، بدون تراکنش/موجودی |
| `test_validation_only_funded_stage` | مرحله غیر‌رییل ⇒ ۴۰۰ |
| `test_validation_amount_over_withdrawable` | بیش از سود قابل برداشت ⇒ ۴۰۰ |
| `test_status_transitions_and_income_at_received` | چرخهٔ کامل + درآمد در RECEIVED + idempotency |
| `test_invalid_transition_rejected` | REQUESTED→RECEIVED ⇒ ۴۰۰ |
| `test_cancel_records_no_income` | CANCELLED ⇒ بدون اثر مالی |
| `test_transfer_is_not_income` | `total_income` ثابت، `total_transfers` افزایش |
| `test_delete_reverses_income` | حذف ⇒ برگشت موجودی/`total_withdrawn` + soft-delete تراکنش |
| `test_update_amount_adjusts_transaction` | ویرایش مبلغ ⇒ اصلاح تراکنش/موجودی |
| `test_serializer_exposes_status_and_transitions` | خروجی serializer |

---

## ۵. خروجی اجرای تست

```text
tests/test_phase33_withdrawal.py ......................... 10 passed
pytest (کل مجموعه) ....................................... 149 passed
alembic upgrade head ..................................... a7b8c9d0e1f2 ✓
prop_withdrawals: currency/status/reference/transaction_id/created_at + 3 FK + index ✓
```

---

## ۶. یادداشت‌های طراحی

1. **Idempotency:** فراخوانی دوبارهٔ `RECEIVED` تراکنش دوم نمی‌سازد (چون `transaction_id`
   ست شده است) ⇒ بدون Double Counting.
2. **`total_withdrawn`** فقط در `RECEIVED` افزایش می‌یابد تا با `withdrawable_profit`
   (`user_share − total_withdrawn`) سازگار باشد.
3. **انتقال ≠ درآمد:** مطابق `TransactionType` پروژه، انتقال‌ها با `type=EXCHANGE` ثبت
   می‌شوند (پروژه مقدار `TRANSFER` ندارد) و در `finance/summary.total_transfers` می‌آیند.
4. **بکاپ:** `backend/trading_desk.db.bak_phase33_pre` قبل از مهاجرت ساخته شد.

