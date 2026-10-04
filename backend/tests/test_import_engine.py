"""تست‌های فاز ۳۰ — Import Engine (Preview → Confirm → Atomic Commit).

پوشش:
- اعتبارسنجی Trade Contract (version_id اجباری / REAL_PERSONAL / REAL_PROP)
- Preview بدون هیچ تغییر در معاملات + شمارنده‌های batch
- Commit اتمیک (خطای یک رکورد ⇒ هیچ رکوردی ذخیره نمی‌شود)
- ImportProfile (Broker / SourceFormat / Symbol Mapping / Column Mapping / Default Context)
- Import هرگز FinancialAccount نمی‌سازد
"""
import io

import pytest
from openpyxl import Workbook

from app.models.finance import FinancialAccount, Currency
from app.models.imports import (
    ImportBatch,
    ImportBatchRow,
    ImportIdentity,
    ImportRowStatus,
    ImportStatus,
)
from app.models.prop import PropAccount, PropFirm, PropStage, StageStatus, StageType
from app.models.strategy import Strategy, StrategyVersion, Trade, TestType
from app.models.trading import Broker, PersonalTradingAccount
from app.services.import_engine import ImportEngine, normalize_test_type


# ═════════════════════════════════════════════
# Fixtures / Helpers
# ═════════════════════════════════════════════
SOFT4X_HEADERS = [
    "Open Time", "Close Time", "Type", "Open Price", "Close Price",
    "Size", "SL", "TP", "P/L", "Commission",
]


def _version(db, name="v1"):
    strategy = Strategy(name=f"S-{name}")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name=name)
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def _pta(db, label="A"):
    broker = Broker(name=f"Broker-{label}")
    db.add(broker)
    db.flush()
    account = PersonalTradingAccount(
        broker_id=broker.id,
        account_number=f"ACC-{label}",
        account_label=label,
        currency=Currency.USD,
        initial_balance=10000.0,
        current_balance=10000.0,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def _stage(db, *, profit_share=80.0):
    firm = PropFirm(name="FTMO")
    db.add(firm)
    db.flush()
    prop_account = PropAccount(prop_firm_id=firm.id, account_label="P1")
    db.add(prop_account)
    db.flush()
    stage = PropStage(
        prop_account_id=prop_account.id,
        stage_type=StageType.STAGE_1,
        profit_target=1000.0,
        initial_balance=10000.0,
        profit_share_percentage=profit_share,
    )
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


def _xlsx_bytes(rows, headers=None):
    """فایل اکسل Soft4X در حافظه (sheet = Trades)."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Trades"
    sheet.append(headers or SOFT4X_HEADERS)
    for row in rows:
        sheet.append(row)

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _soft4x_row(
    open_time="2025-01-02 10:00:00",
    close_time="2025-01-02 11:00:00",
    direction="buy",
    open_price=2000.0,
    close_price=2010.0,
    size=1.0,
    sl=1990.0,
    tp=2030.0,
    pnl=10.0,
    commission=-1.0,
):
    return [
        open_time, close_time, direction, open_price, close_price,
        size, sl, tp, pnl, commission,
    ]


MT4_TRADE_ROW = (
    "<tr><td>2025.01.02 10:00:00</td><td>{ticket}</td><td>{symbol}</td><td>{direction}</td>"
    "<td>1.00</td><td>2000.00</td><td>1990.00</td><td>2030.00</td>"
    "<td>2025.01.02 11:00:00</td><td>2010.00</td><td>-1.00</td><td>0.00</td><td>10.00</td></tr>"
)


def _mt4_html(tickets=("1001",), symbol="XAUUSD", direction="buy"):
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


def _preview_mt4(client, html=None, **form):
    return client.post(
        "/api/imports/preview",
        files={"file": ("report.html", (html or _mt4_html()).encode("utf-8"), "text/html")},
        data={key: str(value) for key, value in form.items()},
    )


def _preview_soft4x(client, content=None, file_name="report.xlsx", **form):
    return client.post(
        "/api/imports/preview",
        files={
            "file": (
                file_name,
                content if content is not None else _xlsx_bytes([_soft4x_row()]),
                "application/vnd.ms-excel",
            )
        },
        data={key: str(value) for key, value in form.items()},
    )


def _commit(client, batch_id, allow=False):
    return client.post(
        f"/api/imports/commit/{batch_id}", json={"allow_possible_duplicates": allow}
    )


@pytest.fixture(autouse=True)
def _reset_import_rate_limit():
    """شمارنده‌ی Rate Limit ایمپورت (۱۰ در دقیقه) بین تست‌ها صفر می‌شود."""
    from app.core.rate_limit import limiter

    limiter.reset()
    yield


# ═════════════════════════════════════════════
# Normalization / Contract
# ═════════════════════════════════════════════
def test_legacy_real_test_type_is_mapped_to_contract():
    """مقدار قدیمی `real` (که UI فاز قبل می‌فرستد) باید به قرارداد فاز ۲۷ نگاشت شود."""
    assert normalize_test_type("real", prop_stage_id=3) is TestType.REAL_PROP
    assert normalize_test_type("real", personal_trading_account_id=5) is TestType.REAL_PERSONAL
    assert normalize_test_type("BACKTEST") is TestType.BACKTEST


def test_preview_requires_version_id(client, db_session):
    db_session.add(Strategy(name="S"))
    db_session.commit()
    response = _preview_mt4(client, test_type="backtest")
    assert response.status_code == 400
    assert "version_id" in response.json()["detail"]


def test_preview_real_personal_requires_account(client, db_session):
    version = _version(db_session)
    response = _preview_mt4(client, test_type="real_personal", version_id=version.id)
    assert response.status_code == 400
    assert "personal_trading_account_id" in response.json()["detail"]


def test_preview_real_prop_requires_stage(client, db_session):
    version = _version(db_session)
    response = _preview_soft4x(client, test_type="real_prop", version_id=version.id)
    assert response.status_code == 400
    assert "prop_stage_id" in response.json()["detail"]


def test_preview_missing_version_target_returns_404(client, db_session):
    db_session.add(Strategy(name="S"))
    db_session.commit()
    response = _preview_mt4(client, test_type="backtest", version_id=999)
    assert response.status_code == 404
    assert response.json()["detail"] == "نسخه استراتژی پیدا نشد"


# ═════════════════════════════════════════════
# Preview — بدون تغییر داده
# ═════════════════════════════════════════════
def test_preview_stages_rows_without_touching_trades(client, db_session):
    version = _version(db_session)
    response = _preview_soft4x(client, test_type="backtest", version_id=version.id)
    assert response.status_code == 200, response.text

    summary = response.json()
    assert summary["total"] == 1
    assert summary["counts"][ImportRowStatus.NEW.value] == 1
    assert summary["status"] == ImportStatus.PENDING.value
    assert summary["imported"] == 0
    assert summary["rows"][0]["symbol"] == "XAUUSD"

    # هیچ معامله‌ای ساخته نشده — فقط staging
    assert db_session.query(Trade).count() == 0
    assert db_session.query(ImportIdentity).count() == 0
    assert db_session.query(ImportBatchRow).count() == 1
    batch = db_session.query(ImportBatch).one()
    assert batch.total == 1
    assert batch.context["test_type"] == TestType.BACKTEST.name
    assert batch.context["version_id"] == version.id


def test_preview_rejects_unknown_extension(client, db_session):
    version = _version(db_session)
    response = _preview_soft4x(
        client, file_name="report.csv", test_type="backtest", version_id=version.id
    )
    assert response.status_code == 400
    assert "xlsx" in response.json()["detail"]


def test_preview_invalid_column_mapping_json(client, db_session):
    version = _version(db_session)
    response = _preview_mt4(
        client, test_type="backtest", version_id=version.id, column_mapping="{not-json"
    )
    assert response.status_code == 400
    assert "column_mapping" in response.json()["detail"]


def test_preview_without_trades_returns_400(client, db_session):
    version = _version(db_session)
    response = _preview_soft4x(
        client,
        content=_xlsx_bytes([]),
        test_type="backtest",
        version_id=version.id,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "هیچ معامله‌ای در فایل یافت نشد"


# ═════════════════════════════════════════════
# Commit — اتمیک و idempotent
# ═════════════════════════════════════════════
def test_commit_imports_trades_and_is_idempotent(client, db_session):
    version = _version(db_session)
    preview = _preview_mt4(client, test_type="backtest", version_id=version.id).json()

    commit = _commit(client, preview["batch_id"])
    assert commit.status_code == 200, commit.text
    result = commit.json()
    assert result["imported"] == 1
    assert result["duplicate"] == 0
    assert result["status"] == ImportStatus.COMMITTED.value

    trades = db_session.query(Trade).all()
    assert len(trades) == 1
    assert trades[0].version_id == version.id
    assert trades[0].test_type == TestType.BACKTEST
    assert db_session.query(ImportIdentity).count() == 1
    identity = db_session.query(ImportIdentity).one()
    assert identity.trade_id == trades[0].id
    assert identity.external_ticket == "1001"
    assert identity.batch_id == preview["batch_id"]

    # اجرای دوباره‌ی همان فایل ⇒ هیچ معامله‌ی جدیدی اضافه نمی‌شود
    second = _preview_mt4(client, test_type="backtest", version_id=version.id).json()
    assert second["counts"][ImportRowStatus.DUPLICATE.value] == 1
    second_commit = _commit(client, second["batch_id"]).json()
    assert second_commit["imported"] == 0
    assert second_commit["duplicate"] == 1
    assert db_session.query(Trade).count() == 1


def test_commit_twice_returns_conflict(client, db_session):
    version = _version(db_session)
    preview = _preview_mt4(client, test_type="backtest", version_id=version.id).json()
    assert _commit(client, preview["batch_id"]).status_code == 200

    again = _commit(client, preview["batch_id"])
    assert again.status_code == 409


def test_invalid_row_blocks_whole_import(client, db_session):
    """قانون ۲: خطای یک رکورد ⇒ Import ناقص ممنوع (هیچ رکوردی ذخیره نمی‌شود)."""
    version = _version(db_session)
    rows = [_soft4x_row(), _soft4x_row(open_time="2025-01-03 10:00:00", size=0)]
    preview = _preview_soft4x(
        client, content=_xlsx_bytes(rows), test_type="backtest", version_id=version.id
    ).json()
    assert preview["counts"][ImportRowStatus.INVALID.value] == 1

    commit = _commit(client, preview["batch_id"])
    assert commit.status_code == 400
    assert "نامعتبر" in commit.json()["detail"]
    assert db_session.query(Trade).count() == 0
    assert db_session.query(ImportIdentity).count() == 0
    assert db_session.query(ImportBatch).one().status == ImportStatus.PENDING


def test_commit_rollback_marks_batch_failed(client, db_session, monkeypatch):
    """خطای غیرمنتظره در میانه‌ی Commit ⇒ rollback کامل + status=FAILED."""
    version = _version(db_session)
    rows = [
        _soft4x_row(),
        _soft4x_row(open_time="2025-01-03 10:00:00", close_time="2025-01-03 11:00:00"),
    ]
    preview = _preview_soft4x(
        client, content=_xlsx_bytes(rows), test_type="backtest", version_id=version.id
    ).json()

    original = ImportEngine._create_trade
    calls = {"count": 0}

    def flaky(self, trade_data):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("boom")
        return original(self, trade_data)

    monkeypatch.setattr(ImportEngine, "_create_trade", flaky)

    commit = _commit(client, preview["batch_id"])
    assert commit.status_code == 500
    assert calls["count"] == 2

    # رکورد اول هم ذخیره نشده است (اتمیک)
    assert db_session.query(Trade).count() == 0
    assert db_session.query(ImportIdentity).count() == 0
    assert db_session.query(ImportBatch).one().status == ImportStatus.FAILED


def test_import_never_creates_financial_account(client, db_session):
    """قانون ۴: Import نباید FinancialAccount بسازد."""
    version = _version(db_session)
    stage = _stage(db_session)
    preview = _preview_soft4x(
        client, test_type="real_prop", version_id=version.id, prop_stage_id=stage.id
    ).json()
    before = db_session.query(FinancialAccount).count()

    assert _commit(client, preview["batch_id"]).status_code == 200
    assert db_session.query(FinancialAccount).count() == before == 0

    # سود مرحله‌ی پراپ هم پس از import به‌روزرسانی شده است
    db_session.expire_all()
    assert db_session.query(PropStage).one().current_profit == 9.0


# ═════════════════════════════════════════════
# ImportProfile — Broker / Mapping / Default Context
# ═════════════════════════════════════════════
CUSTOM_HEADERS = [
    "Time Open", "Time Close", "Side", "Price In", "Price Out",
    "Lots", "Stop", "Target", "Profit", "Fee",
]


def test_profile_crud_and_default_context(client, db_session):
    broker = Broker(name="IC Markets")
    db_session.add(broker)
    db_session.commit()
    version = _version(db_session)
    stage = _stage(db_session)

    created = client.post("/api/imports/profiles", json={
        "name": "Soft4X-IC",
        "broker_id": broker.id,
        "source_format": "soft4x_xlsx",
        "symbol_mapping": {"GOLD": "XAUUSD"},
        "column_mapping": {
            "open_time": "Time Open", "close_time": "Time Close", "type": "Side",
            "open_price": "Price In", "close_price": "Price Out", "size": "Lots",
            "sl": "Stop", "tp": "Target", "pnl": "Profit", "commission": "Fee",
        },
        "default_context": {
            "test_type": "REAL_PROP",
            "version_id": version.id,
            "prop_stage_id": stage.id,
            "symbol": "GOLD",
        },
    })
    assert created.status_code == 200, created.text
    profile_id = created.json()["id"]

    listed = client.get("/api/imports/profiles").json()
    assert len(listed) == 1
    assert listed[0]["broker_name"] == "IC Markets"
    assert listed[0]["source_format"] == "soft4x_xlsx"
    assert listed[0]["default_context"]["prop_stage_id"] == stage.id

    # Preview فقط با profile_id (بدون هیچ پارامتر دیگری)
    content = _xlsx_bytes(
        [[
            "2025-01-02 10:00:00", "2025-01-02 11:00:00", "BUY",
            2000.0, 2010.0, 1.0, 1990.0, 2030.0, 25.0, -1.0,
        ]],
        headers=CUSTOM_HEADERS,
    )
    response = _preview_soft4x(client, content=content, profile_id=profile_id)
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["context"]["test_type"] == TestType.REAL_PROP.name
    assert summary["context"]["prop_stage_id"] == stage.id
    assert summary["rows"][0]["symbol"] == "XAUUSD"       # Symbol Mapping پروفایل
    assert summary["rows"][0]["pnl"] == 25.0              # Column Mapping پروفایل

    commit = _commit(client, summary["batch_id"]).json()
    assert commit["imported"] == 1
    trade = db_session.query(Trade).one()
    assert trade.test_type == TestType.REAL_PROP
    assert trade.prop_stage_id == stage.id
    assert trade.symbol == "XAUUSD"

    # Duplicate Name
    duplicate = client.post("/api/imports/profiles", json={
        "name": "Soft4X-IC", "source_format": "mt4_html",
    })
    assert duplicate.status_code == 400

    # پروفایل ناموجود
    missing = _preview_soft4x(client, profile_id=9999)
    assert missing.status_code == 404

    # حذف
    assert client.delete(f"/api/imports/profiles/{profile_id}").status_code == 200
    assert client.get("/api/imports/profiles").json() == []


def test_profile_rejects_unknown_column_mapping(client):
    response = client.post("/api/imports/profiles", json={
        "name": "bad",
        "source_format": "soft4x_xlsx",
        "column_mapping": {"unknown_field": "X"},
    })
    assert response.status_code == 400
    assert "column_mapping" in response.json()["detail"]


def test_profile_rejects_invalid_default_test_type(client):
    response = client.post("/api/imports/profiles", json={
        "name": "bad-type",
        "source_format": "soft4x_xlsx",
        "default_context": {"test_type": "not-a-type"},
    })
    assert response.status_code == 400


# ═════════════════════════════════════════════
# Batches — تاریخچه / جزئیات / لغو
# ═════════════════════════════════════════════
def test_batch_history_detail_and_cancel(client, db_session):
    version = _version(db_session)
    preview = _preview_mt4(client, test_type="backtest", version_id=version.id).json()

    history = client.get("/api/imports/batches").json()
    assert len(history) == 1
    assert history[0]["batch_id"] == preview["batch_id"]
    assert history[0]["status"] == ImportStatus.PENDING.value

    detail = client.get(f"/api/imports/batches/{preview['batch_id']}").json()
    assert detail["rows_total"] == 1
    assert detail["rows"][0]["status"] == ImportRowStatus.NEW.value

    pending_only = client.get("/api/imports/batches?status=pending").json()
    assert len(pending_only) == 1

    cancelled = client.post(f"/api/imports/batches/{preview['batch_id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == ImportStatus.CANCELLED.value

    # Commit بعد از لغو ⇒ ۴۰۹
    assert _commit(client, preview["batch_id"]).status_code == 409
    assert db_session.query(Trade).count() == 0

    assert client.get("/api/imports/batches?status=bogus").status_code == 400
    assert client.get("/api/imports/batches/9999").status_code == 404


# ═════════════════════════════════════════════
# سازگاری با endpointهای قدیمی (روی همان موتور)
# ═════════════════════════════════════════════
def test_legacy_mt4_endpoint_uses_engine_and_creates_batch(client, db_session):
    version = _version(db_session)
    payload = {"version_id": str(version.id), "test_type": "backtest"}
    html = _mt4_html(tickets=("7", "8")).encode("utf-8")

    response = client.post(
        "/api/imports/mt4",
        files={"file": ("report.html", html, "text/html")},
        data=payload,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["saved_trades"] == 2
    assert body["total_trades"] == 2
    assert body["batch_id"] is not None

    assert db_session.query(Trade).count() == 2
    assert db_session.query(ImportIdentity).count() == 2
    batch = db_session.query(ImportBatch).one()
    assert batch.status == ImportStatus.COMMITTED
    assert batch.imported == 2

    # اجرای دوباره از مسیر قدیمی ⇒ تکراری‌ها نادیده گرفته می‌شوند
    again = client.post(
        "/api/imports/mt4",
        files={"file": ("report.html", html, "text/html")},
        data=payload,
    ).json()
    assert again["saved_trades"] == 0
    assert again["duplicates_count"] == 2
    assert db_session.query(Trade).count() == 2


def test_legacy_soft4x_real_prop_updates_stage(client, db_session):
    version = _version(db_session)
    stage = _stage(db_session)
    response = client.post(
        "/api/imports/soft4x",
        files={
            "file": (
                "report.xlsx",
                _xlsx_bytes([_soft4x_row(pnl=40.0)]),
                "application/vnd.ms-excel",
            )
        },
        data={
            "version_id": str(version.id),
            "prop_stage_id": str(stage.id),
            "test_type": "real",  # مقدار قدیمی UI ⇒ REAL_PROP
            "symbol": "XAUUSD",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["saved_trades"] == 1

    db_session.expire_all()
    trade = db_session.query(Trade).one()
    assert trade.test_type == TestType.REAL_PROP
    assert db_session.query(PropStage).one().current_profit == 39.0  # net_pnl = pnl(40) + commission(-1) + swap(0)




def test_sync_prop_stage_profit_skips_non_active_stages(client, db_session):
    """فاز ۵: sync_prop_stage_profit نباید `current_profit` مراحل غیرفعال را تغییر دهد."""
    version = _version(db_session)
    stage = _stage(db_session)  # stage_1, ACTIVE

    # ایمپورت اول به stage فعال → current_profit به‌روزرسانی شود
    preview = _preview_soft4x(
        client, test_type="real_prop", version_id=version.id, prop_stage_id=stage.id
    ).json()
    assert _commit(client, preview["batch_id"]).status_code == 200
    db_session.expire_all()
    profit_after_first_import = db_session.query(PropStage).one().current_profit

    # اکنون مرحله را PASSED کنیم
    stage.status = StageStatus.PASSED
    db_session.commit()

    # ایمپورت دوم به همان stage (اکنون PASSED) → current_profit نباید تغییر کند
    preview2 = _preview_soft4x(
        client, test_type="real_prop", version_id=version.id, prop_stage_id=stage.id
    ).json()
    assert _commit(client, preview2["batch_id"]).status_code == 200
    db_session.expire_all()
    profit_after_second_import = db_session.query(PropStage).one().current_profit

    assert profit_after_second_import == profit_after_first_import, \
        "current_profit نباید بعد از PASSED شدن تغییر کند"


def test_sync_prop_stage_profit_still_updates_active(client, db_session):
    """فاز ۵: sync_prop_stage_profit همچنان برای مراحل فعال کار می‌کند (نه skip)."""
    from app.services.import_engine import sync_prop_stage_profit

    version = _version(db_session)
    stage = _stage(db_session)  # stage_1, ACTIVE

    # ایمپورت اول
    preview = _preview_soft4x(
        client, test_type="real_prop", version_id=version.id, prop_stage_id=stage.id
    ).json()
    assert _commit(client, preview["batch_id"]).status_code == 200
    db_session.expire_all()
    profit_after_import = db_session.query(PropStage).one().current_profit
    assert profit_after_import == 9.0  # net_pnl = 10 + (-1) + 0

    # مرحله فعال بمانده — فراخوانی مستقیم sync_prop_stage_profit باید به‌روز کند
    sync_prop_stage_profit(db_session, stage.id)
    db_session.expire_all()
    profit_after_sync = db_session.query(PropStage).one().current_profit
    assert profit_after_sync == 9.0  # همان مقدار (تغییری در معاملات نکرده)
