"""Instrument trading specifications used by the risk domain."""

from sqlalchemy import Column, DateTime, Enum, Float, Integer, String

from ...core.database import Base
from ...models.finance import Currency
from ...utils.time_utils import now_utc


class InstrumentSpec(Base):
    """Broker-independent contract and volume specifications for an instrument."""

    __tablename__ = "instrument_specs"

    id = Column(Integer, primary_key=True)
    canonical_symbol = Column(String(50), unique=True, nullable=False)
    broker_symbol = Column(String(50), nullable=True)
    contract_size = Column(Float, nullable=False, default=1.0)
    tick_size = Column(Float, nullable=False, default=0.00001)
    tick_value = Column(Float, nullable=False, default=1.0)
    point_size = Column(Float, nullable=True)
    min_lot = Column(Float, nullable=False, default=0.01)
    max_lot = Column(Float, nullable=False, default=100.0)
    lot_step = Column(Float, nullable=False, default=0.01)
    commission_one_side = Column(Float, nullable=False, default=0.0)
    currency = Column(Enum(Currency), nullable=False, default=Currency.USDT)
    created_at = Column(DateTime(timezone=True), default=now_utc)