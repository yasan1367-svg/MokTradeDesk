"""تست‌های فاز ۵۳.۵ — Import حساب شخصی + PDF با test_type + حفظ فیلترها در CSV/PDF.

- ۵۳.۵.۱: ایمپورت با مقصد حساب معاملاتی شخصی (REAL_PERSONAL) — بک‌اند از قبل پشتیبانی
  داشت؛ حالا UI هم دارد. اینجا مسیر بک‌اند تست می‌شود.
- ۵۳.۵.۲: `GET /api/export/analysis/pdf` پارامتر `test_type` گرفت.
- ۵۳.۵.۳: `date_from/date_to` در CSV/PDF **شامل آخرین روز** (نیمه‌باز) شد.
"""
import io
from datetime import datetime, timezone

from openpyxl import Workbook

from app.models.finance import Currency
from app.models.strategy import (
    AnalysisResult,
    AnalysisScope,
    Strategy,
    StrategyVersion,
    TestType,
    Trade,
    TradeSource,
)
from app.models.trading import Broker, PersonalTradingAccount


SOFT4X_HEADERS = [
    "Open Time", "Close Time", "Type", "Open Price", "Close Price",
    "Size", "SL", "TP", "P/L", "Commission",
]


def _xlsx_bytes(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Trades"
    ws.append(SOFT4X_HEADERS)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _soft4x_row(*, day=2):
    return [
        f"2025-01-{day:02d} 10:00:00", f"2025-01-{day:02d} 11:00:00", "buy",
        2000.0, 2010.0, 1.0, 1990.0, 2020.0, 100.0, 0.0,
    ]


def _version(db, name="v53f"):
    s = Strategy(name=f"S53f-{name}")
    db.add(s)
    db.flush()
    v = StrategyVersion(strategy_id=s.id, version_name=name)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _pta(db):
    b = Broker(name="B-53f")
    db.add(b)
    db.flush()
    a = PersonalTradingAccount(
        broker_id=b.id, account_number="ACC-53f", account_label="53f",
        currency=Currency.USDT, initial_balance=10000.0, current_balance=10000.0,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _trade(db, version_id, pnl, *, day, test_type, pta_id=None):
    db.add(Trade(
        version_id=version_id,
        personal_trading_account_id=pta_id,
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 3, day, 9, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 3, day, 10, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2010.0,
        size=1.0,
        pnl=pnl,
        commission=0.0,
        swap=0.0,
        source=TradeSource.MANUAL,
        test_type=test_type,
    ))


def test_import_real_personal(client, db_session):
    """ایمپورت Soft4X با مقصد حساب شخصی ⇒ معاملات REAL_PERSONAL با همان حساب."""
    v = _version(db_session, "imp")
    pta = _pta(db_session)

    preview = client.post(
        "/api/imports/preview",
        files={"file": ("report.xlsx", _xlsx_bytes([_soft4x_row()]), "application/vnd.ms-excel")},
        data={
            "source_format": "soft4x_xlsx",
            "test_type": "real_personal",
            "version_id": str(v.id),
            "personal_trading_account_id": str(pta.id),
        },
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["counts"]["new"] == 1

    commit = client.post(
        f"/api/imports/commit/{body['batch_id']}",
        json={"allow_possible_duplicates": False},
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["imported"] == 1

    db_session.expire_all()
    trade = db_session.query(Trade).filter(Trade.version_id == v.id).first()
    assert trade is not None
    assert trade.test_type == TestType.REAL_PERSONAL
    assert trade.personal_trading_account_id == pta.id


def test_pdf_with_test_type(client, db_session):
    """PDF تحلیل باید بر پایهٔ `test_type` (FORWARD) ساخته شود، نه تلفیقی."""
    v = _version(db_session, "pdf")
    _trade(db_session, v.id, 100.0, day=1, test_type=TestType.BACKTEST)
    _trade(db_session, v.id, -50.0, day=2, test_type=TestType.FORWARD)
    db_session.commit()

    r = client.get("/api/export/analysis/pdf", params={"version_id": v.id, "test_type": "FORWARD"})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")

    # تحلیل ذخیره‌شده باید فقط FORWARD باشد (اثر جانبی analyze_version)
    db_session.expire_all()
    res = db_session.query(AnalysisResult).filter(
        AnalysisResult.scope == AnalysisScope.VERSION,
        AnalysisResult.scope_key == f"{v.id}:FORWARD",
    ).first()
    assert res is not None
    assert res.total_trades == 1
    assert res.net_pnl == -50.0


def test_export_preserves_filters(client, db_session):
    """CSV باید فیلترهای test_type و بازهٔ تاریخ (شامل آخرین روز) را حفظ کند."""
    v = _version(db_session, "csv")
    _trade(db_session, v.id, 100.0, day=1, test_type=TestType.BACKTEST)
    _trade(db_session, v.id, -800.0, day=20, test_type=TestType.BACKTEST)
    _trade(db_session, v.id, 50.0, day=1, test_type=TestType.FORWARD)
    db_session.commit()

    # بدون فیلتر ⇒ هر ۳ معامله
    full = client.get("/api/export/trades/csv", params={"version_id": v.id})
    assert full.status_code == 200
    assert len([l for l in full.text.strip().splitlines() if l.strip()]) == 4  # header + 3

    # test_type=backtest + بازهٔ یک‌روزه (date_to=date_from) ⇒ فقط معاملهٔ 03-01
    filtered = client.get("/api/export/trades/csv", params={
        "version_id": v.id, "test_type": "backtest",
        "date_from": "2025-03-01", "date_to": "2025-03-01",
    })
    assert filtered.status_code == 200
    rows = [l for l in filtered.text.strip().splitlines() if l.strip()]
    assert len(rows) == 2  # header + 1 (اگر date_to شامل نبود ⇒ 1 (فقط header))
