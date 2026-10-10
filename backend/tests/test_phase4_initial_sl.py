"""فاز ۴ — تست‌های initial_sl (اولویت R-Multiple, MT4 Orders, Soft4X, PATCH)."""
import os
import tempfile
from datetime import datetime, timezone
from openpyxl import Workbook
import pytest
from app.models.strategy import Trade, TradeSource, TestType
from app.services.import_service import Soft4XImporter, MT4Importer
from app.utils.trade_metrics import calculate_r_multiple


# ═════════════════════════════════════════════
# Soft4X — initial_sl کار
# ═════════════════════════════════════════════
SOFT4X_HEADERS = [
    "Open Time", "Close Time", "Type", "Open Price", "Close Price",
    "Size", "SL", "Initial SL", "TP", "P/L", "Commission",
]


def _soft4x_xlsx(rows, headers=SOFT4X_HEADERS):
    wb = Workbook()
    ws = wb.active
    ws.title = "Trades"
    ws.append(headers)
    for r in rows:
        ws.append(r)
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(path)
    return path


def _soft4x_row(*, sl, initial_sl=None, pnl=100.0):
    return [
        "2025-01-02 10:00:00", "2025-01-02 11:00:00", "buy",
        2000.0, 2100.0, 1.0, sl,
        initial_sl,
        2110.0, pnl, 0.0,
    ]


def test_soft4x_initial_sl_used_for_r(db_session):
    """Soft4X با Initial SL: R بر پایهٔ initial_sl محاسبه می‌شود، نه SL جابجا شده."""
    path = _soft4x_xlsx([_soft4x_row(sl=1990.0, initial_sl=1950.0)])
    try:
        trades = Soft4XImporter(db_session, symbol="XAUUSD", test_type="backtest").parse_file(path)
    finally:
        os.remove(path)
    assert len(trades) == 1
    t = trades[0]
    assert t["sl"] == 1990.0
    assert t["initial_sl"] == 1950.0
    assert t["raw_data"]["initial_sl"] == 1950.0
    # R = (2100-2000) / (2000-1950) = 100/50 = 2.0
    assert t["r_multiple"] == 2.0


def test_soft4x_no_initial_sl_fallback_to_sl(db_session):
    """Soft4X بدون Initial SL: R از SL معمولی محاسبه می‌شود."""
    headers = [h for h in SOFT4X_HEADERS if h != "Initial SL"]
    path = _soft4x_xlsx([_soft4x_row(sl=1950.0)], headers=headers)
    try:
        trades = Soft4XImporter(db_session, symbol="XAUUSD", test_type="backtest").parse_file(path)
    finally:
        os.remove(path)
    assert len(trades) == 1
    t = trades[0]
    assert t["initial_sl"] is None
    assert "initial_sl" not in (t.get("raw_data") or {})
    # R = (2100-2000) / (2000-1950) = 2.0 (fallback به sl)
    assert t["r_multiple"] == 2.0


def test_soft4x_initial_sl_not_in_raw_data_if_missing(db_session):
    """Soft4X: ستون Initial SL هست ولی مقدار None ⇒ در raw_data ذخیره نمی‌شود."""
    path = _soft4x_xlsx([_soft4x_row(sl=1990.0, initial_sl=None)])
    try:
        trades = Soft4XImporter(db_session, symbol="XAUUSD", test_type="backtest").parse_file(path)
    finally:
        os.remove(path)
    t = trades[0]
    assert t["initial_sl"] is None
    assert "initial_sl" not in (t.get("raw_data") or {})
# ═════════════════════════════════════════════
# MT4 HTML — Orders → Positions
# ═════════════════════════════════════════════
def _mt4_html_with_orders(positions_rows, orders_rows):
    """ساخت HTML با Positions و Orders (شبیه‌ساز گزارش واقعی MT4)."""
    parts = ['<html><body><table>']
    parts.append(
        '<tr><th colspan="13">Positions</th></tr>'
        '<tr><th>Time</th><th>Position</th><th>Symbol</th><th>Type</th>'
        '<th>Volume</th><th>Price</th><th>S/L</th><th>T/P</th>'
        '<th>Time</th><th>Price</th><th>Commission</th><th>Swap</th><th>Profit</th></tr>'
    )
    for row in positions_rows:
        parts.append(f'<tr>{"".join(f"<td>{c}</td>" for c in row)}</tr>')
    parts.append(
        '<tr><th colspan="14">Orders</th></tr>'
        '<tr><th>Time</th><th>Position</th><th>Symbol</th><th>Type</th>'
        '<th>Volume</th><th>Price</th><th>S/L</th><th>T/P</th>'
        '<th>State</th><th>Time</th><th>Price</th><th>Commission</th><th>Swap</th><th>Profit</th></tr>'
    )
    for row in orders_rows:
        parts.append(f'<tr>{"".join(f"<td>{c}</td>" for c in row)}</tr>')
    parts.append('</table></body></html>')
    return "".join(parts)


def _pos_row(position="1001", sl="1990.0", pnl="10.0"):
    return [
        "2025.01.02 10:00:00", position, "XAUUSD", "buy",
        "1.00", "2000.00", sl, "2030.00",
        "2025.01.02 11:00:00", "2010.00", "-1.00", "0.00", pnl,
    ]


def _order_row(position="1001", sl="1950.0", state="filled"):
    return [
        "2025.01.02 09:00:00", position, "XAUUSD", "buy",
        "1.00", "2000.00", sl, "2030.00", state,
        "2025.01.02 09:30:00", "2010.00", "0.00", "0.00", "0.00",
    ]


def test_mt4_html_orders_used_for_initial_sl(db_session):
    """MT4 HTML با Orders: R از initial_sl (SL سفارش) محاسبه می‌شود."""
    html = _mt4_html_with_orders(
        positions_rows=[_pos_row(position="1001", sl="1990.0")],
        orders_rows=[_order_row(position="1001", sl="1950.0", state="filled")],
    )
    importer = MT4Importer(db_session, test_type="backtest")
    trades = importer.parse_html(html)
    assert len(trades) == 1
    t = trades[0]
    assert t["sl"] == 1990.0
    assert t["initial_sl"] == 1950.0
    assert t["r_multiple"] == 0.2


def test_mt4_html_no_orders_fallback_to_sl(db_session):
    """MT4 HTML بدون Orders: initial_sl = sl (fallback)."""
    html = _mt4_html_with_orders(
        positions_rows=[_pos_row(position="1001", sl="1950.0")],
        orders_rows=[],
    )
    importer = MT4Importer(db_session, test_type="backtest")
    trades = importer.parse_html(html)
    assert len(trades) == 1
    t = trades[0]
    assert t["initial_sl"] == 1950.0
    # R = (2010-2000) / (2000-1950) = 10/50 = 0.2
    assert t["r_multiple"] == pytest.approx(0.2)


def test_mt4_html_order_not_filled_ignored(db_session):
    """MT4 HTML: ردیف Orders با status غير filled نادیده گرفته می‌شود."""
    html = _mt4_html_with_orders(
        positions_rows=[_pos_row(position="1001", sl="1990.0")],
        orders_rows=[_order_row(position="1001", sl="1950.0", state="cancelled")],
    )
    importer = MT4Importer(db_session, test_type="backtest")
    trades = importer.parse_html(html)
    assert len(trades) == 1
    t = trades[0]
    assert t["initial_sl"] == 1990.0
    # R = (2010-2000) / (2000-1990) = 10/10 = 1.0
    assert t["r_multiple"] == pytest.approx(1.0)


def test_mt4_html_multiple_positions_and_orders(db_session):
    """MT4 HTML: چند معامله با تطبیق Position-ID به SL سفارش."""
    html = _mt4_html_with_orders(
        positions_rows=[
            _pos_row(position="1001", sl="1990.0"),
            _pos_row(position="1002", sl="1980.0"),
        ],
        orders_rows=[
            _order_row(position="1001", sl="1950.0", state="filled"),
            _order_row(position="1002", sl="1940.0", state="filled"),
        ],
    )
    importer = MT4Importer(db_session, test_type="backtest")
    trades = importer.parse_html(html)
    assert len(trades) == 2
    t1 = next(t for t in trades if "1001" in str(t.get("raw_data", {})))
    t2 = next(t for t in trades if "1002" in str(t.get("raw_data", {})))
    assert t1["initial_sl"] == 1950.0
    assert t2["initial_sl"] == 1940.0
# ═════════════════════════════════════════════
# PATCH — حفظ initial_sl + هشدار
# ═════════════════════════════════════════════
def test_patch_sl_does_not_change_r_when_initial_sl_exists(client, db_session):
    """تغییر SL پایانی نباید R را تغییر دهد اگر initial_sl موجود است."""
    from tests.test_import_engine import _version
    v = _version(db_session)
    resp = client.post("/api/trades/manual", json={
        "symbol": "XAUUSD", "direction": "buy",
        "open_time": "2025-01-01T10:00:00Z", "open_price": 2000.0,
        "close_time": "2025-01-01T11:00:00Z", "close_price": 2100.0, "size": 1.0,
        "sl": 1990.0, "initial_sl": 1950.0,
        "pnl": 10.0, "test_type": "backtest", "version_id": v.id,
    })
    trade_id = resp.json()["id"]
    db_session.expire_all()
    trade = db_session.get(Trade, trade_id)
    original_r = trade.r_multiple
    assert trade.sl == 1990.0
    assert trade.initial_sl == 1950.0

    resp = client.patch(f"/api/trades/{trade_id}", json={"sl": 1980.0})
    assert resp.status_code == 200
    db_session.expire_all()
    trade = db_session.get(Trade, trade_id)
    assert trade.initial_sl == 1950.0
    assert trade.sl == 1980.0
    assert trade.r_multiple == original_r


def test_patch_open_price_without_initial_sl_warns(client, db_session):
    """PATCH قیمت ورود بدون ارسال initial_sl ⇒ هشدار initial_sl_may_be_stale."""
    from tests.test_import_engine import _version
    v = _version(db_session)
    resp = client.post("/api/trades/manual", json={
        "symbol": "XAUUSD", "direction": "buy",
        "open_time": "2025-01-01T10:00:00Z", "open_price": 2000.0,
        "close_time": "2025-01-01T11:00:00Z", "close_price": 2100.0, "size": 1.0,
        "sl": 1990.0, "initial_sl": 1950.0,
        "pnl": 10.0, "test_type": "backtest", "version_id": v.id,
    })
    trade_id = resp.json()["id"]
    resp = client.patch(f"/api/trades/{trade_id}", json={"open_price": 2010.0})
    assert resp.status_code == 200
    data = resp.json()
    assert "warnings" in data
    assert "initial_sl_may_be_stale" in data["warnings"]


def test_patch_open_price_with_initial_sl_no_warn(client, db_session):
    """PATCH قیمت ورود همراه initial_sl ⇒ بدون هشدار."""
    from tests.test_import_engine import _version
    v = _version(db_session)
    resp = client.post("/api/trades/manual", json={
        "symbol": "XAUUSD", "direction": "buy",
        "open_time": "2025-01-01T10:00:00Z", "open_price": 2000.0,
        "close_time": "2025-01-01T11:00:00Z", "close_price": 2100.0, "size": 1.0,
        "sl": 1990.0, "initial_sl": 1950.0,
        "pnl": 10.0, "test_type": "backtest", "version_id": v.id,
    })
    trade_id = resp.json()["id"]
    resp = client.patch(f"/api/trades/{trade_id}", json={
        "open_price": 2010.0, "initial_sl": 1950.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    warns = data.get("warnings") or []
    assert "initial_sl_may_be_stale" not in warns


# ═════════════════════════════════════════════
# R-Multiple direction-specific
# ═════════════════════════════════════════════
def test_r_buy_risk_from_entry_minus_initial_sl():
    """Buy: Risk = open_price - initial_sl."""
    r = calculate_r_multiple("buy", 2000.0, 2100.0, 1990.0, 1950.0)
    assert r == 2.0


def test_r_sell_risk_from_initial_sl_minus_entry():
    """Sell: Risk = initial_sl - open_price."""
    r = calculate_r_multiple("sell", 2000.0, 1900.0, 2010.0, 2050.0)
    assert r == 2.0


def test_r_unchanged_when_initial_sl_equals_sl():
    """initial_sl == sl ⇒ R مثل وقتی initial_sl=None است."""
    r_with = calculate_r_multiple("buy", 2000.0, 2100.0, 1950.0, 1950.0)
    r_without = calculate_r_multiple("buy", 2000.0, 2100.0, 1950.0, None)
    assert r_with == r_without == 2.0