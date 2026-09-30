"""تست‌های Phase 38 — Personal Finance Foundation.

پوشش:
- `AccountType` گسترش‌یافته (CARD / CASH / TRUST_WALLET)
- `PropAccount.currency` → `Enum(Currency)`
- `PropCost.currency` → `Enum(Currency)` و `cost_type` → `Enum(CostType)`
- ذخیرهٔ lowercase برای `cost_type` (سازگاری با دادهٔ قدیمی)
- `PropAlert.is_read` → `Boolean`
"""
from sqlalchemy import text

from app.models.finance import AccountType, Currency
from app.models.prop import CostType, PropAccount, PropAlert, PropCost


# ═════════════════════════════════════════════
# AccountType
# ═════════════════════════════════════════════
def test_account_type_new_values_added():
    values = {e.value for e in AccountType}
    assert {"bank", "exchange", "crypto_wallet"} <= values  # قبلی‌ها حفظ شدند
    assert {"card", "cash", "trust_wallet"} <= values        # فاز ۳۸


def test_account_type_works_via_api(client):
    for acc_type in ("card", "cash", "trust_wallet"):
        r = client.post("/api/finance/accounts", json={"name": f"A-{acc_type}", "type": acc_type})
        assert r.status_code == 200, r.text

    types = {a["type"] for a in client.get("/api/finance/accounts").json()}
    assert {"card", "cash", "trust_wallet"} <= types


# ═════════════════════════════════════════════
# CostType
# ═════════════════════════════════════════════
def test_cost_type_values():
    assert {e.value for e in CostType} == {
        "purchase", "reset", "addon", "data_fee", "refund", "other"
    }


def test_cost_type_column_is_enum():
    col = PropCost.__table__.c.cost_type
    assert col.nullable is False
    # SQLAlchemy Enum با values_callable ⇒ DB value = lowercase
    assert "purchase" in col.type.enums


def test_cost_type_stored_lowercase_in_db(client, db_session):
    firm = client.post("/api/prop/firms", json={"name": "FTMO"}).json()
    acc = client.post("/api/prop/accounts", json={
        "prop_firm_id": firm["id"], "account_label": "A1",
    }).json()

    r = client.post("/api/prop/costs", json={
        "prop_account_id": acc["id"], "cost_type": "RESET",  # uppercase ورودی
        "amount": 99.0, "currency": "USD", "create_transaction": False,
    })
    assert r.status_code == 200, r.text

    raw = db_session.execute(text("SELECT cost_type FROM prop_costs")).fetchall()
    assert raw == [("reset",)], raw  # lowercase ذخیره شده ✅


def test_cost_type_invalid_rejected(client):
    firm = client.post("/api/prop/firms", json={"name": "FTMO"}).json()
    acc = client.post("/api/prop/accounts", json={
        "prop_firm_id": firm["id"], "account_label": "A1",
    }).json()

    r = client.post("/api/prop/costs", json={
        "prop_account_id": acc["id"], "cost_type": "bogus",
        "amount": 10.0, "create_transaction": False,
    })
    assert r.status_code == 400
    assert "نامعتبر" in r.json()["detail"]


# ═════════════════════════════════════════════
# PropAccount.currency / PropCost.currency → Enum(Currency)
# ═════════════════════════════════════════════
def test_prop_account_currency_is_enum():
    col = PropAccount.__table__.c.currency
    assert "USD" in col.type.enums and "IRR" in col.type.enums


def test_prop_cost_currency_is_enum():
    col = PropCost.__table__.c.currency
    assert "USD" in col.type.enums and "IRR" in col.type.enums


def test_prop_account_currency_persists(client, db_session):
    firm = client.post("/api/prop/firms", json={"name": "FTMO"}).json()
    acc = client.post("/api/prop/accounts", json={
        "prop_firm_id": firm["id"], "account_label": "IRR-Acc", "currency": "IRR",
    }).json()

    row = db_session.query(PropAccount).filter(PropAccount.id == acc["id"]).first()
    assert row.currency == Currency.IRR


def test_purchase_cost_creates_typed_transaction(client, db_session):
    firm = client.post("/api/prop/firms", json={"name": "FTMO"}).json()
    acc = client.post("/api/prop/accounts", json={
        "prop_firm_id": firm["id"], "account_label": "A1",
    }).json()
    payer = client.post("/api/finance/accounts", json={
        "name": "Bank", "type": "bank", "balance": 5000,
    }).json()

    r = client.post("/api/prop/costs", json={
        "prop_account_id": acc["id"], "cost_type": "purchase",
        "amount": 540.0, "currency": "USD",
        "pay_from_account_id": payer["id"], "create_transaction": True,
    })
    assert r.status_code == 200, r.text
    assert r.json()["transaction_id"] is not None

    cost = db_session.query(PropCost).order_by(PropCost.id.desc()).first()
    assert cost.cost_type == CostType.PURCHASE
    assert cost.currency == Currency.USD

    # تراکنش مالی ثبت شد
    # فاز ۴۵.۱: ساخت حساب با موجودی اولیه حالا یک ADJUSTMENT هم می‌سازد ⇒
    # فقط تراکنش purchase را می‌سنجیم.
    txs = client.get("/api/finance/transactions").json()
    purchases = [t for t in txs if t["type"] == "purchase"]
    assert len(purchases) == 1


# ═════════════════════════════════════════════
# PropAlert.is_read → Boolean
# ═════════════════════════════════════════════
def test_prop_alert_is_read_is_boolean(db_session):
    from sqlalchemy import Boolean
    col = PropAlert.__table__.c.is_read
    assert isinstance(col.type, Boolean)


def test_prop_alert_mark_read_flow(client, db_session):
    firm = client.post("/api/prop/firms", json={"name": "FTMO"}).json()
    _ = client.post("/api/prop/accounts", json={
        "prop_firm_id": firm["id"], "account_label": "A1",
    }).json()
    stage_id = client.get("/api/prop/stages/all").json()[0]["id"]

    alert = PropAlert(prop_stage_id=stage_id, message="test alert")
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    assert alert.is_read is False

    rows = client.get("/api/prop/alerts").json()
    assert rows[0]["is_read"] is False

    r = client.patch(f"/api/prop/alerts/{alert.id}/read")
    assert r.status_code == 200

    db_session.expire_all()
    assert db_session.query(PropAlert).filter(PropAlert.id == alert.id).first().is_read is True
    assert client.get("/api/prop/alerts").json()[0]["is_read"] is True

