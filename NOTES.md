# 📌 وضعیت پروژه MokTradeDesk

آخرین به‌روزرسانی: [تاریخ]

---

## 🔖 آخرین کامیت
- `26c1487` — Copilot WIP: prop_rule_engine + trade contract + import pipeline
- Push شده به GitHub ✅

---

## 🎯 نقشه‌ی راه (طبق بلوپرینت)

- [ ] **PHASE 2** — Trade Contract / Models / Validation  ← **الان اینجاییم**
- [ ] **PHASE 3** — Trades API
- [ ] **PHASE 4** — Trades Frontend
- [ ] **PHASE 5** — Import Pipeline
- [ ] **PHASE 6** — Prop Rule Engine (کامل کردن)
- [ ] **PHASE 7** — Analysis / AnalysisRun
- [ ] **PHASE 8** — Journal / Screenshot
- [ ] **PHASE 9** — Testing / Regression
- [ ] **PHASE 10** — Future Personal Finance

---

## ✅ کارهای انجام‌شده (Copilot WIP)

- [x] `PropRuleEngine` اولیه ساخته شد
- [x] `withdraw` تکراری توی `api/prop.py` رفع شد
- [x] `check_pass_ready` از `PropRuleEngine` استفاده می‌کنه
- [x] `Tag` و `PropAccountTag` از `migrations/env.py` حذف شدن (خطای import رفع شد)
- [x] فایل‌های فرانت تغییر کردن (ImportPage، JournalPage، TradesPage، ...)

---

## ⚠️ کارهای باقی‌مونده در `PropRuleEngine` و `api/prop.py`

- [ ] `pass_stage` باید از `PropRuleEngine.evaluate_stage` برای validation استفاده کنه
- [ ] `withdraw` باید `amount` رو با `withdrawable_profit` چک کنه
- [ ] `withdraw` خط `stage.current_profit -= amount` باید حذف بشه (Double Counting)
- [ ] `PropRuleEngine` فیلدهای `suggested_status`, `equity`, `withdrawable_profit`, `total_withdrawn` رو اضافه کنه
- [ ] `PropRuleEngine` منطق `FUNDED_REAL` رو جدا کنه
- [ ] `violations` فقط نقض قوانین باشه (نه «هدف سود نرسیده»)
- [ ] `profit_target_percent` rename بشه
- [ ] `AnalysisService.calculate_stage_progress` حذف بشه (تکراریه)
- [ ] import های تکراری توی `get_prop_analytics` حذف بشن
- [ ] `get_prop_analytics` اسم `total_profit` رو به `remaining_profit` تغییر بده

---

## 🚧 کارهای باقی‌مونده در `api/trades.py` (PHASE 2)

- [ ] `ManualTradeCreate` فیلد `personal_account_id` رو اضافه کنه
- [ ] `create_manual_trade` از `TradeValidator` استفاده کنه
- [ ] `GET /trades` اطلاعات `personal_account` رو برگردونه
- [ ] فیلترها توسعه پیدا کنن
- [ ] Edit کنترل‌شده برای Classification

---

## 🚧 کارهای باقی‌مونده در Import (PHASE 5)

- [ ] Pipeline: Upload → Parse → Normalize → Validate → Duplicate → Preview → Confirm → DB Transaction
- [ ] `ImportBatch` model
- [ ] Duplicate Detection
- [ ] Direction validation (نه پیش‌فرض Sell)

---

## 🚧 Database / Migration

- [ ] فایل migration فعلی **خالیه** (`194035fd2e2e_initial_schema.py`)
- [ ] باید یا حذف و از نو ساخته بشه، یا با دیتای فعلی هماهنگ بشه
- [ ] قبل از هر تغییر DB، **Backup** گرفته بشه

---

## 📌 تصمیمات مهم

- ✅ GitHub از حالت Read-only خارج شد (push مجاز شد برای sync بین خونه و دفتر)
- ⚠️ بلوپرینت باید آپدیت بشه (بند ۲ درباره‌ی GitHub)
- ⚠️ `target_personal_account_id` توی Withdrawal — temporary، در آینده باید `FinancialAccount` بشه
- ⚠️ Trade PnL و Cashflow نباید Double Count بشن

---

## 🖥️ نکات اجرا

### بک‌اند:
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload