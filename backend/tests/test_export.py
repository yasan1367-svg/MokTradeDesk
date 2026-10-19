"""Dashboard PDF uses the requested Analytics population and labels."""
from datetime import datetime, timedelta, timezone

import pytest

from app.api import analytics
from app.models.finance import Currency
from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource


def _capture(monkeypatch):
    from reportlab.platypus import SimpleDocTemplate

    captured = {}
    original_data = analytics.get_dashboard_data
    original_build = SimpleDocTemplate.build

    def data(**kwargs):
        captured["params"] = kwargs
        captured["data"] = original_data(**kwargs)
        return captured["data"]

    def build(doc, flowables, *args, **kwargs):
        captured["header"] = "\n".join(
            item.getPlainText() for item in flowables if hasattr(item, "getPlainText")
        )
        return original_build(doc, flowables, *args, **kwargs)

    monkeypatch.setattr(analytics, "get_dashboard_data", data)
    monkeypatch.setattr(SimpleDocTemplate, "build", build)
    return captured


def test_export_dashboard_pdf_respects_filters(client, db_session, monkeypatch):
    strategy = Strategy(name="PDF population")
    db_session.add(strategy)
    db_session.flush()
    versions = [StrategyVersion(strategy_id=strategy.id, version_name=name) for name in ("selected", "other")]
    db_session.add_all(versions)
    db_session.flush()
    start = datetime(2026, 10, 7, 20, 30, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    for close, pnl, kind, version in [
        (start, 10, TestType.BACKTEST, versions[0]),
        (end - timedelta(microseconds=1), 20, TestType.BACKTEST, versions[0]),
        (start - timedelta(microseconds=1), 1000, TestType.BACKTEST, versions[0]),
        (end, 2000, TestType.BACKTEST, versions[0]),
        (start, 4000, TestType.FORWARD, versions[0]),
        (start, 8000, TestType.BACKTEST, versions[1]),
        (None, 16000, TestType.BACKTEST, versions[0]),
    ]:
        db_session.add(Trade(
            version_id=version.id, symbol="XAUUSD", direction="buy",
            open_time=start - timedelta(hours=1), close_time=close,
            open_price=2000, close_price=2000 if close else None, size=1,
            pnl=pnl, commission=0, swap=0, source=TradeSource.MANUAL, test_type=kind,
        ))
    db_session.commit()
    captured = _capture(monkeypatch)
    params = {
        "date_from": "2026-10-08", "date_to": "2026-10-08",
        "scope": "backtest", "currency": "USDT", "version_id": versions[0].id,
    }
    response = client.get("/api/export/dashboard/pdf", params=params)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert captured["data"]["summary"]["net_pnl"] == 30
    assert captured["data"]["summary"]["closed_trades"] == 2
    for key, value in params.items():
        assert captured["params"][key] == value
    for marker in ("Date from: 2026-10-08", "Date to: 2026-10-08", "Scope: backtest",
                   "Currency: USDT", f"Version: {versions[0].id}", "generated_at (UTC):"):
        assert marker in captured["header"]


@pytest.mark.parametrize("params,currency,scope", [
    ({}, Currency.USDT, "real"),
    ({"currency": "USD", "scope": "all"}, Currency.USD, "all"),
])
def test_export_dashboard_defaults_and_currency(client, monkeypatch, params, currency, scope):
    captured = _capture(monkeypatch)
    response = client.get("/api/export/dashboard/pdf", params=params)
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF-")
    assert captured["params"]["currency"] == currency
    assert captured["params"]["scope"] == scope
    assert captured["params"]["version_id"] is None
    assert f"Currency: {currency.value}" in captured["header"]
    assert "Version: All" in captured["header"]


@pytest.mark.parametrize("params,status", [
    ({"scope": "invalid"}, 400),
    ({"currency": "invalid"}, 422),
    ({"version_id": "invalid"}, 422),
])
def test_export_dashboard_validates_filters(client, params, status):
    assert client.get("/api/export/dashboard/pdf", params=params).status_code == status