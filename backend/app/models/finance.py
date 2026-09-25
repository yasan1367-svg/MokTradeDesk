import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Enum, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship

from ..core.database import Base


# ═════════════════════════════════════════════
# Enums
# ═════════════════════════════════════════════
class AccountType(str, enum.Enum):
    BANK = "bank"
    EXCHANGE = "exchange"
    CRYPTO_WALLET = "crypto_wallet"
    BROKER = "broker"
    PROP = "prop"


class Currency(str, enum.Enum):
    IRR = "IRR"
    USD = "USD"


class CategoryType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    EXCHANGE = "exchange"


class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    EXCHANGE = "exchange"
    PROFIT = "profit"
    LOSS = "loss"
    FEE = "fee"
    PURCHASE = "purchase"


# ═════════════════════════════════════════════
# Models
# ═════════════════════════════════════════════
class Account(Base):
    """حساب مالی (بانکی، صرافی، بروکر، پراپ، کیف‌پول)"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(Enum(AccountType), nullable=False)
    currency = Column(Enum(Currency), nullable=False, default=Currency.USD)
    balance = Column(Float, default=0.0)
    card_number = Column(String, nullable=True)
    broker_name = Column(String, nullable=True)
    prop_firm_name = Column(String, nullable=True)
    prop_firm_id = Column(Integer, ForeignKey("prop_firms.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # relationships
    prop_firm = relationship("PropFirm")
    transactions_out = relationship(
        "Transaction",
        foreign_keys="Transaction.from_account_id",
        back_populates="from_account",
        cascade="all, delete-orphan",
    )
    transactions_in = relationship(
        "Transaction",
        foreign_keys="Transaction.to_account_id",
        back_populates="to_account",
        cascade="all, delete-orphan",
    )
    entries = relationship(
        "Transaction",
        foreign_keys="Transaction.account_id",
        back_populates="account",
        cascade="all, delete-orphan",
    )


class Category(Base):
    """دسته‌بندی تراکنش‌ها (درآمد، هزینه، انتقال، تبدیل)"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(Enum(CategoryType), nullable=False)
    color = Column(String, nullable=True)
    icon = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # relationships
    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    """تراکنش مالی (واریز، برداشت، سود، هزینه و ...)"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(Enum(Currency), nullable=False, default=Currency.USD)
    date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    description = Column(Text, nullable=True)
    type = Column(Enum(TransactionType), nullable=False)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    related_trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    related_prop_account_id = Column(Integer, ForeignKey("prop_accounts.id"), nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # relationships
    account = relationship("Account", foreign_keys=[account_id], back_populates="entries")
    from_account = relationship("Account", foreign_keys=[from_account_id], back_populates="transactions_out")
    to_account = relationship("Account", foreign_keys=[to_account_id], back_populates="transactions_in")
    category = relationship("Category", back_populates="transactions")
    related_trade = relationship("Trade")
    related_prop_account = relationship("PropAccount")