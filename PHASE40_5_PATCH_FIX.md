# PHASE 40.5 — Fix PATCH Trades Bug

> **تاریخ:** ۱۴۰۵/۰۷/۰۸ (2026-09-30)
> **وضعیت:** ✅ کامل — ✅ ۲۴۶ pytest (۰ xfailed) · ✅ `trading_desk.db` واقعی دست‌نخورده
> **قوانین:** ✅ Auto-approve خاموش · ✅ گام‌به‌گام · ✅ commit **نشد**

---

## ۱. خلاصه اجرایی

باگ کشف‌شده در رگرسیون فاز ۴۰ رفع شد: **`PATCH /api/trades/{id}` تغییرات را ذخیره نمی‌کرد.**

- **ریشه:** در `update_trade` (`backend/app/api/trades.py:361-494`) هیچ `db.commit()` وجود نداشت؛ در انتها فقط `db.refresh(trade)` صدا زده می‌شد که به‌دلیل `autoflush=False` تمام تغییرات commit‌نشده را دور می‌ریخت.
- **Fix:** یک خط `db.commit()` پیش از `db.refresh(trade)` اضافه شد (خط ۴۸۶).
- **تست:** تست `test_full_cycle_manual_trade_reclassification` از `xfail` به تست عادی تبدیل و تقویت شد.
- **نتیجه:** `۲۴۶ passed, ۰ xfailed` (EXIT=0).

---

## ۲. یافته‌های کد فعلی (گام ۱)

تابع `update_trade` قبل از اصلاح (`backend/app/api/trades.py:361-490`):

```python
@router.patch("/{trade_id}")
def update_trade(trade_id: int, data: TradeUpdate, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(
        Trade.id == trade_id, Trade.is_deleted == False
    ).first()
    if not trade:
        raise HTTPException(status_code=404, detail="معامله پیدا نشد")

    # ۱-۴) validation (classification / numbers / dates)

    # ۵. اعمال تغییرات روی trade
    if data.note is not None: trade.note = data.note
    ...
    trade.test_type = new_tt          # نمونه
    ...

    # ✅ محاسبه‌ی مجدد R-Multiple
    if any(...):
        trade.r_multiple = calculate_r_multiple(...)

    db.refresh(trade)                 # ← خط ۴۸۳ (قبل از اصلاح) — بدون commit!

    if trade.close_time is not None and trade.personal_trading_account_id:
        FinanceSyncService(db).sync_closed_trades(trade_ids=[trade.id])

    return {"message": "معامله به‌روزرسانی شد"}
```

**شواهد:**
- `Select-String -Pattern 'commit' app/api/trades.py` فقط این خطوط را نشان می‌داد: `535, 544, 585, 674, 726, 770` (حذف سخت/نرم، حذف گروهی، ایجاد دستی، آپلود/حذف اسکرین‌شات) — **هیچ‌کدام مربوط به `update_trade` نیست**.
- `FinanceSyncService.sync_closed_trades` یک **no-op** است (`return 0`) ⇒ آن هم commit نمی‌کند.
- هیچ تست موجودی `PATCH /api/trades` را پوشش نمی‌داد (grep در `test_trades.py`: صفر).

---

## ۳. تشخیص (گام ۲)

| پرسش | پاسخ |
|:---|:---|
| چرا `db.commit()` نیست؟ | گم‌شدن احتمالی هنگام حذف «پل مالی» در فاز ۲۸؛ یا فراموشی در بازنویسی. عمدی نبوده چون کل endpoint بی‌اثر می‌شده. |
| چرا `db.refresh()` در انتهاست؟ | الگوی مرسوم: بعد از ذخیره، شیء را تازه‌سازی کن. ولی **بدون commit**، `refresh()` با `autoflush=False` تغییرات pending را از DB بازخوانی و **دور می‌ریزد**. |
| چرا کاربر متوجه نمی‌شد؟ | endpoint کد **۲۰۰** برمی‌گرداند (فقط return dict)، پس فرانت‌اند فکر می‌کرد ذخیره شده. |
| راه‌حل | افزودن `db.commit()` **قبل از** `db.refresh(trade)`. ترتیب مهم است: commit ⇒ flush + persist، سپس refresh مقادیر تازه/پیش‌فرض سرور را بار می‌کند و `FinanceSyncService` هم مقدار درست می‌بیند. |

---

## ۴. تغییرات (گام ۳)

`backend/app/api/trades.py` — پیش از `db.refresh(trade)` خطوط زیر افزوده شد:

```diff
+    # فاز ۴۰.۵: تغییرات باید persist شوند.
+    # پیش‌تر `db.commit()` گم شده بود و `db.refresh()` زیر، تغییرات commit‌نشده را
+    # دور می‌ریخت ⇒ PATCH هیچ‌وقت ذخیره نمی‌شد (باگ کشف‌شده در رگرسیون فاز ۴۰).
+    db.commit()
     db.refresh(trade)
```

- `db.add(trade)` لازم نیست (شیء از قبل persistent است و در session ردیابی می‌شود).
- `return` همان dict قبلی (`{"message": ...}`) ماند تا **قرارداد API/فرانت‌اند تغییر نکند**.
- تغییر دیگری انجام نشد (بدون `rollback` اضافه/بازنویسی validation) ⇒ کمترین ریسک.

---

## ۵. تست‌ها (گام ۴)

`backend/tests/test_phase40_full_regression.py` — تست ۱۳:

```diff
-@pytest.mark.xfail(
-    reason=("باگ کشف‌شده در رگرسیون: PATCH ... db.commit() ندارد ..."),
-    strict=False,
-)
 def test_full_cycle_manual_trade_reclassification(client, db_session):
+    """فاز ۴۰.۵: PATCH باید تغییرات را persist کند (پیش‌تر db.commit گم بود)."""
     ...
     r = client.patch(f"/api/trades/{trade_id}", json={
         "test_type": "real_personal", "personal_trading_account_id": pta_id,
+        "pnl": 75.0, "note": "reclassified",
     })
     assert r.status_code == 200, r.text
     db_session.rollback()          # حالا نباید اثر commit را برگرداند
     trade = db_session.get(Trade, trade_id)
     assert trade.test_type == TestType.REAL_PERSONAL
     assert trade.personal_trading_account_id == pta_id
+    assert trade.pnl == 75.0
+    assert trade.note == "reclassified"
```

> تست تقویت شد: علاوه بر `test_type`، پایداری `pnl` و `note` هم بررسی می‌شود.

### اجرا

```powershell
cd backend
venv\Scripts\python.exe -m pytest tests/test_phase40_full_regression.py -q -p no:warnings
venv\Scripts\python.exe -m pytest -q -p no:warnings
```

| دستور | نتیجه |
|:---|:---|
| فایل فاز ۴۰ | ✅ **14 passed** · EXIT=0 |
| کل بک‌اند | ✅ **246 passed, 0 xfailed** · EXIT=0 |

---

## ۶. وضعیت xfail → pass

| قبل (فاز ۴۰) | بعد (فاز ۴۰.۵) |
|:---|:---|
| `245 passed, 1 xfailed` | **`246 passed, 0 xfailed`** |
| `test_full_cycle_manual_trade_reclassification` = **XFAIL** (باگ مستند) | همان تست = **PASS** (باگ رفع‌شده) |

بدهی #۱ فاز ۴۰ **بسته شد** (در `HANDOFF.md` و `PHASE40_IMPL_REPORT.md` هم علامت‌گذاری شد).

---

## ۷. تأیید دست‌نخورده‌بودن دیتابیس واقعی

| شاخص | مقدار |
|:---|:---|
| Backupها (قبل → بعد) | ۳۰ → ۳۰ (هیچ Backup جدید) |
| `trades` در `trading_desk.db` | ۰ |
| SHA-256 | `18c9b024…5bd85` — **بدون تغییر** |

---

## ۸. فایل‌ها

| فایل | تغییر |
|:---|:---|
| `backend/app/api/trades.py` | 🔧 افزودن `db.commit()` پیش از `db.refresh` (خط ۴۸۶) |
| `backend/tests/test_phase40_full_regression.py` | 🔧 حذف `xfail` + تقویت assertionها |
| `HANDOFF.md` | 🔧 بدهی #۱ → رفع‌شده · تعداد تست ۲۴۶ |
| `PHASE40_IMPL_REPORT.md` | 🔧 بدهی #۱ → رفع‌شده |
| `PHASE40_5_PATCH_FIX.md` | ➕ این گزارش |

> ⛔ طبق دستور، commit/push انجام نشد. ⏸️ توقف.
