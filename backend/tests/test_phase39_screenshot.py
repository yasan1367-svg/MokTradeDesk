"""تست‌های فاز ۳۹.۳ — رفع «Screenshot دوگانه».

پیش از فاز ۳۹ دو منبع برای اسکرین‌شات وجود داشت:
  ۱) `Trade.screenshot_path` (ستون legacy — در کد هیچ‌گاه خوانده/نوشته نمی‌شد ⇒ **ستون مرده**)
  ۲) جدول `screenshots` (`models/personal.py::Screenshot` با `entity_type='trade'`)

پس از فاز ۳۹ **تنها** منبع، جدول `screenshots` است.

پوشش:
- حذف ستون legacy از مدل `Trade`
- خواندن جزئیات معامله از جدول `screenshots`
- شمارش اسکرین‌شات در لیست معاملات از جدول `screenshots`
- endpoint لیست اسکرین‌شات معامله
"""
from datetime import datetime, timezone

from app.models.personal import Screenshot
from app.models.strategy import (
    Strategy,
    StrategyVersion,
    TestType,
    Trade,
    TradeSource,
)


# ═════════════════════════════════════════════
# helpers
# ═════════════════════════════════════════════
def _version(db) -> StrategyVersion:
    strategy = Strategy(name="S")
    db.add(strategy)
    db.flush()
    version = StrategyVersion(strategy_id=strategy.id, version_name="v1")
    db.add(version)
    db.flush()
    return version


def _trade(db, version_id: int) -> Trade:
    trade = Trade(
        symbol="XAUUSD",
        direction="buy",
        open_time=datetime(2025, 3, 1, 10, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 3, 1, 11, 0, tzinfo=timezone.utc),
        open_price=2000.0,
        close_price=2001.0,
        size=1.0,
        pnl=100.0,
        commission=0.0,
        swap=0.0,
        source=TradeSource.MANUAL,
        test_type=TestType.BACKTEST,
        version_id=version_id,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


def _screenshot(db, trade_id: int, path="storage/screenshots/trade_1_test.png") -> Screenshot:
    row = Screenshot(
        entity_type="trade",
        entity_id=trade_id,
        file_path=path,
        file_hash="deadbeef",
        description="test",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ═════════════════════════════════════════════
# ۱) ستون legacy حذف شده است
# ═════════════════════════════════════════════
def test_screenshot_path_removed():
    """`Trade` دیگر ستون `screenshot_path` ندارد (تنها منبع = جدول screenshots)."""
    assert "screenshot_path" not in Trade.__table__.c

    # و ستون مورد انتظار برای اسکرین‌شات در مدل Trade وجود ندارد
    assert not hasattr(Trade, "screenshot_path")


def test_screenshot_table_is_single_source():
    """جدول `screenshots` با `entity_type`/`entity_id` تنها منبع است."""
    columns = set(Screenshot.__table__.c.keys())
    assert {"entity_type", "entity_id", "file_path"} <= columns
    assert Screenshot.__tablename__ == "screenshots"


# ═════════════════════════════════════════════
# ۲) خواندن از جدول screenshots (نه ستون legacy)
# ═════════════════════════════════════════════
def test_trade_detail_reads_screenshots_from_table(client, db_session):
    version = _version(db_session)
    trade = _trade(db_session, version.id)
    _screenshot(db_session, trade.id, "storage/screenshots/trade_a.png")

    detail = client.get(f"/api/trades/{trade.id}").json()

    assert len(detail["screenshots"]) == 1
    assert detail["screenshots"][0]["file_path"] == "storage/screenshots/trade_a.png"
    assert detail["screenshots"][0]["description"] == "test"
    # خروجی جزئیات نباید هیچ کلید legacy اسکرین‌شات داشته باشد
    assert "screenshot_path" not in detail


def test_trade_list_screenshots_count_from_table(client, db_session):
    version = _version(db_session)
    trade = _trade(db_session, version.id)
    _screenshot(db_session, trade.id)
    _screenshot(db_session, trade.id, "storage/screenshots/trade_b.png")

    body = client.get("/api/trades", params={"version_id": version.id}).json()

    assert body["total"] == 1
    row = body["trades"][0]
    assert row["screenshots_count"] == 2
    assert "screenshot_path" not in row


def test_trade_screenshots_endpoint(client, db_session):
    version = _version(db_session)
    trade = _trade(db_session, version.id)
    _screenshot(db_session, trade.id, "storage/screenshots/trade_c.png")

    rows = client.get(f"/api/trades/{trade.id}/screenshots").json()

    assert len(rows) == 1
    assert rows[0]["file_path"] == "storage/screenshots/trade_c.png"
    assert rows[0]["file_name"] == "trade_c.png"


def test_other_trade_screenshots_not_leaked(client, db_session):
    """`entity_id` باید فیلتر شود — اسکرین‌شات معاملهٔ دیگر نباید دیده شود."""
    version = _version(db_session)
    trade_a = _trade(db_session, version.id)
    trade_b = _trade(db_session, version.id)
    _screenshot(db_session, trade_a.id, "storage/screenshots/only_a.png")
    _screenshot(db_session, trade_b.id, "storage/screenshots/only_b.png")

    detail_a = client.get(f"/api/trades/{trade_a.id}").json()
    detail_b = client.get(f"/api/trades/{trade_b.id}").json()

    assert [s["file_path"] for s in detail_a["screenshots"]] == ["storage/screenshots/only_a.png"]
    assert [s["file_path"] for s in detail_b["screenshots"]] == ["storage/screenshots/only_b.png"]
