# 📌 وضعیت پروژه MokTradeDesk

آخرین به‌روزرسانی: [تاریخ]

---

## 🔖 آخرین کامیت
- `5867112` — PHASE 6: Prop percentages in all forms, dollars displayed everywhere

---

## ✅ کارهای انجام‌شده

### PHASE 2 — Trade Contract
- [x] `api/trades.py` — N+1 حل شد (`joinedload`)
- [x] فیلترهای جدید: `personal_account_id`, `strategy_id`, `date_from`, `date_to`
- [x] `TradeUpdate` توسعه یافت (Edit Classification + Execution)
- [x] `TradeValidator` توی `create` و `update` استفاده می‌شه
- [x] UTC-aware datetime

### PHASE 6 — Prop
- [x] `PropRuleEngine` کامل شد:
  - `equity`, `withdrawable_profit`, `suggested_status`
  - `violations` فقط نقض واقعی (نه «هدف سود نرسیده»)
  - منطق `FUNDED_REAL` جدا
  - `validate_withdrawal`
- [x] `withdraw` تکراری توی `api/prop.py` رفع شد
- [x] `check-pass` از `PropRuleEngine` استفاده می‌کنه
- [x] **فرم Create Account → درصد** (کاربر درصد وارد می‌کنه، Backend دلار ذخیره می‌کنه)
- [x] **مودال Pass (قوانین مرحله بعدی) → درصد**
- [x] **نمایش دلار در همه مودال‌ها** (وضعیت کنونی + بررسی و پاس)

---

## ⏳ کارهای باقی‌مونده

### ۱. Edit Stage — ویرایش قوانین مرحله (درصد ↔ دلار)
- [ ] `editRules` State → `_percent`
- [ ] `startEditStage` → تبدیل دلار → درصد (برای نمایش)
- [ ] `handleSaveStageRules` → تبدیل درصد → دلار (برای ذخیره)
- [ ] UI فرم Edit → `(%)` + معادل دلاری

### ۲. Import باگ — `REAL PROP` → `version_id`
- [ ] `ImportPage.tsx` → برای مقصد پراپ، `version_id` هم بگیره
- [ ] `api/imports.py` → validation درست

### ۳. Migration
- [ ] فایل migration خالیه (`194035fd2e2e_initial_schema.py`)
- [ ] باید یا حذف و از نو ساخته بشه، یا با دیتای فعلی هماهنگ بشه
- [ ] قبل از هر تغییر DB، Backup

### ۴. PHASE 7-10
- [ ] Analysis / AnalysisRun
- [ ] Journal / Screenshot
- [ ] Testing / Regression
- [ ] Personal Finance

---

## 📊 وضعیت PHASE ها

| Phase | نام | وضعیت |
|-------|-----|-------|
| PHASE 0 | Architecture Freeze | ✅ |
| PHASE 1 | Migration Foundation | ⚠️ نصفه |
| PHASE 2 | Trade Contract | ✅ |
| PHASE 3 | Trade API | ✅ |
| PHASE 4 | Trade Frontend | ✅ |
| PHASE 5 | Import Pipeline | ⚠️ نصفه |
| PHASE 6 | Prop Rule Engine | ✅ تقریباً |
| PHASE 7 | Analysis / AnalysisRun | ⏳ |
| PHASE 8 | Journal / Screenshot | ⏳ |
| PHASE 9 | Testing | ⏳ |
| PHASE 10 | Personal Finance | ⏳ |

---

## 🖥️ دستورات اجرا

### Backend:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload




### [تاریخ] - دفتر
- Create Account + Edit Stage → درصد (کامیت `fcbc948`)
- همه‌ی Prop forms الان درصد می‌گیرن