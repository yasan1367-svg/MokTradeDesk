# MokTradeDesk

> **Trading OS شخصی** — مدیریت یکپارچهٔ استراتژی، پراپ، تحلیل، معاملات و مالی.
> `Analyze • Improve • Grow`

**وضعیت:** فازهای ۲۵ تا ۴۰ پیاده‌سازی‌شده · **تست‌ها:** ۲۴۵ pytest (بک‌اند) + ۹ vitest (فرانت‌اند)

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
- **Backup خودکار** (هر ۳۰ دقیقه بررسی)

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
backend/trading_desk.db    # SQLite (WAL mode)
```

---

## فازها

- **Phase 25–40** — پیاده‌سازی‌شده.
- مستندات: `PHASE*_REPORT.md` · `HANDOFF.md` · `CHECKLIST.md`
