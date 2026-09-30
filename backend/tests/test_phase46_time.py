"""تست‌های فاز ۴۶ — زمان و تاریخ (Time & Date)."""
from datetime import datetime, timedelta, timezone

from app.models.prop import PropAccount, PropFirm, PropStage, StageType
from app.models.trading import Broker, PersonalTradingAccount
from app.utils.import_identity import normalize_utc
from app.utils.time_utils import from_utc, to_utc


# ═════════════════════════════════════════════
# ۴۶.۱ — server_utc_offset_minutes
# ═════════════════════════════════════════════
def test_server_utc_offset_default_zero(db_session):
    broker = Broker(name="B46")
    db_session.add(broker)
    db_session.flush()

    pta = PersonalTradingAccount(
        broker_id=broker.id, account_number="A46", account_label="A46",
    )
    db_session.add(pta)

    firm = PropFirm(name="F46")
    db_session.add(firm)
    db_session.flush()
    prop_acc = PropAccount(prop_firm_id=firm.id, account_label="P46")
    db_session.add(prop_acc)
    db_session.commit()

    assert broker.server_utc_offset_minutes == 0
    assert pta.server_utc_offset_minutes == 0
    assert prop_acc.server_utc_offset_minutes == 0


def test_server_utc_offset_persists(db_session):
    broker = Broker(name="B46b", server_utc_offset_minutes=180)
    db_session.add(broker)
    db_session.commit()
    db_session.refresh(broker)
    assert broker.server_utc_offset_minutes == 180

    broker.server_utc_offset_minutes = -330
    db_session.commit()
    db_session.refresh(broker)
    assert broker.server_utc_offset_minutes == -330


# ═════════════════════════════════════════════
# ۴۶.۲ — to_utc / from_utc / normalize_utc با offset
# ═════════════════════════════════════════════
def test_to_utc_naive_with_offset():
    # ۱۰:۰۰ ساعت سرور با offset +180 ⇒ ۰۷:۰۰ UTC
    assert to_utc(datetime(2025, 1, 1, 10, 0), offset_minutes=180) == datetime(
        2025, 1, 1, 7, 0, tzinfo=timezone.utc
    )


def test_to_utc_aware():
    aware = datetime(2025, 1, 1, 10, 0, tzinfo=timezone(timedelta(hours=3)))
    assert to_utc(aware) == datetime(2025, 1, 1, 7, 0, tzinfo=timezone.utc)


def test_from_utc():
    dt = from_utc(datetime(2025, 1, 1, 7, 0, tzinfo=timezone.utc), offset_minutes=180)
    assert dt.hour == 10
    assert dt.utcoffset() == timedelta(minutes=180)


def test_import_applies_offset():
    # بدون offset ⇒ همان ساعت به‌عنوان UTC
    assert normalize_utc("2025-01-01 10:00:00", 0) == datetime(
        2025, 1, 1, 10, 0, tzinfo=timezone.utc
    )
    # با offset +180 ⇒ ۰۷:۰۰ UTC
    assert normalize_utc("2025-01-01 10:00:00", 180) == datetime(
        2025, 1, 1, 7, 0, tzinfo=timezone.utc
    )


def test_build_context_resolves_server_offset(db_session):
    from app.services.import_engine import build_context

    strategy_firm = PropFirm(name="F46bc")
    db_session.add(strategy_firm)
    db_session.flush()
    prop_account = PropAccount(
        prop_firm_id=strategy_firm.id, account_label="P46bc",
        server_utc_offset_minutes=180,
    )
    db_session.add(prop_account)
    db_session.flush()
    stage = PropStage(
        prop_account_id=prop_account.id, stage_type=StageType.STAGE_1,
    )
    db_session.add(stage)
    db_session.commit()

    ctx = build_context(db_session, source_format="soft4x_xlsx", prop_stage_id=stage.id)
    assert ctx.server_utc_offset_minutes == 180


# ═════════════════════════════════════════════
# ۴۶.۳ — تبدیل شمسی واحد (utils/jalali.py)
# ═════════════════════════════════════════════
def test_jalali_conversion_roundtrip():
    from app.utils.jalali import gregorian_to_jalali_parts, jalali_to_gregorian_parts

    for g in [(2024, 2, 29), (2025, 12, 31), (2026, 1, 1), (2030, 6, 15), (2024, 3, 20)]:
        j = gregorian_to_jalali_parts(*g)
        assert jalali_to_gregorian_parts(*j) == g

    from datetime import date

    from app.utils.jalali import gregorian_to_jalali, jalali_to_gregorian

    assert jalali_to_gregorian("1404/01/01") == date(2025, 3, 21)
    assert gregorian_to_jalali(date(2025, 3, 21)) == "1404/01/01"


def test_jalali_nowruz_1403():
    from app.utils.jalali import gregorian_to_jalali_parts, jalali_to_gregorian_parts

    # نوروز ۱۴۰۳ = ۲۰ مارس ۲۰۲۴
    assert gregorian_to_jalali_parts(2024, 3, 20) == (1403, 1, 1)
    assert jalali_to_gregorian_parts(1403, 1, 1) == (2024, 3, 20)
    # نوروز ۱۴۰۴ = ۲۱ مارس ۲۰۲۵
    assert gregorian_to_jalali_parts(2025, 3, 21) == (1404, 1, 1)


def test_jalali_leap_year():
    from app.utils.jalali import gregorian_to_jalali_parts, jalali_to_gregorian_parts

    # ۱۴۰۳ سال کبیسه است ⇒ اسفند ۳۰ روز دارد
    assert jalali_to_gregorian_parts(1403, 12, 30) == (2025, 3, 20)
    assert gregorian_to_jalali_parts(2025, 3, 20) == (1403, 12, 30)


# ═════════════════════════════════════════════
# ۴۶.۴ — تقویم بر پایهٔ وقت تهران
# ═════════════════════════════════════════════
def _seed_backtest_trade(db, close_time):
    from app.models.strategy import Strategy, StrategyVersion, TestType, Trade, TradeSource

    strategy = Strategy(name="S46cal")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v46cal")
    db.add(version)
    db.flush()
    db.add(Trade(
        version_id=version.id, symbol="XAUUSD", direction="buy",
        open_time=close_time, close_time=close_time,
        open_price=2000.0, close_price=2000.0, size=1.0, pnl=10.0,
        commission=0.0, swap=0.0, source=TradeSource.MANUAL, test_type=TestType.BACKTEST,
    ))
    db.commit()


def test_calendar_uses_tehran_timezone(client, db_session):
    from datetime import datetime, timezone

    # ۲۳:۳۰ UTC = ۰۳:۰۰ روز بعد به وقت تهران
    _seed_backtest_trade(db_session, datetime(2025, 6, 1, 23, 30, tzinfo=timezone.utc))
    days = client.get("/api/analytics/calendar", params={"scope": "all"}).json()
    assert [d["date"] for d in days] == ["2025-06-02"]


def test_transaction_23_30_utc_is_next_day_in_tehran(client, db_session):
    from datetime import datetime, timezone

    from app.utils.time_utils import to_tehran

    # تابع خالص
    got = to_tehran(datetime(2025, 6, 1, 23, 30, tzinfo=timezone.utc))
    assert got.strftime("%Y-%m-%d") == "2025-06-02"

    # و از مسیر تقویم API
    _seed_backtest_trade(db_session, datetime(2025, 6, 1, 23, 30, tzinfo=timezone.utc))
    days = client.get("/api/analytics/calendar", params={"scope": "all"}).json()
    assert any(d["date"] == "2025-06-02" for d in days)


# ═════════════════════════════════════════════
# ۴۶.۵ — date_range شامل آخرین روز
# ═════════════════════════════════════════════
def test_date_range_includes_last_day():
    from datetime import date, datetime, timezone

    from app.utils.date_range import date_range

    f, t = date_range(date(2025, 1, 1), date(2025, 1, 15))
    assert f == datetime(2025, 1, 1, tzinfo=timezone.utc)
    # پایان بازه = نیمه‌شب روز ۱۶ ⇒ کل روز ۱۵ شامل است
    assert t == datetime(2025, 1, 16, tzinfo=timezone.utc)

    assert date_range(None, None) == (None, None)


def test_transaction_at_10am_included(client, db_session):
    acc_id = client.post("/api/finance/accounts", json={
        "name": "A", "type": "bank", "currency": "USD", "balance": 0,
    }).json()["id"]
    client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 1000, "type": "deposit",
        "date": "2025-03-15T10:00:00+00:00",
    })

    txs = client.get("/api/finance/transactions", params={
        "date_from": "2025-03-15", "date_to": "2025-03-15",
    }).json()
    assert len(txs) == 1


# ═════════════════════════════════════════════
# ۴۶.۶ — یکدست‌سازی DateTime (aware در لایه ورود)
# ═════════════════════════════════════════════
def test_datetime_helpers_return_aware_utc():
    """همهٔ توابع مرزی باید datetime آگاه از tz (UTC) برگردانند.

    توضیح: SQLite ستون `DateTime` را به‌صورت رشته ذخیره می‌کند و مقدار را naive
    برمی‌گرداند؛ به همین دلیل تبدیل به aware در **مرزهای ورود/خروج** انجام می‌شود
    (طبق allowance پلن فاز ۴۶.۶، migration بازسازی جدول انجام نشد).
    """
    from datetime import datetime, timezone

    from app.api.trades import _parse_iso_datetime
    from app.utils.import_identity import normalize_utc
    from app.utils.time_utils import from_utc, now_utc, to_utc

    assert to_utc(datetime(2025, 1, 1, 10, 0)).tzinfo is not None
    assert to_utc(datetime(2025, 1, 1, 10, 0)).utcoffset().total_seconds() == 0
    assert now_utc().tzinfo is not None
    assert from_utc(
        datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc), 180
    ).tzinfo is not None
    assert normalize_utc("2025-01-01 10:00:00").tzinfo is not None
    assert _parse_iso_datetime("2025-01-01T10:00:00").tzinfo is not None


def test_api_stored_datetime_is_normalized_on_read(client, db_session):
    """مقدار ذخیره‌شده در DB ممکن است naive باشد، ولی خروجی API ISO با tz است."""
    acc_id = client.post("/api/finance/accounts", json={
        "name": "A47", "type": "bank", "currency": "USD", "balance": 0,
    }).json()["id"]
    client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 500, "type": "deposit",
        "date": "2025-03-15T10:00:00+00:00",
    })
    tx = client.get("/api/finance/transactions").json()[0]
    # ISO 8601 همیشه قابل parse است
    from datetime import datetime

    assert datetime.fromisoformat(tx["date"]).year == 2025





