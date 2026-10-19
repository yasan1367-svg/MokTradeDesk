"""تست‌های Phase 36 — Performance & Query Optimization.

پوشش:
- وجود ایندکس‌های درخواستی (trades/transactions)
- ارزیابی گروهی پراپ ⇒ تعداد کوئری ثابت (رفع N+1)
- لیست تراکنش‌های مالی ⇒ بدون N+1 (joinedload)
- Pagination در تراکنش‌ها و برداشت‌های پراپ
"""
from datetime import datetime, timezone

from sqlalchemy import event, inspect

from app.models.prop import PropAccount, PropFirm, PropStage, StageStatus, StageType
from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource
from app.services.prop_rule_engine import PropRuleEngine


class QueryCounter:
    """شمارندهٔ کوئری‌های SQL اجراشده روی یک engine (فاز ۳۶)."""

    def __init__(self, engine):
        self.engine = engine
        self.statements = []

    def __enter__(self):
        event.listen(self.engine, "before_cursor_execute", self._on)
        return self

    def __exit__(self, *exc):
        event.remove(self.engine, "before_cursor_execute", self._on)

    def _on(self, conn, cursor, statement, params, context, executemany):
        self.statements.append(statement)

    @property
    def count(self) -> int:
        return len(self.statements)


def _version(db, name="v1"):
    s = Strategy(name=f"S-{name}")
    db.add(s)
    db.flush()
    v = StrategyVersion(strategy_id=s.id, version_name=name)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _trade(db, pnl, day, stage_id, version_id):
    db.add(Trade(
        symbol="XAUUSD", direction="buy",
        open_time=datetime(2025, 1, day, 9, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, day, 10, 0, tzinfo=timezone.utc),
        open_price=2000.0, close_price=2001.0, size=1.0, pnl=pnl,
        source=TradeSource.MANUAL, test_type=TestType.REAL_PROP,
        prop_stage_id=stage_id, version_id=version_id,
    ))


def _stage(db, version_id, label, trades=(("100", 1),)):
    firm = PropFirm(name=f"F-{label}")
    db.add(firm)
    db.flush()
    acc = PropAccount(prop_firm_id=firm.id, account_label=label)
    db.add(acc)
    db.flush()
    stage = PropStage(
        prop_account_id=acc.id, stage_type=StageType.FUNDED_REAL,
        status=StageStatus.ACTIVE, initial_balance=10000.0,
        profit_target=1000.0, max_daily_dd=500.0, max_total_dd=1000.0,
        min_trading_days=1, profit_share_percentage=80.0, total_withdrawn=0.0,
    )
    db.add(stage)
    db.flush()
    for pnl, day in trades:
        _trade(db, float(pnl), day, stage.id, version_id)
    db.commit()
    db.refresh(stage)
    return stage


# ═════════════════════════════════════════════
# ایندکس‌ها
# ═════════════════════════════════════════════
def test_phase36_indexes_exist(db_session):
    insp = inspect(db_session.get_bind())

    trades_idx = {i["name"] for i in insp.get_indexes("trades")}
    assert {
        "ix_trades_prop_stage_id",
        "ix_trades_personal_trading_account_id",
        "ix_trades_close_time",
    } <= trades_idx

    tx_idx = {i["name"] for i in insp.get_indexes("transactions")}
    assert {
        "ix_transactions_account_id",
        "ix_transactions_date",
        "ix_transactions_type",
    } <= tx_idx


# ═════════════════════════════════════════════
# ارزیابی گروهی پراپ (رفع N+1)
# ═════════════════════════════════════════════
def test_bulk_evaluate_matches_single(db_session):
    v = _version(db_session)
    stages = [
        _stage(db_session, v.id, "A", trades=[("1000", 1), ("500", 2)]),
        _stage(db_session, v.id, "B", trades=[("-700", 1)]),
        _stage(db_session, v.id, "C", trades=[("200", 1)]),
    ]

    bulk = PropRuleEngine.evaluate_stages(db_session, [s.id for s in stages])

    for s in stages:
        single = PropRuleEngine.evaluate_stage(db_session, s.id)
        assert bulk[s.id]["current_profit"] == single["current_profit"]
        assert bulk[s.id]["max_daily_loss"] == single["max_daily_loss"]
        assert bulk[s.id]["max_total_dd"] == single["max_total_dd"]
        assert bulk[s.id]["trading_days"] == single["trading_days"]
        assert bulk[s.id]["overall_severity"] == single["overall_severity"]
        assert bulk[s.id]["stage_id"] == s.id


def test_bulk_evaluate_constant_query_count(db_session):
    v = _version(db_session)
    stages = [
        _stage(db_session, v.id, f"S{i}", trades=[("100", 1), ("-50", 2)])
        for i in range(5)
    ]
    # شناسه‌ها را بیرون از ناحیهٔ اندازه‌گیری استخراج می‌کنیم تا Refresh نمونه‌های
    # منقضی‌شدهٔ تست در شمارش کوئری‌های موتور محاسبه نشود.
    stage_ids = [s.id for s in stages]

    counter = QueryCounter(db_session.get_bind())
    with counter:
        PropRuleEngine.evaluate_stages(db_session, stage_ids)

    # ۲ کوئری (stages + trades) — نه ۱ + ۲×۵
    assert counter.count <= 3, "\n".join(counter.statements)


def test_bulk_evaluate_handles_missing_stage(db_session):
    bulk = PropRuleEngine.evaluate_stages(db_session, [99999])
    assert bulk[99999]["ready_to_pass"] is False
    assert "error" in bulk[99999]


def test_bulk_evaluate_empty_ids(db_session):
    assert PropRuleEngine.evaluate_stages(db_session, []) == {}


# ═════════════════════════════════════════════
# تراکنش‌های مالی — بدون N+1 + Pagination
# ═════════════════════════════════════════════
def _seed_transactions(client, n=5):
    acc_id = client.post(
        "/api/finance/accounts", json={"name": "A", "type": "bank"}
    ).json()["id"]
    cat_id = client.post(
        "/api/finance/categories", json={"name": "C", "type": "income"}
    ).json()["id"]
    for i in range(n):
        client.post("/api/finance/transactions", json={
            "account_id": acc_id, "category_id": cat_id,
            "amount": 100 + i, "type": "profit",
        })
    return acc_id


def test_transactions_list_has_no_n_plus_one(client, db_session):
    _seed_transactions(client, n=6)

    counter = QueryCounter(db_session.get_bind())
    with counter:
        r = client.get("/api/finance/transactions")

    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 6
    # account/category با JOIN بارگذاری می‌شوند ⇒ تعداد کوئری مستقل از تعداد ردیف
    assert counter.count <= 4, counter.statements
    assert all(row["account_name"] == "A" for row in rows)
    assert all(row["category_name"] == "C" for row in rows)


def test_transactions_pagination(client, db_session):
    _seed_transactions(client, n=5)

    page1 = client.get("/api/finance/transactions", params={"limit": 2}).json()
    page2 = client.get("/api/finance/transactions", params={"limit": 2, "offset": 2}).json()
    all_rows = client.get("/api/finance/transactions").json()

    assert len(page1) == 2
    assert len(page2) == 2
    assert {r["id"] for r in page1}.isdisjoint({r["id"] for r in page2})
    assert len(all_rows) == 5  # بدون limit ⇒ سازگاری کامل با قبل


def test_payouts_pagination(client, db_session):
    v = _version(db_session, "pay")
    stage = _stage(db_session, v.id, "P", trades=[("1000", 1), ("500", 2)])
    acc_id = client.post(
        "/api/finance/accounts", json={"name": "Trust", "type": "crypto_wallet"}
    ).json()["id"]

    for i in range(3):
        client.post("/api/prop/payouts", json={
            "prop_stage_id": stage.id, "amount": 100 + i,
            "destination_account_id": acc_id,
        })

    assert len(client.get("/api/prop/payouts").json()) == 3
    assert len(client.get("/api/prop/payouts", params={"limit": 1}).json()) == 1
    page2 = client.get("/api/prop/payouts", params={"limit": 1, "offset": 1}).json()
    assert len(page2) == 1

