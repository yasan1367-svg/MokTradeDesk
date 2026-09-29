"""تست‌های Phase 34/35 — Analysis Context & AnalysisRun (افزودنی).

پوشش:
- جدول جدید `analysis_scopes` (مدل `AnalysisScopeRecord`)
- ستون‌های افزوده‌شده به `analysis_runs` (scope_id / filters_snapshot / trade_count / status)
- اتصال `analysis_results.analysis_run_id` به اجرا
- قانون «Run #1 ثابت، Trade جدید ⇒ Run #2 جدا»
- عدم رگرسیون تحلیل موجود (`AnalysisService.analyze_version`)
"""
from datetime import datetime, timezone

from app.models.strategy import (
    Strategy, StrategyVersion, Trade, TradeSource, TestType,
    AnalysisScope, AnalysisStatus, AnalysisScopeRecord, AnalysisRun, AnalysisResult,
)
from app.services.analysis_service import AnalysisService


def _version(db, name="v1"):
    s = Strategy(name=f"S-{name}")
    db.add(s)
    db.flush()
    v = StrategyVersion(strategy_id=s.id, version_name=name)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _trade(db, pnl, day, version_id, sample_type=TestType.BACKTEST):
    db.add(Trade(
        symbol="XAUUSD", direction="buy",
        open_time=datetime(2025, 1, day, 9, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, day, 10, 0, tzinfo=timezone.utc),
        open_price=2000.0, close_price=2001.0, size=1.0, pnl=pnl,
        source=TradeSource.MANUAL, test_type=sample_type, version_id=version_id,
    ))
    db.commit()


# ═════════════════════════════════════════════
# فاز ۳۴ — AnalysisScopeRecord
# ═════════════════════════════════════════════
def test_analysis_scope_record_created(db_session):
    v = _version(db_session)
    scope = AnalysisScopeRecord(
        strategy_version_id=v.id,
        trade_type=TestType.BACKTEST,
        is_deleted_filter=False,
    )
    db_session.add(scope)
    db_session.commit()
    db_session.refresh(scope)

    assert scope.id is not None
    assert scope.trade_type == TestType.BACKTEST
    assert scope.is_deleted_filter is False
    assert scope.created_at is not None


def test_analysis_scope_record_with_filters(db_session):
    v = _version(db_session)
    scope = AnalysisScopeRecord(
        strategy_version_id=v.id,
        trade_type=TestType.FORWARD,
        from_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        to_date=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )
    db_session.add(scope)
    db_session.commit()
    db_session.refresh(scope)

    assert scope.version.id == v.id
    assert scope.from_date is not None and scope.to_date is not None


# ═════════════════════════════════════════════
# فاز ۳۵ — AnalysisRun & AnalysisResult
# ═════════════════════════════════════════════
def test_analysis_run_scope_link_and_fields(db_session):
    v = _version(db_session)
    scope = AnalysisScopeRecord(strategy_version_id=v.id, trade_type=TestType.BACKTEST)
    db_session.add(scope)
    db_session.commit()

    run = AnalysisRun(
        scope=AnalysisScope.VERSION, scope_key=str(v.id), version_id=v.id,
        scope_id=scope.id, filters_snapshot={"from": "2025-01-01"},
        trade_count=5, status=AnalysisStatus.COMPLETED,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    assert run.scope_id == scope.id
    assert run.scope_record.id == scope.id
    assert run.filters_snapshot == {"from": "2025-01-01"}
    assert run.trade_count == 5
    assert run.status == AnalysisStatus.COMPLETED


def test_analysis_run_default_status_pending(db_session):
    v = _version(db_session)
    run = AnalysisRun(scope=AnalysisScope.VERSION, scope_key="x", version_id=v.id)
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    assert run.status == AnalysisStatus.PENDING
    assert run.trade_count == 0
    assert run.scope_id is None


def test_analysis_result_links_run(db_session):
    v = _version(db_session)
    run = AnalysisRun(
        scope=AnalysisScope.VERSION, scope_key=str(v.id), version_id=v.id,
        status=AnalysisStatus.COMPLETED,
    )
    db_session.add(run)
    db_session.commit()

    result = AnalysisResult(
        scope=AnalysisScope.VERSION, scope_key=str(v.id), version_id=v.id,
        total_trades=2, win_rate=50.0, analysis_run_id=run.id,
    )
    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)

    assert result.analysis_run_id == run.id
    assert result.analysis_run.id == run.id


# ═════════════════════════════════════════════
# قانون: Run #1 ثابت، Trade جدید ⇒ Run #2 جدا (بدون رگرسیون)
# ═════════════════════════════════════════════
def test_runs_are_separate_history(db_session):
    v = _version(db_session)
    _trade(db_session, 100, 1, v.id)

    svc = AnalysisService(db_session)
    svc.analyze_version(v.id)

    # معامله‌ی جدید (بدون حذف Run #1)
    _trade(db_session, 50, 2, v.id)
    svc.analyze_version(v.id)

    runs = (
        db_session.query(AnalysisRun)
        .filter(AnalysisRun.version_id == v.id)
        .order_by(AnalysisRun.id)
        .all()
    )
    assert len(runs) == 2
    assert runs[0].total_trades == 1
    assert runs[1].total_trades == 2


def test_existing_analyze_version_still_works(db_session):
    v = _version(db_session)
    _trade(db_session, 100, 1, v.id)
    _trade(db_session, -40, 2, v.id)

    svc = AnalysisService(db_session)
    out = svc.analyze_version(v.id)

    assert out["run_id"] is not None
    result = out["result"]
    assert result.total_trades == 2
    assert result.win_rate == 50.0

    current = (
        db_session.query(AnalysisResult)
        .filter(AnalysisResult.scope == AnalysisScope.VERSION)
        .all()
    )
    assert len(current) == 1


# ═════════════════════════════════════════════
# تکمیلی فاز ۳۴/۳۵ — سرویس: ScopeRecord + linkage
# ═════════════════════════════════════════════
def test_analyze_creates_scope_record_and_links_run(db_session):
    v = _version(db_session)
    _trade(db_session, 100, 1, v.id)

    out = AnalysisService(db_session).analyze_version(v.id)
    run_id = out["run_id"]
    scope_id = out["scope_id"]

    scope = db_session.query(AnalysisScopeRecord).filter(
        AnalysisScopeRecord.id == scope_id
    ).first()
    assert scope is not None
    assert scope.strategy_version_id == v.id
    assert scope.trade_type == TestType.BACKTEST
    assert scope.is_deleted_filter is True
    assert scope.from_date is not None and scope.to_date is not None

    run = db_session.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    assert run.scope_id == scope.id
    assert run.trade_count == 1
    assert run.status == AnalysisStatus.COMPLETED
    assert run.filters_snapshot["scope"] == "version"
    assert run.filters_snapshot["version_id"] == v.id

    result = out["result"]
    assert result.analysis_run_id == run.id


def test_each_run_gets_its_own_scope_record(db_session):
    v = _version(db_session)
    _trade(db_session, 100, 1, v.id)

    svc = AnalysisService(db_session)
    out1 = svc.analyze_version(v.id)
    _trade(db_session, 50, 2, v.id)
    out2 = svc.analyze_version(v.id)

    # دامنه‌ها و اجراها جدا هستند (Run #1 ثابت، Run #2 جدا)
    assert out1["scope_id"] != out2["scope_id"]
    assert out1["run_id"] != out2["run_id"]
    assert db_session.query(AnalysisScopeRecord).count() == 2
    assert db_session.query(AnalysisRun).filter(AnalysisRun.version_id == v.id).count() == 2

    # نتیجهٔ جاری به Run آخر وصل است
    db_session.expire_all()
    current = (
        db_session.query(AnalysisResult)
        .filter(AnalysisResult.scope == AnalysisScope.VERSION)
        .first()
    )
    assert current.analysis_run_id == out2["run_id"]


def test_resolve_trade_type_for_real_scopes(db_session):
    assert AnalysisService._resolve_trade_type(AnalysisScope.PROP_STAGE, None, []) == TestType.REAL_PROP
    assert AnalysisService._resolve_trade_type(AnalysisScope.PERSONAL_ACCOUNT, None, []) == TestType.REAL_PERSONAL
    assert AnalysisService._resolve_trade_type(AnalysisScope.VERSION, TestType.FORWARD, []) == TestType.FORWARD


