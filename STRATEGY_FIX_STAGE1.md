# گزارش مرحلهٔ اول اصلاح Strategy / Analysis / Comparison

**تاریخ:** ۲۰۲۶-۱۰-۱۲  
**دامنه:** یافته‌های #1، #2 و #4 از `STRATEGY_COMPARISON_FIX_VERIFICATION.md`؛ معاملات تاریخی بسته، scope مطابق نوع تحلیل، حساب‌ها و مبالغ USDT. Dashboard و Finance خارج از دامنه‌اند.

## خلاصه

تازگی تحلیل برای مقایسهٔ فیلترشده نیز بررسی می‌شود؛ مسیرهای Strategy که فهرست معاملات و آمار تحلیلی می‌دهند معاملات باز و REAL را وارد نمی‌کنند؛ و GET با نوع تست صریح دیگر به تحلیل legacy یا نوع متفاوت fallback نمی‌کند. درخواست legacy بدون نوع تست، رفتار سازگاری قبلی را حفظ می‌کند. هیچ migration یا تغییر schema انجام نشد.

## اصلاحات و فایل‌ها

- `backend/app/services/analysis_service.py`: کنترل freshness قبل از هر دو مسیر مقایسهٔ فیلترشده و بدون فیلتر؛ edit/add/delete نامنطبق به‌صورت stale گزارش می‌شوند.
- `backend/app/utils/trade_scope.py`: افزودن predicate مشترک معاملات بستهٔ مجاز برای تحلیل.
- `backend/app/api/strategies.py`: اعمال predicate در فهرست معاملات نسخه و stats استراتژی.
- `backend/app/api/analytics.py`: جلوگیری از fallback به نتیجهٔ نامتناسب در GET دارای `test_type` صریح؛ درخواست بدون نوع همچنان legacy-compatible است.
- `backend/tests/test_phase53_stale_analysis.py`: تست‌های stale فیلترشده برای edit/add/delete، محدودشدن GET نوع‌دار، و کنارگذاشتن معاملات باز از stats و فهرست نسخه.

## اعتبارسنجی

فرمان اجراشده از `C:\MokTradeDesk\backend`:

```text
.\venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_phase53_stale_analysis.py tests/test_phase53_strategy_stats.py tests/test_closed_trades_only.py tests/test_phase53_real_comparison.py
29 passed, 9 warnings in 3.17s
```

هشدارها deprecationهای موجود FastAPI/Starlette، Pydantic و SQLAlchemy هستند. `git diff --check` بدون خطا تمام شد.

## محدودیت‌ها و ریسک باقیمانده

- تشخیص freshness به `updated_at` متکی است؛ ردیف‌های تاریخی با `updated_at=NULL` ممکن است تغییر قدیمی را آشکار نکنند.
- GET بدون `test_type` صریح عمداً fallback legacy را حفظ می‌کند و ممکن است دامنهٔ Backtest/Forward ترکیبی داشته باشد؛ پاسخ همچنان legacy است.
- سایر مصرف‌کنندگان دادهٔ نمودار در frontend در این مرحله تغییر نکرده‌اند؛ Dashboard خارج از دامنهٔ توافق‌شده بود.
- رتبه‌بندی و stats همچنان به دادهٔ تاریخی بسته و مبالغ USDT متکی‌اند؛ این مرحله معنای متریک‌ها/Score را بازطراحی نمی‌کند.

## وضعیت Git

فایل `STRATEGY_COMPARISON_FIX_VERIFICATION.md` پیش از شروع untracked بود و دست‌نخورده باقی ماند. فایل گزارش حاضر جدید است. تغییری خارج از دامنه و commit انجام نشده است.