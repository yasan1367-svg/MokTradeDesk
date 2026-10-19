# گزارش راستی‌آزمایی اصلاحات ممیزی استراتژی و مقایسه

**تاریخ بررسی:** ۲۰۲۶-۱۰-۱۲  
**مبنای بررسی:** `C:\MokTradeDesk\STRATEGY_COMPARISON_AUDIT_2026-10-09.md` و کد موجود در workspace  
**دامنه تغییرات این کار:** فقط این گزارش؛ هیچ کد، تست، schema، migration یا تنظیماتی ویرایش نشده است.

## خلاصه مدیریتی

بررسی کد فعلی نشان می‌دهد برخی یافته‌ها واقعاً اصلاح شده‌اند؛ از جمله جلوگیری از برنده‌شدن مورد صفر‌معامله، گارد تازگی برای تحلیل بدون فیلتر، محدودکردن stats اصلی به معاملات بسته، و حفاظت حذف در برابر تاریخچه/معاملات. بااین‌حال چند مورد مهم فقط بخشی از سناریو را پوشش می‌دهند و نباید به‌عنوان رفع کامل گزارش شوند. به‌خصوص:

- گارد تازگی compare فقط در مسیر بدون فیلتر اجرا می‌شود؛ محاسبه فیلترشده مستقیماً از معاملات فعلی استفاده می‌کند و مسیرهای API تحلیل همچنان اختلاف دارند.
- قاعده closed-only در تحلیل و stats اعمال شده، اما نمودارهای Strategy داده را از endpoint معاملات می‌گیرند و از روی شواهد موجود بسته‌بودن همه ردیف‌ها تضمین نشده است.
- امتیاز DD همچنان از DD پولی و سرمایه فرضی استفاده می‌کند؛ پوشش R در metadata هست، اما در صلاحیت Score اعمال نشده است.
- چند مورد UI، قرارداد API، transaction تحلیل و معنای شاخص‌های مالی هنوز باز هستند.

وضعیت‌ها در این گزارش بر اساس کد فعلی‌اند، نه صرفاً وجود تست یا یادداشت فاز. «FIXED» یعنی مسیر توصیف‌شده در یافته اصلی با کد موجود رفع شده؛ این برچسب تضمین نمی‌کند تمام دامنه‌های محصولیِ گسترده‌تر نیز پوشش داده شده باشند. «PARTIALLY FIXED» به معنی رفع محدود به سناریو/endpoint مشخص است.

## جدول وضعیت ۲۸ یافته

| # | شدت ممیزی | وضعیت | جمع‌بندی فعلی |
|---:|---|---|---|
| 1 | P1 | **PARTIALLY FIXED** | compare بدون فیلتر freshness را کنترل می‌کند؛ مسیر فیلترشده خیر. |
| 2 | P1 | **PARTIALLY FIXED** | تحلیل و stats اصلی closed-only هستند؛ همه مسیرهای نمایش/مقایسه یکسان نیستند. |
| 3 | P1 | **FIXED** | `no_data` از rank و best کنار گذاشته می‌شود. |
| 4 | P1 | **PARTIALLY FIXED** | fallback قدیمی با دامنه کنترل می‌شود، ولی قرارداد legacy و GETهای قدیمی کاملاً یکسان/صریح نیست. |
| 5 | P1 | **OPEN** | Score هنوز DD پولی را نسبت به حساب فرضی می‌سنجد؛ اتصال سرمایه واقعی به Score تأیید نشد. |
| 6 | P1 | **PARTIALLY FIXED** | شمار/درصد پوشش R موجود است؛ قاعده صلاحیت و وزن Score آن را لحاظ نمی‌کند. |
| 7 | P1 | **OPEN** | R از فاصله قیمت و SL اولیه است؛ هزینه‌های پولی در آن وارد نیست. |
| 8 | P1 | **OPEN** | تجمیع ارز/حساب و برچسب ثابت USDT همچنان در قراردادهای بررسی‌شده دیده می‌شود. |
| 9 | P2 | **PARTIALLY FIXED** | آمار per-version افزوده شده، اما aggregate همچنان ترکیب نسخه‌ها و انواع را نمایش می‌دهد. |
| 10 | P2 | **PARTIALLY FIXED** | تابع وضعیت‌دار PF وجود دارد، اما مسیر Strategy هنوز sentinel متفاوت دارد. |
| 11 | P2 | **OPEN** | Sharpe تجمیعی همچنان بر مبنای PnL معامله و تعداد معاملات است. |
| 12 | P2 | **PARTIALLY FIXED** | اعتبارسنجی PATCH از شواهد موجود بهتر از create/Fork است؛ مسیرهای ورودی هنوز هم‌قرارداد نیستند. |
| 13 | P2 | **PARTIALLY FIXED** | URL نوع تست را whitelist می‌کند؛ API همچنان schema رشته‌ای و تاریخ‌های با اعتبارسنجی ناکامل دارد. |
| 14 | P2 | **PARTIALLY FIXED** | UI/URL تکرار را حذف می‌کند؛ schema API از یکتایی/وجود نسخه‌ها اطمینان نمی‌دهد. |
| 15 | P1 | **PARTIALLY FIXED** | حذف با Trade، AnalysisScope، AnalysisRun و نتیجه محافظت می‌شود؛ تمام وابستگی‌های fork/تمام مسیرها اثبات نشده‌اند. |
| 16 | P2 | **OPEN** | حذف نتیجه قدیمی و ساخت نتیجه جدید چند commit دارد، نه یک transaction اتمیک. |
| 17 | P2 | **OPEN** | snapshot موجود قوانین یا نسخه موتور/Score را به اجرا مقید نمی‌کند. |
| 18 | P2 | **OPEN** | label نوع نسخه هنوز با طبقه‌بندی معاملات و نوع درخواست مقایسه یکی نیست. |
| 19 | P2 | **PARTIALLY FIXED** | create نوع تست و edit وضعیت را می‌فرستد؛ create وضعیت و edit نوع تست هنوز ارسال نمی‌شود. |
| 20 | P2 | **OPEN** | کنترل درخواست stale برای بارگیری Strategy/نسخه‌ها/آمار در کد بررسی‌شده مشاهده نشد. |
| 21 | P2 | **OPEN** | با تغییر فیلتر یا clear، پاسخ دیررس compare و نتیجهٔ فیلتر قبلی به‌طور کامل مهار نمی‌شود. |
| 22 | P2 | **OPEN** | CRUD/Fork فهرست‌ها را refresh می‌کند، اما refresh مجدد آمار/عملکرد در همان مسیر دیده نمی‌شود. |
| 23 | P2 | **OPEN** | نمودارها هنوز معاملات را در درخواست‌های جداگانه می‌گیرند و خطاهای موردی را حذف می‌کنند. |
| 24 | P2 | **OPEN** | Radar PnL منفی و کلید سری مبتنی بر نام را به‌صورت قابل اتکا حل نکرده است. |
| 25 | P2 | **PARTIALLY FIXED** | tie policy و حذف no_data از رتبه اضافه شده؛ دلایل رتبه و مساوی بودن هنوز بهبود می‌خواهد. |
| 26 | P2 | **OPEN** | اختلاف timezone و semantics بازه سفارشی در AnalysisService باقی است. |
| 27 | P3 | **OPEN** | schemaهای موازی و typeهای کم‌دقت هنوز وجود دارند. |
| 28 | P3 | **OPEN** | default نام Fork همچنان رشتهٔ دارای `}` اضافه می‌سازد. |

## شواهد تفصیلی

شماره خطوط این بخش در فایل‌های فعلی workspace است و ممکن است با نسخه‌ای که audit اولیه ثبت کرده متفاوت باشد.

### P1 — یافته‌های ۱ تا ۸

1. **تازگی compare — PARTIALLY FIXED.** در `backend/app/services/analysis_service.py:239-249`، وقتی `symbol/date_from/date_to` خالی‌اند، `check_analysis_freshness` اجرا و تحلیل stale به‌صورت خطا برگردانده می‌شود. اما شاخه فیلترشده `_calculate_filtered_metrics` را مستقیم صدا می‌زند (`:239-242`)، پس تغییر Trade پس از تحلیل لزوماً stale اعلام نمی‌شود. تست‌های `backend/tests/test_phase53_stale_analysis.py` تغییر PnL/زمان و no_data را پوشش می‌دهند؛ این تست‌ها به‌تنهایی شاخه‌های همه فیلترها و حذف/افزودن را ثابت نمی‌کنند.
2. **معاملات باز/بسته — PARTIALLY FIXED.** `AnalysisService.analyze_prop_stage` و `analyze_personal_account` شرط `close_time.isnot(None)` دارند (`analysis_service.py:353-374`)، و تحلیل نسخه نیز در همان سرویس closed-only است. stats استراتژی نیز شرط `Trade.close_time.isnot(None)` دارد (`backend/app/api/strategies.py:549-559`). با این حال، گارد freshness، compare فیلترشده و بارگیری معاملات نمودارها باید predicate یکسان داشته باشند؛ endpoint معاملات نمودار در `StrategyPage.tsx:453-463` برای هر نسخه جداگانه فراخوانی می‌شود و تضمین closed-only بودن خروجی/محاسبه کلاینت از این مسیر احراز نشد. تست `backend/tests/test_closed_trades_only.py` تحلیل، حساب پراپ/شخصی و pass-stage را می‌سنجد، نه همه مصرف‌کنندگان UI.
3. **صفر معامله — FIXED.** در `analysis_service.py:263-268` آیتم صفرمعامله `status=no_data`، `rank=None` و `score=0` می‌گیرد؛ sort آن را در انتها می‌گذارد (`:270-285`)، rank نمی‌گیرد (`:286-290`) و انتخاب best فقط total_trades مثبت را می‌پذیرد (`:292-296`). تست `test_compare_zero_trades_is_not_best` در `backend/tests/test_phase53_stale_analysis.py:157-181` همین را assert می‌کند.
4. **legacy Backtest/Forward — PARTIALLY FIXED.** تست‌های `test_compare_legacy_fallback_checks_snapshot_scope` و `test_compare_with_specific_test_type_does_not_use_legacy_fallback` در `backend/tests/test_phase53_stale_analysis.py:108-154` نشان می‌دهند fallback خارج از دامنه یا نوع صریح رد می‌شود. اما چون این حفاظت در مسیرهای مختلف GET/compare باید یکپارچه باشد و برخی APIهای legacy هنوز جدا هستند، رفع کاملِ خطر دامنه legacy احراز نشد.
5. **مقیاس DD در Score — OPEN.** `backend/app/services/analysis_service.py:557-561` درصد واقعی DD را فقط وقتی سرمایه واقعی به آن تحلیل متصل باشد محاسبه می‌کند؛ اما مقایسه `calculate_version_score(metrics_d)` را صدا می‌زند و اثباتی از انتقال/مصرف `max_dd_percent` برای همه نسخه‌ها نیست. تست‌های `backend/tests/test_phase52_score_v2.py` صریحاً مبنای `ASSUMED_ACCOUNT_SIZE=10000` را دارند. بنابراین ریسک پولی در Score نرمال‌شدهٔ سرمایه واقعی نیست.
6. **پوشش R — PARTIALLY FIXED.** محاسبه تحلیل شمار/درصد R معتبر را نگه می‌دارد (در `analysis_service.py` بخش `_calculate_basic_metrics`، خطوط اطراف 551-574)، اما `calculate_version_score` بر تعداد کل معامله نمونه را ارزیابی می‌کند؛ تست‌های `backend/tests/test_phase52_score_v2.py:39-48,73-83` وضعیت نمونه را صرفاً از total_trades تعیین می‌کنند. پوشش را باید در response/Score/نمایش و آستانه صلاحیت نیز وارد کرد.
7. **R خالص از هزینه — OPEN.** `backend/app/utils/trade_metrics.py:9-45` ریسک را از فاصله open تا SL (با اولویت initial_sl) و حرکت قیمت می‌سازد؛ commission/swap در امضای تابع نیست. `backend/tests/test_phase53_r_initial_sl.py` فقط استفاده از Initial SL و fallback به SL را اعتبارسنجی می‌کند، نه R پولی خالص.
8. **ارز و حساب — OPEN.** stats per-version در `backend/app/api/strategies.py:547-570` معاملات نسخه را گروه‌بندی می‌کند، نه currency/account؛ aggregate هم همان مجموعه را جمع می‌زند (`:585-600`). audit اصلی به برچسب ثابت USDT و جمع حساب‌های متفاوت اشاره دارد؛ تغییرات per-version این قرارداد واحد را حل نمی‌کند.

### P2/P3 — یافته‌های ۹ تا ۲۸

9. **aggregate — PARTIALLY FIXED.** `get_strategy_stats` پاسخ `per_version` برای هر version می‌سازد (`strategies.py:562-571`) ولی همچنان aggregate همه معاملات را برمی‌گرداند (`:585-600`) و تفکیک نوع/دوره مشترک را تعریف نمی‌کند.
10. **PF بدون باخت — PARTIALLY FIXED.** `backend/app/services/metrics.py:112-122` تابع `profit_factor_status` با حالت‌های `no_data/no_losses/finite` دارد، اما legacy `profit_factor_from_sums` هنوز مقدار sentinel 999 می‌دهد (`:125-136`) و مسیر Strategy در `backend/app/api/strategies.py` PF sentinel 100 نگه می‌دارد (audit اولیه `:404/:634`). یکسان‌سازی همه مصرف‌کنندگان اثبات نشده است.
11. **Sharpe — OPEN.** `_summarize_trades` در `backend/app/api/strategies.py:475-483` انحراف معیار PnL هر معامله را محاسبه و در `sqrt(total)` ضرب می‌کند؛ تاریخ/بازده دوره‌ای/سرمایه مرجع مبنا نیست.
12. **اعتبارسنجی ساخت/Fork — PARTIALLY FIXED.** در `backend/app/api/strategies.py:50-68` مدل‌های create و Fork هنوز test_type/status را رشته اختیاری می‌پذیرند؛ audit اولیه تفاوت PATCH و create را بازتولید کرده است. پوشش حذف یا ساخت نامعتبر از تست‌های این اجرا اثبات نشد.
13. **نوع تست/تاریخ — PARTIALLY FIXED.** `frontend/src/utils/comparisonUrl.ts:8,43-54` نوع تست را whitelist می‌کند و تاریخ را regex-check می‌کند؛ regex، تاریخ تقویمی ناممکن را رد نمی‌کند. API در `backend/app/schemas/analytics.py:67-72` test_type و تاریخ‌ها را رشته می‌پذیرد. بنابراین اعتبارسنجی UI جای validation سرور و کنترل بازه را نمی‌گیرد.
14. **شناسه تکراری/ناموجود — PARTIALLY FIXED.** URL سمت کاربر شناسه تکراری را حذف می‌کند (`comparisonUrl.ts:34-41`)؛ اما schema سرور فقط تعداد ۲ تا ۱۰ را محدود می‌کند (`backend/app/schemas/analytics.py:67-72`). uniqueness و existence در خود schema تضمین نشده‌اند.
15. **حذف تاریخچه — PARTIALLY FIXED.** تست‌های `backend/tests/test_phase53_delete_safety.py:62-152` گارد 409 برای Trade، تحلیل، AnalysisScope و AnalysisRun را بررسی می‌کنند؛ این رفع بخش عمده بازتولید audit است. حذف با Fork باقی‌مانده و همه وابستگی‌های غیرمستقیم را این suite به‌طور جامع نمی‌پوشاند؛ نتیجه «کاملاً ایمن» اعلام نمی‌شود.
16. **اتمی‌بودن تحلیل — OPEN.** در `backend/app/services/analysis_service.py:422-425` نتیجه قبلی حذف و جداگانه commit می‌شود؛ Scope/Result/Run بعدتر ساخته می‌شوند (`:427-498`). شکست ساخت بعدی می‌تواند وضعیت قبلی را از دسترس خارج کند.
17. **snapshot قوانین — OPEN.** `analysis_service.py:462-470` filters_snapshot شامل scope، شناسه‌ها، نوع تست و حذف‌شده‌هاست، اما snapshot/hash قوانین نسخه یا نسخه الگوریتم/Score در این بخش دیده نمی‌شود.
18. **label نوع نسخه — OPEN.** مدل `StrategyVersion.test_type` رشته‌ای مستقل از `Trade.test_type` است (`backend/app/models/strategy.py:95-108`). از کد فعلی تضمینی وجود ندارد label صفحه معادل نوع واقعی همه معاملات نسخه باشد.
19. **فرم نسخه — PARTIALLY FIXED.** `frontend/src/pages/StrategyPage.tsx:346-365` هنگام ساخت test_type می‌فرستد اما status را نمی‌فرستد؛ در update status ارسال می‌شود ولی test_type خیر. همچنین `VersionUpdate` در `backend/app/api/strategies.py:65-69` test_type ندارد.
20. **پاسخ stale در StrategyPage — OPEN.** بارگذاری فهرست نسخه‌ها/آمار با state صفحه انجام می‌شود؛ کنترل request generation یا تطبیق شناسه پاسخ در مسیرهای بررسی‌شده یافت نشد. تست اختصاصی وارونگی پاسخ برای StrategyPage در اجرای فعلی احراز نشد.
21. **نتیجه stale در Compare UI — OPEN.** `frontend/src/pages/ComparisonPage.tsx:343-350` پاک‌کردن، selectedIds/result را reset می‌کند و compare از همان صفحه فراخوانی می‌شود؛ cancellation/generation token برای پاسخ درحال اجرا مشاهده نشد. نتیجه نیز زیر فیلترهای تغییریافته می‌تواند نمایش داده شود.
22. **refresh آمار CRUD — OPEN.** `StrategyPage.tsx:368-371` پس از ذخیره نسخه فهرست‌ها را بارگذاری می‌کند؛ در شواهد مسیر، فراخوانی مجدد آمار/performance دیده نمی‌شود. مسیرهای delete/Fork نیز در audit اولیه همین نقص را داشتند؛ تست تازه‌سازی وجود ندارد.
23. **نمودارهای سریالی — OPEN.** `StrategyPage.tsx:453-463` برای نسخه‌ها درخواست معاملات جدا می‌زند و خطای یک درخواست را skip می‌کند؛ این با aggregate سروری یک snapshot مشترک تضمین نمی‌کند.
24. **Radar — OPEN.** audit کد `ComparisonRadarChart.tsx` را بررسی کرد: PnL منفی با دامنه نمودار صفر تا صد سازگاری ندارد و label نام نسخه برای سری یکتا تضمین نشده؛ اصلاح شناسه‌محور در کد فعلی احراز نشد.
25. **tie/explanation — PARTIALLY FIXED.** `analysis_service.py:270-315` sort ثانویه بر PF و تعداد معامله دارد و tie مساوی score/PF/sample را علامت می‌زند؛ no_data نیز کنار گذاشته شده. با این حال policy برنده در tie همچنان یک item را به‌عنوان best نگه می‌دارد و کیفیت explanation مورد audit (دلایل متریک‌های ضعیف/دلایل تفاوت رتبه) با این تغییر کامل حل نمی‌شود.
26. **timezone و بازه سفارشی — OPEN.** در `analysis_service.py:497-559` بخش‌های گروه‌بندی و بازه سفارشی از مسیرهای جدا برای زمان استفاده می‌کنند؛ تست‌های اجراشده در این کار این قرارداد زمانی/مرز بازه را پوشش نمی‌دهند.
27. **schemaهای تکراری — OPEN.** `backend/app/api/strategies.py:40-68` همچنان schema داخلی دارد؛ audit وجود schema موازی در `backend/app/schemas/strategy.py` و typeهای فرانت‌اند را گزارش کرده است. آزمون‌های فعلی وجود یک قرارداد تولیدی یگانه را ثابت نمی‌کنند.
28. **نام Fork — OPEN.** `frontend/src/pages/StrategyPage.tsx:395` رشته `${version.version_name} - Fork}` را می‌سازد؛ `}` اضافه در منبع فعلی باقی است.

## اولویت‌های مسدودکننده برای استفاده تصمیم‌ساز

موارد P1 که پیش از اعتماد به «بهترین نسخه» باید بسته شوند:

1. **#1 و #2: یکسان‌سازی freshness و scope** در compare، GET تحلیل، stats و نمودار؛ تمام مسیرها با یک predicate closed-only و نوع/حساب/بازه همسان کار کنند.
2. **#5 و #6: مبنای ریسک و پوشش داده**؛ Score نباید درصد واقعی DD را از DD پولی/سرمایه فرضی استنباط کند و باید کمبود R را در صلاحیت امتیاز آشکار کند.
3. **#7 و #8: معنای اقتصادی متریک‌ها**؛ net R و ارز/حساب باید روشن و قابل ردیابی باشند، نه صرفاً PnLهای پولی تجمیع‌شده.
4. **#3 و #4: وضعیت داده ناموجود و legacy**؛ no_data اکنون بهتر محافظت شده، اما داده legacy با دامنه نامشخص نباید بی‌علامت به رتبه‌بندی راه یابد.

## ترتیب پیشنهادی رفع

1. **دامنه و تازگی:** #1، #2، #3، #4؛ قرارداد بسته‌شده/نوع/حساب و freshness مشترک، و آزمون edit/add/delete/import در compare.
2. **اعتبار رتبه:** #5، #6، #7، #8، سپس #10، #11، #25؛ metadata سرمایه/ارز/R، PF وضعیت‌دار، و policy tie/صلاحیت.
3. **چرخه داده امن:** #12، #13، #14، #15، #16، #17، #18، #27؛ ورودی 4xx، حذف conflict، transaction اتمیک و snapshot قابل بازتولید.
4. **UI و مشاهده‌پذیری:** #19–24، #26، #28؛ ذخیره فیلدها، cancellation/generation، invalidation، خطای جزئی، chart scale/key, timezone و Fork name.

## اجرای آزمون‌ها

- **Backend هدفمند:** اجرای pytest هدفمند قبلی، طبق نتیجه موجود در این نشست: **۳۷ passed**.
- **Backend آزمون‌های تکمیلی این راستی‌آزمایی:** pytest با `-p no:cacheprovider` روی `test_closed_trades_only.py`، `test_phase48a_score.py`، `test_phase52_score_v2.py`، `test_metrics.py`، `test_phase57_analytics_correction.py`، `test_phase53_delete_safety.py` و `test_phase53_r_initial_sl.py`: **۶۲ passed**. هشدارهای deprecation در FastAPI/SQLAlchemy/Pydantic گزارش شدند.
- **Frontend Vitest:** اجرای کامل با `--pool=forks --maxWorkers=1 --reporter=verbose --silent`؛ خروجی verbose تست‌ها را به صورت پاس نشان می‌دهد، اما ابزار اجرا در این نشست خلاصه نهایی و exit code را ثبت نکرد. بنابراین **نتیجه خاتمه runner نامشخص است و pass قطعی suite ادعا نمی‌شود**. اجرای پیشین با `--minWorkers` نامعتبر بود (Vitest 5 این flag را نمی‌پذیرد) و آن اجرا در نتیجه حساب نشده است.
- یک اجرای تکمیلی backend به دلیل ارجاع به نام تست موجودنبود (`test_version_score.py`) شروع نشد؛ بعداً با نام‌های واقعی تست اصلاح و نتیجه ۶۲ پاس ثبت شد.

## محدودیت و کنترل فایل‌ها

این بررسی read-only نسبت به کد و تست‌ها بوده است. فایل مقصد در آغاز وجود نداشت؛ این گزارش تنها فایل جدید مجاز است. در پایان، وجود و محتوای همین فایل و `git status --short` باید کنترل شود. گزارش هیچ ادعایی درباره نبود تغییرات ناشی از فرایندهای هم‌زمان workspace ندارد.