from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum, JSON, ForeignKey, func, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from ..core.database import Base
from .finance import Currency

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


# ── فاز ۳۸: نوع هزینهٔ پراپ ──
class CostType(str, enum.Enum):
    """نوع هزینهٔ پراپ (PURCHASE چلنج، RESET، ADDON، ...).

    توجه (فاز ۳۸): مقدار در دیتابیس به‌صورت **value** (lowercase) ذخیره می‌شود
    (نه NAME) تا با دادهٔ قدیمی (`cost_type="purchase"`) و قرارداد فعلی API
    (`(cost_type or "").lower() == "purchase"`) سازگار بماند.
    """
    PURCHASE = "purchase"
    RESET = "reset"
    ADDON = "addon"
    DATA_FEE = "data_fee"
    REFUND = "refund"
    OTHER = "other"


def _enum_values(enum_cls):
    """SQLAlchemy `values_callable`: ذخیرهٔ value (lowercase) به‌جای NAME."""
    return [e.value for e in enum_cls]


# ── فاز ۳۲: موتور قوانین پراپ ──
class RuleType(str, enum.Enum):
    """انواع قوانین ارزیابی‌شده توسط PropRuleEngine.

    توجه: مقدار enum در دیتابیس به‌صورت NAME ذخیره می‌شود
    ('DAILY_DRAWDOWN' / 'MAX_DRAWDOWN' / ...) نه value.
    """
    DAILY_DRAWDOWN = "daily_drawdown"
    MAX_DRAWDOWN = "max_drawdown"
    PROFIT_TARGET = "profit_target"
    MIN_TRADING_DAYS = "min_trading_days"
    EQUITY_BALANCE = "equity_balance"
    FLOATING_PNL = "floating_pnl"
    STAGE_STATUS = "stage_status"


class Severity(str, enum.Enum):
    """شدت نتیجه‌ی ارزیابی یک قاعده (خروجی Pipeline موتور قوانین).

    توجه: مقدار enum در دیتابیس به‌صورت NAME ذخیره می‌شود
    ('PASS' / 'WARNING' / 'VIOLATION').
    """
    PASS = "pass"
    WARNING = "warning"
    VIOLATION = "violation"


# ── فاز ۳۳: چرخه‌ی عمر برداشت پراپ ──
class WithdrawalStatus(str, enum.Enum):
    """وضعیت برداشت پراپ (فاز ۳۳).

    جریان مجاز:
        REQUESTED → APPROVED → PROCESSING → RECEIVED
        (و هر مرحله‌ی غیرنهایی می‌تواند → CANCELLED شود)

    **قانون مالی:** درآمد (FinancialTransaction) فقط در نقطه‌ی RECEIVED ثبت می‌شود.
    """
    REQUESTED = "requested"
    APPROVED = "approved"
    PROCESSING = "processing"
    RECEIVED = "received"
    CANCELLED = "cancelled"


WITHDRAWAL_TRANSITIONS = {
    WithdrawalStatus.REQUESTED: (
        WithdrawalStatus.APPROVED,
        WithdrawalStatus.CANCELLED,
    ),
    WithdrawalStatus.APPROVED: (
        WithdrawalStatus.PROCESSING,
        WithdrawalStatus.CANCELLED,
    ),
    WithdrawalStatus.PROCESSING: (
        WithdrawalStatus.RECEIVED,
        WithdrawalStatus.CANCELLED,
    ),
    WithdrawalStatus.RECEIVED: (),
    WithdrawalStatus.CANCELLED: (),
}

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
    # فاز ۳۸: String → Enum(Currency) (NAME='USD'/'IRR' ⇒ سازگار با دادهٔ قدیمی)
    currency = Column(Enum(Currency), default=Currency.USD)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    firm = relationship("PropFirm", back_populates="accounts")
    stages = relationship("PropStage", back_populates="account", cascade="all, delete-orphan")
    costs = relationship("PropCost", back_populates="account", cascade="all, delete-orphan")

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
    # فاز ۳۲: تاریخچه‌ی ارزیابی قوانین (Rule Evaluation) برای این مرحله
    rule_violations = relationship(
        "RuleViolation", back_populates="stage", cascade="all, delete-orphan"
    )

class PropWithdrawal(Base):
    __tablename__ = "prop_withdrawals"

    id = Column(Integer, primary_key=True, index=True)
    prop_stage_id = Column(Integer, ForeignKey("prop_stages.id"), nullable=False)
    amount = Column(Float, nullable=False)

    # ── فاز ۳۳ ──
    currency = Column(Enum(Currency), nullable=False, default=Currency.USD)
    withdrawal_date = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    destination_account_id = Column(
        Integer, ForeignKey("accounts.id"), nullable=False
    )
    status = Column(
        Enum(WithdrawalStatus), nullable=False,
        default=WithdrawalStatus.REQUESTED, index=True,
    )
    reference = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    # FinancialTransaction فقط در نقطه‌ی RECEIVED ساخته و این‌جا لینک می‌شود
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    stage = relationship("PropStage", back_populates="withdrawals")
    destination_account = relationship("FinancialAccount", foreign_keys=[destination_account_id])
    financial_transaction = relationship("FinancialTransaction", foreign_keys=[transaction_id])


class PropCost(Base):
    __tablename__ = "prop_costs"

    id = Column(Integer, primary_key=True, index=True)
    prop_account_id = Column(Integer, ForeignKey("prop_accounts.id"), nullable=False)
    # فاز ۳۸: String آزاد → Enum(CostType) با ذخیرهٔ lowercase (سازگار با دادهٔ قدیمی)
    cost_type = Column(
        Enum(CostType, values_callable=_enum_values),
        nullable=False,
        default=CostType.OTHER,
    )
    amount = Column(Float, nullable=False)
    # فاز ۳۸: String → Enum(Currency)
    currency = Column(Enum(Currency), default=Currency.USD)
    cost_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    description = Column(Text, nullable=True)
    is_refunded = Column(Integer, default=0)

    account = relationship("PropAccount", back_populates="costs")

class PropAlert(Base):
    __tablename__ = "prop_alerts"

    id = Column(Integer, primary_key=True, index=True)
    prop_stage_id = Column(Integer, ForeignKey("prop_stages.id"), nullable=False)
    message = Column(Text, nullable=False)
    # فاز ۳۸: Integer → Boolean (0/1 در SQLite سازگار است)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    stage = relationship("PropStage", back_populates="alerts")


class RuleViolation(Base):
    """فاز ۳۲ — نتیجه‌ی ارزیابی یک قاعده برای یک مرحله پراپ.

    هر رکورد یک «بررسی قاعده» (Rule Evaluation) را نگه می‌دارد؛ `severity` می‌تواند
    PASS / WARNING / VIOLATION باشد (پس جدول تاریخچه‌ی کامل ارزیابی است، نه فقط نقض‌ها).
    """
    __tablename__ = "rule_violations"

    id = Column(Integer, primary_key=True, index=True)
    prop_stage_id = Column(
        Integer, ForeignKey("prop_stages.id"), nullable=False, index=True
    )
    rule_type = Column(Enum(RuleType), nullable=False, index=True)
    actual_value = Column(Float, nullable=False)
    limit_value = Column(Float, nullable=False)
    severity = Column(Enum(Severity), nullable=False, index=True)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())

    stage = relationship("PropStage", back_populates="rule_violations")
