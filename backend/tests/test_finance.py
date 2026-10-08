"""تست‌های endpointها و محاسبات مالی (فاز ۱۲)"""
from datetime import datetime, timezone

import pytest

from app.api import finance
from app.models.strategy import Trade, TradeSource, TestType
from app.services.analysis_service import AnalysisService


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

