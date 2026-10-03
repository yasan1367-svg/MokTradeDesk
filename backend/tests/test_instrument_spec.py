from datetime import datetime, timezone

from app.domain.risk.instrument_spec import InstrumentSpec
from app.models.finance import Currency


def test_instrument_spec_create(db_session):
    spec = InstrumentSpec(
        canonical_symbol="TESTUSD",
        broker_symbol="TESTUSD.a",
        contract_size=100000.0,
        tick_size=0.0001,
        tick_value=10.0,
        point_size=0.0001,
        min_lot=0.01,
        max_lot=50.0,
        lot_step=0.01,
        commission_one_side=3.5,
        currency=Currency.USDT,
    )
    db_session.add(spec)
    db_session.commit()

    stored = db_session.query(InstrumentSpec).filter_by(canonical_symbol="TESTUSD").one()
    assert stored.id is not None
    assert stored.broker_symbol == "TESTUSD.a"
    assert stored.contract_size == 100000.0
    assert stored.tick_value == 10.0
    assert stored.commission_one_side == 3.5
    assert stored.currency is Currency.USDT


def test_instrument_spec_defaults(db_session):
    spec = InstrumentSpec(canonical_symbol="DEFAULTUSD")
    db_session.add(spec)
    db_session.commit()
    db_session.refresh(spec)

    assert spec.broker_symbol is None
    assert spec.contract_size == 1.0
    assert spec.tick_size == 0.00001
    assert spec.tick_value == 1.0
    assert spec.point_size is None
    assert spec.min_lot == 0.01
    assert spec.max_lot == 100.0
    assert spec.lot_step == 0.01
    assert spec.commission_one_side == 0.0
    assert spec.currency is Currency.USDT
    assert isinstance(spec.created_at, datetime)
    # SQLite drops timezone metadata when reading DateTime(timezone=True).
    created_at = spec.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    assert created_at.utcoffset() == timezone.utc.utcoffset(created_at)