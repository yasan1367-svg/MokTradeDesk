# گزارش اصلاح Stage 6 — Strategy / Comparison

**تاریخ:** ۲۰۲۶-۱۰-۱۳  
**دامنه:** یکسان‌سازی تفسیر timezone در فیلترهای تاریخ، تجمیع قراردادهای Strategy و بررسی Fork default؛ Stageهای 1 تا 5 حفظ شدند.

## تغییرات

- تاریخ‌های صرفاً تقویمی اکنون به روزهای تقویمی تهران تفسیر می‌شوند و به بازهٔ UTC نیمه‌باز `[شروع روز، شروع روز بعد)` تبدیل می‌شوند؛ بنابراین هر دو روز ابتدا و انتها شامل‌اند.
- timestampهای صریح در فیلتر Comparison به‌عنوان instant باقی می‌مانند؛ timestamp بدون timezone طبق قرارداد UTC تفسیر می‌شود و timestamp timezone-aware به UTC نرمال می‌شود.
- فیلتر تاریخ chart aggregate استراتژی از همان helper بازهٔ تاریخ استفاده می‌کند و مرز بالا را با `<` اعمال می‌کند.
- تحلیل روز هفته و ساعت، و بازه‌های سفارشی، از زمان محلی تهران استفاده می‌کنند.
- مدل‌های درخواست Strategy از `app.schemas.strategy` به API وارد می‌شوند تا schemaهای تکراری در ماژول route حذف شوند. پاسخ ساخت نسخه نیز شمارش‌های صفر و فیلدهای قراردادی نسخه را بازمی‌گرداند.
- انواع مشترک Strategy و StrategyVersion در API کلاینت فرانت‌اند استفاده شده‌اند؛ مدل‌های محلی تکراری در Strategy و Comparison حذف شدند.
- Fork پیش‌فرض از قبل درست بود و بدون تغییر رفتاری باقی ماند: `${version_name} - Fork`.

## آزمون و اعتبارسنجی

- تست‌های Stage 6 هدفمند (analytics، chart aggregate، Strategy contracts): **۴۷ passed**.
- مجموعهٔ متمرکز Stage 1–5 حفظ‌شده: **۱۳۶ passed**.
- `frontend`: اجرای `npm run build` موفق؛ TypeScript و Vite build بدون خطا.
- `git diff --check`: بدون خطای whitespace.

هشدارهای deprecation موجود از FastAPI/Starlette، Pydantic و SQLAlchemy همچنان گزارش می‌شوند و در این تغییرات ایجاد نشده‌اند.

## فایل‌های اصلی تغییرکرده

- `backend/app/utils/date_range.py`
- `backend/app/api/analytics.py`
- `backend/app/api/strategies.py`
- `backend/app/services/analysis_service.py`
- `backend/app/schemas/strategy.py`
- `backend/tests/test_analytics.py`
- `backend/tests/test_strategy_chart_aggregate_stage5.py`
- `backend/tests/test_strategy_stage4_contracts.py`
- `frontend/src/api/client.ts`
- `frontend/src/pages/StrategyPage.tsx`
- `frontend/src/pages/ComparisonPage.tsx`

Stage 6 کامل شد؛ Stage بعدی آغاز نشده است.