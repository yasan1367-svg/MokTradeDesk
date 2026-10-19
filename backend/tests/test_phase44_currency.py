"""تست‌های فاز ۴۴.۵ — جداکردن ارزها (IRR و USD نباید با هم جمع شوند)."""


def _seed_currencies(client):
    """یک حساب USD و یک حساب IRR + واریز ۱۰۰۰$ و ۵٬۰۰۰٬۰۰۰ ریال."""
    usd_acc = client.post("/api/finance/accounts", json={
        "name": "USD-Bank", "type": "bank", "currency": "USD", "balance": 0,
    }).json()["id"]
    irr_acc = client.post("/api/finance/accounts", json={
        "name": "IRR-Bank", "type": "bank", "currency": "IRR", "balance": 0,
    }).json()["id"]
    client.post("/api/finance/transactions", json={
        "account_id": usd_acc, "amount": 1000, "currency": "USD", "type": "deposit",
    })
    client.post("/api/finance/transactions", json={
        "account_id": irr_acc, "amount": 5_000_000, "currency": "IRR", "type": "deposit",
    })
    return usd_acc, irr_acc


def test_summary_groups_by_currency(client):
    _seed_currencies(client)

    body = client.get("/api/finance/summary").json()
    # پیش‌فرض USD — ریال نباید در عدد دلاری بیاید
    assert body["total_income"] == 1000
    assert body["by_currency"]["USDT"]["total_income"] == 1000
    assert body["by_currency"]["IRR"]["total_income"] == 5_000_000
    assert body["currency"] == "USDT"

    irr = client.get("/api/finance/summary?currency=IRR").json()
    assert irr["total_income"] == 5_000_000


def test_cashflow_groups_by_currency(client):
    _seed_currencies(client)

    usd = client.get("/api/finance/charts/cashflow").json()
    assert sum(m["income"] for m in usd) == 1000

    irr = client.get("/api/finance/charts/cashflow?currency=IRR").json()
    assert sum(m["income"] for m in irr) == 5_000_000


def test_money_cycle_groups_by_currency(client):
    _seed_currencies(client)

    body = client.get("/api/finance/money-cycle").json()
    assert body["total_deposits"] == 1000
    assert body["by_currency"]["IRR"]["total_deposits"] == 5_000_000

    irr = client.get("/api/finance/money-cycle?currency=IRR").json()
    assert irr["total_deposits"] == 5_000_000


def test_expenses_groups_by_currency(client):
    usd_acc, irr_acc = _seed_currencies(client)
    client.post("/api/finance/transactions", json={
        "account_id": usd_acc, "amount": 100, "currency": "USD", "type": "fee",
    })
    client.post("/api/finance/transactions", json={
        "account_id": irr_acc, "amount": 200_000, "currency": "IRR", "type": "fee",
    })

    body = client.get("/api/finance/expenses").json()
    assert body["total"] == 100
    assert body["by_currency"]["USDT"] == 100
    assert body["by_currency"]["IRR"] == 200_000


def test_net_profit_currency(client):
    body = client.get("/api/finance/net-profit").json()
    assert body["currency"] == "USDT"
    assert set(body["by_currency"]) == {"USDT", "IRR"}


def test_withdrawals_stats_currency(client):
    body = client.get("/api/finance/withdrawals/stats").json()
    assert body["currency"] == "USDT"
