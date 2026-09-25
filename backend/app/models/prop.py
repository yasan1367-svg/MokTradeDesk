from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from ..core.database import Base

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

class PropFirm(Base):
    __tablename__ = "prop_firms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    default_profit_share = Column(Float, default=80.0)
    website = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    accounts = relationship("PropAccount", back_populates="firm")
    default_rules = relationship("PropFirmDefaultRules", back_populates="firm", cascade="all, delete-orphan")

class PropFirmDefaultRules(Base):
    __tablename__ = "prop_firm_default_rules"

    id = Column(Integer, primary_key=True, index=True)
    prop_firm_id = Column(Integer, ForeignKey("prop_firms.id"), nullable=False)
    stage_type = Column(Enum(StageType), nullable=False)
    profit_target = Column(Float, nullable=True)
    max_daily_dd = Column(Float, nullable=True)
    max_total_dd = Column(Float, nullable=True)
    min_trading_days = Column(Integer, nullable=True)
    profit_share_percentage = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    firm = relationship("PropFirm", back_populates="default_rules")

class PropAccount(Base):
    __tablename__ = "prop_accounts"

    id = Column(Integer, primary_key=True, index=True)
    prop_firm_id = Column(Integer, ForeignKey("prop_firms.id"), nullable=False)
    account_label = Column(String, nullable=False)
    account_number = Column(String, nullable=True)
    currency = Column(String, default="USD")
    is_active = Column(Integer, default=1)
    finance_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    firm = relationship("PropFirm", back_populates="accounts")
    stages = relationship("PropStage", back_populates="account", cascade="all, delete-orphan")
    costs = relationship("PropCost", back_populates="account", cascade="all, delete-orphan")
    finance_account = relationship("Account", foreign_keys=[finance_account_id])

class PropStage(Base):
    __tablename__ = "prop_stages"

    id = Column(Integer, primary_key=True, index=True)
    prop_account_id = Column(Integer, ForeignKey("prop_accounts.id"), nullable=False)
    stage_type = Column(Enum(StageType), nullable=False)
    status = Column(Enum(StageStatus), default=StageStatus.ACTIVE)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    profit_target = Column(Float, nullable=True)
    max_daily_dd = Column(Float, nullable=True)
    max_total_dd = Column(Float, nullable=True)
    min_trading_days = Column(Integer, nullable=True)
    restrictions = Column(JSON, nullable=True)
    initial_balance = Column(Float, nullable=True)
    final_balance = Column(Float, nullable=True)
    profit_share_percentage = Column(Float, nullable=True)
    total_withdrawn = Column(Float, default=0.0)
    current_profit = Column(Float, default=0.0)
    failure_reason = Column(Enum(FailureReason), nullable=True)
    failure_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    account = relationship("PropAccount", back_populates="stages")
    trades = relationship("Trade", back_populates="prop_stage")
    withdrawals = relationship("PropWithdrawal", back_populates="stage", cascade="all, delete-orphan")
    alerts = relationship("PropAlert", back_populates="stage", cascade="all, delete-orphan")

class PropWithdrawal(Base):
    __tablename__ = "prop_withdrawals"

    id = Column(Integer, primary_key=True, index=True)
    prop_stage_id = Column(Integer, ForeignKey("prop_stages.id"), nullable=False)
    amount = Column(Float, nullable=False)
    withdrawal_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    note = Column(Text, nullable=True)
    destination_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    stage = relationship("PropStage", back_populates="withdrawals")
    destination_account = relationship("Account", foreign_keys=[destination_account_id])

class PropCost(Base):
    __tablename__ = "prop_costs"

    id = Column(Integer, primary_key=True, index=True)
    prop_account_id = Column(Integer, ForeignKey("prop_accounts.id"), nullable=False)
    cost_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    cost_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    description = Column(Text, nullable=True)
    is_refunded = Column(Integer, default=0)

    account = relationship("PropAccount", back_populates="costs")

class PropAlert(Base):
    __tablename__ = "prop_alerts"

    id = Column(Integer, primary_key=True, index=True)
    prop_stage_id = Column(Integer, ForeignKey("prop_stages.id"), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    stage = relationship("PropStage", back_populates="alerts")