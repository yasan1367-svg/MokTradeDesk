"""تست‌های Phase 48a — مقایسه و رتبه‌بندی نسخه‌ها (`POST /api/analytics/compare`).

قرارداد جدید: `{comparison, test_type, filters, best}`؛ هر item دارای
`metrics` / `score` / `rank` / `reasons` است.
"""
from datetime import datetime, timezone

from app.models.strategy import AnalysisResult, AnalysisRun, Strategy, StrategyVersion
from app.services.version_score import calculate_version_score


def _iso(month: int, day: int, hour: int = 10) -> str:
    return (
        datetime(2025, month, day, hour, 0, tzinfo=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _make_version(client, db_session, name: str) -> int:
    r = client.post("/api/strategies/", json={"name": name})
    assert r.status_code == 200, r.text
    strategy_id = db_session.query(Strategy).order_by(Strategy.id.desc()).first().id

    r = client.post(
        f"/api/strategies/{strategy_id}/versions",
        json={"version_name": "v1", "test_type": "backtest"},
    )
    assert r.status_code == 200, r.text
    return db_session.query(StrategyVersion).order_by(StrategyVersion.id.desc()).first().id


def _add_trade(client, version_id, pnl, *, month=3, day=1, symbol="XAUUSD", sl=None) -> None:
    r = client.post(
        "/api/trades/manual",
        json={
            "symbol": symbol,
            "direction": "buy",
            "open_time": _iso(month, day, 10),
            "close_time": _iso(month, day, 11),
            "open_price": 2000.0,
            "close_price": 2010.0,
            "sl": sl,
            "size": 1.0,
            "pnl": pnl,
            "test_type": "backtest",
            "version_id": version_id,
        },
    )
    assert r.status_code == 200, r.text


def _analyze(client, version_id) -> None:
    r = client.post(f"/api/analytics/analyze/version/{version_id}?test_type=backtest")
    assert r.status_code == 200, r.text


def _cmp(client, version_ids, **kw):
    r = client.post("/api/analytics/compare", json={"version_ids": version_ids, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def _item(body, vid):
    return next(i for i in body["comparison"] if i["version_id"] == vid)


# ═════════════════════════════════════════════
# مقایسهٔ پایه
# ═════════════════════════════════════════════
def test_compare_two_versions(client, db_session):
    v1 = _make_version(client, db_session, "S-48a-1")
    _add_trade(client, v1, 200.0, day=1)
    _analyze(client, v1)

    v2 = _make_version(client, db_session, "S-48a-2")
    _add_trade(client, v2, -50.0, day=2)
    _analyze(client, v2)

    body = _cmp(client, [v1, v2])
    assert body["test_type"] == "BACKTEST"
    assert {i["version_id"] for i in body["comparison"]} == {v1, v2}
    assert all("metrics" in i for i in body["comparison"])
    assert all("score" in i for i in body["comparison"])
    assert sorted(i["rank"] for i in body["comparison"]) == [1, 2]
    assert body["filters"] == {"symbol": None, "date_from": None, "date_to": None}


def test_compare_ranking(client, db_session):
    """نسخهٔ با عملکرد بهتر باید rank 1 بگیرد (حتی اگر بعداً در لیست بیاید)."""
    best = _make_version(client, db_session, "S-48a-best")
    for d, p in [(1, 300.0), (2, 300.0)]:
        _add_trade(client, best, p, day=d)
    _analyze(client, best)

    worst = _make_version(client, db_session, "S-48a-worst")
    _add_trade(client, worst, -100.0, day=3)
    _analyze(client, worst)

    body = _cmp(client, [worst, best])  # ترتیب ورودی عمداً برعکس
    assert body["comparison"][0]["version_id"] == best
    assert body["comparison"][0]["rank"] == 1
    assert body["best"]["version_id"] == best


def test_compare_score_calculation(client, db_session):
    """Score هر item باید برابر تابع `calculate_version_score` باشد."""
    v1 = _make_version(client, db_session, "S-48a-sc1")
    _add_trade(client, v1, 150.0, day=1)
    _analyze(client, v1)

    v2 = _make_version(client, db_session, "S-48a-sc2")
    _add_trade(client, v2, 100.0, day=2)
    _analyze(client, v2)

    body = _cmp(client, [v1, v2])
    item = _item(body, v1)
    assert item["score"] == calculate_version_score(item["metrics"])["score"]
    assert "sample_status" in item
    assert "warnings" in item
    assert "components" in item


def test_score_metadata_reaches_comparison_in_filtered_and_unfiltered_paths(client, db_session):
    version = _make_version(client, db_session, "S-score-metadata")
    comparison_version = _make_version(client, db_session, "S-score-metadata-peer")
    _add_trade(client, version, 150.0, day=1, sl=1990.0)
    _add_trade(client, version, 100.0, day=2, sl=1990.0)
    _add_trade(client, comparison_version, 100.0, day=3, sl=1990.0)
    _analyze(client, version)
    _analyze(client, comparison_version)

    for params in ({}, {"symbol": "XAUUSD"}):
        item = _item(_cmp(client, [version, comparison_version], **params), version)
        components = item["components"]
        assert components["dd_fallback"] is True
        assert components["dd_score"] == 50.0
        assert components["r_fallback"] is False
        assert components["r_eligible"] is True
        assert components["r_valid_count"] == 2.0
        assert components["r_coverage_percent"] == 100.0
        assert components["r_penalty"] == 0.0
        assert components["r_measure"] == "gross_price_r"


def test_compare_reasons(client, db_session):
    """بهترین نسخه باید دلیل «بهترین نسخه» را داشته باشد."""
    v1 = _make_version(client, db_session, "S-48a-r1")
    _add_trade(client, v1, 500.0, day=1)
    _analyze(client, v1)

    v2 = _make_version(client, db_session, "S-48a-r2")
    _add_trade(client, v2, -100.0, day=2)
    _analyze(client, v2)

    body = _cmp(client, [v1, v2])
    best_item = _item(body, v1)
    assert best_item["reasons"]
    assert any("بالاترین امتیاز" in r["text"] for r in best_item["reasons"])
    weak = _item(body, v2)
    assert any("محدودیت داده" in r["text"] or "ضعف" in r["text"] for r in weak["reasons"])


def test_compare_pf_status_and_score_are_explicit(client, db_session):
    cases = [([100.0], "no_losses", None), ([-100.0], "finite", 0.0), ([0.0], "no_usable_pnl", None), ([], "no_usable_pnl", None)]
    for index, (pnls, status, pf) in enumerate(cases):
        version = _make_version(client, db_session, f"S-pf-status-{index}")
        for day, pnl in enumerate(pnls, 1):
            _add_trade(client, version, pnl, day=day)
        if pnls:
            _analyze(client, version)
        peer = _make_version(client, db_session, f"S-pf-peer-{index}")
        _add_trade(client, peer, 1.0, day=8)
        _analyze(client, peer)
        body = _cmp(client, [version, peer])
        item = _item(body, version)
        if not pnls:
            assert item["status"] == "missing_analysis"
            assert item.get("rank") is None
            continue
        assert item["metrics"]["profit_factor_status"] == status
        if status == "no_losses":
            assert item["metrics"]["profit_factor"] == 999.0  # compatibility field; status is authoritative
        elif pf is not None:
            assert item["metrics"]["profit_factor"] == pf


def test_tied_comparison_has_input_order_independent_tie_metadata(client, db_session):
    versions = []
    for name in ("tie-a", "tie-b"):
        version = _make_version(client, db_session, name)
        for day, pnl in enumerate([100.0, -50.0], 1):
            _add_trade(client, version, pnl, day=day)
        _analyze(client, version)
        versions.append(version)
    first = _cmp(client, versions)
    reverse = _cmp(client, list(reversed(versions)))
    assert {x["version_id"] for x in first["best_ties"]} == {x["version_id"] for x in reverse["best_ties"]}
    assert len(first["best_ties"]) == 2
    assert all(x["rank_tie"] for x in first["comparison"])


def test_fractional_pnl_pf_is_consistent_and_unrounded(client, db_session):
    version = _make_version(client, db_session, "fractional-pf")
    _add_trade(client, version, 1.004, day=1)
    _add_trade(client, version, -0.006, day=2)
    _analyze(client, version)
    peer = _make_version(client, db_session, "fractional-peer")
    _add_trade(client, peer, 0.0, day=4)
    _analyze(client, peer)
    item = _item(_cmp(client, [version, peer]), version)
    assert item["metrics"]["profit_factor"] == 167.33
    assert item["metrics"]["gross_profit"] == 1.004
    assert item["metrics"]["gross_loss"] == 0.006


def test_legacy_snapshot_pf_recovered_from_current_scoped_trades(client, db_session):
    version = _make_version(client, db_session, "legacy-pf")
    _add_trade(client, version, 2.0, day=1)
    _add_trade(client, version, -1.0, day=2)
    _analyze(client, version)
    peer = _make_version(client, db_session, "legacy-peer")
    _add_trade(client, peer, 1.0, day=7)
    _analyze(client, peer)
    analysis = db_session.query(AnalysisResult).filter(AnalysisResult.version_id == version).first()
    run = analysis.analysis_run
    run.full_metrics = {"basic": {}}
    db_session.commit()
    item = _item(_cmp(client, [version, peer]), version)
    assert item["metrics"]["profit_factor"] == 2.0
    assert item["metrics"]["profit_factor_status"] == "finite"
    assert item["components"]["pf_score"] == 40.0


def test_equal_score_secondary_reason_and_full_tie_survives_reverse(client, db_session):
    first = _make_version(client, db_session, "equal-pf-one")
    second = _make_version(client, db_session, "equal-pf-two")
    for day, pnl in enumerate([1.0, -1.0], 1):
        _add_trade(client, first, pnl, day=day)
        _add_trade(client, second, pnl, day=day)
    _analyze(client, first)
    _analyze(client, second)
    # Full equal score/PF/sample remains shared irrespective of request order.
    forward = _cmp(client, [first, second])
    reverse = _cmp(client, [second, first])
    assert [x["version_id"] for x in forward["best_ties"]] == [x["version_id"] for x in reverse["best_ties"]]
    assert len(forward["best_ties"]) == 2
    assert {x["version_id"] for x in forward["best_ties"]} == {x["version_id"] for x in reverse["best_ties"]}


def test_equal_score_pf_and_sample_decisions_are_returned_by_comparison(client, db_session):
    low_pf = _make_version(client, db_session, "equal-score-pf-six")
    high_pf = _make_version(client, db_session, "equal-score-pf-eight")
    sample_low = _make_version(client, db_session, "equal-score-sample-low")
    sample_high = _make_version(client, db_session, "equal-score-sample-high")
    for version, pnls in ((low_pf, [6, -1]), (high_pf, [8, -1]), (sample_low, [1, -1]), (sample_high, [1, -1, 1, -1])):
        for day, pnl in enumerate(pnls, 1):
            _add_trade(client, version, float(pnl), day=day)
        _analyze(client, version)
    # Force equal primary scores so the real service's secondary ordering is under test.
    for run in db_session.query(AnalysisRun).filter(AnalysisRun.version_id.in_([low_pf, high_pf, sample_low, sample_high])):
        run.full_metrics = {**(run.full_metrics or {}), "score": 90}
    db_session.commit()

    pf_body = _cmp(client, [low_pf, high_pf])
    pf_best = pf_body["best"]
    assert pf_best["version_id"] == high_pf
    explanation = " ".join(reason["text"] for reason in pf_best["reasons"])
    assert "معیار تعیین‌کننده: PF" in explanation and "6.0" in explanation and "8.0" in explanation

    sample_body = _cmp(client, [sample_low, sample_high])
    assert sample_body["best"]["version_id"] == sample_high
    sample_explanation = " ".join(reason["text"] for reason in sample_body["best"]["reasons"])
    assert "معیار تعیین‌کننده: تعداد نمونه" in sample_explanation


# ═════════════════════════════════════════════
# فیلترها
# ═════════════════════════════════════════════
def test_compare_with_symbol_filter(client, db_session):
    v1 = _make_version(client, db_session, "S-48a-sym1")
    _add_trade(client, v1, 1000.0, day=1, symbol="XAUUSD")
    _add_trade(client, v1, -800.0, day=2, symbol="EURUSD")
    _analyze(client, v1)

    v2 = _make_version(client, db_session, "S-48a-sym2")
    _add_trade(client, v2, 100.0, day=3)
    _analyze(client, v2)

    unfiltered = _item(_cmp(client, [v1, v2]), v1)["metrics"]["net_pnl"]
    assert unfiltered == 200.0  # 1000 - 800

    filtered = _item(_cmp(client, [v1, v2], symbol="XAUUSD"), v1)["metrics"]["net_pnl"]
    assert filtered == 1000.0


def test_compare_with_date_filter(client, db_session):
    v1 = _make_version(client, db_session, "S-48a-date1")
    _add_trade(client, v1, 1000.0, month=3, day=1)
    _add_trade(client, v1, -800.0, month=3, day=20)
    _analyze(client, v1)

    v2 = _make_version(client, db_session, "S-48a-date2")
    _add_trade(client, v2, 100.0, month=3, day=25)
    _analyze(client, v2)

    unfiltered = _item(_cmp(client, [v1, v2]), v1)["metrics"]["net_pnl"]
    assert unfiltered == 200.0

    filtered = _item(
        _cmp(client, [v1, v2], date_from="2025-03-01", date_to="2025-03-05"), v1
    )["metrics"]["net_pnl"]
    assert filtered == 1000.0
