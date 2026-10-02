"""تست‌های فاز ۵۳.۳.۱ — R-Multiple از «Initial SL» (Soft4X).

باگ: ایمپورتر Soft4X فقط ستون `SL` را می‌خواند؛ اگر SL در طول معامله جابجا شده
باشد، R اشتباه محاسبه می‌شود. حالا ستون `Initial SL` مبناست (fallback به `SL`).
"""
import os
import tempfile

from openpyxl import Workbook

from app.services.import_service import Soft4XImporter
from app.utils.trade_metrics import calculate_r_multiple


HEADERS = [
    "Open Time", "Close Time", "Type", "Open Price", "Close Price",
    "Size", "SL", "Initial SL", "TP", "P/L", "Commission",
]


def _write_xlsx(rows, headers=HEADERS):
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


def _row(*, sl, initial_sl=None, headers=HEADERS):
    base = {
        "Open Time": "2025-01-02 10:00:00",
        "Close Time": "2025-01-02 11:00:00",
        "Type": "buy",
        "Open Price": 2000.0,
        "Close Price": 2100.0,   # move = +100
        "Size": 1.0,
        "SL": sl,
        "Initial SL": initial_sl,
        "TP": 2110.0,
        "P/L": 100.0,
        "Commission": 0.0,
    }
    return [base[h] for h in headers]


def test_r_uses_initial_sl(db_session):
    """با حضور Initial SL، R بر پایهٔ آن محاسبه می‌شود (نه SL جابجا‌شده)."""
    # SL=1990 (اگر مبنا بود R=10) ، Initial SL=1950 ⇒ R = 100/50 = 2
    path = _write_xlsx([_row(sl=1990.0, initial_sl=1950.0)])
    try:
        trades = Soft4XImporter(db_session, symbol="XAUUSD", test_type="backtest").parse_file(path)
    finally:
        os.remove(path)

    assert len(trades) == 1
    t = trades[0]
    assert t["sl"] == 1990.0
    assert t["raw_data"]["initial_sl"] == 1950.0
    assert t["r_multiple"] == 2.0


def test_r_fallback_to_sl(db_session):
    """در نبود Initial SL (ستون یا مقدار)، از SL استفاده می‌شود."""
    # ۱) بدون ستون Initial SL
    headers = [h for h in HEADERS if h != "Initial SL"]
    path = _write_xlsx([_row(sl=1950.0, headers=headers)], headers=headers)
    try:
        trades = Soft4XImporter(db_session, symbol="XAUUSD", test_type="backtest").parse_file(path)
    finally:
        os.remove(path)
    assert len(trades) == 1
    assert "initial_sl" not in trades[0]["raw_data"]
    assert trades[0]["r_multiple"] == 2.0   # 100 / 50

    # ۲) ستون هست ولی مقدارش None ⇒ همان fallback
    assert calculate_r_multiple("buy", 2000, 2100, 1990, None) == 10.0
    # ۳) تابع پایه با initial_sl صریح
    assert calculate_r_multiple("buy", 2000, 2100, 1990, 1950) == 2.0
