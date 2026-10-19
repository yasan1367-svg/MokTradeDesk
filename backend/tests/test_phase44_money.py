"""تست‌های فاز ۴۴.۲/۴۴.۳/۴۴.۴ — پول داشبورد/مالی بدون Double Counting."""
from datetime import datetime, timezone

from app.models.finance import Currency
from app.models.prop import PropAccount, PropFirm, PropStage, StageStatus, StageType
from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource
from app.models.trading import Broker, PersonalTradingAccount


def _version(db):
    strategy = Strategy(name="S44m")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v44m")
    db.add(version)
    db.flush()
    return version


def _pta(db, *, initial=1000.0, current=1500.0, label="B44"):
    broker = Broker(name=f"Broker-{label}")
    db.add(broker)
    db.flush()
    pta = PersonalTradingAccount(
        broker_id=broker.id, account_number=f"ACC-{label}", account_label=label,
        currency=Currency.USD, initial_balance=initial, current_balance=current,
    )
    db.add(pta)
    db.flush()
    return pta


def _stage(db, stage_type):
    firm = PropFirm(name=f"F44-{stage_type.value}")
    db.add(firm)
    db.flush()
    account = PropAccount(prop_firm_id=firm.id, account_label="A")
    db.add(account)
    db.flush()
    stage = PropStage(
        prop_account_id=account.id, stage_type=stage_type,
        status=StageStatus.ACTIVE, initial_balance=10000.0,
        profit_share_percentage=80.0, total_withdrawn=0.0,
    )
    db.add(stage)
    db.flush()
    return stage


def _rtrade(db, version_id, stage_id, pnl):
    db.add(Trade(
        version_id=version_id, prop_stage_id=stage_id, symbol="XAUUSD", direction="buy",
        open_time=datetime(2025, 6, 1, 9, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
        open_price=2000.0, close_price=2000.0, size=1.0, pnl=pnl,
        commission=0.0, swap=0.0, source=TradeSource.MANUAL, test_type=TestType.REAL_PROP,
    ))


def test_dashboard_no_double_counting(client, db_session):
    """broker_balance خودش شامل broker_pnl است ⇒ نباید دو بار شمرده شود."""
    _pta(db_session, initial=1000.0, current=1500.0)  # broker_pnl = 500
    db_session.commit()

    sm = client.get("/api/analytics/dashboard").json()["spendable_money"]
    assert sm["net_pnl"] == 500.0
    assert sm["total_balance"] == 1500.0        # نه 2000 (اشتباه قبلی)
    assert sm["initial_capital"] == 1000.0


def test_funded_pnl_only_funded_real(client, db_session):
    """فقط معاملات مرحلهٔ FUNDED_REAL در funded_pnl شمرده می‌شوند (نه STAGE_1)."""
    version = _version(db_session)
    funded = _stage(db_session, StageType.FUNDED_REAL)
    stage1 = _stage(db_session, StageType.STAGE_1)
    _rtrade(db_session, version.id, funded.id, 500.0)
    _rtrade(db_session, version.id, stage1.id, 300.0)   # نباید شمرده شود
    db_session.commit()

    sm = client.get("/api/analytics/dashboard").json()["spendable_money"]
    assert sm["net_pnl"] == 500.0
    assert sm["total_balance"] == 500.0


def test_spendable_assets_after_payout_no_double_count(client, db_session):
    """فاز ۴۴.۳: بعد از payout دریافت‌شده، همان پول دوباره شمرده نمی‌شود."""
    version = _version(db_session)
    funded = _stage(db_session, StageType.FUNDED_REAL)
    funded.profit_share_percentage = 80.0
    _rtrade(db_session, version.id, funded.id, 1000.0)
    # سود کاربر = ۱۰۰۰ × ۸۰٪ = ۸۰۰ ؛ برداشت‌شده ۳۰۰ ⇒ قابل برداشت = ۵۰۰
    funded.total_withdrawn = 300.0
    db_session.commit()

    body = client.get("/api/finance/spendable-assets").json()
    assert body["prop_stage_3"]["amount"] == 500.0


def test_funded_pnl_consistent_across_endpoints(client, db_session):
    """فاز ۴۴.۴: داشبورد/مالی از یک منبع حقیقت واحد استفاده می‌کنند."""
    from app.services import finance_metrics

    _pta(db_session, initial=1000.0, current=1500.0)  # broker_pnl = 500
    version = _version(db_session)
    funded = _stage(db_session, StageType.FUNDED_REAL)
    _rtrade(db_session, version.id, funded.id, 500.0)
    db_session.commit()

    # ماژول مشترک
    assert finance_metrics.funded_pnl(db_session) == 500.0
    assert finance_metrics.total_balance(db_session) == 2000.0  # 1500 + 500

    # داشبورد
    sm = client.get("/api/analytics/dashboard").json()["spendable_money"]
    assert sm["total_balance"] == 2000.0

    # مالی
    assets = client.get("/api/finance/spendable-assets").json()
    assert assets["prop_stage_3"]["amount"] == finance_metrics.prop_stage_3(db_session) == 400.0

