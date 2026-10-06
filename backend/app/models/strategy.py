from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Enum, JSON, ForeignKey,
    UniqueConstraint, Boolean, CheckConstraint, func,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from ..core.database import Base


# ═════════════════════════════════════════════
# Enums
# ═════════════════════════════════════════════
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
    """قرارداد معامله (فاز ۲۷) — ۴ نوع.

    توجه: مقدار enum در دیتابیس به‌صورت NAME ذخیره می‌شود
    ('BACKTEST' / 'FORWARD' / 'REAL_PERSONAL' / 'REAL_PROP') نه value.
    """
    BACKTEST = "backtest"
    FORWARD = "forward"
    REAL_PERSONAL = "real_personal"
    REAL_PROP = "real_prop"


class AnalysisScope(str, enum.Enum):
    """دامنه‌ی تحلیل (فاز ۲۰/۲۷) — هر scope مجموعه‌ی معاملات مستقل خودش را دارد.

    - VERSION          : تحلیل نسخه‌ی استراتژی (Backtest / Forward)
    - PROP_STAGE       : تحلیل مرحله‌ی پراپ (stage_1 / stage_2 / funded_real)
    - PERSONAL_ACCOUNT : تحلیل حساب معاملاتی شخصی (PersonalTradingAccount)

    توجه: مقدار enum در دیتابیس به‌صورت NAME ذخیره می‌شود
    ('VERSION' / 'PROP_STAGE' / 'PERSONAL_ACCOUNT') نه value.
    مقدار قدیمی 'BROKER' در migration به 'PERSONAL_ACCOUNT' نگاشت می‌شود.
    """
    VERSION = "version"
    PROP_STAGE = "prop_stage"
    PERSONAL_ACCOUNT = "personal_account"


class AnalysisStatus(str, enum.Enum):
    """وضعیت اجرای تحلیل (فاز ۳۵) — افزودنی، بدون اثر روی enumهای موجود.

    توجه: مقدار enum در دیتابیس به‌صورت NAME ذخیره می‌شود
    ('PENDING' / 'RUNNING' / 'COMPLETED' / 'FAILED').
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ═════════════════════════════════════════════
# Models
# ═════════════════════════════════════════════
class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    versions = relationship(
        "StrategyVersion",
        back_populates="strategy",
        cascade="all, delete-orphan"
    )


class StrategyVersion(Base):
    __tablename__ = "strategy_versions"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    version_name = Column(String, nullable=False)
    rules_note = Column(Text, nullable=True)
    status = Column(Enum(StrategyStatus), default=StrategyStatus.RESEARCH)
    # فاز 24: test_type for filtering in UI (BACKTEST / FORWARD / REAL)
    test_type = Column(String, nullable=True)
    # زیرساخت Fork: اگه این نسخه از روی نسخه‌ی دیگه‌ای ساخته شده، اینجا لینک می‌شه
    # (خودِ قابلیت Fork - دکمه/endpoint - بعداً و جدا پیاده می‌شه، این فقط ستونشه)
    forked_from_version_id = Column(Integer, ForeignKey("strategy_versions.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    strategy = relationship("Strategy", back_populates="versions")
    forked_from = relationship("StrategyVersion", remote_side=[id])
    trades = relationship(
        "Trade",
        back_populates="version",
        cascade="all, delete-orphan"
    )
    analysis_results = relationship(
        "AnalysisResult",
        back_populates="version",
        cascade="all, delete-orphan"
    )
    analysis_runs = relationship(
        "AnalysisRun",
        back_populates="version",
        cascade="all, delete-orphan"
    )


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)

    # ── قرارداد Classification (فاز ۲۷) ──
    # version_id برای همه‌ی انواع اجباری است.
    version_id = Column(Integer, ForeignKey("strategy_versions.id"), nullable=False, index=True)
    # فقط REAL_PERSONAL
    personal_trading_account_id = Column(
        Integer, ForeignKey("personal_trading_accounts.id"), nullable=True, index=True
    )
    # فقط REAL_PROP
    # فاز ۳۶: index برای فیلتر پراپ در داشبورد/تجمیع‌های SQL
    prop_stage_id = Column(Integer, ForeignKey("prop_stages.id"), nullable=True, index=True)

    symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    open_time = Column(DateTime(timezone=True), nullable=False)
    close_time = Column(DateTime(timezone=True), nullable=True, index=True)
    open_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=True)
    size = Column(Float, nullable=False)
    sl = Column(Float, nullable=True)
    initial_sl = Column(Float, nullable=True)
    tp = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    r_multiple = Column(Float, nullable=True)
    commission = Column(Float, default=0.0)
    swap = Column(Float, default=0.0)
    entry_sequence = Column(Integer, default=1)

    source = Column(Enum(TradeSource), nullable=False)
    test_type = Column(Enum(TestType), nullable=False, default=TestType.BACKTEST, index=True)
    note = Column(Text, nullable=True)
    # فاز ۳۹.۳: ستون legacy «مسیر اسکرین‌شات» حذف شد (migration: f39a1b2c3d4e).
    # تنها منبع حقیقت اسکرین‌شات، جدول `screenshots` است
    # (`models/personal.py::Screenshot` با `entity_type='trade'` و `entity_id=trade.id`)
    # — این ستون در کد هیچ‌گاه خوانده/نوشته نمی‌شد (ستون مرده).
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # ── فاز ۵۳.۱: زمان آخرین ویرایش (مبنای تشخیص «تحلیل کهنه») ──
    # با هر UPDATE دوباره ست می‌شود تا تحلیل قدیمی
    # حتی وقتی تعداد معاملات تغییر نکند، کهنه شناخته شود. NULL برای رکوردهای
    # قدیمیِ قبل از مهاجرت مجاز است.
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    # ← Duplicate Detection
    trade_hash = Column(String(32), nullable=True, index=True)

    # ── قرارداد Classification در سطح DB (فاز ۲۷) ──
    # BACKTEST/FORWARD → هیچ‌کدام | REAL_PERSONAL → فقط personal | REAL_PROP → فقط prop
    __table_args__ = (
        CheckConstraint(
            "(test_type IN ('BACKTEST','FORWARD') "
            "   AND personal_trading_account_id IS NULL AND prop_stage_id IS NULL) "
            "OR (test_type = 'REAL_PERSONAL' "
            "   AND personal_trading_account_id IS NOT NULL AND prop_stage_id IS NULL) "
            "OR (test_type = 'REAL_PROP' "
            "   AND prop_stage_id IS NOT NULL AND personal_trading_account_id IS NULL)",
            name="ck_trades_classification",
        ),
    )

    version = relationship("StrategyVersion", back_populates="trades")
    prop_stage = relationship("PropStage", back_populates="trades")
    personal_trading_account = relationship(
        "PersonalTradingAccount", back_populates="trades"
    )
    reviews = relationship(
        "JournalReview",
        back_populates="trade",
        cascade="all, delete-orphan"
    )
    # فاز ۳۱: هویت‌های ایمپورت این معامله (Duplicate Detection).
    # Cascade لازم است تا Hard Delete معامله، هویت را هم پاک کند و
    # re-import بعدی اشتباهاً «تکراری» تشخیص داده نشود.
    import_identities = relationship(
        "ImportIdentity",
        back_populates="trade",
        cascade="all, delete-orphan"
    )

    # ══════════════════════════════════════════════
    # فاز ۳: محاسبات خالص PnL (فیلدهای کمکی)
    # ══════════════════════════════════════════════
    @property
    def net_pnl(self) -> float:
        """سود/زیان خالص = pnl + commission + swap

        فقط یک تابع محاسبه‌گر؛ هیچ تغییری در ذخیره‌سازی DB ایجاد نمی‌کند.
        """
        return (self.pnl or 0.0) + (self.commission or 0.0) + (self.swap or 0.0)

    @property
    def is_win(self) -> bool:
        """آیا این معامله سودآور است؟ (net_pnl > 0)"""
        return self.net_pnl > 0

    @property
    def is_loss(self) -> bool:
        """آیا این معامله ضررده است؟ (net_pnl < 0)"""
        return self.net_pnl < 0

    @property
    def is_breakeven(self) -> bool:
        """آیا این معامله سربه‌سر است؟ (net_pnl == 0)"""
        return self.net_pnl == 0.0


class CustomTimeInterval(Base):
    """بازه‌های زمانی سفارشی برای تحلیل معاملات.

    Times are stored as Tehran local time (UTC+3:30).
    The analysis engine matches trades by comparing `open_time` (stored as UTC)
    against the stored interval times. Callers should convert local Tehran
    times to this column's Tehran-local convention.
    """
    __tablename__ = "custom_time_intervals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    start_hour = Column(Integer, nullable=False)
    start_minute = Column(Integer, nullable=False)
    end_hour = Column(Integer, nullable=False)
    end_minute = Column(Integer, nullable=False)
    label = Column(String, nullable=True)
    priority = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TimePoint(Base):
    __tablename__ = "time_points"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    hour = Column(Integer, nullable=False)
    minute = Column(Integer, nullable=False)
    label = Column(String, nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)

    # ── فاز ۲۰/۲۷: دامنه‌ی تحلیل ──
    # scope مشخص می‌کند این تحلیل مربوط به «نسخه»، «مرحله‌ی پراپ» یا «حساب معاملاتی شخصی» است.
    scope = Column(
        Enum(AnalysisScope), nullable=False,
        default=AnalysisScope.VERSION, index=True,
    )
    # کلید متنی دامنه = str(id) همان scope.
    # چرا؟ چون FKها nullable هستند و UniqueConstraint روی NULL کار نمی‌کند.
    scope_key = Column(String, nullable=False, index=True)

    # فقط یکی از این سه پر می‌شود (بسته به scope)
    version_id = Column(Integer, ForeignKey("strategy_versions.id"), nullable=True)
    prop_stage_id = Column(Integer, ForeignKey("prop_stages.id"), nullable=True)
    personal_trading_account_id = Column(
        Integer, ForeignKey("personal_trading_accounts.id"), nullable=True
    )

    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    net_pnl = Column(Float, default=0.0)
    net_r = Column(Float, default=0.0)
    max_dd = Column(Float, default=0.0)

    # متریک‌های جدید
    expectancy = Column(Float, default=0.0)              # اکسپکتنسی دلاری (به ازای هر معامله)
    expectancy_r = Column(Float, nullable=True)           # اکسپکتنسی بر حسب R (اگه SL ثبت شده باشه)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)                 # مقدار مثبت (اندازه‌ی ضرر)
    largest_win = Column(Float, default=0.0)
    largest_loss = Column(Float, default=0.0)             # مقدار مثبت (اندازه‌ی ضرر)
    max_consecutive_losses = Column(Integer, default=0)
    consistency_analysis = Column(JSON, nullable=True)    # {pnl_std_dev, top_trades_contribution_percent, avg_win_avg_loss_ratio}

    session_analysis = Column(JSON, nullable=True)
    weekday_analysis = Column(JSON, nullable=True)
    hour_analysis = Column(JSON, nullable=True)
    custom_time_analysis = Column(JSON, nullable=True)
    time_point_analysis = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # ── فاز ۳۵: اتصال نتیجه به اجرای مربوطه (nullable — افزودنی، سازگار با دادهٔ موجود) ──
    analysis_run_id = Column(
        Integer, ForeignKey("analysis_runs.id"), nullable=True, index=True
    )

    # یک رکورد «جاری» برای هر دامنه (نسخه / مرحله‌ی پراپ / حساب بروکر)
    __table_args__ = (
        UniqueConstraint("scope", "scope_key", name="uq_analysis_results_scope_key"),
    )

    version = relationship("StrategyVersion", back_populates="analysis_results")
    analysis_run = relationship("AnalysisRun", foreign_keys=[analysis_run_id])



class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, index=True)

    # ── فاز ۲۰: دامنه (مثل AnalysisResult) ──
    # بدون UniqueConstraint — این جدول تاریخچه‌ی اجراهاست، نه وضعیت جاری.
    scope = Column(
        Enum(AnalysisScope), nullable=False,
        default=AnalysisScope.VERSION, index=True,
    )
    scope_key = Column(String, nullable=False, index=True)

    version_id = Column(Integer, ForeignKey("strategy_versions.id"), nullable=True)
    prop_stage_id = Column(Integer, ForeignKey("prop_stages.id"), nullable=True)
    personal_trading_account_id = Column(
        Integer, ForeignKey("personal_trading_accounts.id"), nullable=True
    )

    # متریک‌های اصلی (همان‌هایی که در Dashboard و مقایسه استفاده می‌شوند)
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    net_pnl = Column(Float, default=0.0)
    net_r = Column(Float, default=0.0)
    max_dd = Column(Float, default=0.0)
    expectancy = Column(Float, default=0.0)
    expectancy_r = Column(Float, nullable=True)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    largest_win = Column(Float, default=0.0)
    largest_loss = Column(Float, default=0.0)
    max_consecutive_losses = Column(Integer, default=0)

    # کلیه متریک‌های کامل به صورت JSON snapshot
    full_metrics = Column(JSON, nullable=True)

    # ── فاز ۳۵ (افزودنی): اتصال به AnalysisScopeRecord + وضعیت اجرا ──
    scope_id = Column(
        Integer, ForeignKey("analysis_scopes.id"), nullable=True, index=True
    )
    filters_snapshot = Column(JSON, nullable=True)
    trade_count = Column(Integer, default=0)
    status = Column(Enum(AnalysisStatus), nullable=True, default=AnalysisStatus.PENDING)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    version = relationship("StrategyVersion", back_populates="analysis_runs")
    scope_record = relationship("AnalysisScopeRecord", foreign_keys=[scope_id])


class AnalysisScopeRecord(Base):
    """فاز ۳۴ — دامنه‌ی تحلیل (جدول جدید `analysis_scopes`).

    نام کلاس `AnalysisScopeRecord` است (نه `AnalysisScope`) تا با enum فعلی
    `AnalysisScope` تضاد نام ایجاد نشود. قانون فاز ۳۴: همه‌ی تحلیل‌ها از این
    دامنه استفاده کنند.

    توجه: مقدار enum در دیتابیس به‌صورت NAME ذخیره می‌شود.
    """
    __tablename__ = "analysis_scopes"

    id = Column(Integer, primary_key=True, index=True)
    strategy_version_id = Column(
        Integer, ForeignKey("strategy_versions.id"), nullable=True
    )
    trade_type = Column(Enum(TestType), nullable=False)
    personal_trading_account_id = Column(
        Integer, ForeignKey("personal_trading_accounts.id"), nullable=True
    )
    prop_stage_id = Column(Integer, ForeignKey("prop_stages.id"), nullable=True)
    from_date = Column(DateTime(timezone=True), nullable=True)
    to_date = Column(DateTime(timezone=True), nullable=True)
    is_deleted_filter = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    version = relationship("StrategyVersion", foreign_keys=[strategy_version_id])



class SymbolMapping(Base):
    __tablename__ = "symbol_mappings"

    id = Column(Integer, primary_key=True, index=True)
    original_symbol = Column(String, nullable=False, unique=True)
    canonical_symbol = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
