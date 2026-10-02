from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from ..core.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    theme = Column(String, default="dark")  # dark / light / system
    font_size = Column(Integer, default=14)
    timezone = Column(String, default="Asia/Tehran")
    currency = Column(String, default="USDT")
    calendar = Column(String, default="persian")  # persian / gregorian
    default_risk_percent = Column(Integer, default=1)
    default_profit_share = Column(Integer, default=80)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
