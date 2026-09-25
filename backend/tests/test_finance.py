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

