"""فاز ۴۴ — متریک‌های مالی مشترک (یک منبع حقیقت، بدون Double Counting).

مصرف‌کننده‌ها: `api/analytics.py::spendable_money` و `api/finance.py::spendable-assets`.

قرارداد:
- broker_balance = Σ موجودی فعلی حساب‌های معاملاتی شخصی (که **خودش** شامل سود است).
- funded_pnl     = Σ net_pnl معاملات REAL_PROP روی مراحل FUNDED_REAL (فقط همین‌ها).
- total_balance  = broker_balance + funded_pnl   (بدون جمع دوبارهٔ سود بروکر).
- prop_stage_3   = Σ max(0, net_pnl(مرحله) × سهم کاربر − برداشت‌شده)  ← پول قابل برداشت.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.prop import PropStage, StageType
from ..models.strategy import TestType, Trade
from ..models.trading import PersonalTradingAccount
from . import metrics

DEFAULT_PROFIT_SHARE = 80.0


def broker_balance(db: Session) -> float:
    """مجموع موجودی فعلی حساب‌های معاملاتی شخصی (شامل سود تحقق‌یافته)."""
    return float(
        db.query(func.coalesce(func.sum(PersonalTradingAccount.current_balance), 0.0)).scalar() or 0.0
    )


def broker_pnl(db: Session) -> float:
    """سود بروکر = Σ (موجودی فعلی − موجودی اولیه)."""
    row = db.query(
        func.coalesce(func.sum(PersonalTradingAccount.current_balance), 0.0),
        func.coalesce(func.sum(PersonalTradingAccount.initial_balance), 0.0),
    ).one()
    return float(row[0] or 0.0) - float(row[1] or 0.0)


def initial_capital(db: Session) -> float:
    """سرمایهٔ اولیهٔ حساب‌های معاملاتی شخصی."""
    return float(
        db.query(func.coalesce(func.sum(PersonalTradingAccount.initial_balance), 0.0)).scalar() or 0.0
    )


def funded_pnl(db: Session) -> float:
    """سود خالص مراحل رییل پراپ (REAL_PROP روی FUNDED_REAL) — فاز ۴۳: net_pnl."""
    val = (
        db.query(func.coalesce(func.sum(metrics.net_pnl_sql()), 0.0))
        .select_from(Trade)
        .join(PropStage, Trade.prop_stage_id == PropStage.id)
        .filter(
            Trade.test_type == TestType.REAL_PROP,
            PropStage.stage_type == StageType.FUNDED_REAL,
            Trade.is_deleted == False,
        )
        .scalar()
    )
    return float(val or 0.0)


def total_balance(db: Session) -> float:
    """موجودی کل (بدون Double Counting سود بروکر)."""
    return broker_balance(db) + funded_pnl(db)


def _stage_net_pnl(db: Session, stage_id: int) -> float:
    val = (
        db.query(func.coalesce(func.sum(metrics.net_pnl_sql()), 0.0))
        .select_from(Trade)
        .filter(
            Trade.prop_stage_id == stage_id,
            Trade.test_type == TestType.REAL_PROP,
            Trade.is_deleted == False,
        )
        .scalar()
    )
    return float(val or 0.0)


def prop_stage_3(db: Session) -> float:
    """سود قابل برداشت مراحل رییل = Σ max(0, net × سهم کاربر − برداشت‌شده).

    فاز ۴۴.۳: برداشت‌های RECEIVED (`stage.total_withdrawn`) کسر می‌شوند تا پولی که
    قبلاً پرداخت شده دوباره «قابل خرج» نشان داده نشود.
    """
    total = 0.0
    stages = db.query(PropStage).filter(PropStage.stage_type == StageType.FUNDED_REAL).all()
    for stage in stages:
        net = _stage_net_pnl(db, stage.id)
        share = (stage.profit_share_percentage if stage.profit_share_percentage is not None else DEFAULT_PROFIT_SHARE) / 100.0
        withdrawn = float(stage.total_withdrawn or 0.0)
        total += max(net * share - withdrawn, 0.0)
    return round(total, 2)
