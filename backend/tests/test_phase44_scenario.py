"""تست سناریوی فاز ۴۴.۷ — «قابل خرج» بدون Double Counting + دامنهٔ داشبورد."""
from datetime import datetime, timezone

from app.models.finance import Currency
from app.models.prop import PropAccount, PropFirm, PropStage, StageStatus, StageType
from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource
from app.models.trading import Broker, PersonalTradingAccount


def _version(db):
    strategy = Strategy(name="S44s")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v44s")
    db.add(version)
    db.flush()
    return version


def _pta(db, *, initial, current):
    broker = Broker(name="Broker-S44")
    db.add(broker)
    db.flush()
    pta = PersonalTradingAccount(
        broker_id=broker.id, account_number="ACC-S44", account_label="S44",
        currency=Currency.USD, initial_balance=initial, current_balance=current,
    )
    db.add(pta)
    db.flush()
    return pta


def _funded_stage(db):
    firm = PropFirm(name="F44s")
    db.add(firm)
    db.flush()
    account = PropAccount(prop_firm_id=firm.id, account_label="A")
    db.add(account)
    db.flush()
    stage = PropStage(
        prop_account_id=account.id, stage_type=StageType.FUNDED_REAL,
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


def _btrade(db, version_id, pnl, day=1):
    db.add(Trade(
        version_id=version_id, symbol="XAUUSD", direction="buy",
        open_time=datetime(2025, 7, day, 9, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 7, day, 10, 0, tzinfo=timezone.utc),
        open_price=2000.0, close_price=2000.0, size=1.0, pnl=pnl,
        commission=0.0, swap=0.0, source=TradeSource.MANUAL, test_type=TestType.BACKTEST,
    ))


def test_scenario_no_double_counting(client, db_session):
    """حساب بروکر (1000→1200)، payout دریافت‌شده ۳۰۰$ به کیف‌پول.

    «قابل خرج» باید دقیقاً 1200 (موجودی بروکر) + 500 (سود Funded تحقق‌یافته) باشد
    — نه بیشتر (سود بروکر دو بار شمرده نشود).
    """
    _pta(db_session, initial=1000.0, current=1200.0)   # broker_pnl = 200
    version = _version(db_session)
    funded = _funded_stage(db_session)
    _rtrade(db_session, version.id, funded.id, 500.0)
    funded.total_withdrawn = 300.0                     # payout دریافت‌شده
    # کیف‌پول مقصد، ۳۰۰$ را دریافت کرده است
    client.post("/api/finance/accounts", json={
        "name": "Wallet", "type": "crypto_wallet", "currency": "USD", "balance": 300,
    })
    db_session.commit()

    sm = client.get("/api/analytics/dashboard").json()["spendable_money"]
    # 1200 + 500 (نه 1200 + 200 + 500 = 1900)
    assert sm["total_balance"] == 1700.0
    assert sm["net_pnl"] == 700.0  # broker_pnl 200 + funded 500

    assets = client.get("/api/finance/spendable-assets").json()
    assert assets["broker"]["amount"] == 1200.0
    assert assets["crypto_wallet"]["amount"] == 300.0
    # سود قابل برداشت Funded = 500×80% − 300 = 100
    assert assets["prop_stage_3"]["amount"] == 100.0


def test_dashboard_scope_real_ignores_backtest(client, db_session):
    """با ۱۰۰ بک‌تست، اعداد داشبورد (scope=real) نباید تغییر کنند."""
    version = _version(db_session)
    funded = _funded_stage(db_session)
    _rtrade(db_session, version.id, funded.id, 500.0)
    db_session.commit()

    before = client.get("/api/analytics/dashboard").json()["summary"]
    assert before["net_pnl"] == 500.0
    assert before["total_trades"] == 1

    for i in range(100):
        _btrade(db_session, version.id, pnl=10.0, day=(i % 28) + 1)
    db_session.commit()

    after = client.get("/api/analytics/dashboard").json()["summary"]
    assert after["net_pnl"] == 500.0        # بدون تغییر
    assert after["total_trades"] == 1       # بک‌تست‌ها نادیده

    back = client.get("/api/analytics/dashboard", params={"scope": "backtest"}).json()["summary"]
    assert back["total_trades"] == 100
    assert back["net_pnl"] == 1000.0
