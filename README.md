# MokTradeDesk

> **Trading OS شخصی** — مدیریت یکپارچهٔ استراتژی، پراپ، تحلیل، معاملات و مالی.
> `Analyze • Improve • Grow`

**وضعیت:** فازهای ۲۵ تا ۴۲ پیاده‌سازی‌شده · **تست‌ها:** ۲۷۲ pytest (بک‌اند) + ۹ vitest (فرانت‌اند)

---

## قابلیت‌ها

MokTradeDesk یک نرم‌افزار **Local-First** است و کل چرخهٔ معاملاتی را در یک‌جا مدیریت می‌کند:

- **استراتژی‌ها** — Strategy + Version (+ Fork)
- **پراپ** — Prop Firm / Account / Stage (+ Rule Engine)
- **تحلیل** — Multi-scope (Version / Prop / Personal)
- **معاملات** — Trade CRUD + Import (MT4 / Soft4X)
- **مالی** — برداشت پراپ/بروکر + هزینه‌ها + `WalletService` (تنها نویسندهٔ موجودی)
- **ژورنال + اسکرین‌شات**
- **تقویم (شمسی) + ریسک (Sharpe/Sortino/Calmar/VaR/Kelly/Ulcer) + مقایسه**
- **Backup خودکار + Rotation** (ساعتی/روزانه/هفتگی + Snapshot پیش از migration)

---

## ایمنی داده (فاز ۴۲)

- **مسیر DB مطلق:** `DATABASE_URL` از روی `__file__` ساخته می‌شود
  (`backend/trading_desk.db`) و به پوشهٔ اجرای uvicorn وابسته نیست.
- **PRAGMAها:** روی هر اتصال `foreign_keys=ON`، `journal_mode=WAL` و
  `busy_timeout=5000` اعمال می‌شود.
- **Migration خطادار = توقف startup:** اگر `alembic upgrade` شکست بخورد، برنامه
  بالا نمی‌آید (به‌جای اجرا روی schema قدیمی).
- **Snapshot پیش از migration:** اگر migration جدیدی وجود داشته باشد، قبل از
  اجرا یک `trading_desk_premigrate_*.db` ساخته می‌شود.
- **Backup هوشمند:** در startup فقط اگر آخرین Backup قدیمی‌تر از `interval_hours`
  (پیش‌فرض ۲۴ ساعت) باشد Backup ساخته می‌شود.
- **Rotation طبقه‌بندی‌شده:** ۲۴ ساعت آخر ساعتی · ۱–۷ روز روزانه · ۷–۲۸ روز هفتگی ·
  قدیمی‌تر از ۲۸ روز حذف. فایل‌های `premigrate_*` هرگز خودکار حذف نمی‌شوند.
- **Restore ایمن:** `PRAGMA integrity_check` روی فایل Backup، حذف `-wal`/`-shm`
  پس از `engine.dispose()` و پیام «برنامه را ری‌استارت کن».

---

## نصب

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

> Migration در `startup` به‌صورت خودکار اجرا می‌شود؛ برای اجرای دستی:
> `.\venv\Scripts\alembic upgrade head`

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

---

## دسترسی

| سرویس | آدرس |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

---

## تست

```powershell
# Backend (pytest)
cd backend
venv\Scripts\python.exe -m pytest -q -p no:warnings

# Frontend (TypeScript + Vitest + Build)
cd frontend
npx tsc -b --force
npx vitest run
npm run build
```

> تست‌های بک‌اند روی **DB تستی جداگانه** اجرا می‌شوند (فاز ۳۹.۵) و `trading_desk.db` واقعی را لمس نمی‌کنند.

---

## ساختار

```
backend/                   # FastAPI + SQLAlchemy + Alembic
│   ├── app/               # core / models / api / services / utils
│   ├── migrations/        # Alembic
│   └── tests/             # pytest
frontend/                  # React + TypeScript + Vite
backend/trading_desk.db    # SQLite · WAL mode (فاز ۴۲) — مسیر مطلق
```

---

## فازها

- **Phase 25–42** — پیاده‌سازی‌شده.
- مستندات: `PHASE*_REPORT.md` · `HANDOFF.md` · `CHECKLIST.md`
