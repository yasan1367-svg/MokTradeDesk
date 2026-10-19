from datetime import datetime, timezone
import threading

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, enable_sqlite_pragmas
from app.models.strategy import (
    AnalysisResult, AnalysisRun, AnalysisScopeRecord, Strategy, StrategyVersion,
    TestType, Trade, TradeSource,
)
from app.services.analysis_service import AnalysisService, check_analysis_freshness, AnalysisStaleError


def _seed(db):
    strategy = Strategy(name="atomic")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v1", rules_note="rule A")
    db.add(version)
    db.flush()
    trade = Trade(
        version_id=version.id, symbol="XAUUSD", direction="buy",
        open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
        open_price=10, close_price=11, size=1, pnl=1,
        commission=0, swap=0, entry_sequence=1,
        source=TradeSource.MANUAL, test_type=TestType.BACKTEST,
    )
    db.add(trade)
    db.commit()
    return version.id


def test_failure_injection_preserves_previous_result_and_history(db_session, monkeypatch):
    version_id = _seed(db_session)
    first = AnalysisService(db_session).analyze_version(version_id, TestType.BACKTEST)
    db_session.commit()
    old_result_id = first["result"].id
    old_run_id = first["run_id"]
    old_scope_id = first["scope_id"]
    flush = db_session.flush
    calls = 0

    def failing_flush(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise RuntimeError("injected failure while replacing analysis")
        return flush(*args, **kwargs)

    monkeypatch.setattr(db_session, "flush", failing_flush)
    with pytest.raises(RuntimeError, match="injected failure"):
        AnalysisService(db_session).analyze_version(version_id, TestType.BACKTEST)
    monkeypatch.setattr(db_session, "flush", flush)
    assert db_session.query(AnalysisResult).filter_by(id=old_result_id).one().analysis_run_id == old_run_id
    assert db_session.query(AnalysisRun).filter_by(id=old_run_id).count() == 1
    assert db_session.query(AnalysisScopeRecord).filter_by(id=old_scope_id).count() == 1


def test_new_analysis_snapshot_contains_provenance_and_versioned_fingerprint(db_session):
    version_id = _seed(db_session)
    result = AnalysisService(db_session).analyze_version(version_id, TestType.BACKTEST)
    snapshot = db_session.query(AnalysisRun).filter_by(id=result["run_id"]).one().filters_snapshot
    assert snapshot["trade_fingerprint_format"] == 3
    assert snapshot["trade_freshness_fingerprint"]
    assert snapshot["rules_snapshot"] == {"rules_note": "rule A"}
    assert snapshot["rules_hash"]
    assert snapshot["analysis_engine_version"]
    assert snapshot["score_policy_version"]
    assert snapshot["test_type"] == "BACKTEST"
    assert snapshot["provenance_status"] == "complete"
    check_analysis_freshness(db_session, version_id, result["result"].scope_key, result["result"])


def test_legacy_snapshot_is_not_certified_fresh(db_session):
    version_id = _seed(db_session)
    analyzed = AnalysisService(db_session).analyze_version(version_id, TestType.BACKTEST)
    run = db_session.query(AnalysisRun).filter_by(id=analyzed["run_id"]).one()
    run.filters_snapshot = {"scope": "version", "scope_key": analyzed["result"].scope_key}
    db_session.commit()
    with pytest.raises(AnalysisStaleError, match="فاقد fingerprint"):
        check_analysis_freshness(db_session, version_id, analyzed["result"].scope_key, analyzed["result"])


def test_equal_timestamp_r_and_symbol_edits_invalidate_current_fingerprint(db_session):
    from app.services.analysis_service import _trade_freshness_fingerprint

    version_id = _seed(db_session)
    trade = db_session.query(Trade).filter_by(version_id=version_id).one()
    initial = _trade_freshness_fingerprint([trade])
    trade.r_multiple = 2.25
    db_session.commit()
    assert _trade_freshness_fingerprint([trade]) != initial
    after_r = _trade_freshness_fingerprint([trade])
    trade.symbol = "EURUSD"
    db_session.commit()
    assert _trade_freshness_fingerprint([trade]) != after_r


def test_open_time_edit_invalidates_get_and_both_comparison_modes(client, db_session):
    version_id = _seed(db_session)
    other_id = _seed(db_session)
    trade = db_session.query(Trade).filter_by(version_id=version_id).one()
    assert client.post(f"/api/analytics/analyze/version/{version_id}?test_type=backtest").status_code == 200
    assert client.post(f"/api/analytics/analyze/version/{other_id}?test_type=backtest").status_code == 200
    assert client.get(f"/api/analytics/{version_id}?test_type=backtest").status_code == 200
    assert client.post("/api/analytics/compare", json={"version_ids": [version_id, other_id], "test_type": "BACKTEST"}).status_code == 200
    assert client.post("/api/analytics/compare", json={"version_ids": [version_id, other_id], "test_type": None}).status_code == 200
    trade.open_time = datetime(2025, 1, 1, 11, tzinfo=timezone.utc)
    db_session.commit()
    assert client.get(f"/api/analytics/{version_id}?test_type=backtest").status_code == 404
    for test_type in ("BACKTEST", None):
        response = client.post("/api/analytics/compare", json={"version_ids": [version_id, other_id], "test_type": test_type})
        assert response.status_code == 200, response.text
        item = next(row for row in response.json()["comparison"] if row["version_id"] == version_id)
        assert item.get("stale") is True or item.get("error")


def test_caller_transaction_rollback_commit_and_replacement(db_session):
    version_id = _seed(db_session)
    db_session.close()
    with pytest.raises(RuntimeError):
        with db_session.begin():
            AnalysisService(db_session).analyze_version(version_id, TestType.BACKTEST)
            raise RuntimeError("caller rollback")
    assert db_session.query(AnalysisResult).filter_by(version_id=version_id).count() == 0
    assert db_session.query(AnalysisRun).filter_by(version_id=version_id).count() == 0
    db_session.rollback()
    db_session.close()

    first = AnalysisService(db_session).analyze_version(version_id, TestType.BACKTEST)
    previous = first["result"].id
    db_session.commit()
    db_session.close()
    with pytest.raises(RuntimeError):
        with db_session.begin():
            AnalysisService(db_session).analyze_version(version_id, TestType.BACKTEST)
            raise RuntimeError("caller rollback replacement")
    db_session.expire_all()
    assert db_session.query(AnalysisResult).filter_by(version_id=version_id).one().id == previous
    db_session.rollback()
    db_session.close()
    with db_session.begin():
        AnalysisService(db_session).analyze_version(version_id, TestType.BACKTEST)
    assert db_session.query(AnalysisResult).filter_by(version_id=version_id).count() == 1


def test_api_analysis_is_visible_from_independent_session(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db

    engine = create_engine(f"sqlite:///{(tmp_path / 'api-visible.db').as_posix()}", connect_args={"check_same_thread": False})
    from app.core.database import enable_sqlite_pragmas
    enable_sqlite_pragmas(engine)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False)
    seed = sessions()
    version_id = _seed(seed)
    seed.close()

    def override():
        session = sessions()
        try:
            yield session
        finally:
            session.close()
    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            response = client.post(f"/api/analytics/analyze/version/{version_id}?test_type=backtest")
            assert response.status_code == 200, response.text
        verify = sessions()
        try:
            assert verify.query(AnalysisResult).filter_by(version_id=version_id).count() == 1
            assert verify.query(AnalysisRun).filter_by(version_id=version_id).count() == 1
        finally:
            verify.close()
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_personal_and_prop_analysis_persist_after_session_close(tmp_path):
    from app.models.prop import PropAccount, PropFirm, PropStage, StageStatus, StageType
    from app.models.trading import Broker, PersonalTradingAccount
    from app.models.finance import Currency

    engine = create_engine(f"sqlite:///{(tmp_path / 'scope-visible.db').as_posix()}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False)
    db = sessions()
    broker = Broker(name="broker")
    db.add(broker)
    db.flush()
    account = PersonalTradingAccount(broker_id=broker.id, account_number="A", currency=Currency.USDT,
                                    initial_balance=1000, current_balance=1000)
    firm = PropFirm(name="firm")
    db.add_all([account, firm])
    db.flush()
    prop = PropAccount(prop_firm_id=firm.id, account_label="prop", currency=Currency.USDT)
    db.add(prop)
    db.flush()
    stage = PropStage(prop_account_id=prop.id, stage_type=StageType.STAGE_1,
                      status=StageStatus.ACTIVE, initial_balance=1000)
    db.add(stage)
    db.flush()
    for account_id, stage_id, tt in ((account.id, None, TestType.REAL_PERSONAL), (None, stage.id, TestType.REAL_PROP)):
        from app.models.strategy import Strategy, StrategyVersion
        strategy = db.query(Strategy).first()
        if strategy is None:
            strategy = Strategy(name="scope")
            db.add(strategy)
            db.flush()
        version = db.query(StrategyVersion).filter_by(strategy_id=strategy.id).first()
        if version is None:
            version = StrategyVersion(strategy_id=strategy.id, version_name="scope")
            db.add(version)
            db.flush()
        trade = Trade(version_id=version.id, personal_trading_account_id=account_id, prop_stage_id=stage_id,
                      symbol="XAUUSD", direction="buy", open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
                      close_time=datetime(2025, 1, 2, tzinfo=timezone.utc), open_price=10, close_price=11,
                      size=1, pnl=1, commission=0, swap=0, entry_sequence=1,
                      source=TradeSource.MANUAL, test_type=tt)
        db.add(trade)
    account_id, stage_id = account.id, stage.id
    db.commit()
    AnalysisService(db).analyze_personal_account(account_id)
    AnalysisService(db).analyze_prop_stage(stage_id)
    db.close()
    verify = sessions()
    try:
        assert verify.query(AnalysisResult).filter_by(personal_trading_account_id=account_id).count() == 1
        assert verify.query(AnalysisResult).filter_by(scope_key=str(stage_id)).count() == 1
    finally:
        verify.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_no_trade_cleanup_persists_for_service_owned_transaction(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'cleanup-visible.db').as_posix()}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False)
    seed = sessions()
    version_id = _seed(seed)
    analyzed = AnalysisService(seed).analyze_version(version_id, TestType.BACKTEST)
    result_id, run_id = analyzed["result"].id, analyzed["run_id"]
    seed.commit()
    seed.query(Trade).filter_by(version_id=version_id).delete()
    seed.commit()
    seed.close()
    service = sessions()
    with pytest.raises(ValueError, match="معاملات بک"):
        AnalysisService(service).analyze_version(version_id, TestType.BACKTEST)
    service.close()
    verify = sessions()
    try:
        assert verify.query(AnalysisResult).filter_by(id=result_id).count() == 0
        assert verify.query(AnalysisRun).filter_by(id=run_id).count() == 1
    finally:
        verify.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_fingerprint_isolated_by_explicit_test_type(db_session):
    version_id = _seed(db_session)
    trade = db_session.query(Trade).filter_by(version_id=version_id).one()
    analyzed = AnalysisService(db_session).analyze_version(version_id, TestType.BACKTEST)
    trade.test_type = TestType.FORWARD
    db_session.commit()
    with pytest.raises(AnalysisStaleError):
        check_analysis_freshness(db_session, version_id, analyzed["result"].scope_key, analyzed["result"])


def test_file_sqlite_separate_sessions_competing_analysis_preserves_history(tmp_path):
    database_path = tmp_path / "analysis-race.db"
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 5},
    )
    enable_sqlite_pragmas(engine)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False)
    seed = sessions()
    version_id = _seed(seed)
    first = AnalysisService(seed).analyze_version(version_id, TestType.BACKTEST)
    seed.close()

    barrier = threading.Barrier(2)
    outcomes = []
    lock = threading.Lock()

    def analyze():
        session = sessions()
        try:
            barrier.wait()
            outcome = AnalysisService(session).analyze_version(version_id, TestType.BACKTEST)
            value = ("ok", outcome["run_id"])
        except Exception as exc:  # SQLite may serialize or reject the competing writer.
            session.rollback()
            value = ("error", type(exc).__name__)
        finally:
            session.close()
        with lock:
            outcomes.append(value)

    workers = [threading.Thread(target=analyze) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)
    assert all(not worker.is_alive() for worker in workers)
    assert len(outcomes) == 2
    assert all(item[0] in {"ok", "error"} for item in outcomes)
    verify = sessions()
    try:
        assert verify.query(AnalysisRun).filter_by(id=first["run_id"]).count() == 1
        assert verify.query(AnalysisResult).filter_by(version_id=version_id).count() == 1
        assert verify.query(AnalysisRun).filter_by(version_id=version_id).count() >= 2
        assert verify.query(AnalysisScopeRecord).filter_by(strategy_version_id=version_id).count() >= 2
    finally:
        verify.close()
        Base.metadata.drop_all(engine)
        engine.dispose()