# 📊 REMAINING BLUEPRINT ITEMS — MokTradeDesk

**تاریخ تحلیل:** ۱۴۰۴/۰۷/۰۳
**نوع تحلیل:** بررسی کد واقعی (نه مستندات قدیمی)

---

## ✅ نتیجه مهم: تمام ۴ باگ P0 قبلاً رفع شده‌اند

تحلیل اولیه بر اساس مستندات قدیمی (`ANALYSIS.md`، `SUGGESTIONS.md` که مربوط به قبل از Sprint 7 بودند) انجام شده بود. بررسی کد واقعی نشان داد که:

| باگ | وضعیت در کد | محل دقیق |
|:---|:---:|:---|
| `_summarize` از raw pnl | ✅ رفع شده — از `_net_pnl()` | `analysis_service.py:639-647` |
| `_calculate_consistency` از raw pnl | ✅ رفع شده — از `_net_pnl()` | `analysis_service.py:514-516` |
| `_calculate_max_consecutive_losses` از raw pnl | ✅ رفع شده — از `_net_pnl()` | `analysis_service.py:497` |
| Import version_id برای prop/personal | ✅ رفع شده | `imports.py:62, 70` |
| `calculate_stage_progress` تکراری | ✅ حذف شده | در کد یافت نشد |
| AnalysisRun | ✅ پیاده‌سازی شده | `strategy.py:193` + `analysis_service.py:73` |

---

## 📌 وضعیت PHASE‌های بلوپرینت (بر اساس کد واقعی)

| Phase | نام | وضعیت | توضیح |
|:---|:---|:---:|:---|
| PHASE 0 | Architecture Freeze | ✅ | کامل |
| PHASE 1 | Migration Foundation | ✅ | کامل (`c4838cd01bbd`) |
| PHASE 2 | Trade Contract | ✅ | کامل |
| PHASE 3 | Trades API | ✅ | کامل + Pagination |
| PHASE 4 | Trades Frontend | ✅ | کامل |
| PHASE 5 | Import Pipeline | ✅ | کامل (version_id fix شده) |
| PHASE 6 | Prop Rule Engine | ✅ | کامل |
| PHASE 7 | Analysis Engine | ✅ | کامل + AnalysisRun |
| PHASE 8 | Journal/Screenshots | ✅ | کامل |
| PHASE 9 | Testing/Regression | ❌ | شروع نشده |
| PHASE 10 | Personal Finance | ❌ | شروع نشده |

---

## 🟢 بخش‌های باقی‌مانده واقعی

### ۱. PHASE 9 — Testing Suite (pytest + vitest)
- **اولویت:** P4
- **زمان تخمینی:** ۶ ساعت (۴ ساعت backend + ۲ ساعت frontend)
- **توضیح:** تست‌های خودکار برای regression

### ۲. PHASE 10 — Personal Finance Module
- **اولویت:** P3
- **زمان تخمینی:** ۱۲-۲۰ ساعت
- **نیازمندی‌ها:**
  - مدل `FinancialAccount` (Wallet, Exchange, Bank, Cash)
  - مدل `FinancialTransaction` (Income, Expense, Transfer, Conversion, Adjustment)
  - APIهای CRUD
  - صفحه Frontend
  - Migration جدید
- **مهم:** این ماژول با `PersonalAccount` (حساب معاملاتی شخصی) متفاوت است

---

## 🎯 پیشنهاد ترتیب

۱. **PHASE 10: Personal Finance** — اگر آماده شروع هستید
۲. **PHASE 9: Testing Suite** — بعد از Personal Finance

---

## منابع بررسی‌شده

- ✅ `backend/app/services/analysis_service.py` — تمام متدها بررسی شدند
- ✅ `backend/app/api/imports.py` — `version_id` در هر دو مسیر prop و personal تأیید شد
- ✅ `backend/app/models/strategy.py` — مدل `AnalysisRun` تأیید شد
- ✅ `backend/app/api/trades.py` — Pagination تأیید شد
- ✅ `frontend/src/pages/DashboardPage.tsx` — هاردکد وجود ندارد