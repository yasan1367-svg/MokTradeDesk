# فاز ۱۲ — Testing Suite

**تاریخ:** 1405/07/03 | **وضعیت:** ✅ کامل

---

## ۱. بررسی وضعیت قبل
- **pytest**: در `requirements.txt` **نبود** و در هیچ venv نصب نبود.
- **vitest**: در `package.json` **نبود**.
- **تست‌های موجود**: هیچ‌کدام (صفر تست در بک‌اند و فرانت‌اند).

## ۲. Backend — pytest
**نصب:** `pytest`, `pytest-cov`, `httpx` (برای TestClient) — نصب در `venv` و افزودن به `requirements.txt`.

فایل‌های ایجادشده:
- `backend/pytest.ini` — تنظیمات pytest.
- `backend/tests/conftest.py` — fixtures: `db_session` (SQLite درون‌حافظه با `StaticPool`) و `client` (TestClient با dependency override روی `get_db`).
- `backend/tests/test_finance.py` — ۱۳ تست: endpointها (summary/accounts/transactions)، گزارش‌های پیشرفته (monthly/category-breakdown/profit-loss/account-comparison)، Win Rate و Profit Factor (`AnalysisService`)، توابع تاریخ شمسی.
- `backend/tests/test_prop.py` — ۱۰ تست: endpointهای firm/account، `PropRuleEngine` (evaluate_stage، max_drawdown، daily_pnl، validate_withdrawal، withdrawable_profit).
- `backend/tests/test_trades.py` — ۱۰ تست: endpointهای trades (manual/list/detail/errors)، `TradeValidator`، `calculate_r_multiple`.

## ۳. Frontend — vitest
**نصب:** `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom` (pnpm).

فایل‌های ایجادشده/تغییریافته:
- `frontend/vitest.config.ts` — محیط jsdom + setup.
- `frontend/src/test/setup.ts` — افزودن matchers.
- `frontend/src/utils/jalali.ts` — استخراج توابع کمکی تاریخ شمسی از `FinancePage.tsx` (refactor).
- `frontend/src/__tests__/utils.test.ts` — ۴ تست توابع تبدیل تاریخ شمسی.
- `frontend/src/__tests__/components.test.tsx` — ۵ تست کامپوننت‌های `Badge`، `ProgressBar`، `Card`.
- `package.json` — اسکریپت‌های `test` و `test:watch`؛ `tsconfig.app.json` — exclude فایل‌های تست.

## ۴. نتیجه اجرای تست‌ها
| سوئیت | نتیجه |
|---|---|
| Backend (pytest) | ✅ **33 passed** — Coverage: 46% |
| Frontend (vitest) | ✅ **9 passed** (2 files) |
| `tsc -b --force` | ✅ بدون خطا |
| `npm run build` | ✅ موفق |

**پوشش مهم‌ترین ماژول‌ها:** `prop_rule_engine.py` 96%، `trade_metrics.py` 93%، `trade_validator.py` 79%، `finance.py` ~57%.

## ۵. فایل‌های کلیدی تغییریافته
- `backend/requirements.txt`، `backend/pytest.ini`
- `backend/tests/{__init__,conftest,test_finance,test_prop,test_trades}.py`
- `frontend/package.json`، `frontend/vitest.config.ts`، `frontend/tsconfig.app.json`
- `frontend/src/test/setup.ts`، `frontend/src/utils/jalali.ts`
- `frontend/src/__tests__/{utils.test.ts,components.test.tsx}`
- `frontend/src/pages/FinancePage.tsx` (refactor کوچک — استفاده از `utils/jalali`)
- `PHASE12_REPORT.md` (این فایل)

## ۶. اجرای دستی
```bash
# Backend
cd backend && venv\Scripts\python.exe -m pytest --cov=app

# Frontend
cd frontend && pnpm test
```
