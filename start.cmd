@echo off
REM ═════════════════════════════════════════════
REM MokTradeDesk Launcher
REM ═════════════════════════════════════════════

title MokTradeDesk Launcher

echo.
echo ╔════════════════════════════════════════════╗
echo ║       MokTradeDesk - Starting...          ║
echo ╚════════════════════════════════════════════╝
echo.

REM ═════════════════════════════════════════════
REM ۰. اجرای Migration (ساخت/به‌روزرسانی جداول دیتابیس)
REM ═════════════════════════════════════════════
echo [0/3] Running database migrations...
pushd "%~dp0backend"
if exist "venv\Scripts\alembic.exe" (
    venv\Scripts\alembic.exe upgrade head
    if errorlevel 1 (
        echo [WARN] Migration reported an error - see output above.
    ) else (
        echo [OK] Database migrations are up to date.
    )
) else (
    echo [WARN] venv\Scripts\alembic.exe not found - skipping migration.
)
popd

REM ═════════════════════════════════════════════
REM ۱. اجرای Backend در پنجره جدید
REM ═════════════════════════════════════════════
echo [1/3] Starting Backend...
start "MokTradeDesk - Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && python -m uvicorn app.main:app --reload"

REM ═════════════════════════════════════════════
REM ۲. انتظار برای بالا آمدن Backend
REM ═════════════════════════════════════════════
echo [2/3] Waiting for Backend to start...
timeout /t 5 /nobreak >nul

REM ═════════════════════════════════════════════
REM ۳. اجرای Frontend در پنجره جدید
REM ═════════════════════════════════════════════
echo [3/3] Starting Frontend...
start "MokTradeDesk - Frontend" cmd /k "cd /d %~dp0frontend && pnpm dev"

REM ═════════════════════════════════════════════
REM ۴. انتظار برای بالا آمدن Frontend
REM ═════════════════════════════════════════════
echo Waiting for Frontend to start...
timeout /t 5 /nobreak >nul

REM ═════════════════════════════════════════════
REM ۵. باز کردن مرورگر
REM ═════════════════════════════════════════════
echo Opening browser...
start http://localhost:5173

echo.
echo ╔════════════════════════════════════════════╗
echo ║       MokTradeDesk is running!            ║
echo ║                                            ║
echo ║  Backend:  http://localhost:8000          ║
echo ║  Frontend: http://localhost:5173          ║
echo ║  Swagger:  http://localhost:8000/docs     ║
echo ║                                            ║
echo ║  Press any key to close this launcher...  ║
echo ╚════════════════════════════════════════════╝
echo.

pause >nul