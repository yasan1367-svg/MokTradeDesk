from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class PersonalAccount(Base):
    __tablename__ = "personal_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    broker_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    initial_balance: Mapped[float] = mapped_column(Float, nullable=False)
    current_balance: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    trades: Mapped[List["Trade"]] = relationship(back_populates="personal_account")
    ledger_transactions: Mapped[List["LedgerTransaction"]] = relationship(back_populates="personal_account")

class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[Optional[int]] = mapped_column(Integer)
    personal_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("personal_accounts.id", ondelete="SET NULL"))
    prop_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("prop_accounts.id", ondelete="SET NULL"))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    description: Mapped[Optional[str]] = mapped_column(Text)
    transaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    personal_account: Mapped[Optional["PersonalAccount"]] = relationship(back_populates="ledger_transactions")
    prop_account: Mapped[Optional["PropAccount"]] = relationship(back_populates="ledger_transactions")

class JournalReview(Base):
    __tablename__ = "journal_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id", ondelete="CASCADE"), unique=True, nullable=False)
    setup_quality: Mapped[Optional[int]] = mapped_column(Integer)
    execution_quality: Mapped[Optional[int]] = mapped_column(Integer)
    rule_violations: Mapped[Optional[str]] = mapped_column(Text)
    emotional_state: Mapped[Optional[str]] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    lessons: Mapped[Optional[str]] = mapped_column(Text)
    rating: Mapped[Optional[float]] = mapped_column(Float)

    trade: Mapped["Trade"] = relationship(back_populates="journal_review")

class Screenshot(Base):
    __tablename__ = "screenshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
