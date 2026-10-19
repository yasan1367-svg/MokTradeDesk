# گزارش مرحلهٔ دوم اصلاح امتیازدهی Strategy — Score Reliability

**تاریخ:** ۲۰۲۶-۱۰-۱۲  
**دامنه:** یافته‌های #5 تا #8؛ فقط امتیاز Score، قابلیت اتکای R/DD و شفافیت واحد.  
**مبنای محصول:** ژورنال تاریخی معاملات بسته، همهٔ مبالغ/حساب‌های معاملاتی USDT؛ بدون FX، معاملهٔ زنده، پوزیشن باز یا موتور تعیین حجم. مقادیر تاریخی importشده دست‌نخورده‌اند.

## قرارداد دقیق Score

اجزا در بازهٔ ۰ تا ۱۰۰:

- `expectancy_score = clamp(expectancy_r, 0, 1) × 100` فقط اگر R واجد شرایط باشد؛ در غیر این‌صورت neutral برابر ۵۰.
- `win_rate_score = clamp(win_rate, 0, 100)`.
- `pf_score = clamp(profit_factor / 5 × 100, 0, 100)`.
- DD دارای دادهٔ معتبر: `dd_score = clamp(100 − max_dd_percent × 5, 0, 100)`. درصد باید صریحاً موجود باشد؛ `max_dd` پولی هرگز بر سرمایهٔ فرضی تقسیم نمی‌شود. در نبود درصد صریح، مؤلفه neutral=50 و unavailable علامت می‌خورد.
- مقدار `max_dd_percent` تنها در صورت قابل‌تبدیل بودن به عدد finite و نامنفی معتبر است؛ malformed، NaN، ±∞ و مقدار منفی unavailable هستند و DD score برابر ۵۰ به‌عنوان fallback می‌شود. DD معتبر صفر، امتیاز ۱۰۰ دارد.
- وزن‌ها به‌ترتیب ۴۰٪، ۲۰٪، ۲۰٪ و ۲۰٪ هستند.
- جریمهٔ تعداد معامله: کمتر از ۱۰، ۳۰ امتیاز؛ ۱۰ تا ۲۹، ۱۵ امتیاز؛ حداقل ۳۰، صفر.
- اگر متادیتای پوشش R موجود باشد و پوشش کمتر از ۷۰٪ باشد: `r_penalty = (70 − coverage) / 70 × 15`؛ در غیر این‌صورت صفر.
- `score = clamp(weighted_sum − sample_penalty − r_penalty, 0, 100)`.

### صلاحیت R

R فقط وقتی واجد صلاحیت محاسبهٔ مؤلفهٔ expectancy است که metadata موجود باشد، `r_valid_count > 0` و پوشش حداقل ۷۰٪ باشد. پوشش مستقیم `r_coverage_percent` اولویت دارد؛ در صورت نبود آن، از `r_valid_count / total_trades × 100` استفاده می‌شود. metadata کاملاً غایب به‌معنی عملکرد بد نیست: expectancy neutral می‌شود، جریمه/هشدار پوشش نمی‌گیرد و هشدار expectancy ضعیف هم صادر نمی‌شود. R ناقص نیز expectancy را از امتیاز خارج می‌کند و صرفاً جریمهٔ پوشش می‌گیرد.

## معنا و ارز متریک‌ها

`r_multiple` تغییر نکرده و همچنان **gross price R** بر پایهٔ حرکت قیمت و فاصلهٔ ریسک (initial SL، و در نبود آن SL) است؛ commission و swap در آن منظور نمی‌شوند. Expectancy امتیاز نیز صریحاً از همین gross price R است. PnL خالص همچنان متریک پولی مستقل (شامل هزینه‌هایی که محاسبهٔ مشترک PnL اعمال می‌کند) است. net R تاریخی تولید یا حدس زده نمی‌شود.

## شفافیت Comparison

در جدول و پنل جزئیات Comparison وضعیت DD unavailable و امتیاز neutral fallback=50، eligibility/fallback expectancy، برچسب gross price R و حذف commission/swap، metadata پوشش/count و مقدار جریمهٔ پوشش نمایش داده می‌شوند. metadata ذخیره‌شده از snapshot برای مسیر unfiltered و متریک‌های محاسبه‌شدهٔ مجدد برای مسیر filtered در دسترس Score قرار می‌گیرند.

تحلیل/امتیاز در دامنهٔ ژورنال Strategy از PnL معاملاتی USDT استفاده می‌کند؛ DD پولی نیز واحد پولی همان ژورنال را دارد اما بدون سرمایهٔ مبنا درصد DD نیست. FX و تبدیل ارز اضافه نشده است. مقدار عددی importهای تاریخی دستکاری نشده. در فایل‌های موردنیاز این مرحله hardcode ارزی که لازم به حذف باشد مشاهده نشد؛ API stats جاری مقادیر net را تجمیع می‌کند و برچسب `USDT` سخت‌کدشدهٔ نامتناسبی در مسیر هدف پیدا نشد.

## فایل‌های تغییرکرده

- `backend/app/services/version_score.py`: اعتبارسنجی finite/نامنفی DD؛ neutral fallback؛ eligibility و penalty پوشش R؛ metadata شرح Score.
- `backend/app/services/analysis_service.py`: انتقال R valid count/coverage از snapshot در مسیر unfiltered.
- `backend/tests/test_phase52_score_v2.py`: regressionهای DD نامعتبر/صفر و مرز پوشش R.
- `backend/tests/test_phase48a_comparison.py`: انتقال metadata در هر دو مسیر filtered/unfiltered.
- `frontend/src/pages/ComparisonPage.tsx`, `frontend/src/api/client.ts`: نمایش جزئیات fallback، پوشش/جریمه و gross price R.
- `backend/tests/test_phase48a_score.py`: تست‌های سازگاری Score به ورودی صریح DD و R واجدشرایط تغییر کردند.
- `STRATEGY_FIX_STAGE2.md`: همین گزارش.

هیچ migration، تغییر Dashboard/Finance، تبدیل ارز یا بازنویسی مقدار تاریخی انجام نشد. `STRATEGY_COMPARISON_FIX_VERIFICATION.md` و `STRATEGY_FIX_STAGE1.md` دست‌نخورده‌اند؛ تغییرات قبلی محلی حفظ شده‌اند.

## نتایج آزمون

فرمان backend با venv از `C:\MokTradeDesk\backend`:

```text
.\venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_phase52_score_v2.py tests/test_phase48a_score.py tests/test_phase48a_comparison.py tests/test_phase53_r_initial_sl.py tests/test_metrics.py
```

نتیجه: **۵۶ passed، ۹ warnings در ۳٫۸۱ ثانیه**. هشدارها deprecation موجود در Starlette/FastAPI/Pydantic/SQLAlchemy هستند.

Frontend: `npm run build` از `C:\MokTradeDesk\frontend` موفق شد (TypeScript و Vite production build). اجرای کامل `npm run lint` به دلیل ۲۵۱ خطای ESLint قدیمی در سطح کل پروژه موفق نیست؛ lint هدفمند نیز خطاهای موجود `any` و قواعد hook در همان فایل‌های frontend را نشان می‌دهد. این موارد به‌عنوان محدودیت پایه ثبت می‌شوند.

## تصمیم‌های محصولی باز

1. آیا امتیاز DD در آینده باید با سرمایهٔ مبنا/تعریف‌شده برای هر تحلیل پشتیبانی شود؟ تا آن زمان DD بدون درصد صریح neutral است و نه صفر واقعی.
2. آستانهٔ پوشش R برابر ۷۰٪ و حداکثر جریمهٔ ۱۵، policy موقت این Score است و باید با محصول تأیید شود.
3. امتیازهای داده‌های legacy که فاقد metadata پوشش R دارند همچنان قابل محاسبه‌اند اما با expectancy خنثی و بدون جریمهٔ R؛ consumerها باید `components.r_eligible` و `components.dd_available` را برای تفسیر بررسی کنند.
4. محاسبهٔ net R نیازمند تعریف ریسک پولی هم‌واحد و بازبینی کیفیت دادهٔ commission/swap است؛ در این مرحله عمداً تولید نمی‌شود.

