from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from ..core.database import Base


class JournalReview(Base):
    __tablename__ = "journal_reviews"

    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False)
    setup_quality = Column(Integer, nullable=True)
    execution_quality = Column(Integer, nullable=True)
    rule_violations = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    lessons = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    trade = relationship("Trade", back_populates="reviews")
    screenshots = relationship("Screenshot", back_populates="review", cascade="all, delete-orphan")


class Screenshot(Base):
    __tablename__ = "screenshots"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    review_id = Column(Integer, ForeignKey("journal_reviews.id"), nullable=True)
    file_path = Column(String, nullable=False)
    file_hash = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    review = relationship("JournalReview", back_populates="screenshots")
