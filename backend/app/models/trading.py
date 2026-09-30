"""
Domain: TRADING — حساب‌های معاملاتی شخصی (فاز ۲۸)

این دامنه کاملاً از FINANCE جدا است:
- `Broker`                 : بروکر (نهاد معاملاتی)
- `PersonalTradingAccount` : حساب معاملاتی شخصی روی یک بروکر

قانون: `FinancialAccount` (models/finance.py) ≠ `TradingAccount` (این فایل).
یک حساب معاملاتی «حساب مالی» نیست؛ موجودی آن برای تحلیل معاملات است، نه دفتر پول.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Enum, ForeignKey, Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base
from .finance import Currency


class Broker(Base):
    """بروکر معاملاتی — مستقل از FinancialAccount."""
    __tablename__ = "brokers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    website = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    accounts = relationship(
        "PersonalTradingAccount",
        back_populates="broker",
        cascade="all, delete-orphan",
    )


class PersonalTradingAccount(Base):
    """حساب معاملاتی شخصی (Personal Trading Account) روی یک بروکر."""
    __tablename__ = "personal_trading_accounts"

    id = Column(Integer, primary_key=True, index=True)
    broker_id = Column(Integer, ForeignKey("brokers.id"), nullable=False, index=True)
    account_number = Column(String, nullable=False)
    account_label = Column(String, nullable=True)
    currency = Column(Enum(Currency), nullable=False, default=Currency.USD)
    initial_balance = Column(Float, nullable=False, default=0.0)
    current_balance = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    broker = relationship("Broker", back_populates="accounts")
    trades = relationship("Trade", back_populates="personal_trading_account")
