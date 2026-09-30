# چک‌لیست استفاده — MokTradeDesk

## قبل از استفاده

- [ ] Backend اجرا شده (`uvicorn app.main:app --reload`)
- [ ] Frontend اجرا شده (`npm run dev`)
- [ ] DB ساخته شده (`alembic upgrade head` — در startup خودکار است)
- [ ] بررسی سلامت: `GET http://localhost:8000/` → `{"message": "..."}`

## استفادهٔ روزانه

- [ ] ثبت معاملات (دستی یا Import)
- [ ] دسته‌بندی معاملات (Backtest / Forward / REAL_PROP / REAL_PERSONAL)
- [ ] به‌روزرسانی پراپ (Stage، Rule Engine، Payout)
- [ ] ثبت تراکنش‌های مالی (واریز/برداشت/انتقال/اصلاح)
- [ ] تحلیل عملکرد (Dashboard / Analysis / Risk)
- [ ] مرور ژورنال

## بکاپ

```powershell
# بکاپ دستی سریع (توصیه: برنامه را ببند یا از API /api/backup/create استفاده کن)
Copy-Item "backend\trading_desk.db" "backend\trading_desk.db.bak_$(Get-Date -Format 'yyyyMMdd')"

# بکاپ امن آنلاین (بدون بستن برنامه، از داخل backend):
venv\Scripts\python.exe -c "from app.services.backup_service import create_backup; print(create_backup())"
```

- [ ] بکاپ دستی گرفته شده
- [ ] (اختیاری) Backup خودکار فعال است — `GET /api/backup/list`

### کپی ماهانه به دیسک/Drive دیگر (فاز ۴۲.۹)

```powershell
# کل پوشهٔ Backup را روی یک دیسک/مسیر دیگر آرشیو کن (ماهانه)
$dst = "D:\MokTradeDesk_Backup_$(Get-Date -Format 'yyyyMM')"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item "C:\MokTradeDesk\backend\backups\*" $dst -Recurse -Force
# یا فقط فایل دیتابیس اصلی:
Copy-Item "C:\MokTradeDesk\backend\trading_desk.db" "$dst\trading_desk.db"
```

- [ ] آرشیو ماهانه روی دیسک/Drive دیگر کپی شده
- [ ] فایل‌های `trading_desk_premigrate_*.db` (Snapshot پیش از migration) حفظ شده‌اند

> ⚠️ **WAL:** با فعال بودن WAL، اگر برنامه در حال اجراست فقط `trading_desk.db` را
> کپی نکن؛ یا از `/api/backup/create` (که `sqlite3.backup()` امن می‌زند) استفاده کن
> یا همراه `trading_desk.db` فایل‌های `-wal` و `-shm` را هم کپی کن.

## قبل از هر تغییر کد

- [ ] تست‌های بک‌اند سبز: `venv\Scripts\python.exe -m pytest -q -p no:warnings`
- [ ] بررسی TypeScript: `npx tsc -b --force`
- [ ] بررسی Migration: `alembic current` == `alembic heads`

## بعد از هر Migration

- [ ] بکاپ DB گرفته شده
- [ ] `alembic upgrade head` روی DB تستی/کپی اجرا شده
- [ ] `alembic current` == `alembic heads`
- [ ] تست‌ها سبز
