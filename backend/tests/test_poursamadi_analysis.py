"""تست‌های جامع تحلیل تطبیقی بازه‌های پورصمدی و مرزهای زمانی."""
from datetime import datetime, timezone
from app.models.strategy import Strategy, StrategyVersion, Trade, CustomTimeInterval, TestType, TradeSource
from app.services.analysis_service import AnalysisService
from app.utils.time_utils import TEHRAN


def _tehran_dt(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    """ساخت زمان با منطقه زمانی تهران و تبدیل به UTC برای ذخیره در معامله."""
    dt = datetime(year, month, day, hour, minute, tzinfo=TEHRAN)
    return dt.astimezone(timezone.utc)


def _make_trade(version_id: int, symbol: str, open_time: datetime, close_time: datetime, pnl: float, commission: float = -5.0, direction: str = "buy") -> Trade:
    return Trade(
        version_id=version_id,
        symbol=symbol,
        direction=direction,
        open_time=open_time,
        close_time=close_time,
        open_price=2000.0,
        close_price=2010.0,
        size=1.0,
        pnl=pnl,
        commission=commission,
        swap=0.0,
        source=TradeSource.MANUAL,
        test_type=TestType.BACKTEST,
    )


def test_poursamadi_half_open_boundaries_no_double_counting(db_session):
    """تست مرز نیمه‌باز: معامله رأس ۱۷:۰۰ نباید همزمان در A2 و A3 شمرده شود."""
    # ۱. ثبت بازه‌های پورصمدی طلا
    a1 = CustomTimeInterval(
        name="طلا — A1", symbol="XAUUSD", start_hour=10, start_minute=30,
        end_hour=13, end_minute=30, label="A", priority=1, is_active=1
    )
    a2 = CustomTimeInterval(
        name="طلا — A2", symbol="XAUUSD", start_hour=16, start_minute=0,
        end_hour=17, end_minute=0, label="A", priority=1, is_active=1
    )
    a3 = CustomTimeInterval(
        name="طلا — A3", symbol="XAUUSD", start_hour=17, start_minute=0,
        end_hour=18, end_minute=30, label="A", priority=1, is_active=1
    )
    db_session.add_all([a1, a2, a3])
    db_session.commit()

    strat = Strategy(name="Test Poursamadi Strategy")
    db_session.add(strat)
    db_session.commit()
    ver = StrategyVersion(strategy_id=strat.id, version_name="v1.0", test_type=TestType.BACKTEST)
    db_session.add(ver)
    db_session.commit()

    # تریدها به وقت تهران:
    # t1: ۱۶:۰۰ (شروع A2) -> باید فقط در A2 باشد
    # t2: ۱۶:۵۹ (داخل A2) -> باید فقط در A2 باشد
    # t3: ۱۷:۰۰ (مرز بین A2 و A3) -> باید دقیقاً در شروع A3 باشد و در A2 نباشد!
    # t4: ۱۸:۲۹ (داخل A3) -> باید فقط در A3 باشد
    # t5: ۱۴:۰۰ (خارج بازه‌ها) -> باید در سطر «خارج از بازه» بیاید
    trades = [
        _make_trade(ver.id, "XAUUSD", _tehran_dt(2026, 5, 10, 16, 0), _tehran_dt(2026, 5, 10, 16, 30), 100.0),
        _make_trade(ver.id, "XAUUSD", _tehran_dt(2026, 5, 10, 16, 59), _tehran_dt(2026, 5, 10, 17, 30), 50.0),
        _make_trade(ver.id, "XAUUSD", _tehran_dt(2026, 5, 10, 17, 0), _tehran_dt(2026, 5, 10, 17, 45), 80.0),
        _make_trade(ver.id, "XAUUSD", _tehran_dt(2026, 5, 10, 18, 29), _tehran_dt(2026, 5, 10, 19, 0), -40.0, direction="sell"),
        _make_trade(ver.id, "XAUUSD", _tehran_dt(2026, 5, 10, 14, 0), _tehran_dt(2026, 5, 10, 14, 30), -100.0),
    ]
    db_session.add_all(trades)
    db_session.commit()

    service = AnalysisService(db_session)
    result = service._analyze_by_custom_intervals(trades)

    # بررسی نتایج:
    # A1 باید در نتیجه نباشد چون هیچ معامله‌ای در ۱۰:۳۰ تا ۱۳:۳۰ انجام نشد
    assert "طلا — A1 [A]" not in result

    # A2 باید دقیقاً ۲ معامله داشته باشد (۱۶:۰۰ و ۱۶:۵۹)
    assert "طلا — A2 [A]" in result
    assert result["طلا — A2 [A]"]["total_trades"] == 2
    assert result["طلا — A2 [A]"]["wins"] == 2

    # A3 باید دقیقاً ۲ معامله داشته باشد (۱۷:۰۰ و ۱۸:۲۹)
    assert "طلا — A3 [A]" in result
    assert result["طلا — A3 [A]"]["total_trades"] == 2
    assert result["طلا — A3 [A]"]["wins"] == 1
    assert result["طلا — A3 [A]"]["losses"] == 1

    # خارج از بازه باید دقیقاً ۱ معامله داشته باشد (۱۴:۰۰)
    assert "طلا — خارج از بازه [خارج]" in result
    assert result["طلا — خارج از بازه [خارج]"]["total_trades"] == 1
    assert result["طلا — خارج از بازه [خارج]"]["losses"] == 1


def test_poursamadi_symbol_alias_and_suffix_matching(db_session):
    """تست تطبیق نمادهای بروکر مانند GOLD، US30 و پسوند .m."""
    dji = CustomTimeInterval(
        name="داو — A1", symbol="DJIUSD", start_hour=17, start_minute=0,
        end_hour=18, end_minute=30, label="A", priority=1, is_active=1
    )
    gold = CustomTimeInterval(
        name="طلا — A1", symbol="XAUUSD", start_hour=10, start_minute=30,
        end_hour=13, end_minute=30, label="A", priority=1, is_active=1
    )
    db_session.add_all([dji, gold])
    db_session.commit()

    strat = Strategy(name="Broker Symbol Strategy")
    db_session.add(strat)
    db_session.commit()
    ver = StrategyVersion(strategy_id=strat.id, version_name="v1.0", test_type=TestType.BACKTEST)
    db_session.add(ver)
    db_session.commit()

    trades = [
        # نماد با پسوند بروکر XAUUSD.m
        _make_trade(ver.id, "XAUUSD.m", _tehran_dt(2026, 5, 10, 11, 0), _tehran_dt(2026, 5, 10, 11, 30), 120.0),
        # نام مستعار داوجونز در بروکر: US30
        _make_trade(ver.id, "US30", _tehran_dt(2026, 5, 10, 17, 30), _tehran_dt(2026, 5, 10, 18, 0), 200.0, direction="sell"),
    ]
    db_session.add_all(trades)
    db_session.commit()

    service = AnalysisService(db_session)
    result = service._analyze_by_custom_intervals(trades)

    assert "طلا — A1 [A]" in result
    assert result["طلا — A1 [A]"]["total_trades"] == 1
    assert result["طلا — A1 [A]"]["net_pnl"] == 115.0

    assert "داو — A1 [A]" in result
    assert result["داو — A1 [A]"]["total_trades"] == 1
    assert result["داو — A1 [A]"]["net_pnl"] == 195.0


def test_custom_interval_midnight_crossing(db_session):
    """تست بازه‌هایی که از نیمه‌شب عبور می‌کنند (مانند ۲۳:۰۰ تا ۰۱:۳۰)."""
    night_window = CustomTimeInterval(
        name="شبانه", symbol="BTCUSD", start_hour=23, start_minute=0,
        end_hour=1, end_minute=30, label="N", priority=1, is_active=1
    )
    db_session.add(night_window)
    db_session.commit()

    strat = Strategy(name="Crypto Strategy")
    db_session.add(strat)
    db_session.commit()
    ver = StrategyVersion(strategy_id=strat.id, version_name="v1.0", test_type=TestType.BACKTEST)
    db_session.add(ver)
    db_session.commit()

    trades = [
        # ۲۳:۳۰ تهران (قبل نیمه‌شب)
        _make_trade(ver.id, "BTCUSD", _tehran_dt(2026, 5, 10, 23, 30), _tehran_dt(2026, 5, 11, 0, 15), 50.0, commission=0.0),
        # ۰۰:۴۵ تهران (بعد نیمه‌شب)
        _make_trade(ver.id, "BTCUSD", _tehran_dt(2026, 5, 11, 0, 45), _tehran_dt(2026, 5, 11, 1, 15), 80.0, commission=0.0),
        # ۰۲:۰۰ تهران (خارج بازه)
        _make_trade(ver.id, "BTCUSD", _tehran_dt(2026, 5, 11, 2, 0), _tehran_dt(2026, 5, 11, 2, 30), -30.0, commission=0.0, direction="sell"),
    ]
    db_session.add_all(trades)
    db_session.commit()

    service = AnalysisService(db_session)
    result = service._analyze_by_custom_intervals(trades)

    assert "شبانه [N]" in result
    assert result["شبانه [N]"]["total_trades"] == 2
    assert result["شبانه [N]"]["net_pnl"] == 130.0

    assert "BTCUSD — خارج از بازه [خارج]" in result
    assert result["BTCUSD — خارج از بازه [خارج]"]["total_trades"] == 1
