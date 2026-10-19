# MokTradeDesk

نرم‌افزار شخصی مدیریت معاملات (Trading OS) — Strategy · Prop · Analysis · Trades · Finance.

`Analyze • Improve • Grow`

**وضعیت:** فازهای ۱ تا ۴۸a پیاده‌سازی‌شده · **تست‌ها:** ۳۷۳ pytest (بک‌اند) + ۹ vitest (فرانت‌اند)

---

## پیش‌نیازها

- **Python 3.12+**
- **Node.js 20+** — مدیریت پکیج: **`pnpm`** (پروژه `pnpm-lock.yaml` دارد). `npm` هم کار می‌کند.
- **Windows** (تست‌شده؛ لینوکس/مک احتمالاً کار می‌کند)

---

## نصب

### ۱. Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### ۲. Frontend

```powershell
cd frontend
pnpm install      # یا: npm install
```

### ۳. ساخت Database (اختیاری — startup خودکار انجام می‌دهد)

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m alembic upgrade head
```

> اجرای دستی این دستور **اختیاری** است (فقط برای دیدن خطاها/کنترل دستی)؛ در غیر این صورت
> بک‌اند در `startup` خودش `alembic upgrade head` را اجرا می‌کند.

---

## اجرا

### روش سریع (Windows) — پیشنهادی

```powershell
# در ریشهٔ پروژه
.\start.vbs     # migration + Backend + Frontend + باز کردن مرورگر (با splash)
.\stop.vbs      # بستن همهٔ سرویس‌ها
```

### روش دستی (دو Terminal)

**Terminal 1 — Backend**

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

**Terminal 2 — Frontend**

```powershell
cd frontend
pnpm dev         # یا: npm run dev
```

### آدرس‌ها

| سرویس | آدرس |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

مرورگر: **http://localhost:5173**

---

## تست

**Backend**

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m pytest -q -p no:warnings
```
انتظار: **~۳۷۳ تست pass**.

**Frontend**

```powershell
cd frontend
npx tsc -b --force
npx vitest run
npm run build
```

> تست‌های بک‌اند روی **DB تستی جداگانه** اجرا می‌شوند و `trading_desk.db` واقعی را لمس نمی‌کنند.

---

## بکاپ

### از UI
**Settings ← Backup** ← دکمهٔ «ساخت Backup» (ساخت/دانلود/بازیابی/حذف + تنظیمات Backup خودکار).
Backup خودکار هم در پس‌زمینه (هر ۳۰ دقیقه بررسی، طبق `interval_hours`) اجرا می‌شود.

### دستی

```powershell
Copy-Item "backend\trading_desk.db" "backend\trading_desk.db.bak_$(Get-Date -Format 'yyyyMMdd_HHmm')"
```

### بازیابی

**Settings ← Backup ← «بازیابی»** (با تأیید)

⚠️ **قبل از بازیابی، نرم‌افزار را ببند.**

### بازگرداندن دستی (وقتی DB خراب شده)

```powershell
# ۱) ابتدا سرورها را ببند (.\stop.vbs)
# ۲) فایل‌های جانبی SQLite را پاک کن
Remove-Item "backend\trading_desk.db-wal","backend\trading_desk.db-shm" -ErrorAction SilentlyContinue
# ۳) بکاپ را برگردان
Copy-Item "backend\trading_desk.db.bak_YYYYMMDD_HHMM" "backend\trading_desk.db"
```

---

## ساختار پروژه

```
MokTradeDesk/
├── backend/                  # FastAPI + SQLAlchemy + Alembic
│   ├── app/                  # core / models / api / services / utils
│   ├── migrations/           # Alembic
│   ├── tests/                # pytest (DB تستی جدا)
│   ├── backups/              # Backupهای خودکار
│   ├── logs/                 # app.log
│   ├── alembic.ini
│   ├── requirements.txt
│   └── trading_desk.db       # SQLite · WAL mode — مسیر مطلق (فاز ۴۲)
├── frontend/                 # React + TypeScript + Vite
│   └── src/
├── logs/                     # backend.log · frontend.log · migration.log · stop.log
├── start.vbs / stop.vbs      # لانچر ویندوز
└── README.md
```

---

## عیب‌یابی

### Backend بالا نمی‌آید

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m alembic upgrade head      # خطای migration را این‌جا ببین
python -m uvicorn app.main:app --reload
```
لاگ را چک کن: `backend\logs\app.log` و `logs\backend.log`.

### Frontend بالا نمی‌آید

```powershell
cd frontend
Remove-Item -Recurse -Force node_modules
pnpm install        # یا: npm install
pnpm dev
```

### DB خراب شده / برنامه روی دادهٔ اشتباه است

۱) همهٔ سرویس‌ها را ببند (`.\stop.vbs`) ۲) `trading_desk.db-wal` / `-shm` را پاک کن
۳) بکاپ را برگردان (بخش «بکاپ» بالا).

### پورت‌ها اشغال است

```powershell
# Backend روی پورت دیگر
python -m uvicorn app.main:app --reload --port 8001

# Frontend روی پورت دیگر
pnpm dev -- --port 5174
```
> در صورت تغییر پورت، `VITE_API_BASE_URL` فرانت را هم به آدرس بک‌اند جدید تنظیم کن
> (فایل `.env` فرانت — نمونه در `.env.example`).

---

## نکات مهم

- **قبل از هر تغییر و قبل از هر migration، از DB بکاپ بگیر.**
- **migration در `startup` خودکار اجرا می‌شود** و در صورت خطا **برنامه بالا نمی‌آید**
  (به‌جای اجرا روی schema قدیمی). پیش از migration جدید، یک Snapshot با پیشوند
  `trading_desk_premigrate_*.db` ساخته می‌شود.
- **مسیر DB مطلق است** (`backend/trading_desk.db`) و به پوشهٔ اجرای uvicorn وابسته نیست.
- **`.env.example` را کورکورانه کپی نکن:** `DATABASE_URL=sqlite:///./app.db` مسیر DB را عوض می‌کند؛
  اگر `.env` نمی‌سازی، همان مسیر پیش‌فرض امن است.
- **DB تستی است** — پاک شدنش مهم نیست (تست‌ها از آن استفاده نمی‌کنند).

---

## فازهای پیاده‌شده

- **Phase 1–48a** — پیاده‌سازی‌شده. برای جزئیات: `git log --oneline` و فایل‌های `PHASE*_IMPL_REPORT.md`.

