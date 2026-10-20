"""تست‌های اندپوینت و سرویس استیتمنت رسمی (Institutional Statement)"""
from datetime import datetime, timezone
import pytest
from app.models.strategy import Strategy, StrategyVersion, Trade, TestType, TradeSource


def test_statement_empty(client, db_session):
    """استیتمنت در زمان نبود معامله پاسخی معتبر و بدون ارور می‌دهد"""
    res = client.get("/api/statement/data?trader_name=Yasan&initial_balance=10000")
    assert res.status_code == 200
    data = res.json()
    assert data["credentials"]["trader_name"] == "Yasan"
    assert data["credentials"]["initial_balance"] == 10000.0
    assert data["credentials"]["current_balance"] == 10000.0
    assert data["credentials"]["verification_hash"].startswith("MTD-AUDIT-")
    assert data["metrics"]["total_trades"] == 0
    assert data["metrics"]["net_pnl"] == 0.0
    assert len(data["equity_curve"]) == 1


def test_statement_with_trades(client, db_session):
    """استیتمنت محاسبات دقیق شاخص‌های نهادی، ماتریس ماهانه و تفکیک لانگ/شورت را برمی‌گرداند"""
    strat = Strategy(name="Institutional Strategy")
    db_session.add(strat)
    db_session.flush()

    ver = StrategyVersion(strategy_id=strat.id, version_name="v1.0")
    db_session.add(ver)
    db_session.flush()

    # ایجاد چند معامله در ماه‌های مختلف
    t1 = Trade(
        version_id=ver.id,
        symbol="EURUSD",
        direction="buy",
        open_time=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
        close_time=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        open_price=1.0500,
        close_price=1.0600,
        size=1.0,
        pnl=100.0,
        commission=-5.0,
        swap=-2.0,
        r_multiple=2.0,
        source=TradeSource.MANUAL,
        test_type=TestType.FORWARD,
    )
    t2 = Trade(
        version_id=ver.id,
        symbol="EURUSD",
        direction="sell",
        open_time=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
        close_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        open_price=1.0600,
        close_price=1.0650,
        size=1.0,
        pnl=-50.0,
        commission=-5.0,
        swap=0.0,
        r_multiple=-1.0,
        source=TradeSource.MANUAL,
        test_type=TestType.FORWARD,
    )
    t3 = Trade(
        version_id=ver.id,
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2026, 2, 5, 10, 0, tzinfo=timezone.utc),
        close_time=datetime(2026, 2, 5, 14, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2020.0,
        size=0.5,
        pnl=200.0,
        commission=-10.0,
        swap=-1.0,
        r_multiple=3.0,
        source=TradeSource.MANUAL,
        test_type=TestType.FORWARD,
    )
    db_session.add_all([t1, t2, t3])
    db_session.commit()

    res = client.get("/api/statement/data?initial_balance=10000&trader_name=LeadTrader&account_id=ACC-99")
    assert res.status_code == 200
    data = res.json()

    # t1: 100 - 5 - 2 = +93
    # t2: -50 - 5 = -55
    # t3: 200 - 10 - 1 = +189
    # Total PnL = 93 - 55 + 189 = 227
    assert data["metrics"]["total_trades"] == 3
    assert data["metrics"]["winning_trades"] == 2
    assert data["metrics"]["losing_trades"] == 1
    assert data["metrics"]["net_pnl"] == 227.0
    assert data["credentials"]["current_balance"] == 10227.0
    assert data["metrics"]["return_pct"] == 2.27

    # Long vs Short
    assert data["long_short"]["long_trades"] == 2
    assert data["long_short"]["short_trades"] == 1
    assert data["long_short"]["long_wins"] == 2
    assert data["long_short"]["short_wins"] == 0

    # Monthly performance matrix (Year 2026 has Jan and Feb)
    assert len(data["monthly_matrix"]) == 1
    m2026 = data["monthly_matrix"][0]
    assert m2026["year"] == 2026
    assert m2026["months"]["Jan"] is not None  # Jan pnl = 93 - 55 = 38 -> 0.38%
    assert m2026["months"]["Feb"] is not None  # Feb pnl = 189 -> 1.89%
    assert m2026["months"]["Mar"] is None

    # Top symbols
    assert len(data["top_symbols"]) >= 2
    symbols = [s["symbol"] for s in data["top_symbols"]]
    assert "EURUSD" in symbols
    assert "XAUUSD" in symbols


def test_statement_pdf_generation(client, db_session):
    """تولید PDF استیتمنت به دو زبان انگلیسی و فارسی بدون خطا و با فرمت معتبر PDF انجام می‌شود"""
    # تست انگلیسی
    res_en = client.get("/api/statement/pdf?lang=en&initial_balance=10000&trader_name=Yasan")
    assert res_en.status_code == 200
    assert res_en.headers["content-type"] == "application/pdf"
    assert res_en.content[:4] == b"%PDF"

    # تست فارسی
    res_fa = client.get("/api/statement/pdf?lang=fa&initial_balance=10000&trader_name=یاسان")
    assert res_fa.status_code == 200
    assert res_fa.headers["content-type"] == "application/pdf"
    assert res_fa.content[:4] == b"%PDF"
