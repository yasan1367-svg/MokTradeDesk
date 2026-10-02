import pytest

from app.models.finance import AccountType, Currency, FinancialAccount
from app.models.trading import Broker, BrokerCashMovement, PersonalTradingAccount
from app.services.finance_metrics import broker_pnl


def _accounts(db_session, financial_balance=0):
    broker = Broker(name='Broker')
    wallet = FinancialAccount(
        name='Wallet', type=AccountType.CRYPTO_WALLET,
        currency=Currency.USDT, balance=financial_balance,
    )
    db_session.add_all([broker, wallet])
    db_session.flush()
    trading = PersonalTradingAccount(
        broker_id=broker.id, account_number='123', currency=Currency.USDT,
        initial_balance=1000, current_balance=1500,
    )
    db_session.add(trading)
    db_session.commit()
    return trading, wallet


def _movement(client, trading, wallet, direction='withdrawal_from_broker', amount=250):
    response = client.post('/api/broker/cash-movements', json={
        'personal_trading_account_id': trading.id,
        'financial_account_id': wallet.id,
        'direction': direction,
        'amount': amount,
        'date': '2026-10-02T09:00:00Z',
        'note': 'Original note',
    })
    assert response.status_code == 200, response.text
    return response.json()['movement']['id']


def test_withdrawal_edit_and_delete_preserve_broker_profit(client, db_session):
    trading, wallet = _accounts(db_session)
    movement_id = _movement(client, trading, wallet)
    db_session.refresh(trading)
    db_session.refresh(wallet)
    assert (trading.current_balance, wallet.balance) == (1250, 250)
    assert broker_pnl(db_session) == 500
    assert client.get('/api/finance/summary').json()['total_income'] == 0

    response = client.patch(f'/api/broker/cash-movements/{movement_id}', json={
        'amount': 300, 'note': '',
    })
    assert response.status_code == 200, response.text
    assert response.json()['movement']['note'] == ''
    db_session.refresh(trading)
    db_session.refresh(wallet)
    assert (trading.current_balance, wallet.balance) == (1200, 300)
    assert broker_pnl(db_session) == 500
    assert client.get('/api/broker/payouts/stats').json()['total'] == 300

    response = client.delete(f'/api/broker/cash-movements/{movement_id}')
    assert response.status_code == 200, response.text
    db_session.refresh(trading)
    db_session.refresh(wallet)
    assert (trading.current_balance, wallet.balance) == (1500, 0)
    assert broker_pnl(db_session) == 500
    assert client.get('/api/broker/payouts/stats').json()['total'] == 0


def test_switching_broker_account_restores_original_balance(client, db_session):
    trading, wallet = _accounts(db_session)
    second = PersonalTradingAccount(
        broker_id=trading.broker_id, account_number='456', currency=Currency.USDT,
        initial_balance=500, current_balance=500,
    )
    db_session.add(second)
    db_session.commit()
    movement_id = _movement(client, trading, wallet)
    response = client.patch(f'/api/broker/cash-movements/{movement_id}', json={
        'personal_trading_account_id': second.id, 'amount': 100,
    })
    assert response.status_code == 200, response.text
    assert response.json()['movement']['personal_account_name'] == '456'
    for account in (trading, second, wallet):
        db_session.refresh(account)
    assert (trading.current_balance, second.current_balance, wallet.balance) == (1500, 400, 100)
    assert broker_pnl(db_session) == 500


def test_deposits_are_capital_movements_not_profit_or_expense(client, db_session):
    trading, wallet = _accounts(db_session, financial_balance=1000)
    movement_id = _movement(client, trading, wallet, 'deposit_to_broker', 400)
    db_session.refresh(trading)
    db_session.refresh(wallet)
    assert (trading.current_balance, wallet.balance) == (1900, 600)
    assert broker_pnl(db_session) == 500
    summary = client.get('/api/finance/summary').json()
    assert summary['total_income'] == summary['total_expense'] == 0
    assert client.get('/api/broker/payouts/stats').json()['total'] == 0
    assert client.get('/api/finance/asset-trend').json()['trend'][-1]['total_usdt'] == 0
    assert client.delete(f'/api/broker/cash-movements/{movement_id}').status_code == 200


@pytest.mark.parametrize('field', ['direction', 'personal_trading_account_id', 'financial_account_id', 'amount'])
def test_required_movement_fields_cannot_be_cleared(client, db_session, field):
    trading, wallet = _accounts(db_session)
    movement_id = _movement(client, trading, wallet)
    response = client.patch(f'/api/broker/cash-movements/{movement_id}', json={field: None})
    assert response.status_code == 422, response.text
    db_session.refresh(trading)
    db_session.refresh(wallet)
    assert (trading.current_balance, wallet.balance) == (1250, 250)


def test_linked_finance_entry_cannot_be_edited_directly(client, db_session):
    trading, wallet = _accounts(db_session)
    movement_id = _movement(client, trading, wallet)
    movement = db_session.get(BrokerCashMovement, movement_id)
    endpoint = f'/api/finance/transactions/{movement.transaction_id}'
    assert client.patch(endpoint, json={'amount': 10}).status_code == 400
    assert client.delete(endpoint).status_code == 400


def test_broker_date_filter_includes_whole_day_and_utc_offset(client, db_session):
    trading, wallet = _accounts(db_session)
    _movement(client, trading, wallet)
    assert len(client.get('/api/broker/cash-movements?date_to=2026-10-02').json()) == 1
    assert len(client.get('/api/broker/cash-movements?date_from=2026-10-02T12:00:00%2B03:30').json()) == 1
    assert client.get('/api/broker/cash-movements?date_from=invalid').status_code == 400
