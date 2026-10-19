# 📋 گزارش فاز ۲۱ — Finance Bridge

> **تاریخ:** ۱۴۰۵/۰۷/۰۴ (2026-09-26) · **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ کامل — ✅ ۵۲ تست پاس · ✅ build فرانت‌اند (tsc + vite) · ✅ همگام‌سازی دستی + خودکار

---

## خلاصه

فاز ۲۱: **اتصال معاملات به حسابداری**. وقتی یک معامله در بروکر یا مرحله ۳ پراپ بسته می‌شود،
یک `Transaction` خودکار ساخته می‌شود و `Account.balance` به‌روز می‌شود.
داشبورد از `Transaction`ها می‌خواند (نه از Tradeهای خام).

---

## فایل‌های تغییر‌یافته

| فایل | وضعیت | توضیح |
|---|---|---|
| **جدید** | `backend/app/services/finance_sync_service.py` | سرویس همگام‌سازی + جلوگیری از تکرار |
| `backend/app/api/trades.py` | تغییر | همگام‌سازی خودکار هنگام ایجاد/ویرایش معامله بسته |
| `backend/app/api/finance.py` | تغییر | `POST /api/finance/sync/trades` برای همگام‌سازی دستی |
| `backend/app/api/analytics.py` | تغییر | `spendable_money` از Transactionها می‌خواند |
| `frontend/src/pages/FinancePage.tsx` | تغییر | دکمه «همگام‌سازی معاملات» در تب حساب‌ها |
| **جدید** | `PHASE21_REPORT.md` | این فایل |

---

## ۱. سرویس همگام‌سازی — `finance_sync_service.py`

### منطق

```python
class FinanceSyncService:
    def sync_closed_trades(self, trade_ids: Optional[List[int]] = None) -> int
```

- **ورودی**: معاملات بسته‌شده (`close_time IS NOT NULL`).
- **فیلتر**: فقط معاملات متصل به **بروکر** (`Account.type=BROKER`) یا **مرحله ۳ پراپ** (`StageType.FUNDED_REAL`).
- **جلوگیری از تکرار**: `~Transaction.related_trade_id == Trade.id` (اگر قبلاً ساخته شده، رد می‌شود).
- **خروجی**: `Transaction` با `type=PROFIT` (سود) یا `LOSS` (زیان) + به‌روزرسانی `Account.balance`.

### جریان

```
Trade بسته می‌شود (close_time + pnl != 0)
    ↓
    آیا finance_account_id با Account.type=BROKER دارد؟   → Transaction(account_id=بروکر)
    یا prop_stage_id با StageType=FUNDED_REAL دارد؟         → Transaction(account_id=پراپ مالی)
    ↓
    Transaction(amount=abs(net_pnl), type=PROFIT|LOSS,
                related_trade_id=trade.id,
                related_prop_account_id=prop_account.id)
    ↓
    Account.balance ±= amount
```

### ۳ نقطه‌ی فراخوانی

| محل | نحوه | زمان |
|---|---|---|
| `trades.py:create_manual_trade` | رویدادمبنا | هنگام ثبت معامله بسته |
| `trades.py:update_trade` | رویدادمبنا | هنگام ویرایش معامله (اگر close_time + account وجود دارد) |
| `finance.py:POST /sync/trades` | دستی (API) | هر زمان کاربر بخواهد |

---

## ۲. داشبورد اصلاح‌شده

**قبل (فاز ۲۰):**
```python
spendable_net = SUM(Trade.net_pnl)  # از معاملات خام
```

**بعد (فاز ۲۱):**
```python
broker_pnl  = SUM(Transaction PROFIT) - SUM(Transaction LOSS)  FOR Account.type=BROKER
funded_pnl  = SUM(Transaction PROFIT) - SUM(Transaction LOSS)  FOR Account.type=PROP + Funded stage
init_capital = SUM(Transaction DEPOSIT) FOR Account.type=BROKER
```

---

## ۳. Frontend

دکمه «🔄 همگام‌سازی معاملات» در صفحه Finance (تب حساب‌ها).
بعد از کلیک: `POST /api/finance/sync/trades` → Toast با نتیجه.

---

## ۴. تست

| تست | نتیجه |
|---|---|
| `pytest` | ✅ **۵۲ passed** |
| `tsc --noEmit` | ✅ exit=0 |
| `pnpm build` | ✅ exit=0 |
| `py_compile` همه فایل‌ها | ✅ exit=0 |

---

*گزارش فاز ۲۱ — تهیه‌شده در ۱۴۰۵/۰۷/۰۴.*