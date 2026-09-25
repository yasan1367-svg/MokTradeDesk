# 📊 تحلیل جامع پروژه MokTradeDesk

**تاریخ تحلیل**: ۱۴۰۴/۰۷/۰۲ (۲۰۲۶-۰۹-۲۳)  
**نسخه بررسی‌شده**: آخرین کامیت `5867112`  
**ابعاد بررسی**: Backend (FastAPI + SQLAlchemy) + Frontend (React 19 + TypeScript)  
**فایل‌های مرجع**: MokTradeDesk-1.md, MokTradeDesklast-bluprint-2.md, MokTradeDesk-3..md, NOTES.md

---

## 📌 خلاصه وضعیت

| شاخص | وضعیت |
|-------|--------|
| **تطابق با بلوپرینت** | ~۸۵٪ (بخش‌های اصلی پیاده‌سازی شده، ۸ باگ/نقص باقی‌مانده) |
| **پایداری Backend** | خوب (ولی ۵ باگ منطقی باقی‌مانده) |
| **پایداری Frontend** | خوب (۱ باگ Import + هاردکدهای Dashboard) |
| **Migration** | سالم و آماده‌ی کار (فقط `c4838cd01bbd`) |
| **واحدها (دلار/درصد)** | ✅ به‌درستی پیاده‌سازی شده |
| **Prop Rule Engine** | ✅ کامل و صحیح |
| **Analysis Engine** | ⚠️ ناقص — ۴ باگ محاسباتی و نداشتن AnalysisRun |
| **امنیت داده تاریخی** | ✅ مخرب‌ نبودن رعایت شده (جز overwrite تحلیل) |

## 🎯 مقایسه با بلوپرینت

### ✅ بخش‌های منطبق با بلوپرینت

| بخش | وضعیت | توضیح |
|------|--------|--------|
| Trade Classification Contract | ✅ | BACKTEST/FORWARD/REAL-PERSONAL/REAL-PROP با XOR |
| TradeValidator | ✅ | اعتبارسنجی کامل Classification و Numbers و Dates |
| PropRuleEngine.evaluate_stage | ✅ | Daily DD, Total DD, Profit Target, Trading Days |
| PropRuleEngine.validate_withdrawal | ✅ | بررسی کامل قبل از برداشت |
| درصد ↔ دلار (Create Account) | ✅ | کاربر درصد می‌دهد، Backend دلار ذخیره می‌کند |
| درصد ↔ دلار (Pass Modal) | ✅ | قوانین مرحله بعدی با درصد |
| درصد ↔ دلار (Edit Stage) | ✅ | `startEditStage` + `handleSaveStageRules` |
| نمایش دلار در همه مودال‌ها | ✅ | وضعیت کنونی + بررسی و پاس |
| Duplicate Detection (trade_hash) | ✅ | MD5 hash در Import |
| net_pnl در تحلیل پایه | ✅ | `_calculate_basic_metrics` از net_pnl استفاده می‌کند |
| net_pnl در max_dd تحلیل | ✅ | `_calculate_max_drawdown` از net_pnl استفاده می‌کند |
| net_pnl در PropRuleEngine | ✅ | equity از total_pnl (pnl+commission+swap) محاسبه می‌شود |
| N+1 حل‌شده در trades | ✅ | `joinedload` در GET trades |
| RTL + Vazirmatn + شمسی | ✅ | UI فارسی و RTL |

### ⚠️ انحراف‌ها و نواقص

| شماره | شرح | شدت |
|--------|------|------|
| ۱ | `_summarize` هنوز از raw `pnl` استفاده می‌کند (نه net_pnl) | 🔴 |
| ۲ | `calculate_stage_progress` هنوز حذف نشده (تکراری با PropRuleEngine) | 🟡 |
| ۳ | Import برای پراپ و شخصی version_id را ارسال نمی‌کند | 🔴 |
| ۴ | `_calculate_max_consecutive_losses` از raw `pnl` استفاده می‌کند | 🟡 |
| ۵ | `_calculate_consistency` از raw `pnl` استفاده می‌کند | 🟡 |
| ۶ | AnalysisRun پیاده‌سازی نشده (تحلیل قبلی overwrite می‌شود) | 🟡 |
| ۷ | Dashboard هاردکدهای مصنوعی دارد | 🟢 |
| ۸ | `datetime.utcnow()` در کل پروژه استفاده شده (deprecated) | 🟢 |
---

## 🔴 باگ‌های بحرانی (اولویت فوری)

### ۱. Import — version_id برای REAL PROP و REAL PERSONAL ارسال نمی‌شود
**فایل**: `backend/app/api/imports.py` (خطوط ۵۹-۷۱ و ۱۵۸-۱۷۰)

```python
# مشکل:
elif prop_stage_id:
    result = importer.save_trades(
        trades,
        prop_stage_id=prop_stage_id,
        personal_account_id=personal_account_id,
    )  # ← version_id ارسال نشده!

elif personal_account_id:
    result = importer.save_trades(
        trades,
        personal_account_id=personal_account_id,
    )  # ← version_id ارسال نشده!
```

طبق Trade Classification Contract، معاملات REAL باید version_id داشته باشند.  
`ImportPage.tsx` از قبل version_id را برای مقصد prop و personal ارسال می‌کند، ولی API از آن استفاده نمی‌کند.

**راه‌حل**:
1. در `api/imports.py`، `version_id` را به هر دو مسیر `elif prop_stage_id` و `elif personal_account_id` اضافه کنید.
2. Validation اضافه شود که برای REAL، حتماً version_id وجود داشته باشد.

---

### ۲. `_summarize` از raw `pnl` استفاده می‌کند (نه net_pnl = pnl + commission + swap)
**فایل**: `backend/app/services/analysis_service.py` (خط ۶۸۵-۷۰۴)

```python
def _summarize(self, trades: List[Trade]) -> Dict[str, Any]:
    ...
    net_pnl = sum(t.pnl for t in trades if t.pnl) or 0  # ❌ فقط pnl
```

در حالی که `_calculate_basic_metrics` (خط ۴۶۸-۵۲۴) از `net_pnl = pnl + commission + swap` استفاده می‌کند.  
این باعث می‌شود تحلیل‌های Session، Weekday، Hour و Custom Interval با تحلیل پایه ناهم‌خوان باشند.

**تأثیر**: تمام تحلیل‌های جانبی (جلسات، روزهای هفته، ساعات، بازه‌های سفارشی) اعداد نادرستی نشان می‌دهند.

**راه‌حل**: Helper function `_net_pnl(t)` را به متد کلاس تبدیل کنید و در `_summarize` هم استفاده کنید.
---

## 🟡 باگ‌های با اولویت متوسط

### ۳. `calculate_stage_progress` تکراری — باید حذف شود
**فایل**: `backend/app/services/analysis_service.py` (خط ۳۸۵-۴۶۳)

این متد با `PropRuleEngine.evaluate_stage` تکراری است. تمام منطق پراپ باید فقط در `PropRuleEngine` باشد.  
حذف این متد باعث کاهش کد تکراری و جلوگیری از Divergence منطق در آینده می‌شود.

**راه‌حل**: متد کامل حذف شود (و هر جایی که از آن استفاده می‌شود، به `PropRuleEngine.evaluate_stage` تغییر کند).

---

### ۴. `_calculate_max_consecutive_losses` از raw `pnl` استفاده می‌کند
**فایل**: `backend/app/services/analysis_service.py` (خط ۵۴۰-۵۵۱)

```python
if t.pnl is not None and t.pnl < 0:  # ❌ باید net_pnl باشد
```

**راه‌حل**: از `_net_pnl(t)` استفاده کند.

---

### ۵. `_calculate_consistency` از raw `pnl` استفاده می‌کند
**فایل**: `backend/app/services/analysis_service.py` (خط ۵۵۳-۵۸۹)

```python
wins = [t for t in trades if t.pnl and t.pnl > 0]     # ❌ باید net_pnl باشد
pnl_values = [t.pnl for t in trades if t.pnl is not None]  # ❌ باید net_pnl باشد
```

**راه‌حل**: تمام ارجاعات به `t.pnl` در این متد با `_net_pnl(t)` جایگزین شود.

---

### ۶. AnalysisRun (تاریخچه تحلیل) پیاده‌سازی نشده
**فایل‌های مورد نیاز**: `backend/app/models/strategy.py` + `backend/app/services/analysis_service.py`

مشکل فعلی: `analyze_version` هر بار تحلیل قبلی را **حذف** و یک رکورد جدید می‌سازد (overwrite).

```python
existing = self.db.query(AnalysisResult).filter(
    AnalysisResult.version_id == version_id
).first()
if existing:
    self.db.delete(existing)  # ❌ تاریخچه از بین می‌رود
    self.db.commit()
```

**راه‌حل طبق بلوپرینت**:
- مدل جدید `AnalysisRun` با فیلدهای: `id, version_id, created_at, metrics_snapshot (JSON), notes`
- `analyze_version` به‌جای overwrite، یک `AnalysisRun` جدید بسازد
- API جدید `GET /api/analytics/runs/{version_id}` برای نمایش تاریخچه

---

## 🟢 باگ‌های با اولویت پایین

### ۷. `datetime.utcnow()` در Python 3.12 منسوخ شده
**فایل‌ها**: تمام مدل‌ها و APIها (بیش از ۲۰ محل)

```python
created_at = Column(DateTime, default=datetime.utcnow)  # ⚠️ deprecated
```

باید با `datetime.now(timezone.utc)` جایگزین شود. همچنین `from datetime import timezone` باید اضافه شود.

---

### ۸. Dashboard هاردکد دارد
**فایل**: `frontend/src/pages/DashboardPage.tsx`

- `ProgressBar value={65}` (خط ۳۶۴) — مقدار ثابت برای پیشرفت پراپ
- `۶۵٪` (خط ۳۶۷) — درصد ثابت
- `۷۸٪`, `۹۲٪`, `۶۵٪` (خطوط ۳۸۱-۳۹۶) — اهداف ماهانه/فصلی/سالانه
- `sparkData` آرایه‌های ثابت (خطوط ۵۷-۸۴)

**راه‌حل**:
- پیشرفت پراپ از `currentStageProgress.profit_progress_percent` خوانده شود
- اهداف از API واقعی یا تنظیمات خوانده شوند
---

## 📋 ۱٪ باقی‌مانده — کارهای تکمیلی

با توجه به اینکه پروژه ۹۹٪ کامل اعلام شده، این‌ها دقیقاً همان ۱٪ باقی‌مانده هستند:

### تکمیل PHASE 5 (Import Pipeline)
- رفع باگ version_id در import برای مقصد prop و personal (باگ شماره ۱)

### تکمیل PHASE 6 (Prop Rule Engine)
- حذف `calculate_stage_progress` تکراری (باگ شماره ۳)

### تکمیل PHASE 7 (Analysis)
- رفع `_summarize` برای استفاده از net_pnl (باگ شماره ۲)
- رفع `_calculate_max_consecutive_losses` (باگ شماره ۴)
- رفع `_calculate_consistency` (باگ شماره ۵)
- اضافه کردن مدل و API تحلیل `AnalysisRun` (باگ شماره ۶)

### تمیزکاری عمومی
- جایگزینی `datetime.utcnow()` با `datetime.now(timezone.utc)` (باگ شماره ۷)
- حذف هاردکدهای Dashboard (باگ شماره ۸)

### PHASE 8-9-10 (آینده)
- PHASE 8: استانداردسازی Screenshot و Journal
- PHASE 9: تست Regression
- PHASE 10: ماژول مالی شخصی (Personal Finance)

---

## 🗺️ نقشه راه گام‌به‌گام

| گام | شرح | فایل‌ها | اولویت | زمان تخمینی |
|-----|------|---------|--------|-------------|
| **۱. Backup** | کپی `trading_desk.db` به `.db.bak` | — | 🔴 | ۱ دقیقه |
| **۲. رفع Import** | اضافه کردن version_id به مسیر prop/personal | `api/imports.py` | 🔴 | ۱۵ دقیقه |
| **۳. رفع `_summarize`** | استفاده از net_pnl به‌جای raw pnl | `services/analysis_service.py` | 🔴 | ۱۰ دقیقه |
| **۴. رفع consistency** | `_calculate_consistency` با net_pnl | `services/analysis_service.py` | 🟡 | ۱۰ دقیقه |
| **۵. رفع consecutive** | `_calculate_max_consecutive_losses` با net_pnl | `services/analysis_service.py` | 🟡 | ۵ دقیقه |
| **۶. حذف تکراری** | حذف `calculate_stage_progress` | `services/analysis_service.py` | 🟡 | ۵ دقیقه |
| **۷. AnalysisRun** | مدل + API + تغییر analyze_version | `models/strategy.py`, `services/analysis_service.py`, `api/analytics.py`, migration | 🟡 | ۱-۲ ساعت |
| **۸. رفع Dashboard** | حذف هاردکدها | `frontend/src/pages/DashboardPage.tsx` | 🟢 | ۳۰ دقیقه |
| **۹. utcnow** | جایگزینی datetime سراسری | تمام فایل‌های backend | 🟢 | ۲۰ دقیقه |
| **۱۰. بررسی نهایی** | اجرای Backend + Frontend و تست Regression | — | 🔴 | ۳۰ دقیقه |

> **جمع زمان تخمینی گام‌های ۱ تا ۶ (حیاتی)**: ~۱ ساعت  
> **کل زمان تخمینی (با گام‌های ۷-۱۰)**: ~۴-۵ ساعت
---

## 📊 سلامت کد — ارزیابی تفصیلی

### Backend Models — ✅ ۱۰۰٪
تمام مدل‌ها مطابق بلوپرینت پیاده‌سازی شده‌اند:
- `Trade` با `version_id`, `personal_account_id`, `prop_stage_id`, `commission`, `swap`, `trade_hash`
- `Strategy` + `StrategyVersion` با `forked_from_version_id`
- `PropFirm` + `PropAccount` + `PropStage` + `PropWithdrawal` + `PropCost` + `PropAlert`
- `PersonalAccount` + `LedgerTransaction` + `JournalReview` + `Screenshot`
- `AnalysisResult` با تمام متریک‌های جدید (expectancy, consistency و غیره)
- `CustomTimeInterval`, `TimePoint`, `SymbolMapping`, `UserSettings`

### Backend Services — ⚠️ ۸۵٪
- `PropRuleEngine` — ✅ کامل و صحیح
- `TradeValidator` — ✅ کامل و صحیح
- `ImportService` — ✅ (اما API-level باگ دارد)
- `AnalysisService` — ⚠️ ۴ باگ محاسباتی
- `TradeMetrics` — ✅

### Backend API — ⚠️ ۹۰٪
- تمام endpointهای لازم پیاده‌سازی شده‌اند
- مشکل اصلی: `api/imports.py` — version_id در مسیر prop/personal
- `api/prop.py` — withdraw به‌درستی از PropRuleEngine استفاده می‌کند

### Frontend — ⚠️ ۹۰٪
- تمام صفحات اصلی پیاده‌سازی شده‌اند
- `PropPage.tsx` — ✅ درصد↔دلار کامل
- `ImportPage.tsx` — ✅ از قبل version_id را برای prop ارسال می‌کند
- `DashboardPage.tsx` — ⚠️ هاردکد
- RTL + شمسی — ✅

### Migration — ✅ ۱۰۰٪
- `c4838cd01bbd_initial_schema_with_trade_hash.py` — کامل و سالم
- تمام جداول در migration تعریف شده‌اند
- فایل خالی `194035fd2e2e` که در NOTES.md ذکر شده بود، وجود ندارد (ظاهراً حذف یا rename شده)

---

## ✅ تأیید نهایی

### آنچه درست کار می‌کند:
- ✅ Trade Classification Contract (XOR validation)
- ✅ Prop Rule Engine (تمام محاسبات)
- ✅ درصد ↔ دلار (تمام فرم‌ها)
- ✅ Import با Duplicate Detection
- ✅ net_pnl در تحلیل پایه و max_dd
- ✅ RTL و تاریخ شمسی
- ✅ Migration فعلی کامل است

### آنچه باید فوراً رفع شود:
- 🔴 Import version_id (API-level bug)
- 🔴 `_summarize` با net_pnl

### آنچه در اولویت دوم است:
- 🟡 حذف `calculate_stage_progress`
- 🟡 رفع `_calculate_max_consecutive_losses` و `_calculate_consistency`
- 🟡 AnalysisRun

### آنچه برای تمیزکاری:
- 🟢 هاردکدهای Dashboard
- 🟢 `datetime.utcnow()` → `datetime.now(timezone.utc)`

---

**امضای تحلیل**: AI Senior Developer & Software Analyst  
**وضعیت**: آماده‌ی اقدام — منتظر تأیید کاربر برای شروع پیاده‌سازی