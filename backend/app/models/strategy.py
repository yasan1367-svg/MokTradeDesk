import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class VersionStatus(str, enum.Enum):
    RESEARCH = "research"
    FORWARD = "forward"
    APPROVED = "approved"
    LIVE = "live"
    DEPRECATED = "deprecated"

class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    versions: Mapped[List["StrategyVersion"]] = relationship(back_populates="strategy", cascade="all, delete-orphan")

class StrategyVersion(Base):
    __tablename__ = "strategy_versions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    version_name: Mapped[str] = mapped_column(String(50), nullable=False)
    rules_note: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[VersionStatus] = mapped_column(SQLEnum(VersionStatus), default=VersionStatus.RESEARCH, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    strategy: Mapped["Strategy"] = relationship(back_populates="versions")
    trades: Mapped[List["Trade"]] = relationship(back_populates="version")
    analysis_results: Mapped[List["AnalysisResult"]] = relationship(back_populates="version", cascade="all, delete-orphan")

class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("strategy_versions.id"), nullable=False)
    prop_stage_id: Mapped[Optional[int]] = mapped_column(ForeignKey("prop_stages.id", ondelete="SET NULL"))
    personal_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("personal_accounts.id", ondelete="SET NULL"))
    
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    open_price: Mapped[float] = mapped_column(Float, nullable=False)
    close_price: Mapped[Optional[float]] = mapped_column(Float)
    size: Mapped[float] = mapped_column(Float, nullable=False)
    sl: Mapped[Optional[float]] = mapped_column(Float)
    tp: Mapped[Optional[float]] = mapped_column(Float)
    pnl: Mapped[Optional[float]] = mapped_column(Float)
    r_multiple: Mapped[Optional[float]] = mapped_column(Float)
    commission: Mapped[float] = mapped_column(Float, default=0.0)
    swap: Mapped[float] = mapped_column(Float, default=0.0)
    entry_sequence: Mapped[Optional[int]] = mapped_column(Integer)
    source: Mapped[Optional[str]] = mapped_column(String(50))
    note: Mapped[Optional[str]] = mapped_column(Text)
    screenshot_path: Mapped[Optional[str]] = mapped_column(String(500))
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)
    news_event: Mapped[Optional[str]] = mapped_column(String(200))
    trade_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    version: Mapped["StrategyVersion"] = relationship(back_populates="trades")
    prop_stage: Mapped[Optional["PropStage"]] = relationship(back_populates="trades")
    personal_account: Mapped[Optional["PersonalAccount"]] = relationship(back_populates="trades")
    journal_review: Mapped[Optional["JournalReview"]] = relationship(back_populates="trade", uselist=False, cascade="all, delete-orphan")

class CustomTimeInterval(Base):
    __tablename__ = "custom_time_intervals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[Optional[str]] = mapped_column(String(20))
    start_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    end_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    end_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)

class TimePoint(Base):
    __tablename__ = "time_points"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[Optional[str]] = mapped_column(String(20))
    hour: Mapped[int] = mapped_column(Integer, nullable=False)
    minute: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("strategy_versions.id", ondelete="CASCADE"), nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    net_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    net_r: Mapped[float] = mapped_column(Float, default=0.0)
    max_dd: Mapped[float] = mapped_column(Float, default=0.0)
    session_analysis: Mapped[Optional[dict]] = mapped_column(JSON)
    weekday_analysis: Mapped[Optional[dict]] = mapped_column(JSON)
    hour_analysis: Mapped[Optional[dict]] = mapped_column(JSON)
    custom_time_analysis: Mapped[Optional[dict]] = mapped_column(JSON)
    time_point_analysis: Mapped[Optional[dict]] = mapped_column(JSON)
    monte_carlo_result: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    version: Mapped["StrategyVersion"] = relationship(back_populates="analysis_results")
