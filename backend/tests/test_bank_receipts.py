from datetime import datetime, timezone

import pytest

from app.models.finance import AccountType, Currency, FinancialAccount, TransactionType
from app.services.wallet_service import WalletService


def _account(db_session, name, account_type, currency=Currency.IRR, balance=0):
    account = FinancialAccount(name=name, type=account_type, currency=currency, balance=balance)
    db_session.add(account)
    db_session.commit()
    return account


def _transfer(client, source, destination, amount):
    response = client.post('/api/finance/transactions', json={
        'account_id': destination.id,
        'from_account_id': source.id,
        'to_account_id': destination.id,
        'amount': amount,
        'currency': source.currency.value,
        'type': 'transfer',
        'date': '2026-10-02T09:00:00Z',
    })
    assert response.status_code == 200, response.text
    return response.json()['id']


def test_receipt_to_bank_counts_once_across_reports(client, db_session):
    exchange = _account(db_session, 'Exchange', AccountType.EXCHANGE, balance=1000)
    bank = _account(db_session, 'Bank', AccountType.BANK)
    second_bank = _account(db_session, 'Second bank', AccountType.BANK)
    _transfer(client, exchange, bank, 400)
    _transfer(client, bank, second_bank, 100)

    summary = client.get('/api/finance/summary?currency=IRR').json()
    assert summary['total_income'] == 400
    assert summary['by_currency']['USDT']['total_income'] == 0
    assert client.get(f'/api/finance/accounts/{bank.id}/stats').json()['total_income'] == 400
    assert client.get(f'/api/finance/accounts/{second_bank.id}/stats').json()['total_income'] == 0
    cashflow = client.get('/api/finance/charts/cashflow?currency=IRR').json()
    assert sum(month['income'] for month in cashflow) == 400
    monthly = client.get('/api/finance/reports/monthly?currency=IRR&year=1405').json()
    assert sum(month['income'] for month in monthly['months']) == 400
    assert client.get('/api/finance/reports/category-breakdown?currency=IRR').json()['total_income'] == 400
    assert client.get('/api/finance/reports/profit-loss?currency=IRR').json()['total_income'] == 400
    comparison = client.get('/api/finance/reports/account-comparison?currency=IRR').json()
    assert sum(account['total_income'] for account in comparison) == 400
    db_session.refresh(bank)
    db_session.refresh(second_bank)
    db_session.refresh(exchange)
    assert (exchange.balance, bank.balance, second_bank.balance) == (600, 300, 100)


def test_wallet_exchange_transfers_are_not_income(client, db_session):
    wallet = _account(db_session, 'Wallet', AccountType.CRYPTO_WALLET, Currency.USDT, 1000)
    exchange = _account(db_session, 'Exchange', AccountType.EXCHANGE, Currency.USDT)
    _transfer(client, wallet, exchange, 250)
    summary = client.get('/api/finance/summary').json()
    assert summary['total_income'] == 0
    assert summary['assets_by_currency']['USDT'] == 1000


def test_bank_receipt_edit_and_delete_update_income(client, db_session):
    exchange = _account(db_session, 'Exchange', AccountType.EXCHANGE, balance=1000)
    bank = _account(db_session, 'Bank', AccountType.BANK)
    transaction_id = _transfer(client, exchange, bank, 400)
    response = client.patch(f'/api/finance/transactions/{transaction_id}', json={'amount': 300})
    assert response.status_code == 200, response.text
    assert client.get('/api/finance/summary?currency=IRR').json()['total_income'] == 300
    response = client.delete(f'/api/finance/transactions/{transaction_id}')
    assert response.status_code == 200, response.text
    assert client.get('/api/finance/summary?currency=IRR').json()['total_income'] == 0
    db_session.refresh(bank)
    db_session.refresh(exchange)
    assert bank.balance == 0
    assert exchange.balance == 1000


@pytest.mark.parametrize('payload', [
    {'currency': 'USDT'},
    {'type': None},
    {'amount': 0},
    {'amount': 'NaN'},
])
def test_invalid_edits_roll_back_balances(client, db_session, payload):
    exchange = _account(db_session, 'Exchange', AccountType.EXCHANGE, balance=1000)
    bank = _account(db_session, 'Bank', AccountType.BANK)
    transaction_id = _transfer(client, exchange, bank, 400)
    response = client.patch(f'/api/finance/transactions/{transaction_id}', json=payload)
    assert response.status_code in (400, 422), response.text
    db_session.refresh(bank)
    db_session.refresh(exchange)
    assert (exchange.balance, bank.balance) == (600, 400)
    assert client.get('/api/finance/summary?currency=IRR').json()['total_income'] == 400


def test_edit_transfer_rejects_destination_with_other_currency(client, db_session):
    exchange = _account(db_session, 'Exchange', AccountType.EXCHANGE, balance=1000)
    bank = _account(db_session, 'Bank', AccountType.BANK)
    dollar_bank = _account(db_session, 'Dollar bank', AccountType.BANK, Currency.USDT)
    transaction_id = _transfer(client, exchange, bank, 400)
    response = client.patch(f'/api/finance/transactions/{transaction_id}', json={
        'to_account_id': dollar_bank.id,
    })
    assert response.status_code == 400, response.text
    for account in (exchange, bank, dollar_bank):
        db_session.refresh(account)
    assert (exchange.balance, bank.balance, dollar_bank.balance) == (600, 400, 0)


def test_wallet_defaults_to_its_account_currency(db_session):
    bank = _account(db_session, 'Bank', AccountType.BANK)
    transaction = WalletService.post(
        db_session, account_id=bank.id, type=TransactionType.DEPOSIT,
        amount=100, date=datetime(2026, 10, 2, tzinfo=timezone.utc),
    )
    assert transaction.currency == Currency.IRR
