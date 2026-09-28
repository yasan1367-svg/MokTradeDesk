"""تست‌های فاز ۳۱ — Duplicate Detection و یکپارچگی ایمپورت.

پوشش:
- سه حالت NEW / DUPLICATE / POSSIBLE_DUPLICATE
- Soft Delete: رکورد حذف‌شده‌ی نرم باید در تشخیص تکرار دیده شود
- ImportIdentity: یکتایی hash + cascade با حذف کامل معامله
- شمارنده‌های ImportBatch و وضعیت‌ها
- جداسازی دامنه (یک فایل مشترک بین دو نسخه ⇒ تکراری نیست)
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.imports import ImportBatch, ImportIdentity, ImportRowStatus, ImportStatus
from app.models.strategy import Trade, TradeSource, TestType
from app.utils.import_identity import build_identity_hash, normalize_utc
from tests.test_import_engine import (  # noqa: F401 — helpers مشترک
    _commit,
    _mt4_html,
    _preview_mt4,
    _preview_soft4x,
    _soft4x_row,
    _version,
    _xlsx_bytes,
)


@pytest.fixture(autouse=True)
def _reset_import_rate_limit():
    """شمارنده‌ی Rate Limit ایمپورت (۱۰ در دقیقه) بین تست‌ها صفر می‌شود."""
    from app.core.rate_limit import limiter

    limiter.reset()
    yield


def _mk_trade(
    db,
    *,
    version_id,
    symbol="XAUUSD",
    open_time=datetime(2025, 1, 2, 10, 0, tzinfo=timezone.utc),
    close_time=datetime(2025, 1, 2, 12, 30, tzinfo=timezone.utc),
    direction="buy",
    size=1.0,
    pnl=5.0,
):
    """معامله‌ی BACKTEST دست‌ساز (شبیه ثبت دستی) در همان دامنه‌ی فایل تست."""
    trade = Trade(
        version_id=version_id,
        symbol=symbol,
        direction=direction,
        open_time=open_time,
        close_time=close_time,
        open_price=2000.0,
        close_price=2010.0,
        size=size,
        pnl=pnl,
        source=TradeSource.MANUAL,
        test_type=TestType.BACKTEST,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


# ═════════════════════════════════════════════
# Identity Hash
# ═════════════════════════════════════════════
def test_identity_hash_is_stable_and_scope_aware():
    common = dict(
        source="MT4_IMPORT",
        external_ticket="1001",
        symbol="XAUUSD",
        open_time="2025-01-02 10:00:00",
        close_time="2025-01-02 11:00:00",
    )
    base = build_identity_hash(**common, version_id=1, test_type=TestType.BACKTEST)
    assert base == build_identity_hash(**common, version_id=1, test_type=TestType.BACKTEST)

    # همان فایل در نسخه‌ی دیگر ⇒ هویت متفاوت (وگرنه اشتباهاً تکراری می‌شد)
    assert base != build_identity_hash(**common, version_id=2, test_type=TestType.BACKTEST)
    # نوع تست متفاوت ⇒ هویت متفاوت
    assert base != build_identity_hash(**common, version_id=1, test_type=TestType.FORWARD)
    # شماره‌ی سفارش متفاوت ⇒ هویت متفاوت
    assert base != build_identity_hash(
        **{**common, "external_ticket": "1002"},
        version_id=1,
        test_type=TestType.BACKTEST,
    )
    assert normalize_utc("2025-01-02 10:00:00").isoformat().startswith("2025-01-02T10:00:00")


def test_identity_hash_is_unique_in_database(db_session):
    version = _version(db_session)
    trade_a = _mk_trade(db_session, version_id=version.id)
    trade_b = _mk_trade(db_session, version_id=version.id, close_time=datetime(2025, 1, 2, 13, 0, tzinfo=timezone.utc))

    db_session.add(ImportIdentity(
        trade_id=trade_a.id,
        source="MT4_IMPORT",
        symbol="XAUUSD",
        open_time=trade_a.open_time,
        close_time=trade_a.close_time,
        identity_hash="same-hash",
        version_id=version.id,
        test_type=TestType.BACKTEST,
    ))
    db_session.commit()

    db_session.add(ImportIdentity(
        trade_id=trade_b.id,
        source="MT4_IMPORT",
        symbol="XAUUSD",
        open_time=trade_b.open_time,
        close_time=trade_b.close_time,
        identity_hash="same-hash",
        version_id=version.id,
        test_type=TestType.BACKTEST,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ═════════════════════════════════════════════
# NEW / DUPLICATE / POSSIBLE_DUPLICATE
# ═════════════════════════════════════════════
def test_duplicate_after_import(client, db_session):
    version = _version(db_session)
    first = _preview_mt4(client, test_type="backtest", version_id=version.id).json()
    assert first["counts"][ImportRowStatus.NEW.value] == 1
    assert _commit(client, first["batch_id"]).json()["imported"] == 1

    second = _preview_mt4(client, test_type="backtest", version_id=version.id).json()
    assert second["counts"][ImportRowStatus.DUPLICATE.value] == 1
    assert second["counts"][ImportRowStatus.NEW.value] == 0
    assert second["blocking"] is False

    result = _commit(client, second["batch_id"]).json()
    assert result["imported"] == 0
    assert result["duplicate"] == 1
    assert db_session.query(Trade).count() == 1


def test_soft_deleted_trade_is_still_detected(client, db_session):
    """قانون فاز ۳۱: معامله‌ی حذف‌شده‌ی نرم باید در Duplicate Detection دیده شود."""
    version = _version(db_session)
    first = _preview_mt4(client, test_type="backtest", version_id=version.id).json()
    _commit(client, first["batch_id"])

    trade = db_session.query(Trade).one()
    trade.is_deleted = True
    db_session.commit()

    preview = _preview_mt4(client, test_type="backtest", version_id=version.id).json()
    assert preview["counts"][ImportRowStatus.DUPLICATE.value] == 1
    assert "حذف نرم" in preview["rows"][0]["message"]
    assert preview["rows"][0]["matched_trade_id"] == trade.id

    result = _commit(client, preview["batch_id"]).json()
    assert result["imported"] == 0
    assert db_session.query(Trade).count() == 1


def test_possible_duplicate_requires_explicit_confirmation(client, db_session):
    """همان نماد + همان زمان ورود در همان دامنه (نه هویت کامل) ⇒ نیاز به تصمیم کاربر."""
    version = _version(db_session)
    _mk_trade(db_session, version_id=version.id)  # close_time متفاوت از فایل

    preview = _preview_mt4(client, test_type="backtest", version_id=version.id).json()
    assert preview["counts"][ImportRowStatus.POSSIBLE_DUPLICATE.value] == 1
    assert preview["blocking"] is True

    blocked = _commit(client, preview["batch_id"])
    assert blocked.status_code == 409
    assert db_session.query(Trade).count() == 1
    assert db_session.query(ImportBatch).one().status == ImportStatus.PENDING

    allowed = _commit(client, preview["batch_id"], allow=True)
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["imported"] == 1
    assert db_session.query(Trade).count() == 2


def test_same_external_ticket_with_other_details_is_possible_duplicate(client, db_session):
    """همان شماره‌ی سفارش با زمان متفاوت ⇒ POSSIBLE_DUPLICATE (نه DUPLICATE)."""
    version = _version(db_session)
    first = _preview_mt4(client, test_type="backtest", version_id=version.id).json()
    _commit(client, first["batch_id"])

    # همان ticket=1001 ولی زمان ورود دیگری در همان دامنه
    html = _mt4_html(tickets=("1001",))
    html = html.replace("2025.01.02 10:00:00", "2025.02.10 09:00:00")
    html = html.replace("2025.01.02 11:00:00", "2025.02.10 10:00:00")
    preview = _preview_mt4(
        client, html=html, test_type="backtest", version_id=version.id
    ).json()
    assert preview["counts"][ImportRowStatus.POSSIBLE_DUPLICATE.value] == 1
    assert "1001" in preview["rows"][0]["message"]

    assert _commit(client, preview["batch_id"]).status_code == 409
    assert _commit(client, preview["batch_id"], allow=True).status_code == 200
    assert db_session.query(Trade).count() == 2


def test_duplicate_rows_inside_same_file(client, db_session):
    """دو ردیف یکسان در یک فایل ⇒ ردیف دوم تکراری است (بدون شکستن Commit)."""
    version = _version(db_session)
    preview = _preview_soft4x(
        client,
        content=_xlsx_bytes([_soft4x_row(), _soft4x_row()]),
        test_type="backtest",
        version_id=version.id,
    ).json()

    assert preview["counts"][ImportRowStatus.NEW.value] == 1
    assert preview["counts"][ImportRowStatus.DUPLICATE.value] == 1

    result = _commit(client, preview["batch_id"]).json()
    assert result["imported"] == 1
    assert result["duplicate"] == 1
    assert db_session.query(Trade).count() == 1


def test_scope_isolation_between_versions(client, db_session):
    """یک فایل مشترک برای دو نسخه ⇒ در هر دو نسخه NEW است (دامنه بخشی از هویت)."""
    version_a = _version(db_session, name="A")
    version_b = _version(db_session, name="B")

    first = _preview_mt4(client, test_type="backtest", version_id=version_a.id).json()
    assert _commit(client, first["batch_id"]).status_code == 200

    second = _preview_mt4(client, test_type="backtest", version_id=version_b.id).json()
    assert second["counts"][ImportRowStatus.NEW.value] == 1
    assert _commit(client, second["batch_id"]).json()["imported"] == 1

    assert db_session.query(Trade).count() == 2


def test_hard_delete_removes_identity_so_reimport_is_new(client, db_session):
    """حذف کامل معامله ⇒ هویتش هم پاک می‌شود و re-import دیگر تکراری نیست."""
    version = _version(db_session)
    first = _preview_mt4(client, test_type="backtest", version_id=version.id).json()
    _commit(client, first["batch_id"])
    assert db_session.query(ImportIdentity).count() == 1

    trade = db_session.query(Trade).one()
    db_session.delete(trade)
    db_session.commit()
    assert db_session.query(ImportIdentity).count() == 0

    preview = _preview_mt4(client, test_type="backtest", version_id=version.id).json()
    assert preview["counts"][ImportRowStatus.NEW.value] == 1
    assert _commit(client, preview["batch_id"]).json()["imported"] == 1


def test_batch_counters_and_completed_at(client, db_session):
    version = _version(db_session)
    _mk_trade(db_session, version_id=version.id)          # ⇒ ردیف مشکوک به تکرار
    preview = _preview_soft4x(
        client,
        content=_xlsx_bytes([_soft4x_row(), _soft4x_row()]),  # ردیف دوم تکراریِ همان فایل
        test_type="backtest",
        version_id=version.id,
    ).json()

    batch = db_session.query(ImportBatch).order_by(ImportBatch.id.desc()).first()
    assert batch.total == 2
    assert batch.duplicate == 2          # ۱ مشکوک + ۱ تکراری در همان فایل
    assert batch.failed == 0
    assert batch.imported == 0
    assert batch.completed_at is None

    result = _commit(client, preview["batch_id"], allow=True).json()
    assert result["status"] == ImportStatus.COMMITTED.value
    assert result["imported"] == 1
    assert result["duplicate"] == 1

    db_session.expire_all()
    batch = db_session.query(ImportBatch).order_by(ImportBatch.id.desc()).first()
    assert batch.status == ImportStatus.COMMITTED
    assert batch.imported == 1
    assert batch.duplicate == 1
    assert batch.failed == 0
    assert batch.completed_at is not None


