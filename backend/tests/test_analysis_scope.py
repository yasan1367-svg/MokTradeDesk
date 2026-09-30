"""تست‌های دامنه‌ی تحلیل — معاملات REAL نباید در تحلیل Backtest/Forward شمرده شوند

باگ: کوئری‌های تحلیل فقط بر اساس `version_id` فیلتر می‌کردند و `test_type` را
در نظر نمی‌گرفتند؛ بنابراین معاملات REAL (پراپ/شخصی) که با Import MT4 روی همان
نسخه ذخیره می‌شدند، متریک‌های Backtest/Forward را آلوده می‌کردند.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.strategy import (
    AnalysisResult, AnalysisRun, AnalysisScope, Strategy, StrategyVersion, Trade,
    TestType, TradeSource,
)
from app.models.trading import Broker, PersonalTradingAccount
from app.models.prop import PropAccount, PropFirm, PropStage, StageType
from app.models.finance import Currency
from app.services.analysis_service import AnalysisService
from app.utils.trade_scope import analysis_trades_filter


# ═════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════
def _get_or_create_pta(db):
    """یک حساب معاملاتی شخصی مشترک برای تست (فاز ۲۸)"""
    existing = db.query(PersonalTradingAccount).first()
    if existing:
        return existing
    broker = Broker(name="Broker-T")
    db.add(broker)
    db.flush()
    pta = PersonalTradingAccount(
        broker_id=broker.id, account_number="T-1", account_label="T",
        currency=Currency.USD, initial_balance=10000.0, current_balance=10000.0,
    )
    db.add(pta)
    db.flush()
    return pta


def _add_trade(db, version_id, test_type, pnl):
    """یک معامله‌ی بسته‌شده‌ی ساده می‌سازد (برای REAL_PERSONAL حساب شخصی خودکار ساخته می‌شود)"""
    pta_id = None
    if test_type == TestType.REAL_PERSONAL:
        pta_id = _get_or_create_pta(db).id
    trade = Trade(
        version_id=version_id,
        personal_trading_account_id=pta_id,
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, 2, 11, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2010.0,
        size=1.0,
        pnl=pnl,
        commission=0.0,
        swap=0.0,
        entry_sequence=1,
        source=TradeSource.MANUAL,
        test_type=test_type,
    )
    db.add(trade)
    return trade


def _make_version(db, name="v1"):
    strategy = Strategy(name=f"S-{name}")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name=name)
    db.add(version)
    db.commit()
    db.refresh(version)
    return strategy, version


def _add_stale_result(db, version_id, total_trades):
    """یک تحلیل کهنه/آلوده را شبیه‌سازی می‌کند (رکوردهای پیش از فاز ۱۹)"""
    row = AnalysisResult(
        scope=AnalysisScope.VERSION,
        scope_key=str(version_id),
        version_id=version_id,
        total_trades=total_trades,
        win_rate=57.14,
        net_pnl=101.96,
    )
    db.add(row)
    db.commit()
    return row


# ═════════════════════════════════════════════
# analysis_trades_filter — تست واحد
# ═════════════════════════════════════════════
def test_analysis_filter_keeps_everything_except_real(db_session):
    _, v = _make_version(db_session)
    _add_trade(db_session, v.id, TestType.BACKTEST, 100)
    _add_trade(db_session, v.id, TestType.FORWARD, 50)
    _add_trade(db_session, v.id, TestType.REAL_PERSONAL, -9999)
    legacy = _add_trade(db_session, v.id, TestType.BACKTEST, 10)  # noqa: F841
    db_session.commit()

    # فاز ۲۸: test_type دیگر NULL نمی‌شود (NOT NULL)؛ فقط REAL_* حذف می‌شوند.
    kept = db_session.query(Trade).filter(analysis_trades_filter()).all()
    assert len(kept) == 3
    assert not any(t.test_type == TestType.REAL_PERSONAL for t in kept)


# ═════════════════════════════════════════════
# AnalysisService.analyze_version
# ═════════════════════════════════════════════
def test_analyze_version_ignores_real_trades(db_session):
    _, v = _make_version(db_session)
    for _ in range(3):
        _add_trade(db_session, v.id, TestType.BACKTEST, 100)
    for _ in range(5):
        _add_trade(db_session, v.id, TestType.REAL_PERSONAL, -1000)
    db_session.commit()

    metrics = AnalysisService(db_session).analyze_version(v.id)["result"]
    assert metrics.total_trades == 3          # نه ۸
    assert metrics.net_pnl == 300.0           # نه 300 - 5000
    assert metrics.win_rate == 100.0


def test_analyze_version_counts_forward_trades(db_session):
    """FORWARD هم مثل BACKTEST جزو تحلیل است"""
    _, v = _make_version(db_session)
    _add_trade(db_session, v.id, TestType.FORWARD, 25)
    _add_trade(db_session, v.id, TestType.REAL_PERSONAL, -500)
    db_session.commit()

    metrics = AnalysisService(db_session).analyze_version(v.id)["result"]
    assert metrics.total_trades == 1
    assert metrics.net_pnl == 25.0


def test_analyze_version_real_only_raises(db_session):
    _, v = _make_version(db_session)
    _add_trade(db_session, v.id, TestType.REAL_PERSONAL, -50)
    db_session.commit()

    with pytest.raises(ValueError) as exc:
        AnalysisService(db_session).analyze_version(v.id)
    assert "REAL" in str(exc.value)


# ═════════════════════════════════════════════
# Endpointها
# ═════════════════════════════════════════════
def test_analyze_endpoint_real_only_returns_404(client, db_session):
    _, v = _make_version(db_session)
    _add_trade(db_session, v.id, TestType.REAL_PERSONAL, -50)
    db_session.commit()

    r = client.post(f"/api/analytics/analyze/{v.id}")
    assert r.status_code == 404
    assert "REAL" in r.json()["detail"]


def test_analyze_endpoint_metrics_are_clean(client, db_session):
    _, v = _make_version(db_session)
    _add_trade(db_session, v.id, TestType.BACKTEST, 100)
    _add_trade(db_session, v.id, TestType.REAL_PERSONAL, -700)
    db_session.commit()

    assert client.post(f"/api/analytics/analyze/{v.id}").status_code == 200

    detail = client.get(f"/api/analytics/{v.id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["total_trades"] == 1
    assert body["net_pnl"] == 100.0


def test_strategy_stats_ignores_real_trades(client, db_session):
    strategy, v = _make_version(db_session)
    for _ in range(2):
        _add_trade(db_session, v.id, TestType.BACKTEST, 100)
    for _ in range(3):
        _add_trade(db_session, v.id, TestType.REAL_PERSONAL, -500)
    db_session.commit()

    r = client.get(f"/api/strategies/{strategy.id}/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["total_trades"] == 2
    assert body["summary"]["net_pnl"] == 200.0
    assert body["trade_counts"]["winning"] == 2


# ═════════════════════════════════════════════
# فاز ۱۹ — گارد سازگاری GET /api/analytics/{version_id}
# ═════════════════════════════════════════════
def test_get_analysis_real_only_version_returns_404(client, db_session):
    """نسخه‌ی فقط-REAL با تحلیل کهنه → نباید تحلیل آلوده سرو شود"""
    _, v = _make_version(db_session)
    _add_trade(db_session, v.id, TestType.REAL_PERSONAL, -50)
    _add_stale_result(db_session, v.id, total_trades=21)
    db_session.commit()

    r = client.get(f"/api/analytics/{v.id}")
    assert r.status_code == 404
    assert "REAL" in r.json()["detail"]


def test_get_analysis_stale_snapshot_returns_404(client, db_session):
    """تحلیل ذخیره‌شده با تعداد معاملات قابل‌تحلیل فعلی هم‌خوان نیست → ۴۰۴"""
    _, v = _make_version(db_session)
    _add_trade(db_session, v.id, TestType.BACKTEST, 100)
    _add_stale_result(db_session, v.id, total_trades=5)   # ادعای ۵ معامله
    db_session.commit()

    r = client.get(f"/api/analytics/{v.id}")
    assert r.status_code == 404
    assert "کهنه" in r.json()["detail"]


def test_get_analysis_outdated_after_new_backtest_trade(client, db_session):
    """افزودن معامله‌ی Backtest جدید، تحلیل قبلی را کهنه می‌کند"""
    _, v = _make_version(db_session)
    _add_trade(db_session, v.id, TestType.BACKTEST, 100)
    db_session.commit()
    assert client.post(f"/api/analytics/analyze/{v.id}").status_code == 200
    assert client.get(f"/api/analytics/{v.id}").status_code == 200

    _add_trade(db_session, v.id, TestType.BACKTEST, 50)
    db_session.commit()

    r = client.get(f"/api/analytics/{v.id}")
    assert r.status_code == 404
    assert "کهنه" in r.json()["detail"]


def test_reanalyze_cleans_stale_result_when_no_analyzable_trades(client, db_session):
    """تحلیل مجدد روی نسخه‌ی بدون معامله‌ی Backtest/Forward، رکورد کهنه را پاک می‌کند"""
    _, v = _make_version(db_session)
    _add_trade(db_session, v.id, TestType.REAL_PERSONAL, -50)
    _add_stale_result(db_session, v.id, total_trades=21)
    db_session.commit()

    r = client.post(f"/api/analytics/analyze/{v.id}")
    assert r.status_code == 404
    assert "REAL" in r.json()["detail"]

    db_session.expire_all()
    left = (
        db_session.query(AnalysisResult)
        .filter(AnalysisResult.version_id == v.id)
        .first()
    )
    assert left is None
    # و بعد از پاک‌شدن، GET هم دیگر چیزی سرو نمی‌کند
    assert client.get(f"/api/analytics/{v.id}").status_code == 404


# ═════════════════════════════════════════════
# فاز ۲۰.۱ — دامنه‌ی تحلیل (scope / scope_key)
# ═════════════════════════════════════════════
def test_analyze_persists_scope_and_scope_key(client, db_session):
    """تحلیل نسخه با scope=VERSION و scope_key=str(version_id) ذخیره می‌شود"""
    _, v = _make_version(db_session)
    _add_trade(db_session, v.id, TestType.BACKTEST, 100)
    db_session.commit()

    assert client.post(f"/api/analytics/analyze/{v.id}").status_code == 200
    db_session.expire_all()

    row = (
        db_session.query(AnalysisResult)
        .filter(
            AnalysisResult.scope == AnalysisScope.VERSION,
            AnalysisResult.scope_key == str(v.id),
        )
        .first()
    )
    assert row is not None
    assert row.version_id == v.id
    assert row.prop_stage_id is None
    assert row.personal_trading_account_id is None
    assert row.total_trades == 1

    run = (
        db_session.query(AnalysisRun)
        .filter(
            AnalysisRun.scope == AnalysisScope.VERSION,
            AnalysisRun.scope_key == str(v.id),
        )
        .first()
    )
    assert run is not None
    assert run.version_id == v.id


def test_analysis_result_scope_key_is_unique(db_session):
    """فاز ۲۰.۱: قید یکتایی (scope, scope_key) برقرار است"""
    _, v = _make_version(db_session)
    _add_stale_result(db_session, v.id, total_trades=1)
    db_session.commit()

    # تلاش دوم برای همان دامنه → باید IntegrityError بدهد
    with pytest.raises(IntegrityError):
        _add_stale_result(db_session, v.id, total_trades=2)
        db_session.commit()
    db_session.rollback()


def _make_stage(db):
    """یک PropStage واقعی می‌سازد (فاز ۴۲.۸: با FK روشن، id جعلی مجاز نیست)."""
    firm = PropFirm(name="Firm-T")
    db.add(firm)
    db.flush()
    account = PropAccount(prop_firm_id=firm.id, account_label="PA-T")
    db.add(account)
    db.flush()
    stage = PropStage(prop_account_id=account.id, stage_type=StageType.STAGE_1)
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


def test_analysis_result_allows_same_key_across_scopes(db_session):
    """کلید یکسان در دو scope مختلف مجاز است (مثلاً version_id=1 و prop_stage_id=1)"""
    _, v = _make_version(db_session)
    stage = _make_stage(db_session)

    version_row = AnalysisResult(
        scope=AnalysisScope.VERSION, scope_key="1", version_id=v.id,
        total_trades=1, win_rate=100.0, net_pnl=10.0,
    )
    prop_row = AnalysisResult(
        scope=AnalysisScope.PROP_STAGE, scope_key="1", prop_stage_id=stage.id,
        total_trades=2, win_rate=50.0, net_pnl=-5.0,
    )
    db_session.add_all([version_row, prop_row])
    db_session.commit()

    assert db_session.query(AnalysisResult).count() == 2

