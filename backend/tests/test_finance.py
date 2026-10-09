"""تست‌های endpointها و محاسبات مالی (فاز ۱۲)"""
from datetime import datetime, timezone

import pytest

from app.api import finance
from app.models.strategy import Trade, TradeSource, TestType
from app.services.analysis_service import AnalysisService


def _conversion_accounts(db, destination_currency="USDT"):
    from app.models.finance import FinancialAccount, AccountType, Currency
    accounts = [FinancialAccount(name="source", type=AccountType.BANK, currency=Currency.IRR, balance=0),
                FinancialAccount(name="destination", type=AccountType.EXCHANGE, currency=Currency(destination_currency), balance=0)]
    db.add_all(accounts)
    db.commit()
    return accounts


def _conversion_payload(accounts, **changes):
    source, destination = accounts
    return dict(account_id=destination.id, from_account_id=source.id,
                to_account_id=destination.id, type="convert", amount=600000,
                to_amount=10, **changes)


@pytest.mark.parametrize("balance", [0, 25])
def test_create_pair_creates_two_accounts(db_session, balance):
    from app.models.finance import FinancialAccount, FinancialTransaction
    result = finance.create_account(finance.AccountCreate(name=" Bit24 ", type="exchange", create_pair=True, balance=balance), db_session)
    assert [a["name"] for a in result["accounts"]] == ["Bit24_IRR", "Bit24_USDT"]
    assert [a.balance for a in db_session.query(FinancialAccount).all()] == [balance, balance]
    assert db_session.query(FinancialTransaction).count() == (2 if balance else 0)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        finance.create_account(finance.AccountCreate(name="Bit24", type="exchange", create_pair=True), db_session)
    assert exc.value.status_code == 409


def test_convert_debits_and_credits(db_session):
    from app.models.finance import FinancialTransaction
    from app.services.wallet_service import WalletService
    accounts = _conversion_accounts(db_session)
    result = finance.create_transaction(finance.TransactionCreate(**_conversion_payload(accounts)), db_session)
    tx = db_session.get(FinancialTransaction, result["id"])
    assert [a.balance for a in accounts] == [-600000, 10]
    assert all(WalletService.reconcile(db_session, a.id)["is_balanced"] for a in accounts)
    assert WalletService.ledger(db_session, accounts[1].id)[0]["currency"] == "USDT"
    assert WalletService.ledger(db_session, accounts[1].id)[0]["amount"] == 10
    assert WalletService.deltas(tx) == {accounts[0].id: -600000, accounts[1].id: 10}
    finance.update_transaction(tx.id, finance.TransactionUpdate(amount=300000, to_amount=5), db_session)
    assert [a.balance for a in accounts] == [-300000, 5]
    finance.delete_transaction(tx.id, db_session)
    assert [a.balance for a in accounts] == [0, 0]


def test_convert_rejects_same_currency(db_session):
    from fastapi import HTTPException
    accounts = _conversion_accounts(db_session, "IRR")
    with pytest.raises(HTTPException):
        finance.create_transaction(finance.TransactionCreate(**_conversion_payload(accounts)), db_session)


def test_convert_rejects_same_account(db_session):
    from fastapi import HTTPException
    accounts = _conversion_accounts(db_session)
    payload = _conversion_payload(accounts)
    payload["to_account_id"] = accounts[0].id
    with pytest.raises(HTTPException):
        finance.create_transaction(finance.TransactionCreate(**payload), db_session)


def test_convert_requires_to_amount(db_session):
    from fastapi import HTTPException
    payload = _conversion_payload(_conversion_accounts(db_session))
    del payload["to_amount"]
    with pytest.raises(HTTPException):
        finance.create_transaction(finance.TransactionCreate(**payload), db_session)


def test_convert_currency_derived_from_accounts(db_session):
    from app.models.finance import FinancialTransaction, Currency
    from fastapi import HTTPException
    accounts = _conversion_accounts(db_session)
    payload = _conversion_payload(accounts)
    result = finance.create_transaction(finance.TransactionCreate(**payload), db_session)
    tx = db_session.get(FinancialTransaction, result["id"])
    assert (tx.currency, tx.to_currency) == (Currency.IRR, Currency.USDT)
    payload["currency"] = "USDT"
    with pytest.raises(HTTPException):
        finance.create_transaction(finance.TransactionCreate(**payload), db_session)


def test_transfer_still_works_for_same_currency(db_session):
    accounts = _conversion_accounts(db_session, "IRR")
    payload = _conversion_payload(accounts)
    payload.update(type="transfer", currency="IRR", amount=10)
    del payload["to_amount"]
    finance.create_transaction(finance.TransactionCreate(**payload), db_session)
    assert [a.balance for a in accounts] == [-10, 10]


def _make_trade(pnl, *, r=None, day=1, version_id=None):
    return Trade(
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 3, day, 10, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 3, day, 11, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2000.0,
        size=1.0,
        pnl=pnl,
        r_multiple=r,
        commission=0.0,
        swap=0.0,
        source=TradeSource.MANUAL,
        test_type=TestType.BACKTEST,
        version_id=version_id,
    )


def _ver(db, name="fv"):
    """نسخه‌ی استراتژی برای معاملات تست (version_id اکنون اجباری است — فاز ۲۸)"""
    from app.models.strategy import Strategy, StrategyVersion
    s = Strategy(name=f"S-{name}")
    db.add(s)
    db.flush()
    v = StrategyVersion(strategy_id=s.id, version_name=name)
    db.add(v)
    db.flush()
    return v


def _pta(db, label="PTA", balance=0.0):
    """حساب معاملاتی شخصی (فاز ۲۸)"""
    from app.models.trading import Broker, PersonalTradingAccount
    from app.models.finance import Currency
    broker = Broker(name=f"Broker-{label}")
    db.add(broker)
    db.flush()
    pta = PersonalTradingAccount(
        broker_id=broker.id, account_number=f"ACC-{label}", account_label=label,
        currency=Currency.USD, initial_balance=balance, current_balance=balance,
    )
    db.add(pta)
    db.flush()
    return pta


# ═════════════════════════════════════════════
# تاریخ شمسی
# ═════════════════════════════════════════════
def _real_eligibility_trade(db, kind, pnl):
    from app.models.finance import Currency
    from app.models.prop import PropAccount, PropFirm, PropStage, StageType

    version = _ver(db, "eligibility")
    trade = _make_trade(pnl, version_id=version.id)
    if kind == "broker":
        account = _pta(db, "eligibility")
        account.currency = Currency.USDT
        trade.test_type = TestType.REAL_PERSONAL
        trade.personal_trading_account_id = account.id
    else:
        firm = PropFirm(name="Eligibility firm")
        db.add(firm)
        db.flush()
        account = PropAccount(prop_firm_id=firm.id, account_label="Eligibility", currency=Currency.USDT)
        db.add(account)
        db.flush()
        stage = PropStage(prop_account_id=account.id, stage_type=StageType.FUNDED_REAL)
        db.add(stage)
        db.flush()
        trade.test_type = TestType.REAL_PROP
        trade.prop_stage_id = stage.id
    db.add(trade)
    return trade


@pytest.mark.parametrize("kind", ["broker", "prop_stage_3"])
def test_finance_excludes_open_trades_with_pnl(client, db_session, kind):
    from app.services.finance_metrics import funded_pnl

    closed = _real_eligibility_trade(db_session, kind, 100.0)
    opened = _make_trade(500.0, version_id=closed.version_id)
    opened.test_type = closed.test_type
    opened.personal_trading_account_id = closed.personal_trading_account_id
    opened.prop_stage_id = closed.prop_stage_id
    opened.close_time = None
    opened.close_price = None
    db_session.add(opened)
    db_session.commit()

    if kind == "prop_stage_3":
        assert funded_pnl(db_session) == 100.0
    response = client.get("/api/finance/real-pnl", params={"currency": "USDT"})
    assert response.status_code == 200, response.text
    assert response.json()[kind] == {"pnl": 100.0, "trades": 1}
    assert response.json()["total"] == {"pnl": 100.0, "trades": 1}


@pytest.mark.parametrize("kind", ["broker", "prop_stage_3"])
@pytest.mark.parametrize("swap", [0.0, -2.0])
def test_finance_includes_closed_with_null_pnl(client, db_session, kind, swap):
    from app.services.finance_metrics import funded_pnl

    trade = _real_eligibility_trade(db_session, kind, None)
    trade.commission = -1.0
    trade.swap = swap
    db_session.commit()
    expected = -1.0 + swap

    if kind == "prop_stage_3":
        assert funded_pnl(db_session) == expected
    response = client.get("/api/finance/real-pnl", params={"currency": "USDT"})
    assert response.status_code == 200, response.text
    assert response.json()[kind] == {"pnl": expected, "trades": 1}
    assert response.json()["total"] == {"pnl": expected, "trades": 1}


def test_real_summary_filters_on_close_time(client, db_session):
    from app.models.finance import Currency

    version = _ver(db_session, "real-summary-dates")
    account = _pta(db_session, "real-summary-dates")
    account.currency = Currency.USDT
    for day, pnl in [(1, 50.0), (2, 100.0), (3, -20.0), (4, 1000.0)]:
        trade = _make_trade(pnl, day=day, version_id=version.id)
        trade.test_type = TestType.REAL_PERSONAL
        trade.personal_trading_account_id = account.id
        trade.open_time = datetime(2025, 2, 28, tzinfo=timezone.utc)
        if day == 3:
            trade.close_time = datetime(2025, 3, 3, 23, 59, 59, 999999, tzinfo=timezone.utc)
        if day == 4:
            trade.close_time = None
        db_session.add(trade)
    db_session.commit()

    for dates, expected_net, expected_count in [
        ({}, 130.0, 3),
        ({"date_from": "2025-03-02"}, 80.0, 2),
        ({"date_to": "2025-03-02"}, 150.0, 2),
        ({"date_from": "2025-03-02", "date_to": "2025-03-03"}, 80.0, 2),
        ({"date_from": "2025-03-04"}, 0.0, 0),
    ]:
        response = client.get("/api/finance/real-summary", params={"currency": "USDT", **dates})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["net_pnl"] == expected_net
        assert body["total_trades"] == expected_count
        assert body["scope"] == "FUNDED_REAL + REAL_PERSONAL"
        if dates == {"date_from": "2025-03-02", "date_to": "2025-03-03"}:
            assert body["sparkline"] == [100.0, 80.0]
            assert body["max_dd"] == 20.0


def test_gregorian_to_jalali_known_dates():
    assert finance._gregorian_to_jalali(2025, 3, 21) == (1404, 1, 1)
    assert finance._gregorian_to_jalali(2026, 3, 21) == (1405, 1, 1)
    assert finance._gregorian_to_jalali(2025, 1, 1) == (1403, 10, 12)


def test_jalali_round_trip():
    for g in [(2024, 2, 29), (2025, 12, 31), (2026, 1, 1), (2030, 6, 15)]:
        j = finance._gregorian_to_jalali(*g)
        assert finance._jalali_to_gregorian(*j) == g


def test_jalali_months_count():
    assert len(finance.JALALI_MONTHS) == 12
    assert finance.JALALI_MONTHS[0] == "فروردین"
    assert finance.JALALI_MONTHS[-1] == "اسفند"


# ═════════════════════════════════════════════
# محاسبات پایه (Win Rate / Profit Factor)
# ═════════════════════════════════════════════
def test_basic_metrics_win_rate_and_profit_factor():
    svc = AnalysisService(db=None)
    trades = [_make_trade(100), _make_trade(-50), _make_trade(50)]
    m = svc._calculate_basic_metrics(trades)
    assert m["total_trades"] == 3
    assert m["win_rate"] == pytest.approx(66.67, abs=0.01)
    assert m["profit_factor"] == pytest.approx(3.0)
    assert m["net_pnl"] == pytest.approx(100.0)
    assert m["largest_win"] == pytest.approx(100.0)
    assert m["largest_loss"] == pytest.approx(50.0)
    assert m["max_consecutive_losses"] == 1


def test_profit_factor_edge_cases():
    svc = AnalysisService(db=None)
    assert svc._profit_factor(100, 0) == 999.0
    assert svc._profit_factor(0, 0) == 0.0
    assert svc._profit_factor(150, 50) == pytest.approx(3.0)


@pytest.mark.parametrize("pnls, expected", [
    ([], 0.0),
    ([0.0], 0.0),
    ([100.0], 999.0),
    ([-50.0], 0.0),
    ([150.0, -50.0], 3.0),
    ([1000.0, -1.0], 1000.0),
])
def test_real_summary_profit_factor_contract(client, db_session, pnls, expected):
    from app.models.finance import Currency
    from app.services import metrics

    version = _ver(db_session, "pf-contract")
    account = _pta(db_session, "pf-contract")
    account.currency = Currency.USDT
    trades = []
    for pnl in pnls:
        trade = _make_trade(pnl, version_id=version.id)
        trade.test_type = TestType.REAL_PERSONAL
        trade.personal_trading_account_id = account.id
        db_session.add(trade)
        trades.append(trade)
    db_session.commit()

    response = client.get("/api/finance/real-summary", params={"currency": "USDT"})
    assert response.status_code == 200, response.text
    assert response.json()["profit_factor"] == expected
    assert metrics.calculate_basic_metrics(trades)["profit_factor"] == expected
    assert AnalysisService(db_session)._calculate_basic_metrics(trades)["profit_factor"] == expected


def test_commission_and_swap_reduce_net_pnl():
    svc = AnalysisService(db=None)
    t = _make_trade(100)
    t.commission = -10.0
    t.swap = -5.0
    m = svc._calculate_basic_metrics([t])
    assert m["net_pnl"] == pytest.approx(85.0)


# ═════════════════════════════════════════════
# Endpointها
# ═════════════════════════════════════════════
def test_summary_empty(client):
    r = client.get("/api/finance/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total_income"] == 0
    assert body["transaction_count"] == 0


def test_create_account_and_list(client):
    r = client.post("/api/finance/accounts", json={
        "name": "Main", "type": "bank", "currency": "USD", "balance": 1000,
    })
    assert r.status_code == 200
    accounts = client.get("/api/finance/accounts").json()
    assert len(accounts) == 1
    assert accounts[0]["name"] == "Main"


@pytest.mark.parametrize("tx_type, expected_income", [
    ("deposit", 0),
    ("external_income", 500),
])
def test_create_transaction_and_filter(client, tx_type, expected_income):
    acc_id = client.post("/api/finance/accounts", json={"name": "A", "type": "bank"}).json()["id"]
    tx = client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 500, "type": tx_type,
    })
    assert tx.status_code == 200

    txs = client.get("/api/finance/transactions").json()
    assert len(txs) == 1
    assert txs[0]["type"] == tx_type

    filtered = client.get("/api/finance/transactions", params={"account_id": acc_id}).json()
    assert len(filtered) == 1
    assert client.get("/api/finance/summary").json()["total_income"] == expected_income


def test_reports_monthly(client):
    acc_id = client.post("/api/finance/accounts", json={"name": "A", "type": "bank"}).json()["id"]
    client.post("/api/finance/transactions", json={"account_id": acc_id, "amount": 1000, "type": "profit"})
    client.post("/api/finance/transactions", json={"account_id": acc_id, "amount": 400, "type": "loss"})

    body = client.get("/api/finance/reports/monthly").json()
    assert len(body["months"]) == 12
    assert body["months"][0]["month_name"] == "فروردین"
    assert sum(m["income"] for m in body["months"]) == 1000
    assert sum(m["expense"] for m in body["months"]) == 400


def test_reports_category_breakdown(client):
    acc_id = client.post("/api/finance/accounts", json={"name": "A", "type": "bank"}).json()["id"]
    client.post("/api/finance/transactions", json={"account_id": acc_id, "amount": 300, "type": "external_income"})

    body = client.get("/api/finance/reports/category-breakdown").json()
    assert body["total_income"] == 300
    assert len(body["items"]) >= 1
    assert body["items"][0]["percent"] == pytest.approx(100.0)


def test_reports_profit_loss(client):
    acc_id = client.post("/api/finance/accounts", json={"name": "A", "type": "bank"}).json()["id"]
    client.post("/api/finance/transactions", json={"account_id": acc_id, "amount": 1000, "type": "profit"})
    client.post("/api/finance/transactions", json={"account_id": acc_id, "amount": 400, "type": "loss"})

    body = client.get("/api/finance/reports/profit-loss").json()
    assert body["net_profit"] == 600
    assert body["margin"] == pytest.approx(60.0)
    assert len(body["yearly"]) == 1
    assert body["yearly"][0]["net"] == 600


def test_reports_account_comparison(client):
    acc_id = client.post("/api/finance/accounts", json={"name": "A", "type": "bank"}).json()["id"]
    client.post("/api/finance/transactions", json={"account_id": acc_id, "amount": 1000, "type": "profit"})
    client.post("/api/finance/transactions", json={"account_id": acc_id, "amount": 400, "type": "loss"})

    rows = client.get("/api/finance/reports/account-comparison").json()
    assert len(rows) == 1
    assert rows[0]["total_income"] == 1000
    assert rows[0]["total_expense"] == 400
    assert rows[0]["net"] == 600


# ═════════════════════════════════════════════
# فاز ۲۲ — گزارش‌های مالی جدید
# ═════════════════════════════════════════════
from app.models.finance import FinancialAccount, AccountType, Currency, FinancialTransaction, TransactionType  # noqa: E402,F401
from app.models.prop import PropFirm, PropAccount, PropStage, StageType, StageStatus  # noqa: E402


def _seed_funded_stage(db):
    """ساخت یک مرحلهٔ FUNDED_REAL برای تست‌ها (فاز ۲۸: بدون پل مالی)"""
    firm = PropFirm(name="Test Firm")
    db.add(firm)
    db.flush()
    prop_acc = PropAccount(prop_firm_id=firm.id, account_label="A1")
    db.add(prop_acc)
    db.flush()
    stage = PropStage(
        prop_account_id=prop_acc.id,
        stage_type=StageType.FUNDED_REAL,
        status=StageStatus.ACTIVE,
    )
    db.add(stage)
    db.flush()
    return stage, prop_acc


def test_spendable_assets_empty(client):
    body = client.get("/api/finance/spendable-assets").json()
    assert body["prop_stage_3"]["amount"] == 0
    assert body["bank"]["currency"] == "IRR"
    assert body["broker"]["currency"] == "USDT"
    assert body["total"] == {"usdt": 0.0, "irr": 0.0}


def test_spendable_assets(client, db_session):
    client.post("/api/finance/accounts", json={
        "name": "Bank", "type": "bank", "currency": "IRR", "balance": 100000000,
    })
    client.post("/api/finance/accounts", json={
        "name": "Ex", "type": "exchange", "currency": "USD", "balance": 200,
    })
    client.post("/api/finance/accounts", json={
        "name": "TW", "type": "crypto_wallet", "currency": "USD", "balance": 100,
    })

    # فاز ۲۸: موجودی بروکر از حساب معاملاتی شخصی (نه حساب مالی)
    _pta(db_session, label="B", balance=3000.0)

    # مرحلهٔ پراپ FUNDED + معاملهٔ REAL_PROP با سود 500
    stage, _prop_acc = _seed_funded_stage(db_session)
    v = _ver(db_session, name="spend")
    prop_trade = _make_trade(500, version_id=v.id)
    prop_trade.prop_stage_id = stage.id
    prop_trade.test_type = TestType.REAL_PROP
    db_session.add(prop_trade)
    db_session.commit()

    body = client.get("/api/finance/spendable-assets").json()
    # فاز ۴۴.۳: prop_stage_3 اکنون سهمِ کاربر از سود = ۵۰۰ × ۸۰٪ = ۴۰۰
    # (پیش‌تر سود کامل ۵۰۰ بدون اعمال profit_share شمرده می‌شد.)
    assert body["prop_stage_3"]["amount"] == 400
    assert body["broker"]["amount"] == 3000
    assert body["exchange"]["amount"] == 200
    # فاز ۳۹ (رفع G6): سبد trust_wallet از TRUST_WALLET پر می‌شود و کیف‌پول دیجیتال
    # سبد مستقل خودش را دارد. پیش از فاز ۳۹ این مقدار اشتباهاً ۱۰۰ بود (باگ G6).
    assert body["trust_wallet"]["amount"] == 0
    assert body["crypto_wallet"]["amount"] == 100
    assert body["bank"]["amount"] == 100000000
    assert body["total"]["usdt"] == 3300
    assert body["total"]["irr"] == 100000000


def test_real_pnl(client, db_session):
    pta = _pta(db_session, label="B")
    stage, _ = _seed_funded_stage(db_session)
    v = _ver(db_session, name="realpnl")

    prop_trade = _make_trade(100, version_id=v.id)
    prop_trade.prop_stage_id = stage.id
    prop_trade.test_type = TestType.REAL_PROP
    prop_trade.commission = -10.0  # net = 90
    broker_trade = _make_trade(300, version_id=v.id)
    broker_trade.test_type = TestType.REAL_PERSONAL
    broker_trade.personal_trading_account_id = pta.id
    db_session.add_all([prop_trade, broker_trade])
    db_session.commit()

    body = client.get("/api/finance/real-pnl").json()
    assert body["prop_stage_3"] == {"pnl": 90.0, "trades": 1}
    assert body["broker"] == {"pnl": 300.0, "trades": 1}
    assert body["total"] == {"pnl": 390.0, "trades": 2}


def test_net_profit(client, db_session):
    bank_id = client.post("/api/finance/accounts", json={
        "name": "B", "type": "bank", "currency": "USD",
    }).json()["id"]
    pta = _pta(db_session, label="B")
    v = _ver(db_session, name="netprofit")
    broker_trade = _make_trade(800, version_id=v.id)
    broker_trade.test_type = TestType.REAL_PERSONAL
    broker_trade.personal_trading_account_id = pta.id
    db_session.add(broker_trade)
    # هزینه‌ها: کارمزد 15 + خرید 100 (از حساب مالی بانکی)
    for amt, typ in [(15, "fee"), (100, "purchase")]:
        client.post("/api/finance/transactions", json={
            "account_id": bank_id, "amount": amt, "type": typ,
        })
    db_session.commit()

    body = client.get("/api/finance/net-profit").json()
    assert body["real_pnl"] == 800.0
    assert body["expenses"] == 115.0
    assert body["net_profit"] == 685.0


def test_money_flow(client):
    bank_id = client.post("/api/finance/accounts", json={"name": "Bank", "type": "bank", "currency": "IRR"}).json()["id"]
    # فاز ۴۵.۵: ارز حساب باید با ارز تراکنش هم‌خوان باشد ⇒ exchange هم IRR است
    exch_id = client.post("/api/finance/accounts", json={"name": "Ex", "type": "exchange", "currency": "IRR"}).json()["id"]
    client.post("/api/finance/transactions", json={
        "account_id": exch_id, "amount": 100000000, "currency": "IRR", "type": "withdrawal",
        "from_account_id": bank_id, "to_account_id": exch_id,
    })
    body = client.get("/api/finance/money-flow").json()
    assert len(body["flows"]) == 1
    flow = body["flows"][0]
    assert flow["from"] == "bank"
    assert flow["to"] == "exchange"
    assert flow["amount"] == 100000000
    assert flow["currency"] == "IRR"
    assert flow["type"] == "withdrawal"


def test_expenses_breakdown(client):
    # فاز ۲۸: FinancialAccount دیگر type=prop ندارد؛ تفکیک پراپ بر اساس متن تراکنش انجام می‌شود.
    prop_id = client.post("/api/finance/accounts", json={"name": "Prop", "type": "bank"}).json()["id"]
    exch_id = client.post("/api/finance/accounts", json={"name": "Ex", "type": "exchange"}).json()["id"]
    bank_id = client.post("/api/finance/accounts", json={"name": "Bank", "type": "bank"}).json()["id"]
    client.post("/api/finance/transactions", json={"account_id": prop_id, "amount": 50, "type": "purchase", "description": "خرید پراپ"})
    client.post("/api/finance/transactions", json={"account_id": prop_id, "amount": 30, "type": "fee", "description": "اشتراک پراپ"})
    client.post("/api/finance/transactions", json={"account_id": exch_id, "amount": 15, "type": "fee", "description": "کارمزد صرافی"})
    client.post("/api/finance/transactions", json={"account_id": bank_id, "amount": 20, "type": "fee", "description": "سایر"})

    body = client.get("/api/finance/expenses").json()
    assert body["prop_purchase"] == 50
    assert body["prop_subscription"] == 30
    assert body["exchange_fee"] == 15
    assert body["other"] == 20
    assert body["total"] == 115


def test_money_cycle(client):
    bank_id = client.post("/api/finance/accounts", json={"name": "Bank", "type": "bank", "balance": 3000}).json()["id"]
    exch_id = client.post("/api/finance/accounts", json={"name": "Ex", "type": "exchange", "balance": 0}).json()["id"]
    client.post("/api/finance/transactions", json={"account_id": bank_id, "amount": 5000, "type": "deposit"})
    client.post("/api/finance/transactions", json={"account_id": bank_id, "amount": 2000, "type": "withdrawal"})
    client.post("/api/finance/transactions", json={"account_id": exch_id, "amount": 3000, "type": "transfer"})
    client.post("/api/finance/transactions", json={
        "account_id": exch_id, "amount": 4000, "type": "transfer",
        "from_account_id": bank_id, "to_account_id": exch_id,
    })

    body = client.get("/api/finance/money-cycle").json()
    assert body["total_deposits"] == 5000
    assert body["total_withdrawals"] == 2000
    assert body["total_exchanges"] == 7000
    assert body["total_transfers"] == 4000
    # فاز ۳۹ (رفع G1): تراکنش‌ها دیگر بی‌اثر نیستند ⇒ موجودی واقعی کیف‌پول‌ها:
    #   bank = 3000 + 5000 (deposit) − 2000 (withdrawal) − 4000 (transfer out) = 2000
    #   exch = 0 + 4000 (transfer in)                                          = 4000
    #   (انتقال یک‌طرفهٔ ۳۰۰۰ موجودی را تغییر نمی‌دهد — تبدیل بیرون از نرم‌افزار)
    # پیش از فاز ۳۹ این مقدار ۳۰۰۰ بود چون هیچ تراکنشی موجودی را تغییر نمی‌داد.
    assert body["current_balance"] == 6000


def test_financial_calendar(client, db_session):
    v = _ver(db_session, name="cal")
    trade = _make_trade(50, day=15, version_id=v.id)
    trade2 = _make_trade(30, day=15, version_id=v.id)
    db_session.add_all([trade, trade2])
    acc_id = client.post("/api/finance/accounts", json={"name": "A", "type": "bank"}).json()["id"]
    client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 1000, "type": "deposit",
        "date": "2025-03-15T10:00:00+00:00",
    })
    db_session.commit()

    body = client.get("/api/finance/financial-calendar").json()
    assert len(body["days"]) == 1
    day = body["days"][0]
    # 2025-03-15 میلادی → 1403/12/25 شمسی
    assert day["date"] == "1403/12/25"
    assert day["pnl"] == 80.0
    assert day["trades"] == 2
    assert day["deposits"] == 1000.0


def test_asset_trend(client):
    acc_id = client.post("/api/finance/accounts", json={"name": "A", "type": "bank"}).json()["id"]
    client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 1000, "type": "deposit", "date": "2025-03-15T10:00:00+00:00",
    })
    client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 200, "type": "profit", "date": "2025-03-16T10:00:00+00:00",
    })

    body = client.get("/api/finance/asset-trend").json()
    assert len(body["trend"]) == 2
    assert body["trend"][0]["total_usdt"] == 1000
    assert body["trend"][1]["total_usdt"] == 1200


def test_exchange_account_currency_enforcement(client):
    """یک حساب صرافی ⋯ ارز تراکنش باید با ارز حساب یکسان باشد."""
    acc_id = client.post("/api/finance/accounts", json={"name": "A", "type": "exchange", "currency": "IRR"}).json()["id"]
    # تراکنش با ارز یکسان (IRR) ⇒ موفق
    r = client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 100000000, "currency": "IRR", "type": "transfer",
        "date": "2025-03-15T10:00:00+00:00",
    })
    assert r.status_code == 200, r.text
    # تراکنش با ارز متفاوت ⇒ ۴۰۰
    r = client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 1000, "currency": "USDT", "type": "transfer",
        "date": "2025-03-15T11:00:00+00:00",
    })
    assert r.status_code == 400
    assert "ارز" in r.json()["detail"]


@pytest.mark.parametrize(
    "source_type,destination_type,tx_type,expected_flow",
    [
        ("bank", "exchange", "transfer", "expense"),
        ("exchange", "bank", "transfer", "income"),
        ("crypto_wallet", "bank", "transfer", "income"),
        ("bank", "crypto_wallet", "transfer", "expense"),
        ("bank", "bank", "transfer", "none"),
    ],
)
def test_transfer_cash_flow_by_account_direction(
    client, db_session, source_type, destination_type, tx_type, expected_flow
):
    from app.models.finance import FinancialAccount, FinancialTransaction

    source_id = client.post("/api/finance/accounts", json={
        "name": "Source", "type": source_type, "currency": "USDT",
    }).json()["id"]
    destination_id = client.post("/api/finance/accounts", json={
        "name": "Destination", "type": destination_type, "currency": "USDT",
    }).json()["id"]
    response = client.post("/api/finance/transactions", json={
        "account_id": destination_id, "from_account_id": source_id,
        "to_account_id": destination_id, "amount": 25, "type": tx_type,
    })

    assert response.status_code == 200, response.text
    tx = db_session.get(FinancialTransaction, response.json()["id"])
    assert tx.cash_flow.value == expected_flow


@pytest.mark.parametrize("account_type,expected_flow", [("bank", "income"), ("crypto_wallet", "none")])
def test_external_income_cash_flow_depends_on_bank_destination(
    client, db_session, account_type, expected_flow
):
    from app.models.finance import FinancialTransaction

    account_id = client.post("/api/finance/accounts", json={
        "name": "Income destination", "type": account_type, "currency": "USDT",
    }).json()["id"]
    response = client.post("/api/finance/transactions", json={
        "account_id": account_id, "amount": 25, "type": "external_income",
    })

    assert response.status_code == 200, response.text
    tx = db_session.get(FinancialTransaction, response.json()["id"])
    assert tx.cash_flow.value == expected_flow

