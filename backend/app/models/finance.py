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
    """نوع حساب مالی (فاز ۲۷ → گسترش فاز ۳۸) — فقط پول.

    حساب‌های معاملاتی (بروکر/پراپ) دیگر اینجا نیستند:
    - بروکر  → models/trading.py :: PersonalTradingAccount
    - پراپ   → models/prop.py    :: PropAccount / PropStage

    فاز ۳۸: `CARD` (کارت بانکی)، `CASH` (نقد) و `TRUST_WALLET` (کیف پول امانی)
    برای پشتیبانی کامل Master Plan اضافه شدند.
    """
    BANK = "bank"
    EXCHANGE = "exchange"
    CRYPTO_WALLET = "crypto_wallet"
    CARD = "card"                # فاز ۳۸: کارت بانکی
    CASH = "cash"                # فاز ۳۸: وجه نقد
    TRUST_WALLET = "trust_wallet"  # فاز ۳۸: کیف پول امانی/واسط


class Currency(str, enum.Enum):
    IRR = "IRR"
    USD = "USD"


class CategoryType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    CONVERSION = "conversion"    # فاز ۳۷: تبدیل ارز (USD ↔ IRR)
    # فاز ۳۸.۴ (Clean Break): `EXCHANGE` حذف شد ⇒ معادل آن `CONVERSION` است.


class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    PROFIT = "profit"
    LOSS = "loss"
    FEE = "fee"
    PURCHASE = "purchase"
    TRANSFER = "transfer"        # فاز ۳۷: انتقال بین حساب‌ها (درآمد/هزینه نیست)
    ADJUSTMENT = "adjustment"    # فاز ۳۷: اصلاح دستی موجودی (مثبت/منفی)
    # فاز ۳۸.۴ (Clean Break): `EXCHANGE` حذف شد ⇒ معادل آن `TRANSFER` است.


# ═════════════════════════════════════════════
# Models
# ═════════════════════════════════════════════
class FinancialAccount(Base):
    """حساب مالی (بانکی، صرافی، کیف‌پول).

    فاز ۳۷: کلاس از `Account` به `FinancialAccount` تغییر نام یافت تا با
    `PropAccount` و `PersonalTradingAccount` اشتباه نشود. نام جدول **بدون تغییر** است
    (`accounts`).

    فاز ۳۸.۴ (Clean Break): alias سازگاری `Account` **حذف شد** ⇒ فقط نام جدید معتبر است.
    """
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(Enum(AccountType), nullable=False)
    currency = Column(Enum(Currency), nullable=False, default=Currency.USD)
    balance = Column(Float, default=0.0)
    card_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # relationships
    transactions_out = relationship(
        "FinancialTransaction",
        foreign_keys="FinancialTransaction.from_account_id",
        back_populates="from_account",
        cascade="all, delete-orphan",
    )
    transactions_in = relationship(
        "FinancialTransaction",
        foreign_keys="FinancialTransaction.to_account_id",
        back_populates="to_account",
        cascade="all, delete-orphan",
    )
    entries = relationship(
        "FinancialTransaction",
        foreign_keys="FinancialTransaction.account_id",
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
    transactions = relationship("FinancialTransaction", back_populates="category")


class FinancialTransaction(Base):
    """تراکنش مالی (واریز، برداشت، سود، هزینه، انتقال، تبدیل، اصلاح).

    فاز ۳۷: کلاس از `Transaction` به `FinancialTransaction` تغییر نام یافت (افزودنی روی
    `TransactionType.TRANSFER`/`ADJUSTMENT` و `CategoryType.CONVERSION`). نام جدول
    **بدون تغییر** است (`transactions`).

    فاز ۳۸.۴ (Clean Break): alias سازگاری `Transaction` **حذف شد** ⇒ فقط نام جدید معتبر است.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(Enum(Currency), nullable=False, default=Currency.USD)
    date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    description = Column(Text, nullable=True)
    type = Column(Enum(TransactionType), nullable=False, index=True)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    related_trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    related_prop_account_id = Column(Integer, ForeignKey("prop_accounts.id"), nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # relationships
    account = relationship("FinancialAccount", foreign_keys=[account_id], back_populates="entries")
    from_account = relationship("FinancialAccount", foreign_keys=[from_account_id], back_populates="transactions_out")
    to_account = relationship("FinancialAccount", foreign_keys=[to_account_id], back_populates="transactions_in")
    category = relationship("Category", back_populates="transactions")
    related_trade = relationship("Trade")
    related_prop_account = relationship("PropAccount")