import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class PropStageType(str, enum.Enum):
    STAGE_1 = "stage_1"
    STAGE_2 = "stage_2"
    FUNDED_REAL = "funded_real"

class PropStageStatus(str, enum.Enum):
    ACTIVE = "active"
    PASSED = "passed"
    FAILED = "failed"
    CLOSED = "closed"

class PropFirm(Base):
    __tablename__ = "prop_firms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    website: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    default_rules: Mapped[List["PropFirmDefaultRules"]] = relationship(back_populates="prop_firm", cascade="all, delete-orphan")
    accounts: Mapped[List["PropAccount"]] = relationship(back_populates="prop_firm")

class PropFirmDefaultRules(Base):
    __tablename__ = "prop_firm_default_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    prop_firm_id: Mapped[int] = mapped_column(ForeignKey("prop_firms.id", ondelete="CASCADE"), nullable=False)
    max_daily_loss: Mapped[Optional[float]] = mapped_column(Float)
    max_total_loss: Mapped[Optional[float]] = mapped_column(Float)
    profit_target: Mapped[Optional[float]] = mapped_column(Float)
    min_trading_days: Mapped[Optional[int]] = mapped_column(Integer)
    raw_rules: Mapped[Optional[dict]] = mapped_column(JSON)

    prop_firm: Mapped["PropFirm"] = relationship(back_populates="default_rules")

class PropAccount(Base):
    __tablename__ = "prop_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    prop_firm_id: Mapped[int] = mapped_column(ForeignKey("prop_firms.id"), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    challenge_type: Mapped[Optional[str]] = mapped_column(String(50))
    initial_balance: Mapped[float] = mapped_column(Float, nullable=False)
    current_balance: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    prop_firm: Mapped["PropFirm"] = relationship(back_populates="accounts")
    stages: Mapped[List["PropStage"]] = relationship(back_populates="prop_account", cascade="all, delete-orphan")
    withdrawals: Mapped[List["PropWithdrawal"]] = relationship(back_populates="prop_account")
    costs: Mapped[List["PropCost"]] = relationship(back_populates="prop_account")
    ledger_transactions: Mapped[List["LedgerTransaction"]] = relationship(back_populates="prop_account")

class PropStage(Base):
    __tablename__ = "prop_stages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    prop_account_id: Mapped[int] = mapped_column(ForeignKey("prop_accounts.id", ondelete="CASCADE"), nullable=False)
    stage_type: Mapped[PropStageType] = mapped_column(SQLEnum(PropStageType), nullable=False)
    status: Mapped[PropStageStatus] = mapped_column(SQLEnum(PropStageStatus), default=PropStageStatus.ACTIVE, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    target_profit: Mapped[Optional[float]] = mapped_column(Float)
    max_loss_limit: Mapped[Optional[float]] = mapped_column(Float)

    prop_account: Mapped["PropAccount"] = relationship(back_populates="stages")
    alerts: Mapped[List["PropAlert"]] = relationship(back_populates="prop_stage", cascade="all, delete-orphan")
    trades: Mapped[List["Trade"]] = relationship(back_populates="prop_stage")

class PropWithdrawal(Base):
    __tablename__ = "prop_withdrawals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    prop_account_id: Mapped[int] = mapped_column(ForeignKey("prop_accounts.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    prop_account: Mapped["PropAccount"] = relationship(back_populates="withdrawals")

class PropCost(Base):
    __tablename__ = "prop_costs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    prop_account_id: Mapped[int] = mapped_column(ForeignKey("prop_accounts.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    cost_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    prop_account: Mapped["PropAccount"] = relationship(back_populates="costs")

class PropAlert(Base):
    __tablename__ = "prop_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    prop_stage_id: Mapped[int] = mapped_column(ForeignKey("prop_stages.id", ondelete="CASCADE"), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    prop_stage: Mapped["PropStage"] = relationship(back_populates="alerts")
