"""Regression tests for P1-01 broker balance freshness."""
from datetime import datetime, timezone

from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource
from app.models.trading import Broker, BrokerCashMovement, PersonalTradingAccount
from app.models.finance import AccountType, FinancialAccount, FinancialTransaction, TransactionType
from app.services.finance_sync_service import FinanceSyncService


def _account(db):
    broker = Broker(name="Sync broker")
    db.add(broker)
    db.flush()
    account = PersonalTradingAccount(
        broker_id=broker.id,
        account_number="SYNC-1",
        initial_balance=1000,
        current_balance=1000,
    )
    db.add(account)
    strategy = Strategy(name="Sync strategy")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v1")
    db.add(version)
    db.commit()
    return account, version


def _trade(account, version, pnl, commission=0, swap=0):
    return Trade(
        version_id=version.id,
        personal_trading_account_id=account.id,
        test_type=TestType.REAL_PERSONAL,
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
        open_price=2000,
        close_price=2010,
        size=1,
        pnl=pnl,
        commission=commission,
        swap=swap,
        source=TradeSource.MANUAL,
    )


def _movement(db, account, direction, amount):
    financial_account = FinancialAccount(
        name="Movement test account", type=AccountType.BANK, currency=account.currency, balance=0
    )
    db.add(financial_account)
    db.flush()
    transaction = FinancialTransaction(
        account_id=financial_account.id,
        amount=amount,
        currency=account.currency,
        date=datetime(2025, 1, 3, tzinfo=timezone.utc),
        type=TransactionType.ADJUSTMENT,
    )
    db.add(transaction)
    db.flush()
    return BrokerCashMovement(
        personal_trading_account_id=account.id,
        financial_account_id=financial_account.id,
        transaction_id=transaction.id,
        direction=direction,
        amount=amount,
        currency=account.currency,
        date=datetime(2025, 1, 3, tzinfo=timezone.utc),
    )


def test_recompute_balance_tracks_trades_deletions_and_movements(db_session):
    account, version = _account(db_session)
    service = FinanceSyncService(db_session)

    winner = _trade(account, version, 55, commission=-3, swap=-2)
    db_session.add(winner)
    db_session.commit()
    service.sync_closed_trades([winner.id])
    assert account.current_balance == 1050

    loser = _trade(account, version, -18, commission=-1, swap=-1)
    db_session.add(loser)
    db_session.commit()
    service.sync_closed_trades([loser.id])
    assert account.current_balance == 1030

    db_session.delete(winner)
    db_session.commit()
    service.recompute_accounts([account.id])
    assert account.current_balance == 980

    db_session.add(_movement(db_session, account, "deposit_to_broker", 100))
    db_session.commit()
    service.sync_closed_trades()
    assert account.current_balance == 1080

    db_session.add(_movement(db_session, account, "withdrawal_from_broker", 30))
    db_session.commit()
    service.sync_closed_trades()
    assert account.current_balance == 1050


def test_recompute_ignores_open_and_non_personal_trades(db_session):
    account, version = _account(db_session)
    open_trade = _trade(account, version, 500)
    open_trade.close_time = None
    db_session.add(open_trade)
    other = _trade(account, version, 900)
    other.test_type = TestType.BACKTEST
    other.personal_trading_account_id = None
    db_session.add(other)
    db_session.commit()

    assert FinanceSyncService(db_session).recompute_account_balance(account.id) == 1000