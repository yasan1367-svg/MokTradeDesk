# 📋 گزارش فازهای ۱۵.۱۱ + ۱۵.۱۲

> **تاریخ:** ۱۴۰۵/۰۷/۰۳ (2026-09-25)
> **مدل:** `deepseek/deepseek-v4.1-flash`
> **ترتیب اجرا:** ۱۵.۱۱ ← ۱۵.۱۲
> **وضعیت کلی:** ✅ هر دو فاز انجام شد — ✅ `py_compile` OK · ✅ `pytest` ۳۳ تست پاس · ✅ Frontend `tsc` + `build` بدون تغییر/رگرسیون

| فاز | عنوان | وضعیت |
|---|---|---|
| ۱۵.۱۱ | محدودیت حجم آپلود فایل | ✅ انجام شد (helper مشترک + ۴ نقطه) |
| ۱۵.۱۲ | Missing endpoint در `finance.py` | ✅ انجام شد (CRUD کامل برداشت‌ها) |

**فایل‌های تغییر‌یافته:**
- `backend/app/utils/uploads.py` — **جدید**
- `backend/app/api/trades.py` · `backend/app/api/personal.py` · `backend/app/api/imports.py`
- `backend/app/api/finance.py`
- **بدون تغییر Frontend**

---

## 🎯 فاز ۱۵.۱۱ — محدودیت حجم آپلود فایل

### مشکل (قبل)
هر ۴ endpoint آپلود، فایل را **بدون هیچ سقف حجمی** می‌خواندند:

```python
# trades.py:583 (upload_screenshot)
content = await file.read()          # ← بدون بررسی حجم

# personal.py:48 (upload_review_screenshot)
content = await file.read()          # ← بدون بررسی حجم

# imports.py:16 (import_soft4x)
with tempfile.NamedTemporaryFile(...) as tmp_file:
    content = await file.read()      # ← بدون بررسی حجم
    tmp_file.write(content)

# imports.py:94 (import_mt4)
content = await file.read()          # ← بدون بررسی حجم
```

⇒ آپلود یک فایل حجیم می‌توانست حافظه/دیسک سرور را پر کند (یافتهٔ `BE-05` در بررسی جامع).

### راه‌حل: helper مشترک جدید
فایل **جدید** `backend/app/utils/uploads.py`:
```python
from fastapi import HTTPException, UploadFile

# سقف حجم آپلود: ۱۰ مگابایت
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
MAX_UPLOAD_SIZE_MB = MAX_UPLOAD_SIZE // (1024 * 1024)


async def read_upload_limited(file: UploadFile, max_size: int = MAX_UPLOAD_SIZE) -> bytes:
    """خواندن محتوای فایل آپلودی با بررسی سقف حجم.

    - ابتدا از `file.size` (اگر Starlette آن را پر کرده باشد) استفاده می‌شود.
    - در غیر این صورت با `seek(0, 2)` + `tell()` حجم محاسبه و مکان به ابتدا برمی‌گردد.
    - در صورت عبور از سقف → HTTPException(413)
    - در پایان، حجم واقعی خوانده‌شده هم دوباره بررسی می‌شود (محافظت مضاعف).
    """
    size = getattr(file, "size", None)
    if size is None:
        try:
            file.file.seek(0, 2)
            size = file.file.tell()
            file.file.seek(0)
        except Exception:
            size = None

    if size is not None and size > max_size:
        raise HTTPException(status_code=413, detail=_too_large_detail())

    content = await file.read()

    if len(content) > max_size:
        raise HTTPException(status_code=413, detail=_too_large_detail())

    return content
```

### اعمال در ۴ نقطه (بعد)
| فایل | قبل | بعد |
|---|---|---|
| `trades.py:605` | `content = await file.read()` | `content = await read_upload_limited(file)` |
| `personal.py:69` | `content = await file.read()` | `content = await read_upload_limited(file)` |
| `imports.py:40` | `content = await file.read()` | `content = await read_upload_limited(file)` |
| `imports.py:119` | `content = await file.read()` | `content = await read_upload_limited(file)` |

+ `from ..utils.uploads import read_upload_limited` در هر ۳ فایل.

### تست ✅
```
=== 15.11: MAX_UPLOAD_SIZE ===
  MAX_UPLOAD_SIZE = 10485760 bytes (10 MB)

=== 15.11: helper directly ===
  small file -> 1024 bytes  OK
  large file -> HTTPException 413

=== 15.11: endpoint (trades screenshot, 11MB png) ===
  trade id = 1
  status = 413 | detail = «حجم فایل بیش از حد مجاز است (حداکثر 10 مگابایت)»
  small file status = 200
```
- فایل ۱۰MB → ✅ قبول
- فایل ۱۱MB (هم از طریق helper و هم از طریق endpoint واقعی) → ✅ **HTTP 413** با پیام فارسی
- فایل کوچک → ✅ 200 (بدون رگرسیون)

---

## 🎯 فاز ۱۵.۱۲ — Missing endpoint در `finance.py` (CRUD برداشت‌ها)

### 🔍 بررسی وضعیت قبل (طبق درخواست)
ابتدا وضعیت موجود بررسی شد:

| مورد | وضعیت قبل |
|---|---|
| `TransactionType.WITHDRAWAL = "withdrawal"` | ✅ وجود دارد (`models/finance.py:36`) |
| `GET /api/finance/withdrawals/stats` | ✅ وجود دارد (`finance.py:429`) |
| مدل جداگانهٔ Withdrawal در finance | ❌ ندارد (فقط `PropWithdrawal` در `models/prop.py` برای مراحل پراپ) |
| `GET /api/finance/withdrawals` (لیست) | ❌ **نبود** |
| `POST /api/finance/withdrawals` (ایجاد) | ❌ **نبود** |
| `PUT/PATCH /api/finance/withdrawals/{id}` | ❌ **نبود** |
| `DELETE /api/finance/withdrawals/{id}` | ❌ **نبود** |

**نتیجهٔ بررسی:** برداشت‌های مالی در همان مدل `Transaction` با `type=WITHDRAWAL` ذخیره می‌شوند (همان‌طور که `get_withdrawal_stats` و `charts/cashflow` می‌خوانند). فقط **CRUD کامل نبود** — که اضافه شد.

### راه‌حل: Schema + Helper + ۴ Endpoint

#### ۱) Schemas (بعد از `TransactionUpdate`)
```python
class WithdrawalCreate(BaseModel):
    account_id: int
    amount: float
    currency: Currency = Currency.USD
    date: Optional[datetime] = None
    description: Optional[str] = None
    category_id: Optional[int] = None


class WithdrawalUpdate(BaseModel):
    account_id: Optional[int] = None
    amount: Optional[float] = None
    currency: Optional[Currency] = None
    date: Optional[datetime] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
```

#### ۲) Helperهای مشترک
```python
def _serialize_withdrawal(w: Transaction) -> dict:
    return {
        "id": w.id, "account_id": w.account_id,
        "account_name": w.account.name if w.account else None,
        "category_id": w.category_id,
        "category_name": w.category.name if w.category else None,
        "amount": w.amount,
        "currency": w.currency.value if w.currency else None,
        "date": w.date.isoformat() if w.date else None,
        "description": w.description,
        "type": w.type.value if w.type else None,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }


def _withdrawal_query(db: Session):
    """کوئری پایهٔ برداشت‌ها (فقط type=withdrawal و حذف‌نشده)"""
    return db.query(Transaction).filter(
        Transaction.is_deleted == False,
        Transaction.type == TransactionType.WITHDRAWAL,
    )
```

#### ۳) Endpointهای CRUD
| متد | مسیر | توضیح |
|---|---|---|
| `GET` | `/api/finance/withdrawals` | لیست + فیلتر `account_id`, `date_from`, `date_to` |
| `POST` | `/api/finance/withdrawals` | ایجاد (بررسی وجود حساب → ساخت `Transaction(type=WITHDRAWAL)`) |
| `PUT` + `PATCH` | `/api/finance/withdrawals/{withdrawal_id}` | ویرایش (هر دو متد روی **یک** هندلر) |
| `DELETE` | `/api/finance/withdrawals/{withdrawal_id}` | حذف **نرم** (`is_deleted = True`، هم‌سبک با `delete_transaction`) |

> **دربارهٔ PUT/PATCH:** درخواست، `PUT` بود؛ اما قرارداد کل پروژه `PATCH` است. برای رعایت هر دو، **یک** هندلر با دو decorator ثبت شد:
> ```python
> @router.put("/withdrawals/{withdrawal_id}")
> @router.patch("/withdrawals/{withdrawal_id}")
> def update_withdrawal(...):
> ```
> ⇒ بدون تکرار منطق، هر دو متد کار می‌کنند.

### ⚠️ نکتهٔ مهم: ترتیب مسیرها (Route Ordering)
مسیر `/withdrawals/stats` **قبل از** `/withdrawals/{withdrawal_id}` تعریف شده است. چون FastAPI به ترتیب اعلان match می‌کند، `stats` به‌عنوان `{withdrawal_id}` گرفته نمی‌شود:
```
/api/finance/withdrawals               -> ['get', 'post']
/api/finance/withdrawals/stats         -> ['get']            ← دست‌نخورده و سالم
/api/finance/withdrawals/{withdrawal_id} -> ['delete', 'patch', 'put']
```
✅ تأیید شد که `GET /api/finance/withdrawals/stats` همچنان `200` می‌دهد.

### تست ✅ (در Swagger / TestClient)
```
=== 15.12: withdrawals CRUD flow ===
  create account: 200
  stats before: 200 (route ordering check)
  POST /withdrawals:      200 {'id': 2, 'message': 'برداشت ثبت شد'}
  GET  /withdrawals:      200 count = 1
  GET  ?account_id=:      200
  PUT  /withdrawals/{id}: 200
  PATCH /withdrawals/{id}:200
  DELETE /withdrawals/{id}:200 {'message': 'برداشت حذف شد'}
  GET after delete count: 0          ← حذف نرم کار می‌کند
  GET missing id -> 404              ← مدیریت خطا درست است
=== cleanup ===
  delete account: 200
```
همهٔ مسیرها در OpenAPI/Swagger ثبت شده‌اند و کامل کار می‌کنند. ✅

---

## 🧪 نتایج تست (نهایی)

### Backend
| دستور | نتیجه |
|---|---|
| `python -m py_compile finance.py trades.py personal.py imports.py utils/uploads.py` | ✅ `py_compile_exit=0` |
| `pytest -q` | ✅ **۳۳ passed** |
| تست آپلود ۱۱MB (helper + endpoint واقعی) | ✅ `413` |
| تست آپلود ۱۰۰ بایت | ✅ `200` |
| CRUD کامل برداشت‌ها | ✅ GET/POST/PUT/PATCH/DELETE همه `200` |
| `GET /withdrawals/stats` (بررسی تداخل مسیر) | ✅ `200` |

### Frontend (تغییری نداشت — فقط به‌عنوان اطمینان)
| دستور | نتیجه |
|---|---|
| `npx tsc -b --force` | ✅ `TSC_EXIT=0` |
| `npm run build` | ✅ `BUILD_EXIT=0` · built in 3.20s · entry chunk 240.85 kB |

---

## ✅ نتیجه‌گیری

| فاز | خروجی |
|---|---|
| **۱۵.۱۱** | helper مشترک `utils/uploads.py` با سقف **۱۰ مگابایت** ساخته شد و در **۴ نقطهٔ آپلود** (`trades`, `personal`, `imports`×۲) اعمال شد. فایل بزرگ → **HTTP 413** با پیام فارسی. |
| **۱۵.۱۲** | CRUD کامل برداشت‌ها اضافه شد: `GET`/`POST` + `PUT`/`PATCH` + `DELETE` (حذف نرم) روی `Transaction(type=withdrawal)`. تداخل با `/withdrawals/stats` بررسی و تأیید شد. |

### 📌 یادداشت‌ها
- **مشکلی رخ نداد که نیاز به توقف باشد.**
- **بدون تغییر Frontend:** هر دو فاز بک‌اندی بودند. (پیشنهاد: افزودن توابع `client.ts` و UI برای برداشت‌ها می‌تواند فاز بعدی باشد.)
- **بدون تغییر در balance حساب‌ها:** طبق رفتار موجود پروژه، `create_transaction` هم balance را تغییر نمی‌دهد؛ برای یکنواختی، CRUD برداشت‌ها هم فقط رکورد ثبت می‌کند. (در صورت نیاز به به‌روزرسانی خودکار موجودی، باید به‌صورت سراسری در `transactions` پیاده شود.)
- **فایل‌های موقت:** همهٔ اسکریپت‌های تست/تأیید پس از استفاده پاک شدند.

*گزارش فازهای ۱۵.۱۱ + ۱۵.۱۲ — تهیه‌شده در ۱۴۰۵/۰۷/۰۳.*

