📄 MokTradeDesk — Project Status & Handoff Document
نسخه: 1.0
تاریخ آخرین به‌روزرسانی: 1405/07/01 (2026-09-22)
آخرین کامیت: b662a5f
Repository: https://github.com/yasan1367-svg/MokTradeDesk-deep
________________________________________
۱. چشم‌انداز پروژه
MokTradeDesk یک Trading Operating System شخصی، Local-first، و قابل توسعه است.
چرخه‌ی اصلی:
text
Backtest → Analysis → Optimization → Forward Test → Real → Review → Improvement
هدف: سیستم کامل برای ثبت، تحلیل، و مدیریت معاملات + Strategy/Version + Import + Journal + Prop + Personal Trading.
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
________________________________________
۳. معماری کلان
Backend Stack
text
FastAPI + SQLAlchemy + Alembic + SQLite
Python 3.12
Frontend Stack
text
React 19 + TypeScript + Vite + TailwindCSS + Recharts
pnpm
RTL + Vazirmatn + تاریخ شمسی
ساختار پروژه
text
MokTradeDesk-deep/
├── backend/
│   ├── app/
│   │   ├── api/           # Endpoints
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
│   │   │   └── database.py
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
│   │   │   └── prop_rule_engine.py   ← جدید
│   │   ├── utils/
│   │   │   ├── trade_metrics.py
│   │   │   └── trade_validator.py
│   │   └── main.py
│   ├── migrations/
│   │   ├── env.py
│   │   └── versions/
│   │       └── c4838cd01bbd_initial_schema_with_trade_hash.py
│   ├── storage/screenshots/
│   ├── requirements.txt
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── api/client.ts
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
│   │   │   └── StatCard.tsx
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
│   └── vite.config.ts
└── NOTES.md
________________________________________
۴. مدل‌های داده (Database Schema)
4.1 جداول (۱۸ جدول)
Strategy:
•	strategies — id, name, description, created_at
•	strategy_versions — id, strategy_id, version_name, rules_note, status, forked_from_version_id, created_at
•	trades — ۲۵ ستون (جدول مرکزی)
•	custom_time_intervals — بازه‌های زمانی سفارشی
•	time_points — نقاط زمانی
•	analysis_results — نتایج تحلیل
•	symbol_mappings — نگاشت نمادها
Prop:
•	prop_firms — شرکت‌های پراپ
•	prop_firm_default_rules — قوانین پیش‌فرض
•	prop_accounts — اکانت‌های پراپ
•	prop_stages — مراحل (Stage1/Stage2/Funded)
•	prop_withdrawals — برداشت‌ها
•	prop_costs — هزینه‌ها
•	prop_alerts — هشدارها
Personal:
•	personal_accounts — اکانت‌های شخصی
•	ledger_transactions — دفتر کل
•	journal_reviews — مرور معاملات
•	screenshots — اسکرین‌شات‌ها (entity_type/entity_id)
Settings:
•	user_settings — تنظیمات کاربر
Alembic:
•	alembic_version — نسخه‌ی migration
4.2 جدول trades (مرکزی)
ستون	نوع	توضیح
id	Integer PK	
version_id	FK strategies_versions	nullable
prop_stage_id	FK prop_stages	nullable
personal_account_id	FK personal_accounts	nullable
symbol	String	e.g., XAUUSD
direction	String	buy/sell
open_time	DateTime	
close_time	DateTime	nullable
open_price	Float	
close_price	Float	nullable
size	Float	
sl	Float	nullable
tp	Float	nullable
pnl	Float	سود خام
r_multiple	Float	nullable
commission	Float	معمولاً منفی
swap	Float	
entry_sequence	Integer	default=1
source	Enum	mt4_import / soft4x_import / manual
test_type	Enum	backtest / forward / real
note	Text	nullable
screenshot_path	String	nullable (قدیمی)
raw_data	JSON	nullable
created_at	DateTime	
trade_hash	String(32)	جدید — برای Duplicate Detection
ایندکس‌ها: id, trade_hash
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
فراخوانی:
•	api/trades.py ← create_manual_trade, update_trade
•	api/imports.py ← import_soft4x, import_mt4
________________________________________
۶. واحدهای اندازه‌گیری (مهم)
فیلد	واحد	ذخیره در DB	نمایش در UI
initial_balance	دلار	دلار	دلار
profit_target	دلار	دلار	دلار + درصد
max_daily_dd	دلار	دلار	دلار + درصد
max_total_dd	دلار	دلار	دلار + درصد
current_profit	دلار	دلار	دلار
equity	دلار	دلار	دلار
withdrawable_profit	دلار	دلار	دلار
profit_share_percentage	درصد	درصد	درصد
profit_progress_percent	درصد	-	فقط نمایش
daily_dd_progress_percent	درصد	-	فقط نمایش
total_dd_progress_percent	درصد	-	فقط نمایش
قانون: کاربر در UI درصد وارد می‌کند، Frontend به دلار تبدیل می‌کند، Backend دلار ذخیره می‌کند.
فرمول‌ها:
typescript
profit_target_amount = (profit_target_percent / 100) * initial_balance
max_daily_dd_amount = (max_daily_dd_percent / 100) * initial_balance
max_total_dd_amount = (max_total_dd_percent / 100) * initial_balance
________________________________________
۷. PnL و Commission (مهم)
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
فایل: backend/app/services/analysis_service.py ← _calculate_basic_metrics, _calculate_max_drawdown
________________________________________
۸. Migration (Alembic)
8.1 وضعیت فعلی
فایل: backend/migrations/versions/c4838cd01bbd_initial_schema_with_trade_hash.py
شامل: ۱۸ جدول + ایندکس‌ها + trade_hash
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
8.3 نکات
•	قبل از هر migration ← Backup از trading_desk.db
•	DB فعلی: SQLite، بدون داده‌ی مهم (تست)
•	alembic.ini: sqlalchemy.url = sqlite:///./trading_desk.db
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
ستون‌ها: ۱۳ ستون (Time, Position, Symbol, Type, Volume, Price, S/L, T/P, Time, Price, Commission, Swap, Profit)
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
9.4 ImportBatch (باقی‌مانده)
وضعیت: ❌ پیاده نشده
طبق بلوپرینت:
•	جدول import_batches با فیلدهای: source, account, test_type, strategy_version, timestamp, stats
•	Pipeline: Preview ← User Confirmation ← DB Transaction
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
خروجی evaluate_stage:
python
{
    "stage_id", "stage_type", "status",
    "initial_balance", "equity", "current_profit", "current_profit_percent",
    "profit_target", "profit_progress_percent",
    "max_daily_loss", "max_daily_dd_limit", "daily_dd_progress_percent", "daily_dd_violated",
    "max_total_dd", "max_total_dd_limit", "total_dd_progress_percent", "total_dd_violated",
    "trading_days", "min_trading_days", "days_met",
    "target_reached", "ready_to_pass", "suggested_status", "violations",
    "is_funded", "total_withdrawn", "profit_share_percentage", "withdrawable_profit",
    "total_trades",
}
وضعیت‌های پیشنهادی:
•	ready_to_pass — آماده‌ی پاس
•	in_progress — در حال پیشرفت
•	failed_daily_dd — DD روزانه نقض شده
•	failed_total_dd — DD کلی نقض شده
مصرف‌کننده: api/prop.py ← check_pass_ready (endpoint GET /api/prop/stages/{stage_id}/check-pass)
________________________________________
۱۱. Analysis Service
فایل: backend/app/services/analysis_service.py
کلاس: AnalysisService
متدهای اصلی:
python
def analyze_version(self, version_id: int) -> AnalysisResult
def compare_versions(self, version_ids: List[int], min_trades: int = 0) -> Dict
def calculate_stage_progress(self, stage_id: int) -> Dict  # ← باید حذف شود
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
________________________________________
۱۲. Frontend Pages (وضعیت)
صفحه	فایل	وضعیت
Dashboard	DashboardPage.tsx	✅ Prop-focused
Analysis	AnalysisPage.tsx	✅ کار می‌کند
Comparison	ComparisonPage.tsx	✅
Strategy	StrategyPage.tsx	✅
Trades	TradesPage.tsx	✅
Journal	JournalPage.tsx	✅
Prop	PropPage.tsx	✅ درصد ↔ دلار
Personal	PersonalPage.tsx	✅
Import	ImportPage.tsx	✅ Duplicate Detection
Settings	SettingsPage.tsx	✅
Navigation: App.tsx ← state-based (نه router)
Sidebar: components/Sidebar.tsx
فونت: Vazirmatn (CDN)
تاریخ: شمسی (PersianDateInput.tsx)
________________________________________
۱۳. وضعیت فعلی (Done)
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
o	withdraw تکراری رفع شد
o	Create Account ← درصد
o	Edit Stage ← درصد
o	Pass Modal ← درصد
•	❌ pass_stage validation پیاده نشده
•	❌ withdraw خط current_profit -= amount حذف نشده
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
۱۴. کارهای باقی‌مانده (To-Do)
🔴 اولویت بالا
14.1.1 api/prop.py — pass_stage validation
مشکل: الان هر کسی می‌تواند با POST، مرحله را پاس کند (حتی اگر DD نقض شده باشد).
راه‌حل:
python
@router.post("/stages/{stage_id}/pass")
def pass_stage(stage_id: int, request: PassStageWithRulesRequest, db: Session = Depends(get_db)):
    stage = db.query(PropStage).filter(PropStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="مرحله پیدا نشد")

    if stage.stage_type == StageType.FUNDED_REAL:
        raise HTTPException(status_code=400, detail="مرحله رییل قابل پاس شدن نیست")

    # ✅ چک آمادگی با Rule Engine
    evaluation = PropRuleEngine.evaluate_stage(db, stage_id)
    if not evaluation.get("ready_to_pass"):
        raise HTTPException(
            status_code=400,
            detail=f"مرحله آماده‌ی پاس شدن نیست. دلایل: {', '.join(evaluation.get('violations', []))}"
        )
    # ... ادامه
فایل: backend/app/api/prop.py ← pass_stage
14.1.2 withdraw خط current_profit -= amount
مشکل: current_profit با withdraw کم می‌شود ← Double Counting
راه‌حل: خط stage.current_profit -= request.amount حذف شود.
current_profit فقط از روی trades محاسبه می‌شود.
فایل: backend/app/api/prop.py ← withdraw
14.1.3 withdraw validation با validate_withdrawal
python
is_valid, error = PropRuleEngine.validate_withdrawal(db, stage_id, amount)
if not is_valid:
    raise HTTPException(status_code=400, detail=error)
فایل: backend/app/api/prop.py ← withdraw
🟡 اولویت متوسط
14.2.1 _summarize — net_pnl
مشکل: _summarize هنوز sum(t.pnl) استفاده می‌کند.
راه‌حل: مثل _calculate_basic_metrics، از _net_pnl(t) استفاده کند.
فایل: backend/app/services/analysis_service.py ← _summarize
14.2.2 calculate_stage_progress حذف
مشکل: تکراری با PropRuleEngine.evaluate_stage.
راه‌حل: متد حذف شود.
فایل: backend/app/services/analysis_service.py ← calculate_stage_progress
14.2.3 AnalysisRun (تاریخچه تحلیل)
طبق بلوپرینت:
AnalysisRun = هر اجرای تحلیل
AnalysisResult/Current Result = خروجی فعلی یا Snapshot
تا تاریخچه تحلیل‌ها از بین نرود.
راه‌حل:
•	جدول analysis_runs با فیلدهای: version_id, created_at, metrics_snapshot, notes
•	analyze_version ← AnalysisRun جدید بسازد (به جای overwrite)
فایل: backend/app/models/strategy.py + backend/app/services/analysis_service.py
🟢 اولویت پایین
14.3.1 DashboardPage هاردکدها
مشکل: جدول «آخرین معاملات» و «پیشرفت اهداف» هاردکد هستند.
راه‌حل: از API بخواند (GET /api/trades/?limit=10).
فایل: frontend/src/pages/DashboardPage.tsx
14.3.2 AnalysisPage — بهبود UI
پیشنهاد:
•	Drawdown Chart (underwater)
•	Metric Cards حرفه‌ای‌تر
•	Rolling Win Rate
•	Monthly Breakdown
فایل: frontend/src/pages/AnalysisPage.tsx
14.3.3 Import — Preview + ImportBatch
طبق بلوپرینت:
Pipeline: Upload ← Parse ← Normalize ← Validate ← Duplicate ← Preview ← User Confirmation ← DB Transaction
فایل: backend/app/api/imports.py + backend/app/models/strategy.py
14.3.4 Screenshot — Standardization
طبق بلوپرینت:
Screenshot باید رابطه استاندارد و منبع اصلی مشخصی داشته باشد.
مشکل: Trade.screenshot_path (تک) + جدول screenshots (چند) — دوگانگی.
راه‌حل: Trade.screenshot_path حذف، فقط screenshots بماند.
14.3.5 target_personal_account_id در Withdrawal
طبق بلوپرینت:
مقصد آینده Withdrawal باید FinancialAccount باشد، نه Personal Trading Account.
راه‌حل: در Phase 10 (Personal Finance) حل شود. فعلاً temporary.
14.3.6 Instrument Entity
طبق بلوپرینت:
Instrument Entity مستقل: canonical_symbol, display_name, asset_class, tick_size, pip_size, contract_size, aliases.
وضعیت: پیاده نشده. SymbolMapping فعلی جایگزین ساده است.
14.3.7 Decimal برای Money
طبق بلوپرینت:
برای Money در آینده Decimal
وضعیت: الان Float استفاده می‌شود.
14.3.8 UTC-aware datetime
طبق بلوپرینت:
UTC/Timezone-aware datetime
وضعیت: datetime.utcnow() استفاده می‌شود (naive).
________________________________________
۱۵. API Endpoints (کامل)
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
۱۶. محیط اجرا
Backend
powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
URL: http://localhost:8000
Docs: http://localhost:8000/docs
Frontend
powershell
cd frontend
pnpm install
pnpm dev
URL: http://localhost:5173
Database
•	SQLite: backend/trading_desk.db
•	Backup: Copy-Item "trading_desk.db" "trading_desk.db.bak_$(Get-Date -Format 'yyyyMMdd_HHmm')"
________________________________________
۱۷. Git Workflow
Repository: https://github.com/yasan1367-svg/MokTradeDesk-deep
Branch: main
دستورات:
powershell
git status
git add .
git commit -m "PHASE X: description"
git push origin main
git pull origin main
آخرین کامیت‌ها:
text
b662a5f PHASE 5+7: Duplicate Detection, Migration foundation, net_pnl with commission, Dashboard dollars
8f0c45a PHASE 5: Fix Import UX - auto-set test_type=real, add version_id to prop UI
fcbc948 PHASE 6: Prop Create Account + Edit Stage use percentages
f36920d Update NOTES.md with full progress
ead47d0 Update NOTES.md with today's progress
5867112 PHASE 6: Prop percentages in all forms, dollars displayed everywhere
f9da0fe PHASE 6: Fix PropPage units - show dollars instead of wrong percentages
7e2547b PHASE 6: Fix prop units, complete PropRuleEngine
da85553 Remove accidental 'h origin main' file
2302dc8 PHASE 2: Trade API - fix N+1, add filters, expand TradeUpdate with validation
7fa1d69 PHASE 2: Trade API - fix N+1, add filters,


۱۸. دستورالعمل برای AI/توسعه‌دهنده بعدی
اصول کلیدی
Backend = Source of Truth — تمام validation و منطق در Backend

StrategyVersion محور — Classification و Analysis بر اساس StrategyVersion

Trade Classification Contract — personal_account_id XOR prop_stage_id (در REAL)

Trade PnL ≠ Cashflow — بدون Double Counting

Prop Logic متمرکز — فقط در PropRuleEngine

Migration قبل از Schema Change — Backup ← Inspect ← Migration ← Verify

واحدها: DB = دلار، UI = درصد (تبدیل در Frontend)

net_pnl = pnl + commission + swap — همه‌ی محاسبات Analysis

Persistence: SQLite (trading_desk.db)

GitHub = Source of Truth

قبل از هر تغییر
□ Backup از trading_desk.db
□ git status (ببین چی تغییر کرده)
□ git pull origin main
□ بررسی تأثیر تغییر
بعد از هر تغییر
□ تست
□ git add .
□ git commit -m "PHASE X: description"
□ git push origin main
□ آپدیت NOTES.md
کارهای باقی‌مانده (اولویت‌بندی)
🔴 api/prop.py — pass_stage validation

🔴 api/prop.py — withdraw Double Counting

🟡 analysis_service.py — _summarize net_pnl

🟡 analysis_service.py — حذف calculate_stage_progress

🟡 AnalysisRun — تاریخچه تحلیل

🟢 DashboardPage — حذف هاردکدها

🟢 AnalysisPage — بهبود UI (Drawdown Chart, Metric Cards)

🟢 Import — Preview + ImportBatch

🟢 Screenshot — Standardization

🟢 Instrument Entity

🟢 Decimal برای Money

🟢 UTC-aware datetime

🟢 PHASE 9 — Testing / Regression

🟢 PHASE 10 — Personal Finance

پایان سند
