from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Enum, JSON, ForeignKey,
    UniqueConstraint, Boolean,
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
    BACKTEST = "backtest"
    FORWARD = "forward"
    REAL = "real"


class AnalysisScope(str, enum.Enum):
    """دامنه‌ی تحلیل (فاز ۲۰) — هر scope مجموعه‌ی معاملات مستقل خودش را دارد.

    - VERSION    : تحلیل نسخه‌ی استراتژی (Backtest / Forward)
    - PROP_STAGE : تحلیل مرحله‌ی پراپ (stage_1 / stage_2 / funded_real)
    - BROKER     : تحلیل حساب بروکر (Account.type = BROKER)

    توجه: مقدار enum در دیتابیس به‌صورت NAME ذخیره می‌شود
    ('VERSION' / 'PROP_STAGE' / 'BROKER') نه value.
    """
    VERSION = "version"
    PROP_STAGE = "prop_stage"
    BROKER = "broker"


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

    version_id = Column(Integer, ForeignKey("strategy_versions.id"), nullable=True)
    prop_stage_id = Column(Integer, ForeignKey("prop_stages.id"), nullable=True)
    finance_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    open_time = Column(DateTime(timezone=True), nullable=False)
    close_time = Column(DateTime(timezone=True), nullable=True)
    open_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=True)
    size = Column(Float, nullable=False)
    sl = Column(Float, nullable=True)
    tp = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    r_multiple = Column(Float, nullable=True)
    commission = Column(Float, default=0.0)
    swap = Column(Float, default=0.0)
    entry_sequence = Column(Integer, default=1)

    source = Column(Enum(TradeSource), nullable=False)
    test_type = Column(Enum(TestType), default=TestType.BACKTEST)
    note = Column(Text, nullable=True)
    screenshot_path = Column(String, nullable=True)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # ── Soft Delete (فاز ۲۵) ──
    # حذف نرم: معامله از لیست‌ها پنهان می‌شود ولی داده‌اش حفظ می‌گردد.
    is_deleted = Column(Boolean, default=False, nullable=False, server_default="0", index=True)

        # ← Duplicate Detection
    trade_hash = Column(String(32), nullable=True, index=True)

    version = relationship("StrategyVersion", back_populates="trades")
    prop_stage = relationship("PropStage", back_populates="trades")
    finance_account = relationship("Account")
    reviews = relationship(
        "JournalReview",
        back_populates="trade",
        cascade="all, delete-orphan"
    )


class CustomTimeInterval(Base):
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

    # ── فاز ۲۰: دامنه‌ی تحلیل ──
    # scope مشخص می‌کند این تحلیل مربوط به «نسخه»، «مرحله‌ی پراپ» یا «حساب بروکر» است.
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
    finance_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

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

    # یک رکورد «جاری» برای هر دامنه (نسخه / مرحله‌ی پراپ / حساب بروکر)
    __table_args__ = (
        UniqueConstraint("scope", "scope_key", name="uq_analysis_results_scope_key"),
    )

    version = relationship("StrategyVersion", back_populates="analysis_results")


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
    finance_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

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

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    version = relationship("StrategyVersion", back_populates="analysis_runs")


class SymbolMapping(Base):
    __tablename__ = "symbol_mappings"

    id = Column(Integer, primary_key=True, index=True)
    original_symbol = Column(String, nullable=False, unique=True)
    canonical_symbol = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
