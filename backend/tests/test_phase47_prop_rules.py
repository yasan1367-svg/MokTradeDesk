"""تست‌های فاز ۴۷ — موتور قوانین پراپ و برداشت."""
from app.models.prop import PropAccount, PropFirm, PropStage, StageStatus, StageType


def _stage(db, **kw):
    """مرحلهٔ پراپ ساده برای تست."""
    firm = PropFirm(name="F47")
    db.add(firm)
    db.flush()
    account = PropAccount(prop_firm_id=firm.id, account_label="A47")
    db.add(account)
    db.flush()
    stage = PropStage(prop_account_id=account.id, stage_type=StageType.STAGE_1, **kw)
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


# ═════════════════════════════════════════════
# ۴۷.۱ — ستون‌های DD روی PropStage
# ═════════════════════════════════════════════
def test_prop_stage_default_dd_mode_static(db_session):
    assert _stage(db_session).dd_mode == "static"


def test_prop_stage_default_dd_basis_balance(db_session):
    assert _stage(db_session).dd_basis == "balance"


def test_prop_stage_default_day_boundary_utc(db_session):
    assert _stage(db_session).day_boundary_utc_offset == 0
