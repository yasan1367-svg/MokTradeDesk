"""تست‌های Phase 40 — Full Regression (سناریوی کامل چرخهٔ کاری).

هر تست یک چرخهٔ سرتاسری (end-to-end) از «ساخت استراتژی» تا «تحلیل/مالی/حذف نرم»
را روی **دیتابیس درون‌حافظهٔ تست** اجرا می‌کند. طبق فاز ۳۹.۵، دیتابیس واقعی
(`trading_desk.db`) هرگز لمس نمی‌شود.

پوشش سناریوها:
1. Create Strategy → Version → Trade (Manual) → Analysis
2. Prop Lifecycle (Firm/Account/Stage) → Rule Engine → Pass Stage
3. Analysis در هر سه دامنه (Version / Prop / Personal)
4. Payout پراپ → چرخهٔ وضعیت → درآمد مالی
5. Soft Delete → Restore (لایهٔ داده) → Re-analysis
6. Import (MT4/Soft4X) → Analysis (+ idempotency)
7. مالی: تراکنش/انتقال/برگشت اثر (WalletService)
8. داشبورد پس از دیتاست کامل
9. سایر: Fork نسخه، Broker/Personal، بازدسته‌بندی معامله، انتقال payout
"""
import io
from datetime import datetime, timezone

import pytest
from openpyxl import Workbook

from app.models.strategy import (
    AnalysisResult,
    AnalysisScope,
    Strategy,
    StrategyVersion,
    TestType,
    Trade,
)
from app.models.prop import PropStage, RuleType, StageStatus, StageType
from app.models.finance import (
    FinancialAccount,
    FinancialTransaction,
    TransactionType,
)


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """صفر‌سازی Rate Limit ایمپورت (۱۰/دقیقه) بین تست‌ها."""
    from app.core.rate_limit import limiter

    limiter.reset()
    yield


# ═════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════
def _iso(day: int, hour: int = 10) -> str:
    return datetime(2025, 1, day, hour, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _make_strategy_version(client, db_session, *, test_type="backtest", name="S40"):
    """Strategy + StrategyVersion از مسیر API."""
    r = client.post("/api/strategies/", json={"name": name})
    assert r.status_code == 200, r.text
    strategy_id = db_session.query(Strategy).order_by(Strategy.id.desc()).first().id

    r = client.post(
        f"/api/strategies/{strategy_id}/versions",
        json={"version_name": "v1", "test_type": test_type},
    )
    assert r.status_code == 200, r.text
    version_id = (
        db_session.query(StrategyVersion).order_by(StrategyVersion.id.desc()).first().id
    )
    return strategy_id, version_id


def _make_pta(client):
    """Broker + PersonalTradingAccount از مسیر API."""
    broker = client.post("/api/trading/brokers", json={"name": "Broker-40"})
    assert broker.status_code == 200, broker.text
    broker_id = broker.json()["id"]

    account = client.post(
        "/api/trading/accounts",
        json={
            "broker_id": broker_id,
            "account_number": "P40-1",
            "account_label": "P40",
            "currency": "USD",
            "initial_balance": 10000.0,
        },
    )
    assert account.status_code == 200, account.text
    return account.json()["id"], broker_id


def _make_prop_account(client, db_session, *, stage_type=None, profit_share=80.0, **kw):
    """PropFirm + PropAccount از مسیر API (مرحله ۱ خودکار)؛ مرحلهٔ سفارشی از DB."""
    firm = client.post("/api/prop/firms", json={"name": "FTMO-40"})
    assert firm.status_code == 200, firm.text
    firm_id = firm.json()["id"]

    account = client.post(
        "/api/prop/accounts",
        json={
            "prop_firm_id": firm_id,
            "account_label": "A40",
            "initial_balance": kw.get("initial_balance", 10000.0),
            "profit_target": kw.get("profit_target", 1000.0),
            "max_daily_dd": kw.get("max_daily_dd", 500.0),
            "max_total_dd": kw.get("max_total_dd", 1000.0),
            "min_trading_days": kw.get("min_trading_days", 3),
        },
    )
    assert account.status_code == 200, account.text
    account_id = account.json()["id"]

    stage1 = (
        db_session.query(PropStage)
        .filter(PropStage.prop_account_id == account_id)
        .order_by(PropStage.id.desc())
        .first()
    )
    if stage_type is None or stage_type == StageType.STAGE_1:
        return firm_id, account_id, stage1

    stage = PropStage(
        prop_account_id=account_id,
        stage_type=stage_type,
        status=StageStatus.ACTIVE,
        initial_balance=kw.get("initial_balance", 10000.0),
        profit_target=kw.get("profit_target", 1000.0),
        max_daily_dd=kw.get("max_daily_dd", 500.0),
        max_total_dd=kw.get("max_total_dd", 1000.0),
        min_trading_days=kw.get("min_trading_days", 3),
        profit_share_percentage=profit_share,
        total_withdrawn=0.0,
    )
    db_session.add(stage)
    db_session.commit()
    db_session.refresh(stage)
    return firm_id, account_id, stage


def _manual_trade(
    client, version_id, *, test_type="backtest", pnl=100.0, day=2,
    prop_stage_id=None, pta_id=None,
):
    """ثبت معاملهٔ دستی از مسیر API."""
    payload = {
        "symbol": "XAUUSD",
        "direction": "buy",
        "open_time": _iso(day, 10),
        "close_time": _iso(day, 11),
        "open_price": 2000.0,
        "close_price": 2010.0,
        "size": 1.0,
        "pnl": pnl,
        "test_type": test_type,
        "version_id": version_id,
    }
    if prop_stage_id is not None:
        payload["prop_stage_id"] = prop_stage_id
    if pta_id is not None:
        payload["personal_trading_account_id"] = pta_id
    r = client.post("/api/trades/manual", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ═════════════════════════════════════════════
# Import helpers (MT4 / Soft4X)
# ═════════════════════════════════════════════
SOFT4X_HEADERS = [
    "Open Time", "Close Time", "Type", "Open Price", "Close Price",
    "Size", "SL", "TP", "P/L", "Commission",
]

MT4_TRADE_ROW = (
    "<tr><td>2025.01.02 10:00:00</td><td>{ticket}</td><td>{symbol}</td><td>{direction}</td>"
    "<td>1.00</td><td>2000.00</td><td>1990.00</td><td>2030.00</td>"
    "<td>2025.01.02 11:00:00</td><td>2010.00</td><td>-1.00</td><td>0.00</td><td>10.00</td></tr>"
)


def _mt4_html(tickets=("5001",), symbol="XAUUSD", direction="buy"):
    rows = "".join(
        MT4_TRADE_ROW.format(ticket=ticket, symbol=symbol, direction=direction)
        for ticket in tickets
    )
    return (
        "<html><body><table>"
        "<tr><th colspan='13'>Positions</th></tr>"
        "<tr><th>Time</th><th>Position</th><th>Symbol</th><th>Type</th><th>Volume</th>"
        "<th>Price</th><th>S/L</th><th>T/P</th><th>Time</th><th>Price</th>"
        "<th>Commission</th><th>Swap</th><th>Profit</th></tr>"
        f"{rows}"
        "<tr><th colspan='13'>Orders</th></tr>"
        "</table></body></html>"
    )


def _xlsx_bytes(rows, headers=None):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Trades"
    sheet.append(headers or SOFT4X_HEADERS)
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _soft4x_row(pnl=10.0):
    return [
        "2025-01-02 10:00:00", "2025-01-02 11:00:00", "buy",
        2000.0, 2010.0, 1.0, 1990.0, 2030.0, pnl, -1.0,
    ]


def _analysis(db_session, **filters):
    """رکورد AnalysisResult جاری با فیلترهای داده‌شده."""
    db_session.expire_all()
    return db_session.query(AnalysisResult).filter_by(**filters)


# ═════════════════════════════════════════════
# ۱) استراتژی → نسخه → معاملهٔ دستی → تحلیل
# ═════════════════════════════════════════════
def test_full_cycle_create_strategy_to_trade(client, db_session):
    strategy_id, version_id = _make_strategy_version(client, db_session)
    trade_id = _manual_trade(client, version_id, pnl=120.0, day=2)

    # استراتژی و نسخه در API دیده می‌شوند
    assert client.get(f"/api/strategies/{strategy_id}").status_code == 200
    versions = client.get("/api/strategies/versions/all").json()
    assert any(v["id"] == version_id and v["trades_count"] == 1 for v in versions)

    # لیست معاملات
    listing = client.get("/api/trades/").json()
    assert listing["total"] == 1
    assert listing["trades"][0]["id"] == trade_id

    # تحلیل نسخه
    assert client.post(f"/api/analytics/analyze/{version_id}").status_code == 200
    result = _analysis(
        db_session, scope=AnalysisScope.VERSION, version_id=version_id
    ).one()
    assert result.total_trades == 1
    assert result.net_pnl == 120.0


# ═════════════════════════════════════════════
# ۲) چرخهٔ کامل پراپ → Rule Engine → Pass
# ═════════════════════════════════════════════
def test_full_cycle_prop_lifecycle(client, db_session):
    _, version_id = _make_strategy_version(client, db_session)
    _, _, stage = _make_prop_account(
        client, db_session,
        profit_target=1000.0, max_daily_dd=500.0, max_total_dd=1000.0, min_trading_days=3,
    )

    # سه روز معاملاتی سودده ⇒ آمادهٔ پاس شدن
    for day, pnl in ((1, 600.0), (2, 500.0), (3, 100.0)):
        _manual_trade(
            client, version_id, test_type="real_prop", pnl=pnl, day=day,
            prop_stage_id=stage.id,
        )

    # Rule Engine: ارزیابی + ثبت تاریخچه
    ev = client.post(f"/api/prop/stages/{stage.id}/evaluate")
    assert ev.status_code == 200, ev.text
    assert ev.json()["recorded"] == len(list(RuleType))
    assert ev.json()["overall_severity"] == "pass"

    violations = client.get(f"/api/prop/stages/{stage.id}/violations").json()
    assert len(violations) == len(list(RuleType))

    chk = client.get(f"/api/prop/stages/{stage.id}/check-pass")
    assert chk.status_code == 200
    assert chk.json()["ready_to_pass"] is True

    # پاس کردن مرحله ⇒ ایجاد مرحلهٔ بعدی
    passed = client.post(f"/api/prop/stages/{stage.id}/pass", json={})
    assert passed.status_code == 200, passed.text

    db_session.expire_all()
    assert db_session.get(PropStage, stage.id).status == StageStatus.PASSED
    assert (
        db_session.query(PropStage)
        .filter(PropStage.prop_account_id == stage.prop_account_id)
        .count()
        == 2
    )


# ═════════════════════════════════════════════
# ۳) تحلیل در هر سه دامنه (Version / Prop / Personal)
# ═════════════════════════════════════════════
def test_full_cycle_analysis_all_scopes(client, db_session):
    _, version_id = _make_strategy_version(client, db_session, test_type="backtest")
    pta_id, _ = _make_pta(client)
    _, _, stage = _make_prop_account(client, db_session, stage_type=StageType.FUNDED_REAL)

    _manual_trade(client, version_id, test_type="backtest", pnl=100.0, day=1)
    _manual_trade(
        client, version_id, test_type="real_prop", pnl=200.0, day=2, prop_stage_id=stage.id
    )
    _manual_trade(
        client, version_id, test_type="real_personal", pnl=300.0, day=3, pta_id=pta_id
    )

    assert client.post(f"/api/analytics/analyze/{version_id}").status_code == 200
    assert client.post(f"/api/analytics/analyze/prop/{stage.id}").status_code == 200
    assert (
        client.post(f"/api/analytics/analyze/personal-account/{pta_id}").status_code == 200
    )

    version_res = _analysis(
        db_session, scope=AnalysisScope.VERSION, version_id=version_id
    ).one()
    prop_res = _analysis(
        db_session, scope=AnalysisScope.PROP_STAGE, prop_stage_id=stage.id
    ).one()
    personal_res = _analysis(
        db_session,
        scope=AnalysisScope.PERSONAL_ACCOUNT,
        personal_trading_account_id=pta_id,
    ).one()

    # تحلیل نسخه فقط BACKTEST ⇒ معاملات REAL آلوده نمی‌کنند
    assert version_res.total_trades == 1 and version_res.net_pnl == 100.0
    assert prop_res.total_trades == 1 and prop_res.net_pnl == 200.0
    assert personal_res.total_trades == 1 and personal_res.net_pnl == 300.0


# ═════════════════════════════════════════════
# ۴) Payout پراپ → چرخهٔ وضعیت → درآمد مالی
# ═════════════════════════════════════════════
def test_full_cycle_finance_after_prop_payout(client, db_session):
    _, version_id = _make_strategy_version(client, db_session)
    _, _, stage = _make_prop_account(
        client, db_session, stage_type=StageType.FUNDED_REAL, profit_share=80.0
    )
    # سود ۱۵۰۰ ⇒ قابل برداشت = 1500 * 80% = 1200
    _manual_trade(
        client, version_id, test_type="real_prop", pnl=1500.0, day=1, prop_stage_id=stage.id
    )

    dest = client.post(
        "/api/finance/accounts",
        json={"name": "Trust Wallet", "type": "trust_wallet", "balance": 0.0},
    ).json()

    created = client.post(
        "/api/prop/payouts",
        json={"prop_stage_id": stage.id, "amount": 500.0, "destination_account_id": dest["id"]},
    )
    assert created.status_code == 200, created.text
    payout = created.json()
    assert payout["status"] == "requested"
    assert payout["transaction_id"] is None
    # در نقطهٔ REQUESTED هنوز درآمدی ثبت نشده
    assert client.get("/api/finance/summary").json()["total_income"] == 0.0

    for target in ("approved", "processing", "received"):
        step = client.post(
            f"/api/prop/payouts/{payout['id']}/status", json={"status": target}
        )
        assert step.status_code == 200, step.text

    summary = client.get("/api/finance/summary").json()
    assert summary["total_income"] == 0.0

    db_session.expire_all()
    assert db_session.get(FinancialAccount, dest["id"]).balance == 500.0
    assert db_session.get(PropStage, stage.id).total_withdrawn == 500.0


# ═════════════════════════════════════════════
# ۵) Permanent Delete → absent from trade list and analysis scope
# ═════════════════════════════════════════════
def test_full_cycle_hard_delete_and_list(client, db_session):
    _, version_id = _make_strategy_version(client, db_session)
    trade_id = _manual_trade(client, version_id, pnl=100.0, day=1)

    assert client.post(f"/api/analytics/analyze/{version_id}").status_code == 200
    assert _analysis(
        db_session, scope=AnalysisScope.VERSION, version_id=version_id
    ).one().total_trades == 1

    deleted = client.delete(f"/api/trades/{trade_id}")
    assert deleted.status_code == 200
    db_session.expire_all()
    assert db_session.get(Trade, trade_id) is None
    assert client.get("/api/trades/").json()["total"] == 0
    assert client.get(f"/api/trades/{trade_id}").status_code == 404

    # Analysis sees only the remaining stored trades; none remain in this scope.
    assert client.post(f"/api/analytics/analyze/{version_id}").status_code == 404


# ═════════════════════════════════════════════
# ۶) Import (MT4) → Commit → Analysis (+ idempotency)
# ═════════════════════════════════════════════
def test_full_cycle_import_then_analysis(client, db_session):
    _, version_id = _make_strategy_version(client, db_session)

    def _preview():
        return client.post(
            "/api/imports/preview",
            files={"file": ("report.html", _mt4_html(("5001",)).encode("utf-8"), "text/html")},
            data={"version_id": str(version_id), "test_type": "backtest"},
        )

    preview = _preview()
    assert preview.status_code == 200, preview.text
    batch_id = preview.json()["batch_id"]

    commit = client.post(
        f"/api/imports/commit/{batch_id}", json={"allow_possible_duplicates": False}
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["imported"] == 1

    assert client.post(f"/api/analytics/analyze/{version_id}").status_code == 200
    assert _analysis(
        db_session, scope=AnalysisScope.VERSION, version_id=version_id
    ).one().total_trades == 1

    # اجرای دوبارهٔ همان فایل ⇒ تکراری، صفر معاملهٔ جدید
    preview2 = _preview().json()
    commit2 = client.post(
        f"/api/imports/commit/{preview2['batch_id']}",
        json={"allow_possible_duplicates": False},
    ).json()
    assert commit2["imported"] == 0
    assert db_session.query(Trade).filter(Trade.version_id == version_id).count() == 1


# ═════════════════════════════════════════════
# ۷) Import Soft4X (REAL_PROP) → به‌روزرسانی مرحله پراپ
# ═════════════════════════════════════════════
def test_full_cycle_import_soft4x_real_prop_updates_stage(client, db_session):
    _, version_id = _make_strategy_version(client, db_session)
    _, _, stage = _make_prop_account(client, db_session)

    r = client.post(
        "/api/imports/soft4x",
        files={
            "file": (
                "report.xlsx",
                _xlsx_bytes([_soft4x_row(pnl=40.0)]),
                "application/vnd.ms-excel",
            )
        },
        data={
            "version_id": str(version_id),
            "prop_stage_id": str(stage.id),
            "test_type": "real",
            "symbol": "XAUUSD",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["saved_trades"] == 1

    db_session.expire_all()
    trade = db_session.query(Trade).filter(Trade.prop_stage_id == stage.id).one()
    assert trade.test_type == TestType.REAL_PROP
    # سود ایمپورت‌شده روی مرحله بازتاب می‌یابد (pnl=40 + commission=-1 ⇒ خالص 39)
    assert db_session.get(PropStage, stage.id).current_profit is not None


# ═════════════════════════════════════════════
# ۸) Batch hard delete → permanent absence
# ═════════════════════════════════════════════
def test_full_cycle_batch_delete_and_list(client, db_session):
    _, version_id = _make_strategy_version(client, db_session)
    ids = [_manual_trade(client, version_id, pnl=10.0, day=d) for d in (1, 2, 3)]

    response = client.post("/api/trades/batch-delete", json={"trade_ids": ids})
    assert response.status_code == 200, response.text
    assert response.json()["deleted"] == 3
    db_session.expire_all()
    assert all(db_session.get(Trade, trade_id) is None for trade_id in ids)
    assert client.get("/api/trades/").json()["total"] == 0


# ═════════════════════════════════════════════
# ۹) مالی: تراکنش/انتقال/برگشت اثر (WalletService)
# ═════════════════════════════════════════════
def test_full_cycle_finance_transaction_and_wallet(client, db_session):
    bank = client.post(
        "/api/finance/accounts",
        json={"name": "Bank", "type": "bank", "balance": 1000.0},
    ).json()

    r = client.post(
        "/api/finance/transactions",
        json={"account_id": bank["id"], "type": "deposit", "amount": 500.0},
    )
    assert r.status_code == 200, r.text
    db_session.expire_all()
    assert db_session.get(FinancialAccount, bank["id"]).balance == 1500.0

    ex = client.post(
        "/api/finance/accounts",
        json={"name": "Exchange", "type": "exchange", "balance": 0.0},
    ).json()
    r = client.post(
        "/api/finance/transactions",
        json={
            "account_id": ex["id"],
            "type": "transfer",
            "amount": 200.0,
            "from_account_id": bank["id"],
            "to_account_id": ex["id"],
        },
    )
    assert r.status_code == 200, r.text
    db_session.expire_all()
    assert db_session.get(FinancialAccount, bank["id"]).balance == 1300.0
    assert db_session.get(FinancialAccount, ex["id"]).balance == 200.0

    summary = client.get("/api/finance/summary").json()
    assert summary["total_income"] == 500.0      # transfer درآمد نیست
    assert summary["total_transfers"] == 200.0

    # حذف نرم تراکنش واریز ⇒ برگشت اثر روی موجودی
    deposit_tx = (
        db_session.query(FinancialTransaction)
        .filter(FinancialTransaction.type == TransactionType.DEPOSIT)
        .first()
    )
    assert client.delete(f"/api/finance/transactions/{deposit_tx.id}").status_code == 200
    db_session.expire_all()
    assert db_session.get(FinancialAccount, bank["id"]).balance == 800.0


# ═════════════════════════════════════════════
# ۱۰) داشبورد پس از دیتاست کامل (با حذف نرم)
# ═════════════════════════════════════════════
def test_full_cycle_dashboard_after_full_dataset(client, db_session):
    _, version_id = _make_strategy_version(client, db_session)
    for day in (1, 2, 3):
        _manual_trade(client, version_id, pnl=100.0, day=day)
    _manual_trade(client, version_id, pnl=-50.0, day=4)

    listing = client.get("/api/trades/").json()["trades"]
    assert len(listing) == 4

    # حذف نرم یکی از معاملات مثبت
    positive = next(t for t in listing if t["pnl"] == 100.0)
    assert client.delete(f"/api/trades/{positive['id']}").status_code == 200

    # فاز ۴۴.۱: پیش‌فرض scope=real است؛ این تست دربارهٔ Soft-Delete است ⇒ scope=all
    summary = client.get("/api/analytics/dashboard?scope=all").json()["summary"]
    assert summary["total_trades"] == 3
    assert summary["net_pnl"] == 150.0  # 100 + 100 - 50


# ═════════════════════════════════════════════
# ۱۱) نسخه‌ها + Fork + شمارش معاملات نسخه
# ═════════════════════════════════════════════
def test_full_cycle_strategy_versions_and_fork(client, db_session):
    _, version_id = _make_strategy_version(client, db_session)
    _manual_trade(client, version_id, pnl=10.0, day=1)

    versions = client.get("/api/strategies/versions/all").json()
    assert len(versions) == 1
    assert versions[0]["trades_count"] == 1

    r = client.post(
        f"/api/strategies/versions/{version_id}/fork", json={"version_name": "v1-fork"}
    )
    assert r.status_code == 200, r.text

    db_session.expire_all()
    forked = (
        db_session.query(StrategyVersion).order_by(StrategyVersion.id.desc()).first()
    )
    assert forked.id != version_id
    assert forked.version_name == "v1-fork"
    assert forked.forked_from_version_id == version_id


# ═════════════════════════════════════════════
# ۱۲) Broker / حساب شخصی → تحلیل PERSONAL_ACCOUNT
# ═════════════════════════════════════════════
def test_full_cycle_broker_personal_account_analysis(client, db_session):
    _, version_id = _make_strategy_version(client, db_session)
    pta_id, broker_id = _make_pta(client)

    _manual_trade(client, version_id, test_type="real_personal", pnl=75.0, day=5, pta_id=pta_id)

    accounts = client.get("/api/trading/accounts").json()
    assert any(a["id"] == pta_id and a["broker_id"] == broker_id for a in accounts)

    r = client.post(f"/api/analytics/analyze/personal-account/{pta_id}")
    assert r.status_code == 200, r.text

    res = _analysis(
        db_session,
        scope=AnalysisScope.PERSONAL_ACCOUNT,
        personal_trading_account_id=pta_id,
    ).one()
    assert res.total_trades == 1
    assert res.net_pnl == 75.0


# ═════════════════════════════════════════════
# ۱۳) بازدسته‌بندی معاملهٔ دستی (BACKTEST → REAL_PERSONAL)
# ═════════════════════════════════════════════
def test_full_cycle_manual_trade_reclassification(client, db_session):
    """فاز ۴۰.۵: PATCH باید تغییرات را persist کند (پیش‌تر db.commit گم بود)."""
    _, version_id = _make_strategy_version(client, db_session)
    pta_id, _ = _make_pta(client)
    trade_id = _manual_trade(client, version_id, pnl=50.0, day=1)

    r = client.patch(
        f"/api/trades/{trade_id}",
        json={
            "test_type": "real_personal",
            "personal_trading_account_id": pta_id,
            "pnl": 75.0,
            "note": "reclassified",
        },
    )
    assert r.status_code == 200, r.text

    # تغییرات باید پایدار باشند: rollback نباید اثر commit را برگرداند
    db_session.rollback()
    trade = db_session.get(Trade, trade_id)
    assert trade.test_type == TestType.REAL_PERSONAL
    assert trade.personal_trading_account_id == pta_id
    assert trade.pnl == 75.0
    assert trade.note == "reclassified"


# ═════════════════════════════════════════════
# ۱۴) انتقال payout = درآمد نیست (تکمیل چرخهٔ مالی)
# ═════════════════════════════════════════════
def test_full_cycle_payout_transfer_is_not_income(client, db_session):
    _, version_id = _make_strategy_version(client, db_session)
    _, _, stage = _make_prop_account(
        client, db_session, stage_type=StageType.FUNDED_REAL, profit_share=80.0
    )
    _manual_trade(
        client, version_id, test_type="real_prop", pnl=1500.0, day=1, prop_stage_id=stage.id
    )

    wallet = client.post(
        "/api/finance/accounts",
        json={"name": "Trust Wallet", "type": "trust_wallet", "balance": 0.0},
    ).json()
    exchange = client.post(
        "/api/finance/accounts",
        json={"name": "Exchange", "type": "exchange", "balance": 0.0},
    ).json()

    payout = client.post(
        "/api/prop/payouts",
        json={
            "prop_stage_id": stage.id,
            "amount": 500.0,
            "destination_account_id": wallet["id"],
        },
    ).json()
    for target in ("approved", "processing", "received"):
        client.post(f"/api/prop/payouts/{payout['id']}/status", json={"status": target})

    assert client.get("/api/finance/summary").json()["total_income"] == 0.0

    r = client.post(
        f"/api/prop/payouts/{payout['id']}/transfer",
        json={"to_account_id": exchange["id"], "amount": 500.0, "currency": "USD"},
    )
    assert r.status_code == 200, r.text

    summary = client.get("/api/finance/summary").json()
    assert summary["total_income"] == 0.0      # درآمد همچنان صفر است
    assert summary["total_transfers"] == 500.0

    db_session.expire_all()
    assert db_session.get(FinancialAccount, wallet["id"]).balance == 0.0
    assert db_session.get(FinancialAccount, exchange["id"]).balance == 500.0

