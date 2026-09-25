# 📋 گزارش فاز ۱۶ — Payout History (تاریخچهٔ برداشت‌ها)

> **تاریخ:** ۱۴۰۵/۰۷/۰۳ (2026-09-25) · **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ کامل — ✅ `pytest` ۳۳ پاس · ✅ `tsc` + `build` موفق (chunk جدید ۱۴.۱۶ kB)

---

## ۱. بررسی وضعیت قبل

| مورد | یافته |
|---|---|
| `PropWithdrawal` (`models/prop.py:102-113`) | `id` · `prop_stage_id` (FK، NOT NULL) · `amount` · `withdrawal_date` · `note` · `destination_account_id` (FK accounts، nullable) — relationships: `stage`, `destination_account` |
| مدل بروکر | ❌ **وجود ندارد** — بروکر فقط `AccountType.BROKER` روی `Account` است ⇒ برداشت بروکر = `Transaction(type=withdrawal)` |
| endpointهای موجود | `POST /api/prop/stages/{id}/withdraw` + `GET /api/prop/stages/{id}/withdrawals` — **لیست کلی/آمار/ویرایش/حذف نداشتند** |

---

## ۲. Backend — تغییرات

### ۲.۱ `prop.py` — منطق مشترک + ۵ endpoint
یک helper مشترک ساخته شد و `withdraw` موجود هم به آن منتقل شد (بدون تکرار منطق):
```python
def _create_payout_record(db, stage_id, amount, note, destination_account_id, withdrawal_date=None):
    # اعتبارسنجی FUNDED_REAL + PropRuleEngine.validate_withdrawal
    # ساخت PropWithdrawal + Transaction(type=withdrawal) + بهروزرسانی موجودیها
```

| متد | مسیر | توضیح |
|---|---|---|
| `GET` | `/api/prop/payouts` | لیست کلی + فیلتر `firm_id`, `currency`, `date_from`, `date_to` (با `joinedload`، بدون N+1) |
| `GET` | `/api/prop/payouts/stats` | total / count / average / largest / `monthly[]` / `by_firm[]` (محاسبات در SQL) |
| `POST` | `/api/prop/payouts` | ثبت برداشت (`prop_stage_id` در body) |
| `PUT` **+** `PATCH` | `/api/prop/payouts/{id}` | ویرایش (+ اصلاح `total_withdrawn`) |
| `DELETE` | `/api/prop/payouts/{id}` | حذف (+ بازگرداندن `total_withdrawn`) |

### ۲.۲ `broker.py` — **جدید** (router با prefix `/api/broker`)
چون مدل جدا برای بروکر نیست، از `Transaction` روی حسابهای BROKER استفاده شد:
```python
# برداشت بروکر = Transaction(type=WITHDRAWAL) join Account(type=BROKER)
```
| متد | مسیر |
|---|---|
| `GET` | `/api/broker/payouts` (فیلتر `account_id`, `currency`, بازهٔ تاریخ) |
| `GET` | `/api/broker/payouts/stats` (total/count/average/largest/`monthly[]`/`by_account[]`) |

> ثبت/ویرایش/حذف بروکر از همان `/api/finance/withdrawals` (فاز ۱۵.۱۲) استفاده می‌کند — بدون تکرار منطق.

### ۲.۳ `main.py`
```python
app.include_router(broker.router, prefix="/api/broker", tags=["broker"])
```
**تعداد مسیرهای OpenAPI: 78 → 85** ✅

---

## ۳. Frontend — تغییرات

### ۳.۱ صفحهٔ جدید `PayoutHistoryPage.tsx` (۱۴.۱۶ kB · lazy chunk)
- **تبها:** «🏢 پراپ» / «📈 بروکر»
- **فیلترها:** از تاریخ، تا تاریخ (هر دو با `PersianDateInput` شمسی)، ارز، شرکت پراپ
- **آمار:** مجموع / تعداد / میانگین / بزرگترین برداشت (کارت با گرادیان theme-aware)
- **نمودار:** `recharts` BarChart برداشتها در طول زمان + مقایسهٔ شرکتها/حسابها
- **جدول:** تاریخ (شمسی) · مبلغ · پراپ/بروکر · مرحله · حساب مقصد · توضیحات (+ حذف)
- **فرم «ثبت برداشت جدید»:** مرحله (فقط `funded_real`) · مبلغ · حساب مقصد · تاریخ شمسی · توضیحات
- **Skeleton** (`RiskSkeleton`) هنگام بارگذاری · **EmptyState** برای حالت خالی · **Toast** برای پیامها
- کاملاً **Dark Mode** (توکنهای `var(--*)`) و **RTL**

### ۳.۲ `client.ts` — ۷ تابع جدید
`getPropPayouts` · `getPropPayoutsStats` · `createPropPayout` · `updatePropPayout` · `deletePropPayout` · `getBrokerPayouts` · `getBrokerPayoutsStats`

### ۳.۳ ناوبری
- `App.tsx`: `lazy` + نوع `Page` + `PAGE_TITLES` + رندر زیر `ErrorBoundary` (در CommandPalette خودکار اضافه شد چون از `PAGE_TITLES` ساخته می‌شود)
- `Sidebar.tsx`: آیتم «💸 برداشتها» در گروه «حسابها»

### ۳.۴ اتصال به بخشهای دیگر
- **داشبورد:** کارت «💸 آمار برداشتها» (مجموع/تعداد پراپ و بروکر) با دکمهٔ «مشاهده همه →» به صفحهٔ برداشتها
- **مالی:** برداشت پراپ همان `Transaction(type=withdrawal)` را میسازد (اتصال موجود حفظ و از طریق helper مشترک یکپارچه شد)
- **پراپ:** صفحهٔ جدید از `PropWithdrawal` میخواند

---

## ۴. تست

| مورد | نتیجه |
|---|---|
| `py_compile` (prop.py, broker.py, main.py) | ✅ `0` |
| `app.openapi()` | ✅ **۸۵ مسیر** · ۵ مسیر payout ثبت شد |
| `GET /api/prop/payouts` · `/stats` · `/stats?currency=USD` | ✅ `200` |
| `GET /api/broker/payouts` · `/stats` | ✅ `200` |
| PUT/DELETE/`POST` با id نامعتبر | ✅ `404` (مدیریت خطا) |
| `POST /api/prop/stages/{id}/withdraw` (پس از refactor) | ✅ سالم (helper مشترک) |
| `pytest -q` | ✅ **۳۳ passed** |
| `npx tsc -b --force` | ✅ `TSC_EXIT=0` |
| `npm run build` | ✅ `BUILD_EXIT=0` · `PayoutHistoryPage` = 14.16 kB · entry = 241.29 kB |

### 📌 نکتهٔ فنی (رفعشده در مسیر)
`_PAYOUT_EAGER` که اوّل بهصورت ثابت ماژول تعریف شده بود، هنگام import باعث `InvalidRequestError: JournalReview` میشد (پیکربندی mapper پیش از import کامل مدلها). به **تابع** `_payout_eager()` تبدیل شد تا ارزیابی به زمان اجرا موکول شود.

### 📌 محدودیتها
- **تست چشمی مرورگر انجام نشد** (محیط headless) — اعتبارسنجی با `tsc` + `build` + تست API.
- فرم «ثبت برداشت جدید» فقط برای تب **پراپ** است (طبق درخواست، بروکر فقط لیست+آمار دارد؛ ثبت بروکر از صفحهٔ مالی).

*گزارش فاز ۱۶ — تهیهشده در ۱۴۰۵/۰۷/۰۳.*
