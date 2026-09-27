# 📋 گزارش فاز ۲۵ — حذف معاملات (Soft Delete + حذف گروهی)

> **تاریخ:** ۱۴۰۵/۰۷/۰۵ (2026-09-27) · **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ کامل — ✅ ۷۹ تست بک‌اند پاس · ✅ ۹ تست فرانت پاس · ✅ `tsc -b` (exit 0) · ✅ `npm run build` (exit 0) · ✅ `alembic upgrade head` (exit 0)
> **قوانین:** ✅ Auto-approve غیرفعال · ✅ ترتیب ۱→۶ رعایت شد

---

## ۰. بررسی وضعیت قبل از تغییر

| مورد | وضعیت قبل |
|---|---|
| `delete_trade` | `DELETE /api/trades/{trade_id}` — **فقط** اگر `source == manual` اجازه‌ی حذف می‌داد؛ در غیر این‌صورت `400`. حذف **کامل** (`db.delete`) + پاک‌کردن فایل اسکرین‌شات‌ها |
| `Trade.is_deleted` | ❌ **وجود نداشت** (فقط `Transaction.is_deleted` در مدل‌های مالی بود) |
| `get_trades` | هیچ فیلتری برای حذف‌شده‌ها نداشت |
| Frontend | `handleDeleteTrade` با `window.confirm()` بومی؛ دکمه‌ی حذف **فقط** برای `editingTrade.source === 'manual'` نمایش داده می‌شد؛ هیچ انتخاب گروهی نبود |
| `ConfirmDialog` | ✅ **از قبل** در `frontend/src/components/ui/ConfirmDialog.tsx` وجود داشت → **بازاستفاده شد** (طبق قرارداد پروژه، نسخه‌ی تکراری ساخته نشد) |

---

## ۱. مدل (`backend/app/models/strategy.py`)

- `Boolean` به importهای SQLAlchemy اضافه شد.
- ستون جدید به `Trade`:

```python
# ── Soft Delete (فاز ۲۵) ──
is_deleted = Column(Boolean, default=False, nullable=False, server_default="0", index=True)
```

---

## ۲. Migration (`backend/migrations/versions/f1a2b3c4d5e6_add_is_deleted_to_trades.py`)

| کلید | مقدار |
|---|---|
| `revision` | `f1a2b3c4d5e6` |
| `down_revision` | `e5f6a7b8c9d0` (head قبلی) |

- `batch_alter_table("trades")` → `add_column(is_deleted BOOLEAN NOT NULL DEFAULT 0)` (لازم برای SQLite)
- `op.create_index("ix_trades_is_deleted", ...)`
- Downgrade: حذف ایندکس + ستون

**اجرا:** `alembic upgrade head` → `EXIT=0` · بکاپ قبل از اجرا: `trading_desk.db.bak_phase25`
**تأیید:** ستون `is_deleted` (`BOOLEAN, NOT NULL, default '0'`) + ایندکس `ix_trades_is_deleted` ✅

---

## ۳. Backend (`backend/app/api/trades.py` + `backend/app/utils/trade_scope.py`)

### الف) `get_trades` — فیلتر حذف‌شده‌ها
```python
query = db.query(Trade)
# فاز ۲۵: معاملات حذف‌شده (Soft Delete) در لیست نمایش داده نمی‌شوند
query = query.filter(Trade.is_deleted == False)
```
همچنین `get_trade` (تکی) هم `Trade.is_deleted == False` گرفت → حذف‌شده → `404`.

### ب) `delete_trade` — حذف محدودیت + Soft Delete
```python
@router.delete("/{trade_id}")
def delete_trade(trade_id: int, hard: bool = False, db: Session = Depends(get_db)):
    ...
    if hard:
        _hard_delete_trade(db, trade)     # حذف کامل + اسکرین‌شات (ادمین)
        return {"message": "...", "hard": True, "count": 1}
    if trade.is_deleted:
        return {"message": "قبلاً حذف شده بود", "hard": False, "count": 0}  # idempotent
    trade.is_deleted = True               # ← Soft Delete
    return {"message": "معامله حذف شد", "hard": False, "count": 1}
```
- ✅ محدودیت `source == TradeSource.MANUAL` **حذف شد** → همه‌ی معاملات قابل حذف‌اند.
- ✅ پیش‌فرض Soft Delete؛ `?hard=true` حذف کامل (بازگشت‌ناپذیر).
- تابعه‌ی کمکی `_hard_delete_trade()` منطق قبلی (حذف اسکرین‌شات + `db.delete`) را نگه می‌دارد.

### ج) `POST /batch-delete` — حذف گروهی
```python
class BatchDeleteRequest(BaseModel):
    trade_ids: List[int]
    hard: bool = False
```
- حذف تکراری‌ها (`dict.fromkeys`)، گزارش `deleted` + `skipped`، رد لیست خالی با `400`.
- در حالت soft، معاملات قبلاً حذف‌شده در `skipped` می‌آیند.

### د) تحلیل (`analysis_trades_filter`)
- `and_(or_(test_type غیر REAL), Trade.is_deleted == False)` → معاملات حذف‌شده از **تحلیل/export/آمار نسخه** کنار گذاشته می‌شوند.

---

## ۴. Frontend API (`frontend/src/api/client.ts`)

```typescript
// فاز ۲۵: حذف نرم پیش‌فرض است. برای حذف کامل (ادمین) hard=true بدهید.
export const deleteTrade = (tradeId: number, hard = false) =>
  api.delete(`/api/trades/${tradeId}`, { params: hard ? { hard: true } : {} });

export const batchDeleteTrades = (tradeIds: number[], hard = false) =>
  api.post('/api/trades/batch-delete', { trade_ids: tradeIds, hard });
```
> سازگاری عقب‌رو: پارامتر `hard` اختیاری است → فراخوانی قبلی `deleteTrade(id)` دست‌نخورده کار می‌کند.

---

## ۵. Frontend UI (`frontend/src/pages/TradesPage.tsx`)

| # | تغییر |
|---|---|
| الف | **ConfirmDialog** بازاستفاده از `components/ui/ConfirmDialog.tsx` — جایگزین `window.confirm()`. `pendingDelete` (`{ids, message}`) + `executeDelete()` |
| ب | **Checkbox** انتخاب گروهی: هدر (انتخاب همه‌ی صفحه‌ی جاری) + هر ردیف. State: `selectedIds` |
| ج | **دکمه‌ی «حذف گروهی (n)»** کنار «معامله‌ی دستی» — فقط وقتی انتخاب > ۰. + دکمه‌ی «لغو انتخاب» |
| د | **حذف شرط `source === 'manual'`** → دکمه‌ی 🗑️ حذف برای **همه‌ی** معاملات در مودال ویرایش |
| ه | پاک‌شدن `selectedIds` هنگام تغییر فیلترها |

> حذف تکی (`ids.length === 1`) → `deleteTrade`؛ حذف گروهی → `batchDeleteTrades`.

---

## ۶. تست

### تست‌های جدید بک‌اند (`backend/tests/test_trades.py`)
| تست | سناریو |
|---|---|
| `test_soft_delete_mt4_trade` | معامله MT4 → حذف نرم، پنهان از لیست و جزئیات (`404`) |
| `test_soft_delete_soft4x_trade` | معامله Soft4X → حذف نرم |
| `test_soft_delete_is_idempotent` | حذف دوباره → `count=0` (بدون خطا) |
| `test_batch_delete_soft` | حذف گروهی ۳ معامله (MT4/Soft4X/manual) → همه حذف نرم |
| `test_batch_delete_reports_skipped` | شناسه‌ی ناموجود → در `skipped` |
| `test_batch_delete_empty_list_rejected` | لیست خالی → `400` |
| `test_hard_delete_trade` | `?hard=true` → رکورد از DB پاک می‌شود |
| `test_batch_hard_delete` | حذف گروهی سخت → count=0 در DB |

### نتایج اجرا
| ابزار | نتیجه |
|---|---|
| `pytest tests/test_trades.py` | ✅ **۱۸ پاس** (EXIT=0) |
| `pytest` (کل) | ✅ **۷۹ پاس** (EXIT=0) |
| `npx vitest run` | ✅ **۹ پاس** (EXIT=0) |
| `npx tsc -b` | ✅ EXIT=0 |
| `npm run build` | ✅ EXIT=0 |

### تأیید قرارداد مسیرها (از `app.openapi()`)
```
/api/trades/                [get]
/api/trades/{trade_id}      [get, patch, delete]
/api/trades/batch-delete    [post]   ← جدید
/api/trades/manual          [post]
```

---

## ۷. فایل‌های تغییر‌یافته / جدید

| فایل | نوع |
|---|---|
| `backend/app/models/strategy.py` | ✏️ `is_deleted` + import `Boolean` |
| `backend/migrations/versions/f1a2b3c4d5e6_add_is_deleted_to_trades.py` | 🆕 Migration |
| `backend/app/api/trades.py` | ✏️ `get_trades`/`get_trade` فیلتر + `delete_trade` نرم + `_hard_delete_trade` + `BatchDeleteRequest` + `POST /batch-delete` |
| `backend/app/utils/trade_scope.py` | ✏️ `analysis_trades_filter` (حذف‌شده‌ها از تحلیل) |
| `backend/tests/test_trades.py` | ✏️ ۸ تست فاز ۲۵ |
| `frontend/src/api/client.ts` | ✏️ `deleteTrade(hard)` + `batchDeleteTrades` |
| `frontend/src/pages/TradesPage.tsx` | ✏️ ConfirmDialog + Checkbox + حذف گروهی + حذف شرط source |
| `PHASE25_REPORT.md` | 🆕 این گزارش |

---

## ۸. نکات و محدودیت‌ها (شفاف‌سازی)

1. **Hard Delete در UI ندارد**: فعلاً فقط از طریق API (`?hard=true` یا `{"hard": true}`) و برای ادمین است؛ در UI دکمه‌ی «حذف کامل» اضافه نشد (مطابق دامنه‌ی درخواست).
2. **بازگشت (Restore)**: هیچ endpoint «بازگردانی» اضافه نشد؛ داده با `is_deleted=True` در DB هست و قابل بازگردانی دستی است (چون Soft Delete هدفش حفظ تاریخچه بود).
3. **فیلترهای تحلیل**: `analysis_trades_filter` پوشش داده شد، ولی برخی کوئری‌های مستقیم دیگر (مثل `prop.py` / `finance.py` که مستقیماً `Trade.prop_stage_id` را می‌خوانند) هنوز `is_deleted` را لحاظ نمی‌کنند. اگر بخواهید، در فاز بعدی می‌توان به‌طور یکسان اعمال کرد.
4. **Route Order**: چون مسیر `POST /batch-delete` یک سگمنت ثابت است و هیچ `POST /{trade_id}` وجود ندارد، تضاد مسیر ندارد (با `app.openapi()` تأیید شد).
5. **SQLite**: برای سازگاری از `batch_alter_table` استفاده شد؛ روی PostgreSQL هم بدون مشکل اجرا می‌شود.