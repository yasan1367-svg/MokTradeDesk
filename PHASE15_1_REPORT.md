# 📋 گزارش فاز ۱۵.۱ — رفع باگ‌های P0

> **تاریخ:** ۱۴۰۵/۰۷/۰۳ (2026-09-25)
> **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ هر ۵ مورد رفع شد — ✅ ۳۳/۳۳ تست Backend پاس شد
> **فایل‌های تغییر‌یافته:** `backend/app/api/export.py` · `backend/app/api/finance.py` · `backend/app/main.py` (فقط ۳ فایل)

---

## ۱. `export.py` — حذف کد مرده و تابع تکراری (خطوط ۷۸-۹۵)

### قبل
```python
78 |     return Paragraph(f"<font color='#6B7A94'>{v:{fmt}}</font>", style)
79 |     """BytesIO -> StreamingResponse"""          # ← کد مرده بعد از return
80 |     buffer.seek(0)
81 |     ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
82 | def _build_pdf_response(buffer, filename_prefix):   # ← تعریف تودرتو
83 |     """BytesIO -> StreamingResponse"""
84 |     buffer.seek(0)
85 |     ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
86 |     return StreamingResponse(...)
91 |     return StreamingResponse(...)                   # ← return تکراری/مرده
```

### بعد
```python
78 |     return Paragraph(f"<font color='#6B7A94'>{v:{fmt}}</font>", style)
79 | 
80 | 
81 | def _build_pdf_response(buffer, filename_prefix):
82 |     """BytesIO -> StreamingResponse"""
83 |     buffer.seek(0)
84 |     ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
85 |     return StreamingResponse(
86 |         buffer,
87 |         media_type="application/pdf",
88 |         headers={"Content-Disposition": f"attachment; filename={filename_prefix}_{ts}.pdf"},
89 |     )
```

**نتیجه:** ✅ فقط **یک** تعریف `_build_pdf_response` باقی ماند (تأیید: `def _build_pdf_response = 1`). کد مرده حذف شد و هر ۴ مسیر export سالم است.

---

## ۲. `finance.py` — افزودن `return` به `delete_category`

### قبل (`finance.py:207-215`)
```python
    if not cat:
        raise HTTPException(status_code=404, detail="دسته‌بندی پیدا نشد")
    db.delete(cat)
    db.commit()
# ═════════════════════════════════════════════
# Transactions
```

### بعد (`finance.py:231-242`)
```python
    if not cat:
        raise HTTPException(status_code=404, detail="دسته‌بندی پیدا نشد")
    db.delete(cat)
    db.commit()
    return {"message": "دسته‌بندی حذف شد"}


# ═════════════════════════════════════════════
# Transactions
```

**نتیجه:** ✅ `DELETE /api/finance/categories/{id}` → `200` با بدنهٔ `{"message":"دسته‌بندی حذف شد"}` (پیش‌تر `null` برمی‌گشت).

---

## ۳. `finance.py` — حذف `delete_account` تکراری

### قبل
- تعریف اول در `finance.py:147` و تعریف دوم (override‌کننده) در `finance.py:979` با مسیر یکسان `DELETE /accounts/{account_id}`.

### بعد
- تعریف دوم (خطوط ۹۷۹-۹۸۷) حذف شد؛ تنها **یک** تعریف در `finance.py:147` باقی ماند.

**نتیجه:** ✅ `def delete_account = 1` و `DELETE /accounts route = 1`. مسیر همچنان کار می‌کند (`create 200 → delete 200`) و تعداد کل مسیرهای OpenAPI بدون تغییر **۷۸** ماند.

---

## ۴. `finance.py` — ماسک‌کردن شمارهٔ کارت

### قبل (`finance.py:111`)
```python
            "card_number": a.card_number,
```

### بعد
یک helper امنیتی اضافه شد (`finance.py:21-39`):
```python
def _mask_card_number(value: Optional[str]) -> Optional[str]:
    """ماسک‌کردن شمارهٔ کارت ... مثال: «6037 9911 2233 4455» → «****4455»"""
    if not value:
        return value
    text = str(value).strip()
    if len(text) <= 4:
        return "****"
    return "****" + text[-4:]


def _is_masked(value) -> bool:
    """آیا مقدار، همان مقدار ماسک‌شدهٔ برگشتی از API است؟"""
    return isinstance(value, str) and "*" in value
```
و در پاسخ لیست:
```python
            "card_number": _mask_card_number(a.card_number),
```

**⚠️ نکتهٔ مهم (جلوگیری از رگرسیون):** فرم ویرایش حساب (`frontend/src/components/AccountForm.tsx:52`) مقدار `card_number` را از همان پاسخ لیست پر می‌کند. اگر مقدار ماسک‌شده ذخیره می‌شد، شمارهٔ واقعی **خراب می‌شد**. برای همین در `update_account` یک محافظ اضافه شد:
```python
    for field, value in data.model_dump(exclude_unset=True).items():
        # از ذخیرهٔ مقدار ماسک‌شده (مثل «****4455») جلوگیری کن تا شمارهٔ واقعی خراب نشود
        if field == "card_number" and _is_masked(value):
            continue
        setattr(account, field, value)
```

**نتیجه:** ✅ `GET /api/finance/accounts` → `card_number = "****4455"` و در تست، `PATCH` با مقدار ماسک‌شده شمارهٔ واقعی را دست‌نخورده نگه داشت (`6037991122334455` حفظ شد). هیچ تغییری در Frontend لازم نشد.

---

## ۵. `main.py` — محدودکردن CORS

### قبل (`main.py:36-42`)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],  # ← wildcard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### بعد (`main.py:36-44`)
```python
# توجه: در production دامنهٔ واقعی فرانت‌اند را این‌جا اضافه کنید.
# (پیش‌تر "*" بود که با allow_credentials=True ترکیب ناامن/نامعتبری می‌ساخت.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**نتیجه:** ✅ `"*"` حذف شد. مقدار نهایی تأییدشده: `allow_origins=['http://localhost:5173', 'http://localhost:3000']`.

> **⚠️ یادآوری production:** هنگام deploy، دامنهٔ واقعی فرانت‌اند را به لیست `allow_origins` اضافه کنید.

---

## 🧪 خلاصه اعتبارسنجی

| # | مورد | روش | نتیجه |
|---|---|---|---|
| 1 | `export.py` سالم + تک‌تابعی | import ماژول + شمارش | ✅ `_build_pdf_response = 1` · ۴ مسیر export فعال |
| 2 | `delete_category` return | `DELETE /api/finance/categories/{id}` | ✅ `200 {"message":"دسته‌بندی حذف شد"}` |
| 3 | `delete_account` تکی | شمارش + `POST`/`DELETE` | ✅ تعریف=1 · create 200 · delete 200 |
| 4 | ماسک کارت | `GET /api/finance/accounts` + `PATCH` | ✅ نمایش `****4455` · مقدار واقعی حفظ شد |
| 5 | CORS | بازرسی middleware | ✅ بدون `*` |
| — | کامپایل | `python -m py_compile` (۳ فایل) | ✅ OK |
| — | مسیرها | `app.openapi()` | ✅ ۷۸ مسیر (بدون تغییر) |
| — | تست‌ها | `pytest -q` | ✅ **۳۳ passed** (exit=0) |

### دستورهای اجراشده
```bash
python -m py_compile app/api/export.py app/api/finance.py app/main.py   # OK
python -m pytest -q                                                    # 33 passed
python -c "from app.main import app; print(len(app.openapi()['paths']))" # 78
```

---

## ✅ نتیجه‌گیری

هر ۵ باگ P0 فاز ۱۵.۱ با موفقیت رفع شد:

1. ✅ `export.py` — کد مرده و تابع تکراری حذف شد.
2. ✅ `finance.py` — `delete_category` اکنون بدنهٔ پاسخ دارد.
3. ✅ `finance.py` — `delete_account` تکراری حذف شد.
4. ✅ `finance.py` — شمارهٔ کارت ماسک شد (بدون شکستن فرم ویرایش).
5. ✅ `main.py` — CORS محدود شد.

- **فایل‌های تغییر‌یافته:** فقط ۳ فایل (`export.py`, `finance.py`, `main.py`) — `34 insertions, 22 deletions`.
- **بدون تغییر در Frontend.**
- **بدون رگرسیون:** ۳۳ تست پاس، ۷۸ مسیر سالم، همهٔ endpointهای مربوطه با `TestClient` تأیید شدند.

### پیشنهاد برای فاز بعدی (۱۵.۲ — P1)
- `BE-07` بازآرایی محاسبات داشبورد به SQL Aggregation.
- `BE-08/09/10` رفع N+1ها.
- `FE-01` Code Splitting صفحات.
- `BE-01` فاز ۲: پیاده‌سازی JWT/API-Key.

*گزارش فاز ۱۵.۱ — تهیه‌شده در ۱۴۰۵/۰۷/۰۳.*

