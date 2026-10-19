"""
Domain: TRADING — حساب‌های معاملاتی شخصی (فاز ۲۸)

این دامنه کاملاً از FINANCE جدا است:
- `Broker`                 : بروکر (نهاد معاملاتی)
- `PersonalTradingAccount` : حساب معاملاتی شخصی روی یک بروکر

قانون: `FinancialAccount` (models/finance.py) ≠ `TradingAccount` (این فایل).
یک حساب معاملاتی «حساب مالی» نیست؛ موجودی آن برای تحلیل معاملات است، نه دفتر پول.
"""

from datetime import datetime, timezone

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
    # فاز ۴۶.۱: اختلاف ساعت سرور بروکر با UTC (دقیقه). MT4 طبق تصمیم D3 = 0.
    server_utc_offset_minutes = Column(Integer, default=0, nullable=False, server_default="0")
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
    currency = Column(Enum(Currency), nullable=False, default=Currency.USDT)
    initial_balance = Column(Float, nullable=False, default=0.0)
    current_balance = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, default=True, nullable=False)
    # فاز ۴۶.۱: اختلاف ساعت سرور بروکر با UTC (دقیقه).
    server_utc_offset_minutes = Column(Integer, default=0, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    broker = relationship("Broker", back_populates="accounts")
    trades = relationship("Trade", back_populates="personal_trading_account")
    cash_movements = relationship("BrokerCashMovement", back_populates="trading_account")


class BrokerCashMovement(Base):
    """جابجایی پول بین حساب معاملاتی شخصی و یکی از حساب‌های مالی خود کاربر."""
    __tablename__ = "broker_cash_movements"

    id = Column(Integer, primary_key=True, index=True)
    personal_trading_account_id = Column(
        Integer, ForeignKey("personal_trading_accounts.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    financial_account_id = Column(
        Integer, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_id = Column(
        Integer, ForeignKey("transactions.id", ondelete="RESTRICT"),
        nullable=False, unique=True, index=True,
    )
    direction = Column(String(32), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(Enum(Currency), nullable=False)
    date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    trading_account = relationship("PersonalTradingAccount", back_populates="cash_movements")
    financial_account = relationship("FinancialAccount")
    transaction = relationship("FinancialTransaction")
