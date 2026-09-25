# 🚀 پیشنهادات تکمیلی و بهبود MokTradeDesk

**تاریخ**: ۱۴۰۴/۰۷/۰۲ (۲۰۲۶-۰۹-۲۳)  
**نسخه بررسی‌شده**: آخرین کامیت `5867112`  
**فایل‌های مرجع**: ANALYSIS.md, MokTradeDesk-1.md, MokTradeDesklast-bluprint-2.md, MokTradeDesk-3..md, NOTES.md

---

## 📊 خلاصه وضعیت فعلی

پروژه در مجموع **~۸۵٪ مطابق بلوپرینت** است. بخش‌های اصلی پیاده‌سازی شده‌اند ولی ۸ باگ/نقص باقی‌مانده است.

| بخش | وضعیت |
|------|--------|
| Strategy/Version Management | ✅ کامل |
| Trade Classification Contract | ✅ کامل |
| Prop Rule Engine | ✅ کامل |
| Import Pipeline | ⚠️ یک باگ (version_id) |
| Analysis Engine | ⚠️ ۴ باگ محاسباتی |
| Journal/Screenshots | ✅ کامل |
| Personal Ledger/Cashflow | ✅ کامل |
| Dashboard | ⚠️ هاردکدهای مصنوعی |
| Settings | ✅ پایه |

---

## 📑 فهرست مطالب

1. [الف) رفع باگ‌های بحرانی (اولویت فوری)](#الف-رفع-باگ‌های-بحرانی-اولویت-فوری)
2. [ب) تکمیل PHASE 7-10 (بخش‌های ناتمام از بلوپرینت)](#ب-تکمیل-phase-7-10-بخش‌های-ناتمام-از-بلوپرینت)
3. [ج) امکانات جدید پیشنهادی](#ج-امکانات-جدید-پیشنهادی)
4. [د) بهبودهای کیفی/UX](#د-بهبودهای-کیفیux)
5. [ه) بهبودهای معماری](#ه-بهبودهای-معماری)
6. [جدول اولویت‌بندی کلی](#جدول-اولویت‌بندی-کلی)

---

## الف) رفع باگ‌های بحرانی (اولویت فوری)

### ۱. 🔴 Import — version_id برای REAL PROP و REAL PERSONAL ارسال نمی‌شود

**فایل**: `backend/app/api/imports.py` (خطوط ۵۹-۷۱ و ۱۵۸-۱۷۰)  
**توضیح**: طبق Trade Classification Contract، معاملات REAL باید version_id داشته باشند.  
`ImportPage.tsx` از قبل version_id را ارسال می‌کند ولی API از آن استفاده نمی‌کند.

**راه‌حل**:
- در `api/imports.py`، `version_id` را به هر دو مسیر `elif prop_stage_id` و `elif personal_account_id` اضافه کنید
- اعتبارسنجی: اگر `test_type == 'real'` و `prop_stage_id` داری، `version_id` الزامی است (برای هر دو حالت prop و personal)

### ۲. 🔴 `_summarize` هنوز از raw `pnl` استفاده می‌کند (نه `net_pnl`)

**فایل**: `backend/app/services/analysis_service.py`  
**توضیح**: تابع `_summarize` که در `_analyze_by_session`, `_analyze_by_weekday`, `_analyze_by_hour` و `_analyze_by_custom_intervals` استفاده می‌شود، از `t.pnl` استفاده می‌کند در حالی که باید از `t.pnl + (t.commission or 0) + (t.swap or 0)` استفاده کند.

### ۳. 🟡 `_calculate_max_consecutive_losses` از raw `pnl` استفاده می‌کند

**فایل**: `backend/app/services/analysis_service.py`  
**توضیح**: باید از `net_pnl` به‌جای `pnl` استفاده کند تا کمیسیون و swap در محاسبه لحاظ شوند.

### ۴. 🟡 `_calculate_consistency` از raw `pnl` استفاده می‌کند

**فایل**: `backend/app/services/analysis_service.py`  
**توضیح**: باید از `net_pnl` استفاده کند.

### ۵. 🟡 `calculate_stage_progress` تکراری با `PropRuleEngine` است

**فایل**: `backend/app/services/analysis_service.py`  
**توضیح**: تابع `calculate_stage_progress` منطق تکراری با `PropRuleEngine.evaluate_stage` دارد. باید حذف شود و همه‌جا از `PropRuleEngine` استفاده شود.

### ۶. 🟡 AnalysisRun پیاده‌سازی نشده (تحلیل قبلی overwrite می‌شود)

**فایل**: `backend/app/services/analysis_service.py`  
**توضیح**: در `analyze_version`، تحلیل قبلی حذف می‌شود (`self.db.delete(existing)`). این یعنی تاریخچه تحلیل در طول زمان از بین می‌رود.

---

## ب) تکمیل PHASE 7-10 (بخش‌های ناتمام از بلوپرینت)

### ۱. AnalysisRun (تاریخچه تحلیل)

**مشکل فعلی**: هر بار تحلیل اجرا می‌شود، نتیجه قبلی حذف و جایگزین می‌شود.  
**اهمیت**: شما نمی‌توانید روند بهبود استراتژی را در طول زمان ببینید.

**پیشنهاد:**

```python
# مدل جدید در models/strategy.py
class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    
    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, ForeignKey("strategy_versions.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    trades_count = Column(Integer)
    net_pnl = Column(Float)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    max_dd = Column(Float)
    expectancy = Column(Float)
    total_metrics = Column(JSON)  # همه متریک‌ها به صورت JSON
```

**در Frontend**:
- صفحه `AnalysisHistory` با نمودار روند
- Line chart برای `net_pnl`, `win_rate`, `profit_factor` در طول زمان
- امکان انتخاب دو تحلیل و مقایسه جزئیات

### ۲. Dashboard واقعی (حذف هاردکدها)

**مشکل فعلی**: اعداد مصنوعی و هاردکد در Dashboard.

**پیشنهاد**:
- محاسبه sparkline از equity curve واقعی (آخرین ۲۰ معامله)
- نمایش سود/زیان واقعی به تفکیک روز/هفته/ماه
- ویجت «بهترین/بدترین روز معاملاتی»
- ویجت «روند پیشرفت» با data واقعی
- اهداف قابل تعریف توسط کاربر با تاریخ هدف

**API جدید**:
```
GET /api/analytics/dashboard-summary
  → { net_pnl, win_rate, max_dd, profit_factor,
      weekly_pnl: [], monthly_pnl: [],
      best_day, worst_day,
      equity_curve: [] }
```

### ۳. Personal Finance Module (ماژول جدید)

طبق بلوپرینت، این ماژول جدا از Personal Trading Account است.

**مدل‌های پیشنهادی**:

```python
class FinancialAccount(Base):
    """کیف پول، صرافی، حساب بانکی، پول نقد"""
    __tablename__ = "financial_accounts"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    account_type = Column(Enum("wallet", "exchange", "bank", "cash", name="fin_acc_type"), nullable=False)
    currency = Column(String(10), default="USD")
    balance = Column(Float, default=0.0)

class FinancialTransaction(Base):
    """تراکنش مالی شخصی"""
    __tablename__ = "financial_transactions"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("financial_accounts.id"), nullable=False)
    transaction_type = Column(Enum("income", "expense", "transfer", "conversion", "adjustment"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10))
    description = Column(String(500))
    linked_trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    linked_prop_payout_id = Column(Integer, ForeignKey("prop_withdrawals.id"), nullable=True)
    transaction_date = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
```

**صفحه جدید**: `FinancePage.tsx` با:
- لیست حساب‌های مالی
- فرم تراکنش جدید
- گزارش درآمد/هزینه
- اتصال Payout پراپ به‌عنوان درآمد

### ۴. Testing Suite

در حال حاضر پروژه هیچ تستی ندارد.

**پیشنهاد**:

**Backend (pytest)**:
```python
# tests/test_prop_rule_engine.py
# tests/test_analysis_service.py
# tests/test_trade_validator.py
---

## ج) امکانات جدید پیشنهادی

### ۱. Risk Management Dashboard

یک صفحه جامع برای مدیریت ریسک:

**Features**:
- **Position Sizing Calculator**: ورودی‌های Balance, Risk% (مثلاً ۱٪), SL, حجم معامله
  ```
  positionSize = (balance * riskPercent / 100) / (entryPrice - stopLoss)
  ```
- **Risk of Ruin Calculator**: احتمال ورشکستگی بر اساس win rate و risk/reward
  ```
  Risk of Ruin = ((1 - RR) / (1 + RR))^M
  ```
- **Correlation Matrix**: همبستگی بین نمادهای معاملاتی (از روی PnL روزانه)
- **Monte Carlo Simulation**: شبیه‌سازی ۱۰۰۰ مسیر مختلف equity
- **Drawdown Analyzer**: تحلیل عمق و مدت drawdownها

**API جدید**:
```
POST /api/analytics/risk-metrics
  → { position_size, risk_of_ruin, correlation_matrix, monte_carlo_paths }
```

### ۲. Calendar View (تقویم معاملاتی)

**Features**:
- نمایش معاملات روی تقویم شمسی (با کتابخانه react-persian-calendar)
- رنگ‌بندی روزها: سبز (سود), قرمز (زیان), خاکستری (بدون معامله)
- کلیک روی روز → نمایش لیست معاملات آن روز
- نمایش مجموع PnL روزانه
- Hot/Cold streaks
- **Economic Calendar**: نمایش رویدادهای مهم (NFP, FOMC, CPI)
  - Import از ForexFactory API یا manual entry
  - اتصال به معاملات (مثلاً «معامله قبل از NFP»)

### ۳. Export & Reporting

**Features**:
- **PDF Report** از تحلیل یک نسخه:
  - صفحه عنوان با نام استراتژی/نسخه
  - خلاصه متریک‌ها
  - نمودار Equity Curve
  - نمودار Win/Loss Pie
  - جدول Session/Weekday/Hour analysis
  - لیست معاملات
- **CSV Export** از لیست معاملات با فیلترهای اعمال‌شده
- **Share Snapshot**: یک تصویر (PNG) قابل اشتراک‌گذاری از وضعیت (با html2canvas)

### ۴. Trade Journal AI Assistant

با استفاده از داده‌های `JournalReview`:

**Features**:
- **الگوهای تکراری خطا**: از روی `rule_violations` اخطار می‌دهد اگر یک خطا تکرار شده
  ```
  "شما ۳ بار متوالی 'معامله خارج از ساعت' داشته‌اید"
  ```
- **گزارش هفتگی/ماهانه خودکار**:
  - خلاصه عملکرد
  - بهترین/بدترین معامله
  - دروس ثبت‌شده
- **Emotional Trading Detection**:
  - افزایش volume بعد از loss (revenge trading)
  - کاهش volume بعد از win (fear)
  - معاملات پشت‌سر هم در کمتر از ۵ دقیقه
# tests/test_import_service.py
```

**Frontend (vitest)**:
```typescript
// src/components/__tests__/MetricCard.test.tsx
// src/pages/__tests__/TradesPage.test.tsx
// src/api/__tests__/client.test.ts
```
### ۵. Multi-Account Prop Dashboard

**Features**:
- **Consolidated View**: همه حساب‌های فعال در یک نگاه
- **Total Equity**: جمع equity همه حساب‌ها
- **Payout Calendar**: تاریخ‌های payout مورد انتظار
- **Challenge Cost Tracking**: ROI روی هزینه‌های چالش
  ```
  ROI = (Total Payouts - Total Challenge Fees) / Total Challenge Fees * 100
  ```
- **Prop Alerts**: هشدار نزدیک شدن به DD limit (با استفاده از مدل `PropAlert` که وجود دارد)

### ۶. Trade Playback (Replay)

**Features**:
- پخش مجدد معاملات به ترتیب زمانی با انیمیشن
- نمایش equity curve در حال رشد
- نمایش نقاط ورود/خروج
- کنترل سرعت پخش (0.5x, 1x, 2x)

**کتابخانه پیشنهادی**: `lightweight-charts` از TradingView برای نمایش کندل + معاملات

### ۷. Notifications & Alerts

با استفاده از دکمه 🔔 در `App.tsx` که placeholder است:

**Features**:
- **Prop Alerts**: نزدیک شدن به Daily DD limit
- **Time Alerts**: یادآوری برای review معاملات ثبت‌نشده
- **Challenge Deadlines**: هشدار اتمام مهلت چالش
- **Browser Notification**: با Notification API
- **Badge Count**: تعداد نوتیفیکیشن‌های نخوانده

### ۸. Data Backup & Restore

**صفحه جدید یا ویجت در Settings**:

**Features**:
- **Backup**: گرفتن zip از trading_desk.db + storage/screenshots/
- **Restore**: آپلود فایل zip و restore
- **Auto-backup**: تنظیم (روزانه/هفتگی) با مسیر مقصد
- **Encryption**: رمزگذاری اختیاری فایل backup با AES

### ۹. Strategy Rule Builder (Visual)

جایگزینی `rules_note` متنی با یک Rule Builder بصری:

**Features**:
- **Entry Rules**: Indicator (MA, RSI, MACD, ...) + Condition (> , < , = , cross) + Value
- **Exit Rules**: TP, SL, Trailing Stop, Time-based
- **Time Filters**: فقط روزهای خاص، فقط ساعت خاص
- **JSON Storage**: ذخیره به صورت structured JSON
  ```json
  {
    "entry": [
      { "indicator": "RSI", "condition": ">", "value": 30, "timeframe": "M15" },
      { "indicator": "MA_50", "condition": ">", "value": "MA_200", "cross": true }
    ],
    "exit": { "tp": 50, "sl": 30, "trailing": true },
    "filters": { "sessions": ["Europe", "America"], "max_spread": 20 }
  }
  ```
- **Backward Compatibility**: `rules_note` به‌عنوان fallback

### ۱۰. Symbol Watchlist & Screener

**Features**:
- **Watchlist**: لیست نمادهای تحت نظر
- **Price Alerts**: هشدار قیمت با WebSocket
- **Screener**: فیلتر نمادها بر اساس volatility, volume, spread

**موارد تست پیشنهادی**:
- `PropRuleEngine.evaluate_stage` — ۱۰ سناریو مختلف
- `TradeValidator.validate_classification` — ۸ سناریو XOR
- `AnalysisService._calculate_basic_metrics` — ۵ سناریو
- Import با فایل‌های نمونه (Soft4X, MT4)
- UI Components (StatCard, Badge, ProgressBar)
---

## د) بهبودهای کیفی/UX

### ۱. Loading States & Skeletons

در بسیاری از صفحات فقط متن «در حال بارگذاری...» نشان داده می‌شود.

**راه‌حل**: کامپوننت `Skeleton` با انیمیشن shimmer.
```typescript
const Skeleton = ({ width, height, className }: Props) => (
  <div
    className={`animate-pulse bg-gradient-to-r from-gray-200 to-gray-300 rounded ${className}`}
    style={{ width, height }}
  />
);
```

### ۲. Error Boundaries

**مشکل فعلی**: یک خطای runtime در React باعث white screen می‌شود.

**راه‌حل**:
```typescript
// components/ErrorBoundary.tsx
class ErrorBoundary extends React.Component {
  // نمایش UI مناسب با دکمه «تلاش مجدد»
}
```

### ۳. Pagination & Virtual Scrolling

**مشکل فعلی**: صفحه Trades با ۱۰۰۰+ معامله کند می‌شود.

**راه‌حل**:
- **Backend**: `offset` و `limit` در `GET /api/trades`
- **Frontend**: Pagination یا Infinite Scroll (با Intersection Observer)
- **Virtual Scrolling**: برای جدول معاملات با `react-window` یا `tanstack-virtual`

### ۴. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Command Palette (جستجوی سریع بین صفحات و معاملات) |
| `Ctrl+N` | معامله جدید (دستی) |
| `Ctrl+I` | رفتن به Import Page |
| `Ctrl+Enter` | ثبت فرم (در مودال‌ها) |
| `Escape` | بستن مودال |
| `Ctrl+F` | جستجو در جدول معاملات |

### ۵. Mobile Responsive

در حال حاضر UI برای desktop طراحی شده. با Tailwind می‌توان:

- `hamburger menu` برای Sidebar در mobile
- `stack vertical` کارت‌ها در mobile
- `modal full screen` در mobile

### ۶. Persian Date Input Completion

کامپوننت `PersianDateInput` ساخته شده ولی در بعضی فرم‌ها هنوز استفاده نشده (مثلاً Settings).

### ۷. بهینه‌سازی Primary Key

در حال حاضر PrimaryKeyهای مدل‌ها `Integer` هستند. برای پروژه‌ای که قرار است بزرگ شود، `UUID` یا `BigInteger` امن‌تر است. (اختیاری)
---

## ه) بهبودهای معماری

### ۱. API Versioning

پیشنهاد: اضافه کردن `/api/v1/` prefix به همه endpoints.
```python
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["strategies"])
```

این کار برای تغییرات آینده ضروری است (مثلاً API v2 با breaking changes).

### ۲. Request Validation (Pydantic strict)

در برخی schemaها `strict=True` اضافه شود تا اعتبارسنجی دقیق‌تری داشته باشیم.
```python
class TradeCreate(BaseModel):
    model_config = ConfigDict(strict=True)  # Pydantic v2
```

### ۳. Background Tasks

برای عملیات سنگین مثل Import فایل‌های بزرگ و تحلیل:

**الگوی پیشنهادی**:
```python
from fastapi import BackgroundTasks

@router.post("/analyze/{version_id}")
async def analyze_version_async(version_id: int, background_tasks: BackgroundTasks):
    task_id = str(uuid4())
    background_tasks.add_task(run_analysis_in_background, version_id, task_id)
    return {"task_id": task_id, "status": "processing"}

@router.get("/analyze/status/{task_id}")
def get_analysis_status(task_id: str):
    return {"status": task_status[task_id]}
```

### ۴. Caching

برای Analysis Results که تغییر نمی‌کنند:
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_analysis(version_id: int):
    # ...
```
یا با Redis برای cache بین sessionها.

### ۵. Environment Variables

برخی مقادیر مثل `API_BASE_URL = 'http://localhost:8000'` در `client.ts` هاردکد شده‌اند. باید به `.env` منتقل شوند.

```env
# frontend/.env
VITE_API_BASE_URL=http://localhost:8000
```

### ۶. Indexing Database

بررسی فیلدهایی که queryهای سنگین روی آن‌ها انجام می‌شود:
- `Trade.version_id` (برای تحلیل)
- `Trade.prop_stage_id` (برای PropRuleEngine)
- `Trade.close_time` (برای مرتب‌سازی و فیلتر تاریخ)
- `JournalReview.trade_id` (برای join)

```python
# در مدل Trade
__table_args__ = (
    Index('ix_trades_version_id', 'version_id'),
    Index('ix_trades_prop_stage_id', 'prop_stage_id'),
    Index('ix_trades_close_time', 'close_time'),
---

## جدول اولویت‌بندی کلی

| اولویت | دسته | آیتم | زمان تخمینی | وابستگی |
|--------|------|------|-------------|---------|
| 🔴 P0 | باگ | Import version_id | ۱۵ دقیقه | — |
| 🔴 P0 | باگ | `_summarize` با net_pnl | ۱۰ دقیقه | — |
| 🔴 P0 | باگ | `_calculate_consistency` با net_pnl | ۱۰ دقیقه | — |
| 🔴 P0 | باگ | `_calculate_max_consecutive_losses` با net_pnl | ۵ دقیقه | — |
| 🟡 P1 | باگ | AnalysisRun | ۱-۲ ساعت | Migration جدید |
| 🟡 P1 | باگ | حذف `calculate_stage_progress` | ۵ دقیقه | — |
| 🟡 P1 | بلوپرینت | Dashboard واقعی (حذف هاردکدها) | ۳ ساعت | — |
| 🟡 P1 | جدید | Dark Mode واقعی | ۴ ساعت | متغیرهای CSS |
| 🟡 P1 | جدید | Calendar View | ۵ ساعت | تقویم شمسی |
| 🟡 P1 | کیفیت | Pagination + Virtual Scrolling | ۳ ساعت | — |
| 🟢 P2 | جدید | Risk Management Dashboard | ۶ ساعت | AnalysisService |
| 🟢 P2 | جدید | Multi-Account Prop Dashboard | ۴ ساعت | PropRuleEngine |
| 🟢 P2 | جدید | Export PDF/CSV | ۴ ساعت | کتابخانه PDF |
| 🟢 P2 | معماری | Background Tasks | ۴ ساعت | — |
| 🟢 P3 | جدید | Trade Playback | ۸ ساعت | lightweight-charts |
| 🟢 P3 | جدید | Personal Finance Module | ۱۲ ساعت | Migration جدید |
| 🟢 P3 | جدید | AI Journal Assistant | ۱۰ ساعت | JournalReview data |
| 🟢 P3 | جدید | Symbol Watchlist & Screener | ۶ ساعت | — |
| 🔵 P4 | بلوپرینت | Testing Suite (pytest) | ۴ ساعت | — |
| 🔵 P4 | بلوپرینت | Testing Suite (vitest) | ۲ ساعت | — |
| 🔵 P4 | جدید | Backup/Restore | ۳ ساعت | — |
| 🔵 P4 | جدید | Notifications & Alerts | ۳ ساعت | PropAlert model |
| 🔵 P4 | جدید | Strategy Rule Builder | ۸ ساعت | — |
| 🔵 P4 | کیفیت | Keyboard Shortcuts | ۲ ساعت | — |
| 🔵 P4 | کیفیت | Mobile Responsive | ۴ ساعت | — |
| 🔵 P4 | کیفیت | Skeleton Loaders | ۱ ساعت | — |
| 🔵 P4 | کیفیت | Error Boundaries | ۱ ساعت | — |
| 🔵 P4 | معماری | API Versioning | ۲ ساعت | — |
| 🔵 P4 | معماری | Logging | ۱ ساعت | — |
| 🔵 P4 | معماری | Environment Variables | ۳۰ دقیقه | — |
| 🔵 P4 | معماری | Database Indexing | ۳۰ دقیقه | Migration |

---

## 🔴 جمع‌بندی اقدام فوری (Sprint 1 — ۲ تا ۳ روز)

### روز ۱: رفع باگ‌ها (~۱ ساعت)
1. ✅ رفع `version_id` در `api/imports.py`
2. ✅ رفع `_summarize` با `net_pnl`
3. ✅ رفع `_calculate_consistency` و `_calculate_max_consecutive_losses`
4. ✅ حذف `calculate_stage_progress`
5. ✅ `datetime.utcnow()` → `datetime.now(timezone.utc)`

### روز ۲: AnalysisRun + Dashboard (~۴ ساعت)
6. ✅ مدل `AnalysisRun` + migration
7. ✅ تغییر `analyze_version` به append
8. ✅ API جدید برای history analysis
9. ✅ رفع Dashboard (حذف هاردکدها)
10. ✅ ویجت‌های واقعی با data از API

### روز ۳: کیفیت + معماری (~۴ ساعت)
11. ✅ Pagination برای Trades API
12. ✅ Skeleton Loaders
13. ✅ Error Boundaries
14. ✅ Environment Variables (VITE_API_BASE_URL)
15. ✅ Database Indexing migration

---

*این سند در تاریخ ۱۴۰۴/۰۷/۰۲ تهیه شده و بر اساس کد موجود و مستندات بلوپرینت پروژه MokTradeDesk است.*
)
```

### ۷. Logging & Monitoring

اضافه کردن logging سیستماتیک:
```python
# utils/logger.py
import logging

logger = logging.getLogger("moktrader")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("moktrader.log")
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
```
### ۷. 🟢 Dashboard هاردکدهای مصنوعی دارد

**فایل**: `frontend/src/pages/DashboardPage.tsx`  
**توضیح**: `sparkData`, `ProgressBar value={65}`, اهداف ماهانه/فصلی/سالانه همه هاردکد هستند.

### ۸. 🟢 `datetime.utcnow()` در کل پروژه استفاده شده (deprecated)

جایگزینی با `datetime.now(timezone.utc)` در تمام فایل‌های backend.