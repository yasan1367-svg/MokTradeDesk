# 🚀 STRATEGY_PROP_IMPROVEMENTS — گزارش تغییرات

**تاریخ:** ۱۴۰۴/۰۷/۰۳
**وضعیت:** ✅ مراحل ۱-۳ تکمیل

---

## ۱. خلاصه مراحل انجام‌شده

| مرحله | قابلیت | وضعیت | فایل‌های تغییر یافته |
|:---|:---|:---:|:---|
| **۱** | 🔱 Fork Version | ✅ | `strategies.py`, `client.ts`, `StrategyPage.tsx` |
| **۲** | 📋 PropFirmDefaultRules | ✅ | `prop.py`, `client.ts`, `PropPage.tsx` |
| **۳** | 🔔 PropAlert (هشدارها) | ✅ | `prop.py`, `client.ts`, `PropPage.tsx`, `DashboardPage.tsx` |

---

## ۲. جزئیات هر مرحله

### مرحله ۱ — Fork Version 🔱

| بخش | شرح | فایل |
|:---|:---|:---:|
| **Backend** | `POST /api/strategies/versions/{id}/fork` — کپی یک نسخه با `forked_from_version_id` | `strategies.py:208-235` |
| **API Client** | تابع `forkVersion(versionId)` | `client.ts:233-234` |
| **Frontend** | دکمه 🔱 کنار هر نسخه + تابع `handleForkVersion` | `StrategyPage.tsx:237-247, 555-561` |

**جزئیات فنی:**
- نام نسخه جدید: `"[نام اصلی] - Fork"`
- `rules_note` از نسخه مبدأ کپی می‌شود
- نسخه جدید در همان `strategy_id` ساخته می‌شود
- ستون `forked_from_version_id` در مدل از قبل وجود داشت

---

### مرحله ۲ — PropFirmDefaultRules 📋

| بخش | شرح | فایل |
|:---|:---|:---:|
| **Backend** | `GET /api/prop/firms/{firm_id}/default-rules` — قوانین پیش‌فرض شرکت | `prop.py:112-140` |
| **API Client** | تابع `getFirmDefaultRules(firmId)` | `client.ts:37-38` |
| **Frontend** | پر شدن خودکار فیلدها هنگام انتخاب شرکت در فرم Create Account | `PropPage.tsx:556-575` |

**جزئیات فنی:**
- مدل `PropFirmDefaultRules` در DB از قبل وجود داشت ولی endpoint نداشت
- هنگام انتخاب شرکت، قوانین `stage_1` از شرکت خوانده می‌شود
- درصدهای profit_target, max_daily_dd, max_total_dd به صورت خودکار محاسبه و پر می‌شوند
- حداقل روزهای معاملاتی نیز پر می‌شود

---

### مرحله ۳ — PropAlert (هشدارها) 🔔

| بخش | شرح | فایل |
|:---|:---|:---:|
| **Backend — هشدار خودکار** | تابع `_generate_alerts_for_stage` — ۳ نوع هشدار | `prop.py:474+` |
| **Backend — لیست** | `GET /api/prop/alerts` — با فیلتر stage_id و unread_only | `prop.py` |
| **Backend — علامت‌گذاری** | `PATCH /api/prop/alerts/{id}/read` | `prop.py` |
| **Backend — تولید انبوه** | `POST /api/prop/alerts/generate` — برای همه مراحل فعال | `prop.py` |
| **Backend — تریگر خودکار** | `check_pass_ready` اکنون هشدار تولید می‌کند | `prop.py:272-278` |
| **API Client** | توابع `getPropAlerts`, `markAlertRead`, `generatePropAlerts` | `client.ts:41-50` |
| **Frontend — PropPage** | بخش «هشدارها» با دکمه‌های بارگذاری/بررسی خودکار/علامت خوانده‌شده | `PropPage.tsx:946+` |
| **Frontend — Dashboard** | کارت «هشدارهای پراپ» با دکمه «✓ خواندم» | `DashboardPage.tsx:274+` |

**انواع هشدارهای خودکار:**
| نوع هشدار | شرط | آیکون |
|:---|:---|:---:|
| **Daily DD نزدیک به حد** | ۸۰% ≤ مصرف < ۱۰۰% | ⚠️ |
| **Daily DD نقض شده** | مصرف ≥ ۱۰۰% | 🚨 |
| **Total DD نزدیک به حد** | ۸۰% ≤ مصرف < ۱۰۰% | ⚠️ |
| **Total DD نقض شده** | مصرف ≥ ۱۰۰% | 🚨 |
| **هدف سود نزدیک** | ۹۰% ≤ پیشرفت < ۱۰۰% | 🎯 |

---

## ۳. مراحل باقی‌مانده

| مرحله | قابلیت | اولویت | وابستگی | تخمین |
|:---|:---|:---:|:---:|:---:|
| **۴** | 📊 آمار تفصیلی استراتژی‌ها | 🟡 P1 | — | ۲-۳ ساعت |
| **۵** | 📈 مقایسه گرافیکی استراتژی‌ها | 🟡 P1 | — | ۲-۳ ساعت |
| **۶** | 💰 آمار برداشت‌ها + Payout History | 🟡 P2 | — | ۱-۲ ساعت |
| **۷** | 🏢 Multi-Account Prop View | 🟡 P2 | — | ۳-۴ ساعت |
| **۸** | 📝 Rules Builder (قوانین ساختاریافته) | 🟢 P2 | — | ۴-۶ ساعت |
| **۹** | 📋 گزارش مالیاتی پراپ | 🟢 P3 | حسابداری | ۲-۳ ساعت |
| **۱۰** | 📊 گزارش عملکرد ترکیبی | 🟢 P3 | حسابداری | ۳-۴ ساعت |
| **۱۱** | ⚖️ Risk Allocation | 🔵 P4 | حسابداری | ۴-۶ ساعت |

---

## ۴. نکات مهم

1. **Fork Version** کم‌نیاز بود (از قبل مدل و ستون DB وجود داشت) اما دکمه و endpoint نداشت
2. **Personal Finance (حسابداری)** پیش‌نیاز مراحل ۹-۱۱ است
3. **قابلیت‌های مستقل** (مراحل ۴-۸) می‌توانند قبل از حسابداری انجام شوند
4. **PropAlert** از مدل موجود `PropAlert` استفاده می‌کند که از قبل در DB بود

---

## ۵. اولویت‌بندی مراحل بعدی

### اولویت بالا 🟡 (می‌تواند قبل از حسابداری انجام شود)
1. **مرحله ۴**: آمار تفصیلی استراتژی‌ها — جدول مقایسه‌ای متریک‌ها
2. **مرحله ۵**: مقایسه گرافیکی استراتژی‌ها — نمودارهای کنار هم

### اولویت متوسط 🟢 (می‌تواند قبل از حسابداری انجام شود)
3. **مرحله ۶**: آمار برداشت‌ها + Payout History
4. **مرحله ۷**: Multi-Account Prop View
5. **مرحله ۸**: Rules Builder

### اولویت پایین 🔵 (وابسته به حسابداری)
6. **مرحله ۹-۱۱**: نیازمند Personal Finance Module

---

## ۶. خلاصه فایل‌های تغییر یافته (کل session)

| فایل | مراحل | نوع تغییر |
|------|:---:|-----------|
| `backend/app/api/strategies.py` | ۱ | ✏️ اضافه شدن Fork endpoint |
| `backend/app/api/prop.py` | ۲, ۳ | ✏️ Default Rules + Alerts (۳ endpoint + auto-generate) |
| `frontend/src/api/client.ts` | ۱, ۲, ۳ | ✏️ `forkVersion`, `getFirmDefaultRules`, `getPropAlerts`, `markAlertRead`, `generatePropAlerts` |
| `frontend/src/pages/StrategyPage.tsx` | ۱ | ✏️ دکمه 🔱 + handler |
| `frontend/src/pages/PropPage.tsx` | ۲, ۳ | ✏️ auto-fill rules + بخش هشدارها |
| `frontend/src/pages/DashboardPage.tsx` | ۳ | ✏️ کارت هشدارها |
| `STRATEGY_PROP_ANALYSIS.md` | — | 🆕 فایل جدید — تحلیل وضعیت |
| `STRATEGY_PROP_IMPROVEMENTS.md` | — | 🆕 فایل جدید — گزارش تغییرات |

---

**تست کامپایل:** ✅ Backend + Frontend — بدون خطا

*این گزارش در تاریخ ۱۴۰۴/۰۷/۰۳ تهیه شده است.*