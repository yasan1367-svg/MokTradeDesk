"""تست‌های endpointها و محاسبات مالی (فاز ۱۲)"""
from datetime import datetime, timezone

import pytest

from app.api import finance
from app.models.strategy import Trade, TradeSource, TestType
from app.services.analysis_service import AnalysisService


def _make_trade(pnl, *, r=None, day=1):
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
    )


# ═════════════════════════════════════════════
# تاریخ شمسی
# ═════════════════════════════════════════════
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
    assert svc._profit_factor(100, 0) == 100.0
    assert svc._profit_factor(0, 0) == 0.0
    assert svc._profit_factor(150, 50) == pytest.approx(3.0)


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


def test_create_transaction_and_filter(client):
    acc_id = client.post("/api/finance/accounts", json={"name": "A", "type": "bank"}).json()["id"]
    tx = client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 500, "type": "deposit",
    })
    assert tx.status_code == 200

    txs = client.get("/api/finance/transactions").json()
    assert len(txs) == 1
    assert txs[0]["type"] == "deposit"

    filtered = client.get("/api/finance/transactions", params={"account_id": acc_id}).json()
    assert len(filtered) == 1
    assert client.get("/api/finance/summary").json()["total_income"] == 500


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
    client.post("/api/finance/transactions", json={"account_id": acc_id, "amount": 300, "type": "deposit"})

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
from app.models.finance import Account, AccountType, Currency, Transaction, TransactionType  # noqa: E402,F401
from app.models.prop import PropFirm, PropAccount, PropStage, StageType, StageStatus  # noqa: E402


def _seed_funded_stage(db, finance_account_id=None):
    """ساخت یک مرحلهٔ FUNDED_REAL برای تست‌ها"""
    firm = PropFirm(name="Test Firm")
    db.add(firm)
    db.flush()
    prop_acc = PropAccount(
        prop_firm_id=firm.id, account_label="A1", finance_account_id=finance_account_id
    )
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
    assert body["broker"]["currency"] == "USD"
    assert body["total"] == {"usd": 0.0, "irr": 0.0}


def test_spendable_assets(client, db_session):
    client.post("/api/finance/accounts", json={
        "name": "Bank", "type": "bank", "currency": "IRR", "balance": 100000000,
    })
    client.post("/api/finance/accounts", json={
        "name": "Broker", "type": "broker", "currency": "USD", "balance": 3000,
    })
    client.post("/api/finance/accounts", json={
        "name": "Ex", "type": "exchange", "currency": "USD", "balance": 200,
    })
    client.post("/api/finance/accounts", json={
        "name": "TW", "type": "crypto_wallet", "currency": "USD", "balance": 100,
    })

    # حساب مالی پراپ (PROP) متصل به مرحلهٔ FUNDED_REAL + تراکنش سود
    prop_fin_id = client.post("/api/finance/accounts", json={
        "name": "PropFin", "type": "prop", "currency": "USD", "balance": 0,
    }).json()["id"]
    _seed_funded_stage(db_session, finance_account_id=prop_fin_id)
    client.post("/api/finance/transactions", json={
        "account_id": prop_fin_id, "amount": 500, "type": "profit",
    })
    db_session.commit()

    body = client.get("/api/finance/spendable-assets").json()
    assert body["prop_stage_3"]["amount"] == 500
    assert body["broker"]["amount"] == 3000
    assert body["exchange"]["amount"] == 200
    assert body["trust_wallet"]["amount"] == 100
    assert body["bank"]["amount"] == 100000000
    assert body["total"]["usd"] == 3800
    assert body["total"]["irr"] == 100000000


def test_real_pnl(client, db_session):
    broker_id = client.post("/api/finance/accounts", json={
        "name": "B", "type": "broker", "currency": "USD",
    }).json()["id"]
    stage, _ = _seed_funded_stage(db_session)

    prop_trade = _make_trade(100)
    prop_trade.prop_stage_id = stage.id
    prop_trade.commission = -10.0  # net = 90
    broker_trade = _make_trade(300)
    broker_trade.finance_account_id = broker_id
    db_session.add_all([prop_trade, broker_trade])
    db_session.commit()

    body = client.get("/api/finance/real-pnl").json()
    assert body["prop_stage_3"] == {"pnl": 90.0, "trades": 1}
    assert body["broker"] == {"pnl": 300.0, "trades": 1}
    assert body["total"] == {"pnl": 390.0, "trades": 2}


def test_net_profit(client, db_session):
    broker_id = client.post("/api/finance/accounts", json={
        "name": "B", "type": "broker", "currency": "USD",
    }).json()["id"]
    broker_trade = _make_trade(800)
    broker_trade.finance_account_id = broker_id
    db_session.add(broker_trade)
    # هزینه‌ها: کارمزد 15 + خرید 100
    for amt, typ in [(15, "fee"), (100, "purchase")]:
        client.post("/api/finance/transactions", json={
            "account_id": broker_id, "amount": amt, "type": typ,
        })
    db_session.commit()

    body = client.get("/api/finance/net-profit").json()
    assert body["real_pnl"] == 800.0
    assert body["expenses"] == 115.0
    assert body["net_profit"] == 685.0


def test_money_flow(client):
    bank_id = client.post("/api/finance/accounts", json={"name": "Bank", "type": "bank", "currency": "IRR"}).json()["id"]
    exch_id = client.post("/api/finance/accounts", json={"name": "Ex", "type": "exchange"}).json()["id"]
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
    prop_id = client.post("/api/finance/accounts", json={"name": "Prop", "type": "prop"}).json()["id"]
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
    client.post("/api/finance/transactions", json={"account_id": exch_id, "amount": 3000, "type": "exchange"})
    client.post("/api/finance/transactions", json={
        "account_id": exch_id, "amount": 4000, "type": "exchange",
        "from_account_id": bank_id, "to_account_id": exch_id,
    })

    body = client.get("/api/finance/money-cycle").json()
    assert body["total_deposits"] == 5000
    assert body["total_withdrawals"] == 2000
    assert body["total_exchanges"] == 7000
    assert body["total_transfers"] == 4000
    assert body["current_balance"] == 3000


def test_financial_calendar(client, db_session):
    trade = _make_trade(50, day=15)
    trade2 = _make_trade(30, day=15)
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
    acc_id = client.post("/api/finance/accounts", json={"name": "A", "type": "broker"}).json()["id"]
    client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 1000, "type": "deposit", "date": "2025-03-15T10:00:00+00:00",
    })
    client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 200, "type": "profit", "date": "2025-03-16T10:00:00+00:00",
    })

    body = client.get("/api/finance/asset-trend").json()
    assert len(body["trend"]) == 2
    assert body["trend"][0]["total_usd"] == 1000
    assert body["trend"][1]["total_usd"] == 1200


def test_exchange_rates(client):
    acc_id = client.post("/api/finance/accounts", json={"name": "A", "type": "exchange"}).json()["id"]
    client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 100000000, "currency": "IRR", "type": "exchange",
        "date": "2025-03-15T10:00:00+00:00",
    })
    client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 1000, "currency": "USD", "type": "exchange",
        "date": "2025-03-15T11:00:00+00:00",
    })

    body = client.get("/api/finance/exchange-rates").json()
    assert len(body["rates"]) == 1
    assert body["rates"][0]["from"] == "IRR"
    assert body["rates"][0]["to"] == "USD"
    assert body["rates"][0]["rate"] == 100000.0

