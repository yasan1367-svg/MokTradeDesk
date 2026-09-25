📄 MokTradeDesk — Complete Handoff Document
نسخه: 2.0 (کامل و جامع)
تاریخ: 1405/07/01 (2026-09-22)
آخرین کامیت: aecf91e
Repository: https://github.com/yasan1367-svg/MokTradeDesk-deep
Branch: main
________________________________________
📌 فهرست مطالب
1.	چشم‌انداز پروژه
2.	اصول توسعه (غیرقابل تغییر)
3.	معماری کلان
4.	ساختار پوشه‌ها
5.	مدل‌های داده (Database Schema)
6.	Trade Classification Contract
7.	واحدهای اندازه‌گیری
8.	PnL و Commission
9.	Migration (Alembic)
10.	Import Pipeline
11.	Prop Rule Engine
12.	Analysis Service
13.	API Endpoints
14.	Frontend Pages
15.	وضعیت فعلی (Done)
16.	کارهای باقی‌مانده (To-Do) — با جزییات
17.	باگ‌های شناخته‌شده
18.	محیط اجرا
19.	Git Workflow
20.	دستورالعمل برای AI بعدی
21.	چک‌لیست تست
22.	تصمیمات معماری
23.	منابع و مراجع
________________________________________
۱. چشم‌انداز پروژه
MokTradeDesk یک Trading Operating System شخصی، Local-first، و قابل توسعه است.
چرخه‌ی اصلی:
text
Backtest → Analysis → Optimization → Forward Test → Real → Review → Improvement
هدف: سیستم کامل برای ثبت، تحلیل، و مدیریت معاملات + Strategy/Version + Import + Journal + Prop + Personal Trading.
Strategy اصلی: SP2L (با Entry #2)
ابزارها: XAUUSD, US30/DJIUSD, EURUSD, GBPUSD
تایم‌فریم: 5 دقیقه
________________________________________
۲. اصول توسعه (غیرقابل تغییر)
اصل	توضیح
Backend Source of Truth	تمام validation و منطق در Backend
StrategyVersion محور	Classification و Analysis بر اساس StrategyVersion
Trade Classification Contract	BACKTEST/FORWARD/REAL-PERSONAL/REAL-PROP
XOR Classification	personal_account_id XOR prop_stage_id (در REAL)
Trade PnL ≠ Cashflow	بدون Double Counting
Personal Trading ≠ Personal Finance	جدا نگه داشته بشن
Prop Logic متمرکز	فقط در PropRuleEngine
Migration قبل از Schema Change	Backup ← Inspect ← Migration ← Verify
GitHub = Source of Truth	push مجاز (برای sync بین خونه و دفتر)
Strategy-specific Logic	قابل تعریف/پیکربندی، نه hard-code
واحدها: DB = دلار، UI = درصد	تبدیل در Frontend
________________________________________
۳. معماری کلان
3.1 Backend Stack
text
FastAPI + SQLAlchemy + Alembic + SQLite
Python 3.12
uvicorn
3.2 Frontend Stack
text
React 19 + TypeScript + Vite 8 + TailwindCSS 3 + Recharts 3
pnpm
RTL + Vazirmatn + تاریخ شمسی
3.3 Database
•	SQLite: backend/trading_desk.db
•	Alembic version: c4838cd01bbd
3.4 Directory Layout
text
MokTradeDesk-deep/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── strategies.py
│   │   │   ├── prop.py
│   │   │   ├── personal.py
│   │   │   ├── imports.py
│   │   │   ├── analytics.py
│   │   │   ├── trades.py
│   │   │   ├── symbol_mappings.py
│   │   │   └── settings.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── __init__.py
│   │   ├── models/
│   │   │   ├── strategy.py
│   │   │   ├── prop.py
│   │   │   ├── personal.py
│   │   │   └── settings.py
│   │   ├── schemas/
│   │   │   ├── analytics.py
│   │   │   ├── personal.py
│   │   │   ├── prop.py
│   │   │   └── strategy.py
│   │   ├── services/
│   │   │   ├── analysis_service.py
│   │   │   ├── import_service.py
│   │   │   └── prop_rule_engine.py
│   │   ├── utils/
│   │   │   ├── trade_metrics.py
│   │   │   └── trade_validator.py
│   │   └── main.py
│   ├── migrations/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── c4838cd01bbd_initial_schema_with_trade_hash.py
│   ├── storage/screenshots/
│   ├── requirements.txt
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   │   ├── ComparisonBarChart.tsx
│   │   │   │   ├── ComparisonRadarChart.tsx
│   │   │   │   ├── EquityCurveChart.tsx
│   │   │   │   ├── PnLDistributionChart.tsx
│   │   │   │   ├── PropAnalytics.tsx
│   │   │   │   ├── SessionBarChart.tsx
│   │   │   │   ├── WeekdayBarChart.tsx
│   │   │   │   └── WinLossPieChart.tsx
│   │   │   ├── ui/
│   │   │   │   ├── Badge.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── ProgressBar.tsx
│   │   │   │   └── StatCard.tsx
│   │   │   ├── AnalysisTable.tsx
│   │   │   ├── GlassCard.tsx
│   │   │   ├── MetricCard.tsx
│   │   │   ├── PersianDateInput.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── StatCard.tsx (نسخه‌ی دوم!)
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── AnalysisPage.tsx
│   │   │   ├── ComparisonPage.tsx
│   │   │   ├── StrategyPage.tsx
│   │   │   ├── TradesPage.tsx
│   │   │   ├── JournalPage.tsx
│   │   │   ├── PropPage.tsx
│   │   │   ├── PersonalPage.tsx
│   │   │   ├── ImportPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── tsconfig.app.json
└── NOTES.md
________________________________________
۴. مدل‌های داده (Database Schema)
4.1 جداول (۱۸ جدول)
Strategy (۷ جدول):
•	strategies — id, name, description, created_at
•	strategy_versions — id, strategy_id, version_name, rules_note, status, forked_from_version_id, created_at
•	trades — ۲۵ ستون (جدول مرکزی)
•	custom_time_intervals — بازه‌های زمانی سفارشی
•	time_points — نقاط زمانی
•	analysis_results — نتایج تحلیل
•	symbol_mappings — نگاشت نمادها
Prop (۷ جدول):
•	prop_firms — شرکت‌های پراپ
•	prop_firm_default_rules — قوانین پیش‌فرض
•	prop_accounts — اکانت‌های پراپ
•	prop_stages — مراحل (Stage1/Stage2/Funded)
•	prop_withdrawals — برداشت‌ها
•	prop_costs — هزینه‌ها
•	prop_alerts — هشدارها
Personal (۴ جدول):
•	personal_accounts — اکانت‌های شخصی
•	ledger_transactions — دفتر کل
•	journal_reviews — مرور معاملات
•	screenshots — اسکرین‌شات‌ها (entity_type/entity_id)
Settings (۱ جدول):
•	user_settings — تنظیمات کاربر
Alembic (۱ جدول):
•	alembic_version
4.2 جدول trades (مرکزی)
ستون	نوع	nullable	توضیح
id	Integer PK	❌	
version_id	FK strategy_versions	✅	
prop_stage_id	FK prop_stages	✅	
personal_account_id	FK personal_accounts	✅	
symbol	String	❌	e.g., XAUUSD
direction	String	❌	buy/sell
open_time	DateTime	❌	
close_time	DateTime	✅	
open_price	Float	❌	
close_price	Float	✅	
size	Float	❌	
sl	Float	✅	
tp	Float	✅	
pnl	Float	✅	سود خام
r_multiple	Float	✅	
commission	Float	✅	معمولاً منفی
swap	Float	✅	
entry_sequence	Integer	✅	default=1
source	Enum	❌	mt4_import / soft4x_import / manual
test_type	Enum	✅	backtest / forward / real
note	Text	✅	
screenshot_path	String	✅	(قدیمی)
raw_data	JSON	✅	
created_at	DateTime	✅	
trade_hash	String(32)	✅	Duplicate Detection
ایندکس‌ها: id, trade_hash
4.3 Enums
python
class StrategyStatus(str, enum.Enum):
    RESEARCH = "research"
    BACKTEST = "backtest"
    OPTIMIZATION = "optimization"
    FORWARD = "forward"
    APPROVED = "approved"
    LIVE = "live"
    REVIEW = "review"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    REJECTED = "rejected"

class TradeSource(str, enum.Enum):
    MT4_IMPORT = "mt4_import"
    SOFT4X_IMPORT = "soft4x_import"
    MANUAL = "manual"

class TestType(str, enum.Enum):
    BACKTEST = "backtest"
    FORWARD = "forward"
    REAL = "real"

class StageType(str, enum.Enum):
    STAGE_1 = "stage_1"
    STAGE_2 = "stage_2"
    FUNDED_REAL = "funded_real"

class StageStatus(str, enum.Enum):
    ACTIVE = "active"
    PASSED = "passed"
    FAILED = "failed"
    CLOSED = "closed"

class FailureReason(str, enum.Enum):
    MAX_DAILY_DD_EXCEEDED = "max_daily_dd_exceeded"
    MAX_TOTAL_DD_EXCEEDED = "max_total_dd_exceeded"
    PROFIT_TARGET_NOT_MET = "profit_target_not_met"
    MIN_TRADING_DAYS_NOT_MET = "min_trading_days_not_met"
    RULE_VIOLATION = "rule_violation"
    MANUAL = "manual"
    OTHER = "other"

class TransactionType(str, enum.Enum):
    TRADE_PNL = "trade_pnl"
    PROP_PAYOUT = "prop_payout"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    CHALLENGE_FEE = "challenge_fee"
    EXPENSE = "expense"
    MANUAL_ADJUSTMENT = "manual_adjustment"
________________________________________
۵. Trade Classification Contract
text
┌────────────────┬───────────┬────────────────────┬──────────────────┐
│ test_type      │ version   │ personal_account   │ prop_stage       │
├────────────────┼───────────┼────────────────────┼──────────────────┤
│ BACKTEST       │ REQUIRED  │ NULL               │ NULL             │
│ FORWARD        │ REQUIRED  │ NULL               │ NULL             │
│ REAL-PERSONAL  │ REQUIRED  │ REQUIRED           │ NULL             │
│ REAL-PROP      │ REQUIRED  │ NULL               │ REQUIRED         │
└────────────────┴───────────┴────────────────────┴──────────────────┘
قانون: personal_account_id XOR prop_stage_id (در REAL)
Validation: backend/app/utils/trade_validator.py ← TradeValidator.validate_classification()
متدهای کمکی:
•	validate_numbers(size, open_price, close_price, sl, tp, ...)
•	validate_dates(open_time, close_time)
فراخوانی:
•	api/trades.py ← create_manual_trade, update_trade
•	api/imports.py ← import_soft4x, import_mt4
________________________________________
۶. واحدهای اندازه‌گیری
فیلد	واحد	ذخیره در DB	نمایش در UI
initial_balance	دلار	دلار	دلار
profit_target	دلار	دلار	دلار + درصد
max_daily_dd	دلار	دلار	دلار + درصد
max_total_dd	دلار	دلار	دلار + درصد
current_profit	دلار	دلار	دلار
equity	دلار	دلار	دلار
withdrawable_profit	دلار	دلار	دلار
profit_share_percentage	درصد	درصد	درصد
profit_progress_percent	درصد	—	فقط نمایش
daily_dd_progress_percent	درصد	—	فقط نمایش
total_dd_progress_percent	درصد	—	فقط نمایش
قانون: کاربر در UI درصد وارد می‌کند، Frontend به دلار تبدیل می‌کند، Backend دلار ذخیره می‌کند.
فرمول‌ها:
typescript
profit_target_amount = (profit_target_percent / 100) * initial_balance
max_daily_dd_amount = (max_daily_dd_percent / 100) * initial_balance
max_total_dd_amount = (max_total_dd_percent / 100) * initial_balance
________________________________________
۷. PnL و Commission
فرمول PnL خالص:
python
net_pnl = pnl + commission + swap
توجه: commission معمولاً منفی ذخیره می‌شود (مثل -0.09). جمع کردن آن یعنی کم شدن از سود.
مثال:
text
pnl = -12.82, commission = -0.09  →  net_pnl = -12.91
همه‌ی محاسبات Analysis بر اساس net_pnl:
•	gross_profit, gross_loss
•	net_pnl
•	avg_win, avg_loss
•	largest_win, largest_loss
•	max_dd (در _calculate_max_drawdown)
•	expectancy
•	profit_factor
فایل: backend/app/services/analysis_service.py
•	_calculate_basic_metrics — ✅ تغییر کرده
•	_calculate_max_drawdown — ✅ تغییر کرده
•	_summarize — ❌ هنوز تغییر نکرده! (کار باقی‌مانده)
Helper پیشنهادی:
python
def _net_pnl(t: Trade) -> float:
    return (t.pnl or 0) + (t.commission or 0) + (t.swap or 0)
________________________________________
۸. Migration (Alembic)
8.1 وضعیت فعلی
فایل: backend/migrations/versions/c4838cd01bbd_initial_schema_with_trade_hash.py
شامل:
•	۱۸ جدول
•	همه‌ی ایندکس‌ها
•	trade_hash + ایندکسش
نکته: Base.metadata.create_all در main.py غیرفعال شده — Migration تنها راه ساخت جدول‌ها است.
8.2 دستورات
powershell
cd backend
.\venv\Scripts\Activate.ps1

# ساخت migration جدید
alembic revision --autogenerate -m "description"

# اعمال
alembic upgrade head

# برگشت
alembic downgrade -1

# تاریخچه
alembic history

# migration فعلی
alembic current
8.3 نکات
•	قبل از هر migration ← Backup از trading_desk.db
•	DB فعلی: SQLite، بدون داده‌ی مهم (تست)
•	alembic.ini: sqlalchemy.url = sqlite:///./trading_desk.db
•	env.py: همه‌ی مدل‌ها import شده
8.4 مشکل Migration در دو سیستم
اگه توی دو سیستم کار می‌کنی (خونه + دفتر):
بعد از هر git pull، اگه migration جدید اومده:
powershell
cd backend
alembic upgrade head
یا اگه DB قدیمیه:
powershell
Copy-Item "trading_desk.db" "trading_desk.db.bak_$(Get-Date -Format 'yyyyMMdd_HHmm')"
Remove-Item "trading_desk.db"
alembic upgrade head
________________________________________
۹. Import Pipeline
9.1 Soft4X Importer (Excel)
فایل: backend/app/services/import_service.py ← Soft4XImporter
Pipeline:
text
Upload → Parse (openpyxl) → Normalize → Validate → Duplicate Check → Save
Sheet: Trades یا Active Sheet
ستون‌ها: Open Time, Close Time, Type, Open Price, Close Price, Size, SL, TP, P/L, Commission
Source: TradeSource.SOFT4X_IMPORT
9.2 MT4 Importer (HTML)
فایل: backend/app/services/import_service.py ← MT4Importer
Pipeline:
text
Upload → Parse (BeautifulSoup) → Normalize → Validate → Duplicate Check → Save
بخش: فقط Positions
ستون‌ها: ۱۳ ستون
1.	Open Time
2.	Position
3.	Symbol
4.	Type
5.	Volume
6.	Open Price
7.	S/L
8.	T/P
9.	Close Time
10.	Close Price
11.	Commission
12.	Swap
13.	Profit
Source: TradeSource.MT4_IMPORT
9.3 Duplicate Detection
الگوریتم:
python
key = f"{source}|{symbol}|{direction}|{open_time}|{close_time}|{open_price}|{close_price}|{size}"
trade_hash = md5(key).hexdigest()
قبل از ذخیره:
python
existing = db.query(Trade).filter(Trade.trade_hash == hash_key).first()
if existing:
    duplicates.append(trade_data)
    continue
خروجی save_trades:
python
{
    "saved": [...],
    "duplicates": [...],
    "total": int,
}
پاسخ API:
json
{
  "message": "X معامله ذخیره شد (استراتژی) — Y معامله تکراری نادیده گرفته شد",
  "total_trades": int,
  "saved_trades": int,
  "duplicates_count": int,
  "preview": [...]
}
9.4 ImportBatch (❌ باقی‌مانده)
طبق بلوپرینت:
•	جدول import_batches با فیلدهای: source, account, test_type, strategy_version, timestamp, stats
•	Pipeline: Preview ← User Confirmation ← DB Transaction
وضعیت: ❌ پیاده نشده
9.5 Preview + User Confirmation (❌ باقی‌مانده)
طبق بلوپرینت:
Pipeline: Upload ← Parse ← Normalize ← Validate ← Duplicate ← Preview ← User Confirmation ← DB Transaction
وضعیت: ❌ پیاده نشده
________________________________________
۱۰. Prop Rule Engine
فایل: backend/app/services/prop_rule_engine.py
کلاس: PropRuleEngine
متدها:
python
@staticmethod
def evaluate_stage(db: Session, stage_id: int) -> Dict[str, Any]:
    """ارزیابی کامل یک مرحله پراپ"""

@staticmethod
def validate_withdrawal(db: Session, stage_id: int, amount: float) -> Tuple[bool, str]:
    """بررسی مجاز بودن برداشت"""

@staticmethod
def _group_daily_pnl(trades: List[Trade]) -> Dict[str, float]:
    """گروه‌بندی PnL بر اساس روز"""

@staticmethod
def _calculate_max_drawdown(trades: List[Trade], initial: float) -> float:
    """محاسبه‌ی حداکثر افت سرمایه"""
خروجی evaluate_stage:
python
{
    # شناسه
    "stage_id", "stage_type", "status",
    
    # موجودی و سود (دلار)
    "initial_balance", "equity", "current_profit", "current_profit_percent",
    
    # هدف سود (دلار)
    "profit_target", "profit_progress_percent",
    
    # Daily DD (دلار)
    "max_daily_loss", "max_daily_dd_limit", "daily_dd_progress_percent", "daily_dd_violated",
    
    # Total DD (دلار)
    "max_total_dd", "max_total_dd_limit", "total_dd_progress_percent", "total_dd_violated",
    
    # روزهای معاملاتی
    "trading_days", "min_trading_days", "days_met",
    
    # وضعیت
    "target_reached", "ready_to_pass", "suggested_status", "violations",
    
    # رییل
    "is_funded", "total_withdrawn", "profit_share_percentage", "withdrawable_profit",
    
    # آمار
    "total_trades",
}
وضعیت‌های پیشنهادی:
•	ready_to_pass — آماده‌ی پاس
•	in_progress — در حال پیشرفت
•	failed_daily_dd — DD روزانه نقض شده
•	failed_total_dd — DD کلی نقض شده
مصرف‌کننده: api/prop.py ← check_pass_ready, pass_stage, withdraw
________________________________________
۱۱. Analysis Service
فایل: backend/app/services/analysis_service.py
کلاس: AnalysisService
متدهای اصلی:
python
def analyze_version(self, version_id: int) -> AnalysisResult
def compare_versions(self, version_ids: List[int], min_trades: int = 0) -> Dict
def calculate_stage_progress(self, stage_id: int) -> Dict  # ← باید حذف شود (تکراری با PropRuleEngine)
def _calculate_basic_metrics(self, trades: List[Trade]) -> Dict[str, Any]
def _calculate_max_drawdown(self, trades: List[Trade]) -> float
def _summarize(self, trades: List[Trade]) -> Dict[str, Any]  # ← باید اصلاح شود
def _analyze_by_session(self, trades: List[Trade]) -> Dict
def _analyze_by_weekday(self, trades: List[Trade]) -> Dict
def _analyze_by_hour(self, trades: List[Trade]) -> Dict
def _analyze_by_custom_intervals(self, trades: List[Trade]) -> Dict
def _calculate_max_consecutive_losses(self, trades: List[Trade]) -> int
def _calculate_consistency(self, trades: List[Trade]) -> Dict
def _calculate_score(self, analysis: AnalysisResult) -> float
def _profit_factor(self, gross_profit: float, gross_loss: float) -> float
متریک‌های محاسبه‌شده:
text
- total_trades, win_rate, profit_factor
- net_pnl, net_r, max_dd
- expectancy, expectancy_r
- avg_win, avg_loss, largest_win, largest_loss
- max_consecutive_losses
- consistency_analysis (pnl_std_dev, top_trades_contribution_percent, avg_win_avg_loss_ratio)
- session_analysis, weekday_analysis, hour_analysis, custom_time_analysis
Health Score:
python
win_rate_score = min(win_rate, 100)
profit_factor_score = min(profit_factor * 20, 100)
net_pnl_score = min(max(net_pnl, 0) / 10, 100)
dd_penalty = min(max_dd / 10, 50)

score = (win_rate_score * 0.35) + (profit_factor_score * 0.35) + (net_pnl_score * 0.30) - (dd_penalty * 0.20)
score = max(min(score, 100), 0)
⚠️ نکته مهم: _calculate_basic_metrics و _calculate_max_drawdown با net_pnl (شامل commission) کار می‌کنند. ولی _summarize هنوز تغییر نکرده.
________________________________________
۱۲. API Endpoints (کامل)
Strategies
text
GET    /api/strategies/
POST   /api/strategies/
GET    /api/strategies/{id}
PATCH  /api/strategies/{id}
DELETE /api/strategies/{id}
GET    /api/strategies/versions/all
GET    /api/strategies/{id}/versions
POST   /api/strategies/{id}/versions
PATCH  /api/strategies/versions/{id}
DELETE /api/strategies/versions/{id}
GET    /api/strategies/versions/{id}/trades
Trades
text
GET    /api/trades/                    # فیلترها: version_id, strategy_id, personal_account_id, prop_stage_id, symbol, test_type, source, date_from, date_to, search, limit, offset
GET    /api/trades/{id}
PATCH  /api/trades/{id}
DELETE /api/trades/{id}
POST   /api/trades/manual
POST   /api/trades/{id}/screenshots
GET    /api/trades/{id}/screenshots
DELETE /api/trades/screenshots/{id}
Prop
text
GET    /api/prop/firms
POST   /api/prop/firms
GET    /api/prop/accounts
POST   /api/prop/accounts
GET    /api/prop/accounts/{id}
GET    /api/prop/stages/all
GET    /api/prop/stages/{id}/check-pass
POST   /api/prop/stages/{id}/pass
POST   /api/prop/stages/{id}/fail
PATCH  /api/prop/stages/{id}/rules
GET    /api/prop/stages/{id}/trades
POST   /api/prop/stages/{id}/withdraw
POST   /api/prop/costs
GET    /api/prop/accounts/{id}/costs
GET    /api/prop/analytics
Personal
text
GET    /api/personal/accounts
POST   /api/personal/accounts
GET    /api/personal/accounts/{id}
PATCH  /api/personal/accounts/{id}
DELETE /api/personal/accounts/{id}
GET    /api/personal/ledger
POST   /api/personal/ledger
DELETE /api/personal/ledger/{id}
GET    /api/personal/cashflow
POST   /api/personal/journal/review
GET    /api/personal/journal/reviews
DELETE /api/personal/journal/reviews/{id}
GET    /api/personal/prop-accounts-list
Imports
text
POST   /api/imports/soft4x
POST   /api/imports/mt4
Analytics
text
POST   /api/analytics/analyze/{version_id}
GET    /api/analytics/{version_id}
POST   /api/analytics/compare
GET    /api/analytics/intervals/
POST   /api/analytics/intervals/
DELETE /api/analytics/intervals/{id}
POST   /api/analytics/intervals/seed-gold
POST   /api/analytics/intervals/seed-dji
Symbol Mappings
text
GET    /api/symbol-mappings/
POST   /api/symbol-mappings/
PATCH  /api/symbol-mappings/{id}
DELETE /api/symbol-mappings/{id}
POST   /api/symbol-mappings/seed-defaults
Settings
text
GET    /api/settings/
PATCH  /api/settings/
________________________________________
۱۳. Frontend Pages (وضعیت)
صفحه	فایل	وضعیت
Dashboard	DashboardPage.tsx	✅ Prop-focused (با $)
Analysis	AnalysisPage.tsx	✅ کار می‌کند (با net_pnl)
Comparison	ComparisonPage.tsx	✅
Strategy	StrategyPage.tsx	✅
Trades	TradesPage.tsx	✅
Journal	JournalPage.tsx	✅
Prop	PropPage.tsx	✅ درصد ↔ دلار + modalError
Personal	PersonalPage.tsx	✅
Import	ImportPage.tsx	✅ Duplicate Detection + version_id
Settings	SettingsPage.tsx	✅
Navigation: App.tsx ← state-based (نه router)
Sidebar: components/Sidebar.tsx
فونت: Vazirmatn (CDN)
تاریخ: شمسی (PersianDateInput.tsx)
________________________________________
۱۴. وضعیت فعلی (Done)
✅ PHASE 0: Architecture Freeze
•	Blueprint + Master Brief
✅ PHASE 1: Migration Foundation
•	Alembic راه‌اندازی
•	c4838cd01bbd_initial_schema_with_trade_hash.py
•	۱۸ جدول + ایندکس‌ها
•	create_all غیرفعال
✅ PHASE 2: Trade Contract
•	TradeValidator.validate_classification
•	TradeValidator.validate_numbers
•	TradeValidator.validate_dates
✅ PHASE 3: Trade API
•	GET /api/trades/ — با فیلترهای کامل
•	GET /api/trades/{id}
•	PATCH /api/trades/{id} — Edit کنترل‌شده
•	DELETE /api/trades/{id} — فقط MANUAL
•	POST /api/trades/manual
•	POST /api/trades/{id}/screenshots
•	N+1 حل شده (joinedload)
✅ PHASE 4: Trade Frontend
•	TradesPage.tsx کامل
✅ PHASE 5: Import Pipeline (نصفه)
•	Soft4X Importer
•	MT4 Importer
•	Duplicate Detection (trade_hash)
•	test_type خودکار real برای پراپ/شخصی
•	version_id اجباری برای پراپ
•	❌ Preview + User Confirmation پیاده نشده
•	❌ ImportBatch پیاده نشده
✅ PHASE 6: Prop Rule Engine
•	PropRuleEngine.evaluate_stage
•	PropRuleEngine.validate_withdrawal
•	api/prop.py:
o	check_pass_ready از Engine
o	pass_stage با validation
o	withdraw تکراری رفع شد
o	withdraw بدون Double Counting
o	Create Account ← درصد
o	Edit Stage ← درصد
o	Pass Modal ← درصد
o	modalError توی مودال
✅ PHASE 7: Analysis (تقریباً)
•	AnalysisService کامل
•	net_pnl شامل commission + swap
•	_calculate_max_drawdown با net_pnl
•	❌ _summarize هنوز net_pnl را درست حساب نمی‌کند
•	❌ calculate_stage_progress حذف نشده
•	❌ AnalysisRun (تاریخچه) پیاده نشده
✅ PHASE 8: Journal / Screenshot
•	Journal Page
•	Screenshot upload
❌ PHASE 9: Testing / Regression
❌ PHASE 10: Personal Finance
________________________________________
۱۵. کارهای باقی‌مانده (To-Do) — با جزییات
🔴 اولویت بالا
15.1.1 _summarize — net_pnl
مشکل: _summarize (session/weekday/hour) هنوز sum(t.pnl) استفاده می‌کند.
راه‌حل:
python
def _summarize(self, trades: List[Trade]) -> Dict[str, Any]:
    def _net_pnl(t: Trade) -> float:
        return (t.pnl or 0) + (t.commission or 0) + (t.swap or 0)

    total = len(trades)
    wins = [t for t in trades if _net_pnl(t) > 0]
    losses = [t for t in trades if _net_pnl(t) < 0]

    gross_profit = sum(_net_pnl(t) for t in wins) if wins else 0
    gross_loss = abs(sum(_net_pnl(t) for t in losses)) if losses else 0

    net_pnl = sum(_net_pnl(t) for t in trades)
    win_rate = (len(wins) / total * 100) if total > 0 else 0
    profit_factor = self._profit_factor(gross_profit, gross_loss)

    return {
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 2),
        "net_pnl": round(net_pnl, 2),
        "profit_factor": round(profit_factor, 2),
    }
فایل: backend/app/services/analysis_service.py ← _summarize
15.1.2 calculate_stage_progress حذف
مشکل: تکراری با PropRuleEngine.evaluate_stage.
راه‌حل: متد کامل حذف شود.
فایل: backend/app/services/analysis_service.py ← calculate_stage_progress
15.1.3 AnalysisRun (تاریخچه تحلیل)
طبق بلوپرینت:
AnalysisRun = هر اجرای تحلیل
AnalysisResult/Current Result = خروجی فعلی یا Snapshot
تا تاریخچه تحلیل‌ها از بین نرود.
راه‌حل:
•	جدول analysis_runs با فیلدهای: version_id, created_at, metrics_snapshot, notes
•	analyze_version ← AnalysisRun جدید بسازد (به جای overwrite)
فایل: backend/app/models/strategy.py + backend/app/services/analysis_service.py
🟡 اولویت متوسط
15.2.1 withdraw double-counting در get_prop_analytics
مشکل: get_prop_analytics از s.current_profit استفاده می‌کند که با withdraw کم شده.
راه‌حل: محاسبه از روی trades.
فایل: backend/app/api/prop.py ← get_prop_analytics
15.2.2 violations توی PropRuleEngine
وضعیت: ✅ حل شده (فقط نقض واقعی)
15.2.3 target_personal_account_id در Withdrawal
طبق بلوپرینت:
مقصد آینده Withdrawal باید FinancialAccount باشد، نه Personal Trading Account.
راه‌حل: در Phase 10 (Personal Finance) حل شود. فعلاً temporary.
🟢 اولویت پایین
15.3.1 DashboardPage هاردکدها
مشکل: جدول «آخرین معاملات» و «پیشرفت اهداف» هاردکد هستند.
راه‌حل: از API بخواند (GET /api/trades/?limit=10).
فایل: frontend/src/pages/DashboardPage.tsx
15.3.2 AnalysisPage — بهبود UI
پیشنهاد:
•	Drawdown Chart (underwater)
•	Metric Cards حرفه‌ای‌تر
•	Rolling Win Rate
•	Monthly Breakdown
فایل: frontend/src/pages/AnalysisPage.tsx
15.3.3 Import — Preview + ImportBatch
طبق بلوپرینت:
Pipeline: Upload ← Parse ← Normalize ← Validate ← Duplicate ← Preview ← User Confirmation ← DB Transaction
فایل: backend/app/api/imports.py + backend/app/models/strategy.py
15.3.4 Screenshot — Standardization
طبق بلوپرینت:
Screenshot باید رابطه استاندارد و منبع اصلی مشخصی داشته باشد.
مشکل: Trade.screenshot_path (تک) + جدول screenshots (چند) — دوگانگی.
راه‌حل: Trade.screenshot_path حذف، فقط screenshots بماند.
فایل: backend/app/models/strategy.py + backend/app/api/trades.py
15.3.5 Instrument Entity
طبق بلوپرینت:
Instrument Entity مستقل: canonical_symbol, display_name, asset_class, tick_size, pip_size, contract_size, aliases.
وضعیت: پیاده نشده. SymbolMapping فعلی جایگزین ساده است.
15.3.6 Decimal برای Money
طبق بلوپرینت:
برای Money در آینده Decimal
وضعیت: الان Float استفاده می‌شود.
15.3.7 UTC-aware datetime
طبق بلوپرینت:
UTC/Timezone-aware datetime
وضعیت: datetime.utcnow() استفاده می‌شود (naive).
15.3.8 Personal Finance (PHASE 10)
طبق بلوپرینت:
•	FinancialAccount — Bank/Card/Cash/Trust Wallet/Exchange Wallet
•	FinancialTransaction — Income/Expense/Transfer/Conversion/Adjustment
•	Transfer بین حساب‌های خود شخص درآمد یا هزینه نیست
•	تبدیل ارز درآمد جدید نیست
•	Payout واقعی Prop می‌تواند در Personal Finance به‌عنوان درآمد معاملاتی ثبت شود
وضعیت: ❌ پیاده نشده
________________________________________
۱۶. باگ‌های شناخته‌شده
🐛 باگ ۱: DashboardPage هاردکد
فایل: frontend/src/pages/DashboardPage.tsx
توضیح: جدول آخرین معاملات و پیشرفت اهداف هاردکد هستند.
راه‌حل: از API بخواند.
🐛 باگ ۲: _summarize net_pnl
فایل: backend/app/services/analysis_service.py
توضیح: _summarize هنوز sum(t.pnl) استفاده می‌کند.
راه‌حل: _net_pnl(t) استفاده کند.
🐛 باگ ۳: calculate_stage_progress تکراری
فایل: backend/app/services/analysis_service.py
توضیح: با PropRuleEngine.evaluate_stage تکراری است.
راه‌حل: حذف شود.
🐛 باگ ۴: get_prop_analytics double-counting
فایل: backend/app/api/prop.py
توضیح: از s.current_profit استفاده می‌کند که با withdraw کم شده.
راه‌حل: محاسبه از روی trades.
🐛 باگ ۵: Import Preview ندارد
فایل: backend/app/api/imports.py
توضیح: Pipeline کامل نیست (Preview + User Confirmation).
راه‌حل: Preview endpoint + Frontend confirmation.
🐛 باگ ۶: Screenshot دوگانگی
فایل: backend/app/models/strategy.py
توضیح: Trade.screenshot_path + جدول screenshots — دوگانگی.
راه‌حل: screenshot_path حذف.
🐛 باگ ۷: StatCard دوگانه
فایل‌ها:
•	frontend/src/components/StatCard.tsx (props: label, value, sub, color)
•	frontend/src/components/ui/StatCard.tsx (props: icon, label, value, change, changeType, color, sparkData)
توضیح: دو نسخه با props متفاوت.
راه‌حل: یکی حذف یا rename شود.
🐛 باگ ۸: HANDOFF.md ساخته نشده
توضیح: هنوز سند نهایی نوشته نشده.
راه‌حل: این سند رو در HANDOFF.md ذخیره کن.
________________________________________
۱۷. محیط اجرا
17.1 Backend
powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
URL: http://localhost:8000
Docs: http://localhost:8000/docs
17.2 Frontend
powershell
cd frontend
pnpm install
pnpm dev
URL: http://localhost:5173
17.3 Database
•	SQLite: backend/trading_desk.db
•	Backup: Copy-Item "trading_desk.db" "trading_desk.db.bak_$(Get-Date -Format 'yyyyMMdd_HHmm')"
17.4 Migration بعد از git pull
powershell
cd backend
.\venv\Scripts\Activate.ps1
alembic upgrade head
________________________________________
۱۸. Git Workflow
Repository: https://github.com/yasan1367-svg/MokTradeDesk-deep
Branch: main
دستورات:
powershell
git status
git add .
git commit -m "PHASE X: description"
git push origin main
git pull origin main
آخرین کامیت‌ها (۱۰ تای آخر):
text
aecf91e PHASE 6: pass_stage validation + withdraw fix + modalError display
e0de080 Add files via upload
b662a5f PHASE 5+7: Duplicate Detection, Migration foundation, net_pnl with commission, Dashboard dollars
8f0c45a PHASE 5: Fix Import UX - auto-set test_type=real, add version_id to prop UI
fcbc948 PHASE 6: Prop Create Account + Edit Stage use percentages (dollars stored)
f36920d Update NOTES.md with full progress
ead47d0 Update NOTES.md with today's progress
5867112 PHASE 6: Prop percentages in all forms, dollars displayed everywhere
f9da0fe PHASE 6: Fix PropPage units - show dollars instead of wrong percentages
7e2547b PHASE 6: Fix prop units, complete PropRuleEngine
________________________________________
۱۹. دستورالعمل برای AI/توسعه‌دهنده بعدی
19.1 اصول کلیدی
1.	Backend = Source of Truth — تمام validation و منطق در Backend
2.	StrategyVersion محور — Classification و Analysis بر اساس StrategyVersion
3.	Trade Classification Contract — personal_account_id XOR prop_stage_id (در REAL)
4.	Trade PnL ≠ Cashflow — بدون Double Counting
5.	Prop Logic متمرکز — فقط در PropRuleEngine
6.	Migration قبل از Schema Change — Backup ← Inspect ← Migration ← Verify
7.	واحدها: DB = دلار، UI = درصد (تبدیل در Frontend)
8.	net_pnl = pnl + commission + swap — همه‌ی محاسبات Analysis
9.	Persistence: SQLite (trading_desk.db)
10.	GitHub = Source of Truth
19.2 قبل از هر تغییر
•	□ 
Backup از trading_desk.db
•	□ 
git status (ببین چی تغییر کرده)
•	□ 
git pull origin main
•	□ 
alembic upgrade head (اگه migration جدید هست)
•	□ 
بررسی تأثیر تغییر
19.3 بعد از هر تغییر
•	□ 
تست
•	□ 
git add .
•	□ 
git commit -m "PHASE X: description"
•	□ 
git push origin main
•	□ 
آپدیت NOTES.md
19.4 اولویت کارهای باقی‌مانده
1.	🔴 _summarize net_pnl
2.	🔴 calculate_stage_progress حذف
3.	🟡 get_prop_analytics double-counting
4.	🟡 AnalysisRun — تاریخچه تحلیل
5.	🟢 DashboardPage هاردکدها
6.	🟢 AnalysisPage بهبود UI (Drawdown Chart)
7.	🟢 Import — Preview + ImportBatch
8.	🟢 Screenshot — Standardization
9.	🟢 Instrument Entity
10.	🟢 Decimal برای Money
11.	🟢 UTC-aware datetime
12.	🟢 PHASE 9 — Testing / Regression
13.	🟢 PHASE 10 — Personal Finance
19.5 نکات مهم
•	commission معمولاً منفی ذخیره می‌شود (-0.09)
•	net_pnl = pnl + commission + swap
•	قبل از Migration، Backup
•	بعد از git pull، alembic upgrade head
•	در دو سیستم (خونه + دفتر)، DB جداگانه است
________________________________________
۲۰. چک‌لیست تست
20.1 Trade
•	□ 
POST /api/trades/manual — با test_type=backtest + version_id
•	□ 
POST /api/trades/manual — با test_type=real + version_id + personal_account_id
•	□ 
POST /api/trades/manual — با test_type=real + version_id + prop_stage_id
•	□ 
POST /api/trades/manual — با test_type=real + version_id (بدون context) ← باید خطا بده
•	□ 
GET /api/trades/?personal_account_id=1
•	□ 
GET /api/trades/?strategy_id=1
•	□ 
GET /api/trades/?date_from=2026-01-01&date_to=2026-12-31
•	□ 
PATCH /api/trades/{id} — تغییر Classification
20.2 Import
•	□ 
Import Soft4X (Excel) — بار اول
•	□ 
Import Soft4X — بار دوم (Duplicate Detection)
•	□ 
Import MT4 (HTML) — بار اول
•	□ 
Import MT4 — بار دوم (Duplicate Detection)
•	□ 
Import برای پراپ — version_id + prop_stage_id اجباری
•	□ 
Import برای شخصی — version_id + personal_account_id اجباری
20.3 Prop
•	□ 
Create Account — درصد
•	□ 
Edit Stage — درصد
•	□ 
Pass Modal — درصد
•	□ 
check-pass — نمایش دلار
•	□ 
pass_stage — validation (اگه DD نقض شده ← خطا)
•	□ 
withdraw — validation (اگه amount > withdrawable ← خطا)
•	□ 
withdraw — بدون Double Counting
•	□ 
modalError — توی مودال
20.4 Analysis
•	□ 
analyze_version — net_pnl با commission
•	□ 
compare_versions — مقایسه
•	□ 
session_analysis — با net_pnl
20.5 Dashboard
•	□ 
Prop فعال
•	□ 
اعداد با $
________________________________________
۲۱. تصمیمات معماری
21.1 GitHub = Source of Truth
تصمیم: push مجاز شد (خلاف بلوپرینت اولیه) برای sync بین خونه و دفتر.
تاریخ: 1405/07/01
21.2 trade_hash برای Duplicate Detection
تصمیم: MD5 از source|symbol|direction|open_time|close_time|open_price|close_price|size.
دلیل: جلوگیری از Import تکراری.
تاریخ: 1405/07/01
21.3 واحدها: DB = دلار، UI = درصد
تصمیم: Backend دلار ذخیره می‌کند، Frontend درصد می‌گیرد.
دلیل: کاربر راحت‌تر درصد وارد می‌کند (پراپ‌ها درصد می‌دهند).
تاریخ: 1405/06/31
21.4 net_pnl = pnl + commission + swap
تصمیم: همه‌ی محاسبات Analysis بر اساس net_pnl.
دلیل: مطابقت با SGB (پراپ).
تاریخ: 1405/07/01
21.5 PropRuleEngine متمرکز
تصمیم: تمام منطق Prop در PropRuleEngine.
دلیل: جلوگیری از پراکندگی.
تاریخ: 1405/06/30
21.6 target_personal_account_id در Withdrawal
تصمیم: فعلاً personal_account_id (temporary).
دلیل: FinancialAccount در Phase 10 پیاده می‌شود.
تاریخ: 1405/06/30
________________________________________
۲۲. منابع و مراجع
22.1 فایل‌های کلیدی
•	Blueprint: MokTradeDesk_Final_Project_Blueprint.docx
•	Master Brief: MokTradeDesk_Master_Project_Brief.docx
•	HANDOFF: HANDOFF.md (این سند)
•	NOTES: NOTES.md
22.2 لینک‌ها
•	GitHub: https://github.com/yasan1367-svg/MokTradeDesk-deep
•	Backend Docs: http://localhost:8000/docs
•	Frontend: http://localhost:5173
22.3 ابزارها
•	Backend: FastAPI + SQLAlchemy + Alembic + SQLite
•	Frontend: React 19 + TypeScript + Vite + TailwindCSS + Recharts
•	Package Manager: pnpm (frontend), pip (backend)
•	Python: 3.12
•	Node: (پیشنهادی 20+)
________________________________________
۲۳. سلب مسئولیت / نکات پایانی
1.	این سند، مرجع اصلی برای توسعه‌ی بعدی است.
2.	هر تغییر مهم باید در این سند (یا NOTES.md) ثبت شود.
3.	قبل از هر Migration Backup بگیرید.
4.	Backend = Source of Truth — هیچ validation توی Frontend نباید کافی باشه.
5.	StrategyVersion محور — همه‌چیز بر اساس نسخه‌ی استراتژی.
6.	Trade PnL ≠ Cashflow — بدون Double Counting.
7.	GitHub = Source of Truth — تغییرات فقط Local + push.
8.	net_pnl = pnl + commission + swap — یادت نره.
9.	واحدها: DB = دلار، UI = درصد.
10.	commission معمولاً منفی — جمع کردنش یعنی کم شدن.
________________________________________
پایان سند
