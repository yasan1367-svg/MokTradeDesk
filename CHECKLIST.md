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
# بکاپ دستی سریع
Copy-Item "backend\trading_desk.db" "backend\trading_desk.db.bak_$(Get-Date -Format 'yyyyMMdd')"
```

- [ ] بکاپ دستی گرفته شده
- [ ] (اختیاری) Backup خودکار فعال است — `GET /api/backup/list`

## قبل از هر تغییر کد

- [ ] تست‌های بک‌اند سبز: `venv\Scripts\python.exe -m pytest -q -p no:warnings`
- [ ] بررسی TypeScript: `npx tsc -b --force`
- [ ] بررسی Migration: `alembic current` == `alembic heads`

## بعد از هر Migration

- [ ] بکاپ DB گرفته شده
- [ ] `alembic upgrade head` روی DB تستی/کپی اجرا شده
- [ ] `alembic current` == `alembic heads`
- [ ] تست‌ها سبز
