# 🚀 Sprint 7 — جایگزینی `datetime.utcnow()` با `datetime.now(timezone.utc)`

**تاریخ**: ۱۴۰۴/۰۷/۰۲ (۲۰۲۶-۰۹-۲۴)
**وضعیت**: ✅ کامل و تست‌شده

---

## 📌 خلاصه

در این اسپرینت، تمام موارد `datetime.utcnow()` (deprecated در Python 3.12) در فایل‌های بک‌اند پروژه با `datetime.now(timezone.utc)` جایگزین شدند.

## ✅ موارد اصلاح‌شده

| فایل | تعداد | نوع تغییر |
|------|-------|-----------|
| `backend/app/api/personal.py` | ۱ | `datetime.utcnow()` ← `datetime.now(timezone.utc)` (مقدار مستقیم) |
| `backend/app/api/prop.py` | ۴ | `datetime.utcnow()` ← `datetime.now(timezone.utc)` (مقدار مستقیم) |
| `backend/app/models/personal.py` | ۵ | `default=datetime.utcnow` ← `default=lambda: datetime.now(timezone.utc)` |
| `backend/app/models/prop.py` | ۷ | `default=datetime.utcnow` ← `default=lambda: datetime.now(timezone.utc)` |
| `backend/app/models/settings.py` | ۱ (+۱ onupdate) | `default=..., onupdate=...` ← `default=..., onupdate=lambda: ...` |
| `backend/app/models/strategy.py` | ۸ | ۷ مورد `default=datetime.utcnow` + ۱ مورد `datetime.now(timezone.utc)` بدون lambda |

**جمع کل**: ۲۷ مورد در ۶ فایل

## 🔧 تفاوت دو نوع تغییر

### نوع ۱: مقدار مستقیم (API files)
برای مواردی که `datetime.utcnow()` در وسط یک تابع صدا زده می‌شود:
```python
# قبل
transaction_date = datetime.utcnow()
# بعد
transaction_date = datetime.now(timezone.utc)
```

### نوع ۲: lambda برای Column default (Model files)
برای مواردی که `datetime.utcnow` به عنوان مرجع تابع به `default=` داده شده است:
```python
# قبل
created_at = Column(DateTime, default=datetime.utcnow)  # ✅ callable reference
# بعد
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))  # ✅ lazy evaluation
```

⚠️ **مهم**: اگر از `datetime.now(timezone.utc)` با پرانتز استفاده می‌شد، مقدار یک بار در زمان import ثابت می‌ماند و تمام رکوردها timestamp یکسان می‌گرفتند. استفاده از `lambda:` مشکل را برطرف کرد.

### فایل‌هایی که از قبل درست بودند
| فایل | توضیح |
|------|--------|
| `backend/app/api/analytics.py` | قبلاً در Sprint 5/6 اصلاح شده بود |
| `backend/app/api/export.py` | از ابتدا با `datetime.now(timezone.utc)` نوشته شده |
| `backend/app/api/trades.py` | از ابتدا `timezone` import داشت |

## 🧪 تست

| آیتم | نتیجه |
|------|--------|
| Import همه مدل‌ها | ✅ بدون خطا |
| Import همه APIها | ✅ بدون خطا |
| `datetime.utcnow` در فایل‌های backend | ✅ **۰ مورد باقی‌مانده** |

## 📊 آمار نهایی

| شاخص | عدد |
|------|-----|
| فایل‌های تغییر‌یافته | ۶ |
| موارد `datetime.utcnow` اصلاح‌شده | ۲۷ |
| موارد باقی‌مانده | **۰** |
| import `timezone` اضافه‌شده | ۵ فایل (personal.py قبلاً import داشت) |
| زمان اجرا | ~۲۰ دقیقه |

## 📝 نکات

1. **فایل‌های مستندات (ANALYSIS.md, SUGGESTIONS.md)** عمداً تغییر نکردند چون هنوز `datetime.utcnow()` را به عنوان "کار باقی‌مانده" ذکر می‌کنند — این مستندات نیازی به اصلاح ندارند.
2. **فایل‌های migration** بررسی نشدند چون migration‌ها snapshot از وضعیت قبلی هستند و نباید تغییر کنند.
3. **Frontend** نیازی به تغییر نداشت چون `datetime.utcnow` مختص Python است.

---
*این گزارش در تاریخ ۱۴۰۴/۰۷/۰۲ تکمیل شده است.*