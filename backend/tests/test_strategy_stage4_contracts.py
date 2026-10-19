from datetime import datetime, timezone

from app.models.strategy import (
    AnalysisResult, AnalysisRun, Strategy, StrategyVersion, TestType, Trade, TradeSource,
)


def _strategy(client, name="S4"):
    response = client.post("/api/strategies/", json={"name": name})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _version(client, strategy_id, **payload):
    response = client.post(
        f"/api/strategies/{strategy_id}/versions",
        json={"version_name": "v1", **payload},
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _trade(db, version_id):
    trade = Trade(
        version_id=version_id, symbol="XAUUSD", direction="buy",
        open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
        open_price=10, close_price=11, size=1, pnl=1,
        commission=0, swap=0, entry_sequence=1,
        source=TradeSource.MANUAL, test_type=TestType.BACKTEST,
    )
    db.add(trade)
    db.commit()
    return trade


def test_strategy_and_version_input_validation_and_patch_semantics(client, db_session):
    assert client.post("/api/strategies/", json={"name": "  "}).status_code == 422
    sid = _strategy(client, "  trimmed  ")
    assert db_session.get(Strategy, sid).name == "trimmed"
    assert client.post(f"/api/strategies/{sid}/versions", json={"version_name": "  "}).status_code == 422
    assert client.post(f"/api/strategies/{sid}/versions", json={"version_name": "v1", "status": "bogus"}).status_code == 422
    before = db_session.query(StrategyVersion).count()
    assert client.post(f"/api/strategies/{sid}/versions", json={"version_name": "bad", "test_type": "BOGUS"}).status_code == 422
    assert db_session.query(StrategyVersion).count() == before
    vid = _version(client, sid, status="APPROVED", test_type="forward")
    legacy_real = _version(client, sid, status="APPROVED", test_type="real")
    assert db_session.get(StrategyVersion, legacy_real).test_type == "real"
    assert client.patch(f"/api/strategies/versions/{vid}", json={"version_name": "  "}).status_code == 422
    assert client.patch(f"/api/strategies/versions/{vid}", json={"status": "bad"}).status_code == 422
    assert client.patch(f"/api/strategies/versions/{vid}", json={"rules_note": "changed"}).status_code == 200
    db_session.expire_all()
    version = db_session.get(StrategyVersion, vid)
    assert version.version_name == "v1" and version.status.value == "approved"
    assert version.test_type == "forward" and version.rules_note == "changed"


def test_version_create_and_patch_persist_status_and_label_without_reclassifying_trades(client, db_session):
    sid = _strategy(client, "version-persistence")
    created = client.post(f"/api/strategies/{sid}/versions", json={
        "version_name": "v", "status": "approved", "test_type": "real",
    })
    assert created.status_code == 200, created.text
    vid = created.json()["id"]
    trade = _trade(db_session, vid)
    assert db_session.get(StrategyVersion, vid).test_type == "real"
    assert trade.test_type == TestType.BACKTEST

    patched = client.patch(f"/api/strategies/versions/{vid}", json={"status": "archived"})
    assert patched.status_code == 200, patched.text
    db_session.expire_all()
    saved = db_session.get(StrategyVersion, vid)
    assert saved.status.value == "archived" and saved.test_type == "real"
    patched = client.patch(f"/api/strategies/versions/{vid}", json={"test_type": "forward"})
    assert patched.status_code == 200, patched.text
    db_session.expire_all()
    saved = db_session.get(StrategyVersion, vid)
    assert saved.test_type == "forward"
    assert db_session.get(Trade, trade.id).test_type == TestType.BACKTEST
    assert client.patch(f"/api/strategies/versions/{vid}", json={"test_type": "bogus"}).status_code == 422
    assert client.patch(f"/api/strategies/versions/{vid}", json={"rules_note": "only rules"}).status_code == 200
    assert db_session.get(StrategyVersion, vid).test_type == "forward"


def test_all_versions_exposes_label_parent_and_closed_actual_type_counts(client, db_session):
    sid = _strategy(client, "version-contract")
    parent = _version(client, sid, test_type="real")
    child_response = client.post(f"/api/strategies/versions/{parent}/fork", json={"version_name": "child"})
    assert child_response.status_code == 200, child_response.text
    child = child_response.json()["id"]
    _trade(db_session, parent)
    closed_forward = Trade(version_id=parent, symbol="XAUUSD", direction="buy", open_time=datetime(2025, 1, 1, tzinfo=timezone.utc), close_time=datetime(2025, 1, 2, tzinfo=timezone.utc), open_price=1, close_price=2, size=1, source=TradeSource.MANUAL, test_type=TestType.FORWARD)
    open_trade = Trade(version_id=parent, symbol="XAUUSD", direction="buy", open_time=datetime(2025, 1, 1, tzinfo=timezone.utc), open_price=1, size=1, source=TradeSource.MANUAL, test_type=TestType.FORWARD)
    db_session.add_all([closed_forward, open_trade])
    db_session.commit()
    rows = {row["id"]: row for row in client.get("/api/strategies/versions/all").json()}
    assert rows[parent]["test_type"] == "real"
    assert rows[parent]["forked_from_version_id"] is None
    assert rows[parent]["trade_counts_by_test_type"] == {"backtest": 1, "forward": 1}
    assert rows[child]["forked_from_version_id"] == parent


def test_fork_validation_and_contract_distinguishes_version_label_from_trade_type(client, db_session):
    sid = _strategy(client)
    vid = _version(client, sid, test_type="forward", status="research")
    assert client.post(f"/api/strategies/versions/{vid}/fork", json={"version_name": " "}).status_code == 422
    assert client.post(f"/api/strategies/versions/{vid}/fork", json={"version_name": "child", "status": "invalid"}).status_code == 422
    before = db_session.query(StrategyVersion).count()
    assert client.post(f"/api/strategies/versions/{vid}/fork", json={"version_name": "bad", "test_type": "BOGUS"}).status_code == 422
    assert db_session.query(StrategyVersion).count() == before
    response = client.post(f"/api/strategies/versions/{vid}/fork", json={"version_name": " child ", "status": "approved"})
    assert response.status_code == 200, response.text
    child = db_session.get(StrategyVersion, response.json()["id"])
    assert child.version_name == "child" and child.test_type == "forward"

    ui_payload = {"version_name": "Real label", "test_type": "real"}
    created = client.post(f"/api/strategies/{sid}/versions", json=ui_payload)
    assert created.status_code == 200, created.text
    assert created.json()["test_type"] == "real"
    forked = client.post(f"/api/strategies/versions/{vid}/fork", json={"version_name": "Real fork", "test_type": "real"})
    assert forked.status_code == 200, forked.text
    assert db_session.get(StrategyVersion, forked.json()["id"]).test_type == "real"


def test_fork_default_name_is_exactly_version_name_plus_fork(client):
    sid = _strategy(client, "fork-default")
    vid = _version(client, sid, version_name="v2")
    response = client.post(f"/api/strategies/versions/{vid}/fork")
    assert response.status_code == 200, response.text
    assert response.json()["version_name"] == "v2 - Fork"


def test_strategy_endpoints_use_authoritative_schema_contracts(client):
    from app.api.strategies import ForkRequest as ApiForkRequest, VersionCreate as ApiVersionCreate
    from app.schemas.strategy import ForkRequest, VersionCreate

    assert ApiForkRequest is ForkRequest
    assert ApiVersionCreate is VersionCreate
    sid = _strategy(client, "contract")
    created = client.post(f"/api/strategies/{sid}/versions", json={
        "version_name": "v", "test_type": "forward", "status": "approved",
    })
    assert created.status_code == 200, created.text
    body = created.json()
    assert {"test_type", "forked_from_version_id", "trades_count", "trade_counts_by_test_type"} <= body.keys()


def test_compare_rejects_invalid_filters_duplicate_ids_and_nonexistent_ids(client):
    sid = _strategy(client)
    first = _version(client, sid)
    second = _version(client, sid, version_name="v2")
    url = "/api/analytics/compare"
    for payload in (
        {"version_ids": [first, second], "test_type": "MIXED"},
        {"version_ids": [first, first]},
        {"version_ids": [first, second], "date_from": "2025-02-30"},
        {"version_ids": [first, second], "date_from": "2025-04-02", "date_to": "2025-04-01"},
        {"version_ids": [True, second]},
        {"version_ids": [1.5, second]},
    ):
        assert client.post(url, json=payload).status_code == 422
    assert client.post(url, json={"version_ids": [first, 999999]}).status_code == 404
    valid = client.post(url, json={"version_ids": [first, second], "test_type": "forward"})
    assert valid.status_code == 200, valid.text
    assert valid.json()["test_type"] == "FORWARD"
    legacy = client.post(url, json={"version_ids": [first, second], "test_type": None})
    assert legacy.status_code == 200, legacy.text


def test_fork_dependency_prevents_deleting_parent_and_dependency_free_version_deletes(client, db_session):
    sid = _strategy(client)
    parent = _version(client, sid)
    fork_response = client.post(f"/api/strategies/versions/{parent}/fork", json={"version_name": "child"})
    assert fork_response.status_code == 200, fork_response.text
    child = fork_response.json()["id"]
    response = client.delete(f"/api/strategies/versions/{parent}")
    assert response.status_code == 409
    assert db_session.get(StrategyVersion, parent) is not None
    assert client.delete(f"/api/strategies/versions/{child}").status_code == 200
    assert client.delete(f"/api/strategies/versions/{parent}").status_code == 200


def test_rule_edit_invalidates_analysis_and_snapshot_preserves_original_rules(client, db_session):
    from app.models.strategy import AnalysisRun

    sid = _strategy(client)
    created = client.post(
        f"/api/strategies/{sid}/versions",
        json={"version_name": "v1", "rules_note": "original rule"},
    )
    assert created.status_code == 200, created.text
    vid = created.json()["id"]
    _trade(db_session, vid)
    analyzed = client.post(f"/api/analytics/analyze/version/{vid}?test_type=backtest")
    assert analyzed.status_code == 200, analyzed.text
    run_id = analyzed.json()["run_id"]
    snapshot = db_session.get(AnalysisRun, run_id).filters_snapshot
    assert snapshot["rules_snapshot"] == {"rules_note": "original rule"}
    assert client.patch(f"/api/strategies/versions/{vid}", json={"rules_note": "edited rule"}).status_code == 200
    result = client.get(f"/api/analytics/{vid}?test_type=backtest")
    assert result.status_code == 404
    assert db_session.get(AnalysisRun, run_id).filters_snapshot["rules_snapshot"] == {"rules_note": "original rule"}


def test_strategy_delete_conflicts_for_fork_and_history_even_without_current_result(client, db_session):
    sid = _strategy(client)
    parent = _version(client, sid)
    child_response = client.post(f"/api/strategies/versions/{parent}/fork", json={"version_name": "child"})
    assert child_response.status_code == 200
    response = client.delete(f"/api/strategies/{sid}")
    assert response.status_code == 409 and "fork" in response.json()["detail"]
    db_session.query(StrategyVersion).filter(StrategyVersion.id == child_response.json()["id"]).delete()
    db_session.commit()
    trade = _trade(db_session, parent)
    assert client.post(f"/api/analytics/analyze/version/{parent}?test_type=backtest").status_code == 200
    db_session.delete(trade)
    result = db_session.query(AnalysisResult).filter_by(version_id=parent).one()
    run_id = result.analysis_run_id
    db_session.delete(result)
    db_session.commit()
    response = client.delete(f"/api/strategies/{sid}")
    assert response.status_code == 409
    assert db_session.get(AnalysisRun, run_id) is not None