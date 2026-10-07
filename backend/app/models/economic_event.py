"""
EconomicEvent — پیش‌بینی‌های تقویم فارکس فکتوری (فاز NEWS).

این مدل برای ذخیرهٔ رویدادهای اقتصادی از تقویم Forex Factory طراحی شده.
هر رکورد نمایندهٔ یک رویداد JSON منبع است، فیلترشده به USD/High/Medium.
"""

from datetime import datetime, date, timezone

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Index,
)
from sqlalchemy.sql import func

from ..core.database import Base


class EconomicEvent(Base):
    """رویداد اقتصادی از تقویم Forex Factory."""
    __tablename__ = "economic_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    currency = Column(String(8), nullable=False)
    impact = Column(String(8), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    forecast = Column(String(64), nullable=True)
    previous = Column(String(64), nullable=True)
    fetched_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_economic_events_currency_impact_time", "currency", "impact", "event_time"),
    )