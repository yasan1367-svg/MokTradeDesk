# ⚡ MokTradeDesk

> **نرم‌افزار مدیریت و تحلیل معاملات** — از بک‌تست تا پراپ و حسابداری
> `Analyze • Improve • Grow`

[![Phases](https://img.shields.io/badge/phases-1--26-blue)]()
[![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20SQLAlchemy-green)]()
[![Frontend](https://img.shields.io/badge/frontend-React%2019%20%2B%20TypeScript-61dafb)]()
[![Tests](https://img.shields.io/badge/tests-90%20(pytest)%20%2B%209%20(vitest)-brightgreen)]()

---

## 📖 معرفی

**MokTradeDesk** یک نرم‌افزار **Local-First** برای تریدرهای حرفه‌ای است که کل چرخهٔ معاملاتی را در یک‌جا مدیریت می‌کند:

| بخش | قابلیت |
|---|---|
| 📊 **داشبورد** | KPI، Equity Curve، توزیع PnL، Session bars، پول قابل خرج |
| 📈 **تحلیل** | تحلیل ۶گانه (Backtest / Forward / پراپ / بروکر / مقایسه / تاریخچه) |
| 🎯 **استراتژی** | مدیریت استراتژی‌ها، نسخه‌ها، Fork، آمار تجمعی |
| 📋 **معاملات** | واردات (Soft4X/MT4)، فیلتر، ویرایش، اسکرین‌شات، حذف نرم/گروهی، **بازگردانی** |
| 🏢 **پراپ** | موتور قوانین (Daily/Total DD، Target، Payout)، هشدارها |
| 💰 **مالی** | ۹ گزارش، پل معامله→حسابداری، تقویم مالی شمسی |
| 📔 **ژورنال** | مرور معاملات، امتیاز، درس‌ها |
| 🛡️ **ریسک** | Sharpe/Sortino/Calmar/VaR/Kelly/Ulcer |
| 🗄️ **Backup** | خودکار + دستی + بازیابی ایمن |

> 💡 همه‌چیز روی سیستم شما اجرا می‌شود — دیتابیس SQLite لوکال، بدون سرور ابری.

---

## ✨ ویژگی‌های کلیدی

- 🌙 **Dark Mode** کامل (مبتنی بر CSS Variables)
- ⌨️ **Command Palette** (`Ctrl+K`)
- 🗑️ **Soft Delete** + **Restore** + حذف گروهی
- 🧭 **Multi-scope Analysis** (۶ دامنهٔ مستقل)
- 🔗 **Finance Bridge** (معاملهٔ بسته‌شده → Transaction خودکار)
- 📅 **تاریخ شمسی** در همه‌جای رابط کاربری (RTL)
- 📄 **Export** PDF/CSV با فونت فارسی
- 💾 **Backup خودکار** (هر ۳۰ دقیقه بررسی)
- 🚀 **Launcher** تک‌کلیکی (`start.vbs` + Splash)

---

## 🚀 راه‌اندازی سریع

### پیش‌نیازها

| ابزار | نسخه |
|---|---|
| Windows | ۱۰/۱۱ |
| Python | ۳.۱۲ |
| Node.js | ۲۰+ |
| pnpm | ۹+ (`npm i -g pnpm`) |

### روش ۱ — لانچر یک‌کلیکی (ساده‌ترین)

```
دوبار کلیک روی  start.vbs
```
➡️ Splash + migration خودکار + Backend + Frontend + باز شدن مرورگر

برای توقف: دوبار کلیک روی `stop.vbs`

### روش ۲ — دستی

**Backend:**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\venv\Scripts\alembic upgrade head          # اختیاری (در startup خودکار است)
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

**Frontend:**
```powershell
cd frontend
pnpm install
pnpm dev
```

| سرویس | آدرس |
|---|---|
| UI | http://localhost:5173 |
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

---

## 🧪 تست

```powershell
# Backend (۹۰ تست)
cd backend
.\venv\Scripts\python.exe -m pytest -q

# Frontend (۹ تست)
cd frontend
npm run test

# بررسی TypeScript + Build
npx tsc -b --force
npm run build
```

---

## 🏗️ فناوری‌ها

| لایه | فناوری |
|---|---|
| **Backend** | Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2 · slowapi · reportlab |
| **Frontend** | React 19 · TypeScript 6 · Vite 8 · Tailwind CSS 3 · Recharts · axios · zustand |
| **Database** | SQLite (WAL mode) |
| **Testing** | pytest (۹۰) · vitest (۹) · Testing Library |
| **Launcher** | VBScript + HTA (Windows) |

---

## 📁 ساختار پروژه

```
MokTradeDesk/
├── start.vbs / stop.vbs / splash.hta   # لانچر
├── README.md / FINAL_BLUEPRINT.md      # مستندات
├── logs/                               # لاگ‌ها
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI + lifespan + CORS + RateLimit
│   │   ├── core/       (config, database, rate_limit)
│   │   ├── models/     (strategy, prop, finance, personal, settings)
│   │   ├── schemas/    (analytics, prop, strategy)
│   │   ├── api/        (۱۳ router)
│   │   ├── services/   (analysis, prop_rule_engine, import, finance_sync, backup)
│   │   └── utils/      (validator, scope, metrics, chart_helpers, uploads, enums)
│   ├── migrations/versions/            # ۹ migration
│   ├── tests/                          # ۹۰ تست
│   ├── backups/                        # Backupهای خودکار
│   └── storage/screenshots/
└── frontend/
    └── src/
        ├── App.tsx / main.tsx          # Shell + Routing + Theme
        ├── pages/                      # ۱۳ صفحه
        ├── components/                 # ۳۱ کامپوننت (ui/ + charts/)
        ├── api/client.ts               # لایهٔ API
        └── utils/jalali.ts             # تاریخ شمسی
```

---

## 📚 مستندات

| سند | موضوع |
|---|---|
| **[`FINAL_BLUEPRINT.md`](./FINAL_BLUEPRINT.md)** | 🧭 بلوپرینت نهایی (فاز ۱-۲۶) — مرجع کامل |
| `PHASE26_REPORT.md` | گزارش فاز ۲۶ (Restore + کیفیت کد) |
| `PHASE25_REPORT.md` / `PHASE25_PART2_REPORT.md` | فاز ۲۵ (Soft Delete) |
| `PHASE*_REPORT.md` | گزارش تمام فازها |
| `COMPREHENSIVE_REVIEW.md` | بررسی جامع پروژه |
| `SUGGESTIONS.md` | پیشنهادات آینده |

---

## 🔧 دستورات پرکاربرد

| کار | دستور |
|---|---|
| اجرای Backend | `cd backend; .\venv\Scripts\python.exe -m uvicorn app.main:app --reload` |
| اجرای Frontend | `cd frontend; pnpm dev` |
| تست Backend | `cd backend; .\venv\Scripts\python.exe -m pytest -q` |
| تست Frontend | `cd frontend; npm run test` |
| وضعیت Migration | `cd backend; .\venv\Scripts\python.exe -m alembic current` |
| Migration جدید | `cd backend; .\venv\Scripts\python.exe -m alembic revision --autogenerate -m "msg"` |
| Backup دستی | `POST /api/backup/create` |

---

## 📄 مجوز

پروژهٔ خصوصی (Private) — استفادهٔ شخصی.

---

*آخرین به‌روزرسانی: فاز ۲۶ — ۱۴۰۵/۰۷/۰۶*

