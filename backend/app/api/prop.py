from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import logging

from ..core.database import get_db
from ..models.prop import (
    PropFirm, PropFirmDefaultRules, PropAccount, PropStage, PropWithdrawal, PropCost,
    PropAlert, StageType, StageStatus, FailureReason,
    WITHDRAWAL_TRANSITIONS,
    CostType,
)
from ..models.finance import (
    FinancialAccount, Category, CategoryType, Currency, TransactionType
)
from ..utils.enums import enum_value
from ..utils.currency import to_currency
from ..utils.time_utils import to_tehran
from ..utils.date_range import filter_by_range
# فاز ۳۹: تنها نویسندهٔ FinancialAccount.balance
from ..services.wallet_service import WalletService, WalletError
from ..services import metrics

logger = logging.getLogger("moktrade")

router = APIRouter()


# ═════════════════════════════════════════════
# Helpers — Prop ↔ Finance (فاز ۵)
# ═════════════════════════════════════════════
def _to_currency(value: Optional[str]) -> Currency:
    """تبدیل ارز رشته‌ای پراپ به Enum مالی — فاز ۴۵.۶: ابزار مشترک (invalid ⇒ USD)."""
    return to_currency(value, default=Currency.USD)


def _get_or_create_category(
    db: Session, name: str, cat_type: CategoryType, color: str, icon: str
) -> Category:
    """دریافت دسته‌بندی با نام داده‌شده یا ساخت آن در صورت نبود"""
    cat = db.query(Category).filter(Category.name == name).first()
    if cat:
        return cat
    cat = Category(name=name, type=cat_type, color=color, icon=icon)
    db.add(cat)
    db.flush()
    return cat


# فاز ۲۸: `_ensure_finance_account` حذف شد — PropAccount حساب معاملاتی است، نه مالی.


# ═════════════════════════════════════════════
# Schemas
# ═════════════════════════════════════════════
class PropFirmCreate(BaseModel):
    name: str
    default_profit_share: Optional[float] = 80.0
    website: Optional[str] = None
    notes: Optional[str] = None


class PropAccountCreate(BaseModel):
    prop_firm_id: int
    account_label: str
    account_number: Optional[str] = None
    currency: str = "USD"
    initial_balance: Optional[float] = 10000.0
    profit_target: Optional[float] = 800.0
    max_daily_dd: Optional[float] = 500.0
    max_total_dd: Optional[float] = 1000.0
    min_trading_days: Optional[int] = 5


class StageRules(BaseModel):
    profit_target: Optional[float] = None
    max_daily_dd: Optional[float] = None
    max_total_dd: Optional[float] = None
    min_trading_days: Optional[int] = None
    initial_balance: Optional[float] = None
    profit_share_percentage: Optional[float] = None


class StageRulesUpdate(BaseModel):
    profit_target: Optional[float] = None
    max_daily_dd: Optional[float] = None
    max_total_dd: Optional[float] = None
    min_trading_days: Optional[int] = None
    initial_balance: Optional[float] = None
    profit_share_percentage: Optional[float] = None


class PassStageWithRulesRequest(BaseModel):
    final_balance: Optional[float] = None
    next_stage_rules: Optional[StageRules] = None


class FailStageRequest(BaseModel):
    failure_reason: str
    failure_details: Optional[str] = None


class WithdrawalCreate(BaseModel):
    amount: float
    note: Optional[str] = None
    destination_account_id: int  # 🆕 فاز ۵ — حساب مالی مقصد (اجباری)
    withdrawal_date: Optional[str] = None  # 🆕 فاز ۵.۱ — تاریخ برداشت (ISO 8601)
    # 🆕 فاز ۳۳
    currency: Optional[str] = None
    reference: Optional[str] = None
    status: Optional[str] = None  # اگر داده شود، بعد از ایجاد اعمال می‌شود


# ── فاز ۱۶: Schemas تاریخچهٔ برداشت (Payout) ──
class PayoutCreate(BaseModel):
    prop_stage_id: int
    amount: float
    note: Optional[str] = None
    destination_account_id: int
    withdrawal_date: Optional[str] = None
    # 🆕 فاز ۳۳
    currency: Optional[str] = None
    reference: Optional[str] = None
    status: Optional[str] = None


class PayoutUpdate(BaseModel):
    amount: Optional[float] = None
    note: Optional[str] = None
    destination_account_id: Optional[int] = None
    withdrawal_date: Optional[str] = None
    # 🆕 فاز ۳۳
    currency: Optional[str] = None
    reference: Optional[str] = None
    status: Optional[str] = None


class PayoutStatusUpdate(BaseModel):
    """تغییر وضعیت برداشت (فاز ۳۳)."""
    status: str
    reference: Optional[str] = None


class TransferCreate(BaseModel):
    """ثبت یک پرش انتقال بین حساب‌های مالی (فاز ۳۳) — درآمد نیست."""
    to_account_id: int
    amount: float
    from_account_id: Optional[int] = None  # پیش‌فرض: حساب مقصد برداشت
    currency: Optional[str] = None
    note: Optional[str] = None
    date: Optional[str] = None



class PropCostCreate(BaseModel):
    prop_account_id: int
    cost_type: str
    amount: float
    currency: str = "USD"
    description: Optional[str] = None
    pay_from_account_id: Optional[int] = None  # 🆕 فاز ۵ — حساب پرداخت‌کننده
    create_transaction: bool = True            # 🆕 فاز ۵ — ثبت خودکار تراکنش


# ═════════════════════════════════════════════
# Prop Firm
# ═════════════════════════════════════════════
@router.get("/firms")
def get_firms(db: Session = Depends(get_db)):
    # selectinload: شمارش اکانت‌ها در یک کوئری (رفع N+1 — فاز ۱۵.۲)
    firms = db.query(PropFirm).options(selectinload(PropFirm.accounts)).all()
    result = []
    for f in firms:
        result.append({
            "id": f.id,
            "name": f.name,
            "default_profit_share": f.default_profit_share,
            "website": f.website,
            "notes": f.notes,
            "created_at": f.created_at,
            "accounts_count": len(f.accounts),
        })
    return result


@router.post("/firms")
def create_firm(firm: PropFirmCreate, db: Session = Depends(get_db)):
    db_firm = PropFirm(**firm.model_dump())
    db.add(db_firm)
    db.commit()
    db.refresh(db_firm)
    return db_firm

# ═════════════════════════════════════════════
# Prop Firm Default Rules
# ═════════════════════════════════════════════
@router.get("/firms/{firm_id}/default-rules")
def get_firm_default_rules(firm_id: int, db: Session = Depends(get_db)):
    """دریافت قوانین پیش‌فرض یک شرکت پراپ"""
    firm = db.query(PropFirm).filter(PropFirm.id == firm_id).first()
    if not firm:
        raise HTTPException(status_code=404, detail="شرکت پراپ پیدا نشد")

    rules = db.query(PropFirmDefaultRules).filter(
        PropFirmDefaultRules.prop_firm_id == firm_id
    ).all()

    return [
        {
            "stage_type": enum_value(r.stage_type),
            "profit_target": r.profit_target,
            "max_daily_dd": r.max_daily_dd,
            "max_total_dd": r.max_total_dd,
            "min_trading_days": r.min_trading_days,
            "profit_share_percentage": r.profit_share_percentage,
            "description": r.description,
        }
        for r in rules
    ]

# ═════════════════════════════════════════════
# Prop FinancialAccount
# ═════════════════════════════════════════════
@router.get("/accounts")
def get_accounts(db: Session = Depends(get_db)):
    # selectinload: firm و stages هر کدام در یک کوئری (رفع N+1 — فاز ۱۵.۲)
    accounts = (
        db.query(PropAccount)
        .options(selectinload(PropAccount.firm), selectinload(PropAccount.stages))
        .all()
    )
    result = []
    for a in accounts:
        firm = a.firm
        result.append({
            "id": a.id,
            "account_label": a.account_label,
            "account_number": a.account_number,
            "currency": a.currency,
            "is_active": a.is_active,
            "firm_id": a.prop_firm_id,
            "firm_name": firm.name if firm else "نامشخص",
            "stages_count": len(a.stages),
            "created_at": a.created_at,
        })
    return result


@router.post("/accounts")
def create_account(account: PropAccountCreate, db: Session = Depends(get_db)):
    firm = db.query(PropFirm).filter(PropFirm.id == account.prop_firm_id).first()
    if not firm:
        raise HTTPException(status_code=404, detail="شرکت پراپ پیدا نشد")

    db_account = PropAccount(
        prop_firm_id=account.prop_firm_id,
        account_label=account.account_label,
        account_number=account.account_number,
        currency=_to_currency(account.currency),  # فاز ۳۸: String → Enum(Currency)
    )
    db.add(db_account)
    db.flush()  # ← گرفتن id بدون commit (تا کل عملیات اتمیک بماند)

    # فاز ۲۸: پل «حساب مالی متناظر پراپ» حذف شد.
    # ایجاد خودکار Stage 1
    stage1 = PropStage(
        prop_account_id=db_account.id,
        stage_type=StageType.STAGE_1,
        status=StageStatus.ACTIVE,
        start_date=datetime.now(timezone.utc),
        initial_balance=account.initial_balance,
        profit_target=account.profit_target,
        max_daily_dd=account.max_daily_dd,
        max_total_dd=account.max_total_dd,
        min_trading_days=account.min_trading_days,
    )
    db.add(stage1)
    db.commit()
    db.refresh(db_account)

    return {
        "id": db_account.id,
        "message": "اکانت و مرحله ۱ ایجاد شد",
    }


@router.get("/accounts/{account_id}")
def get_account_detail(account_id: int, db: Session = Depends(get_db)):
    account = db.query(PropAccount).filter(PropAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="اکانت پیدا نشد")

    firm = db.query(PropFirm).filter(PropFirm.id == account.prop_firm_id).first()
    stages = db.query(PropStage).filter(PropStage.prop_account_id == account_id).all()

    return {
        "id": account.id,
        "account_label": account.account_label,
        "account_number": account.account_number,
        "currency": account.currency,
        "firm_name": firm.name if firm else "نامشخص",
        "stages": [
            {
                "id": s.id,
                "stage_type": s.stage_type.value if s.stage_type else None,
                "status": s.status.value if s.status else None,
                "start_date": s.start_date,
                "end_date": s.end_date,
                "profit_target": s.profit_target,
                "max_daily_dd": s.max_daily_dd,
                "max_total_dd": s.max_total_dd,
                "min_trading_days": s.min_trading_days,
                "initial_balance": s.initial_balance,
                "final_balance": s.final_balance,
                "current_profit": s.current_profit,
                "total_withdrawn": s.total_withdrawn,
                "profit_share_percentage": s.profit_share_percentage,
                "failure_reason": s.failure_reason.value if s.failure_reason else None,
                "failure_details": s.failure_details,
            }
            for s in stages
        ],
    }


# ═════════════════════════════════════════════
# Prop Stage
# ═════════════════════════════════════════════
@router.get("/stages/all")
def get_all_stages(db: Session = Depends(get_db)):
    """دریافت لیست همه‌ی مراحل پراپ (برای انتخاب در Import)"""
    stages = db.query(PropStage).all()
    result = []
    for s in stages:
        account = db.query(PropAccount).filter(PropAccount.id == s.prop_account_id).first()
        firm = db.query(PropFirm).filter(PropFirm.id == account.prop_firm_id).first() if account else None

        stage_label = {
            'stage_1': 'مرحله ۱',
            'stage_2': 'مرحله ۲',
            'funded_real': 'رییل'
        }.get(s.stage_type.value if s.stage_type else '', s.stage_type.value if s.stage_type else '')

        status_label = {
            'active': 'فعال',
            'passed': 'پاس‌شده',
            'failed': 'فیل‌شده',
            'closed': 'بسته‌شده'
        }.get(s.status.value if s.status else '', '')

        result.append({
            "id": s.id,
            "stage_type": s.stage_type.value if s.stage_type else None,
            "stage_label": stage_label,
            "status": s.status.value if s.status else None,
            "status_label": status_label,
            "account_label": account.account_label if account else "نامشخص",
            "firm_name": firm.name if firm else "نامشخص",
            "display_name": f"{firm.name if firm else '?'} / {account.account_label if account else '?'} / {stage_label} ({status_label})",
        })
    return result


@router.get("/stages/{stage_id}/check-pass")
def check_pass_ready(stage_id: int, db: Session = Depends(get_db)):
    """بررسی وضعیت مرحله قبل از پاس کردن + ایجاد هشدار خودکار"""
    from ..services.prop_rule_engine import PropRuleEngine
    evaluation = PropRuleEngine.evaluate_stage(db, stage_id)
    if "error" not in evaluation:
        _generate_alerts_for_stage(db, stage_id, evaluation)
    return evaluation


@router.post("/stages/{stage_id}/pass")
def pass_stage(stage_id: int, request: PassStageWithRulesRequest, db: Session = Depends(get_db)):
    """پاس کردن مرحله با قوانین مرحله‌ی بعدی"""
    from ..services.prop_rule_engine import PropRuleEngine

    stage = db.query(PropStage).filter(PropStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="مرحله پیدا نشد")

    if stage.stage_type == StageType.FUNDED_REAL:
        raise HTTPException(status_code=400, detail="مرحله رییل قابل پاس شدن نیست")

    # ✅ چک آمادگی با PropRuleEngine
    evaluation = PropRuleEngine.evaluate_stage(db, stage_id)
    if "error" in evaluation:
        raise HTTPException(status_code=404, detail=evaluation["error"])

    if not evaluation.get("ready_to_pass"):
        violations = evaluation.get("violations", [])
        detail = "مرحله آماده‌ی پاس شدن نیست"
        if violations:
            detail += f". دلایل: {', '.join(violations)}"
        raise HTTPException(status_code=400, detail=detail)

    # محاسبه‌ی موجودی نهایی از معاملات (با commission)
    from ..models.strategy import Trade
    # فاز ۲۵: معاملات حذف‌شده (Soft Delete) در محاسبه‌ی موجودی نهایی لحاظ نمی‌شوند
    trades = db.query(Trade).filter(
        Trade.prop_stage_id == stage_id, Trade.is_deleted == False
    ).all()
    total_pnl = sum(metrics.net_pnl(t) for t in trades)
    final_balance = (stage.initial_balance or 0) + total_pnl

    # به‌روزرسانی مرحله‌ی فعلی
    stage.status = StageStatus.PASSED
    stage.end_date = datetime.now(timezone.utc)
    stage.final_balance = final_balance
    db.commit()

    # تعیین نوع مرحله‌ی بعدی
    next_stage_type = None
    if stage.stage_type == StageType.STAGE_1:
        next_stage_type = StageType.STAGE_2
    elif stage.stage_type == StageType.STAGE_2:
        next_stage_type = StageType.FUNDED_REAL

    # ایجاد مرحله‌ی بعدی
    if next_stage_type:
        rules = request.next_stage_rules or StageRules()
        next_stage = PropStage(
            prop_account_id=stage.prop_account_id,
            stage_type=next_stage_type,
            status=StageStatus.ACTIVE,
            start_date=datetime.now(timezone.utc),
            initial_balance=rules.initial_balance or final_balance,
            profit_target=rules.profit_target,
            max_daily_dd=rules.max_daily_dd,
            max_total_dd=rules.max_total_dd,
            min_trading_days=rules.min_trading_days,
            profit_share_percentage=rules.profit_share_percentage if next_stage_type == StageType.FUNDED_REAL else None,
        )
        db.add(next_stage)
        db.commit()

    return {
        "message": "مرحله پاس شد. مرحله‌ی بعدی ایجاد شد.",
        "final_balance": final_balance,
        "total_pnl": total_pnl,
    }


@router.post("/stages/{stage_id}/fail")
def fail_stage(stage_id: int, request: FailStageRequest, db: Session = Depends(get_db)):
    stage = db.query(PropStage).filter(PropStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="مرحله پیدا نشد")

    stage.status = StageStatus.FAILED
    stage.end_date = datetime.now(timezone.utc)
    
    # تلاش برای تبدیل به enum، در غیر این صورت "other"
    try:
        stage.failure_reason = FailureReason(request.failure_reason)
    except ValueError:
        stage.failure_reason = FailureReason.OTHER
    
    stage.failure_details = request.failure_details
    db.commit()

    return {"message": "مرحله فیل شد"}


@router.patch("/stages/{stage_id}/rules")
def update_stage_rules(stage_id: int, rules: StageRulesUpdate, db: Session = Depends(get_db)):
    """ویرایش قوانین یک مرحله"""
    stage = db.query(PropStage).filter(PropStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="مرحله پیدا نشد")

    if rules.profit_target is not None:
        stage.profit_target = rules.profit_target
    if rules.max_daily_dd is not None:
        stage.max_daily_dd = rules.max_daily_dd
    if rules.max_total_dd is not None:
        stage.max_total_dd = rules.max_total_dd
    if rules.min_trading_days is not None:
        stage.min_trading_days = rules.min_trading_days
    if rules.initial_balance is not None:
        stage.initial_balance = rules.initial_balance
    if rules.profit_share_percentage is not None:
        stage.profit_share_percentage = rules.profit_share_percentage

    db.commit()
    db.refresh(stage)
    return {"message": "قوانین مرحله با موفقیت به‌روزرسانی شد"}


@router.get("/stages/{stage_id}/trades")
def get_stage_trades(stage_id: int, db: Session = Depends(get_db)):
    """دریافت معاملات یک مرحله"""
    from ..models.strategy import Trade
    # فاز ۲۵: معاملات حذف‌شده نمایش داده نمی‌شوند
    trades = db.query(Trade).filter(
        Trade.prop_stage_id == stage_id, Trade.is_deleted == False
    ).all()
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "direction": t.direction,
            "open_time": t.open_time,
            "close_time": t.close_time,
            "open_price": t.open_price,
            "close_price": t.close_price,
            "size": t.size,
            "pnl": t.pnl,
            "commission": t.commission,
            "swap": t.swap,
        }
        for t in trades
    ]


# ═════════════════════════════════════════════
# فاز ۳۲ — Rule Engine (Rule Evaluation)
# ═════════════════════════════════════════════
def _serialize_rule_violation(v) -> dict:
    """خروجی JSON یک رکورد ارزیابی قاعده"""
    return {
        "id": v.id,
        "prop_stage_id": v.prop_stage_id,
        "rule_type": enum_value(v.rule_type),
        "actual_value": v.actual_value,
        "limit_value": v.limit_value,
        "severity": enum_value(v.severity),
        "occurred_at": v.occurred_at.isoformat() if v.occurred_at else None,
    }


@router.post("/stages/{stage_id}/evaluate")
def evaluate_stage_rules(stage_id: int, db: Session = Depends(get_db)):
    """اجرای Rule Evaluation یک مرحله و ثبت نتایج در `rule_violations`."""
    from ..services.prop_rule_engine import PropRuleEngine

    evaluation = PropRuleEngine.evaluate_stage(db, stage_id)
    if "error" in evaluation:
        raise HTTPException(status_code=404, detail=evaluation["error"])

    checks = evaluation.get("rule_checks", [])
    recorded = PropRuleEngine.record_violations(db, stage_id, checks)
    _generate_alerts_for_stage(db, stage_id, evaluation)

    return {
        "stage_id": stage_id,
        "overall_severity": evaluation.get("overall_severity"),
        "recorded": len(recorded),
        "rule_checks": checks,
        "evaluation": evaluation,
    }


@router.get("/stages/{stage_id}/violations")
def get_stage_violations(
    stage_id: int,
    severity: Optional[str] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """تاریخچهٔ ارزیابی قوانین یک مرحله (جدیدترین اول) — فاز ۳۲."""
    from ..services.prop_rule_engine import PropRuleEngine

    stage = db.query(PropStage).filter(PropStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="مرحله پیدا نشد")

    if severity is not None and severity not in ("pass", "warning", "violation"):
        raise HTTPException(
            status_code=400, detail="severity نامعتبر است (pass | warning | violation)"
        )

    rows = PropRuleEngine.get_violations(db, stage_id, severity=severity, limit=limit)
    return [_serialize_rule_violation(r) for r in rows]


# ═════════════════════════════════════════════
# Withdrawal
# ═════════════════════════════════════════════
@router.post("/stages/{stage_id}/withdraw")
def withdraw(stage_id: int, request: WithdrawalCreate, db: Session = Depends(get_db)):
    """ثبت برداشت برای یک مرحله (فاز ۵ / به‌روزرسانی فاز ۳۳).

    پیش‌فرض وضعیت REQUESTED است؛ اگر `status` داده شود همان اعمال می‌شود
    (درآمد فقط در نقطه‌ی RECEIVED ثبت می‌شود).
    """
    return _create_payout_record(
        db,
        stage_id=stage_id,
        amount=request.amount,
        note=request.note,
        destination_account_id=request.destination_account_id,
        withdrawal_date=request.withdrawal_date,
        currency=request.currency,
        reference=request.reference,
        status=request.status,
    )


@router.get("/stages/{stage_id}/withdrawals")
def get_stage_withdrawals(stage_id: int, db: Session = Depends(get_db)):
    """لیست برداشت‌های یک مرحله پراپ"""
    stage = db.query(PropStage).filter(PropStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="مرحله پیدا نشد")

    rows = (
        db.query(PropWithdrawal)
        .filter(PropWithdrawal.prop_stage_id == stage_id)
        .order_by(PropWithdrawal.withdrawal_date.desc())
        .all()
    )
    return [
        {
            "id": w.id,
            "amount": w.amount,
            "withdrawal_date": w.withdrawal_date,
            "note": w.note,
            "destination_account_id": w.destination_account_id,
            "destination_account_name": (
                w.destination_account.name if w.destination_account else None
            ),
        }
        for w in rows
    ]


# ═════════════════════════════════════════════
# Payouts — تاریخچهٔ برداشت‌ها (فاز ۱۶)
# ═════════════════════════════════════════════
def _create_payout_record(
    db: Session,
    stage_id: int,
    amount: float,
    note: Optional[str],
    destination_account_id: int,
    withdrawal_date: Optional[str] = None,
    currency: Optional[str] = None,
    reference: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """منطق مشترک ثبت برداشت پراپ (فاز ۱۶ → بازنویسی در فاز ۳۳).

    - اعتبارسنجی مرحله (FUNDED_REAL) با PropRuleEngine
    - ایجاد `PropWithdrawal` با وضعیت پیش‌فرض REQUESTED (بدون تراکنش مالی)
    - اگر `status` داده شود، انتقال وضعیت اعمال می‌شود؛ **درآمد فقط در RECEIVED**
      توسط `PayoutService` ثبت می‌شود (نه در لحظه‌ی ایجاد).
    """
    from ..services.prop_rule_engine import PropRuleEngine
    from ..services.payout_service import PayoutService

    stage = db.query(PropStage).filter(PropStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="مرحله پیدا نشد")

    if stage.stage_type != StageType.FUNDED_REAL:
        raise HTTPException(status_code=400, detail="برداشت فقط در مرحله رییل مجاز است")

    is_valid, error = PropRuleEngine.validate_withdrawal(db, stage_id, amount)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    try:
        withdrawal = PayoutService.create(
            db,
            stage=stage,
            amount=amount,
            destination_account_id=destination_account_id,
            note=note,
            reference=reference,
            withdrawal_date=withdrawal_date,
            currency=currency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    posted = None
    if status:
        try:
            withdrawal, posted = PayoutService.set_status(db, withdrawal, status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    return {
        "message": f"برداشت {amount} با وضعیت {withdrawal.status.value} ثبت شد",
        "id": withdrawal.id,
        "status": withdrawal.status.value,
        "transaction_id": posted.id if posted else withdrawal.transaction_id,
        "source_account_id": None,
        "destination_account_id": destination_account_id,
    }


def _serialize_payout(w: PropWithdrawal) -> dict:
    """خروجی یک برداشت پراپ با اطلاعات مرحله/اکانت/شرکت و حساب مقصد"""
    stage = w.stage
    account = stage.account if stage else None
    firm = account.firm if account and account.firm else None
    return {
        "id": w.id,
        "prop_stage_id": w.prop_stage_id,
        "stage_type": stage.stage_type.value if stage and stage.stage_type else None,
        "stage_status": stage.status.value if stage and stage.status else None,
        "prop_account_id": account.id if account else None,
        "account_label": account.account_label if account else None,
        "currency": (w.currency.value if w.currency else (account.currency if account else None)),
        "firm_id": firm.id if firm else None,
        "firm_name": firm.name if firm else None,
        "amount": w.amount,
        "status": enum_value(w.status) if w.status else None,
        "reference": w.reference,
        "transaction_id": w.transaction_id,
        "allowed_transitions": (
            [s.value for s in WITHDRAWAL_TRANSITIONS.get(w.status, ())]
            if w.status
            else []
        ),
        "withdrawal_date": w.withdrawal_date.isoformat() if w.withdrawal_date else None,
        "created_at": w.created_at.isoformat() if w.created_at else None,
        "note": w.note,
        "destination_account_id": w.destination_account_id,
        "destination_account_name": w.destination_account.name if w.destination_account else None,
    }


def _payout_filter_query(
    db: Session,
    firm_id: Optional[int] = None,
    currency: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """کوئری پایهٔ برداشت‌ها با فیلترهای اختیاری (بدون joinedload تا برای aggregate هم قابل استفاده باشد)"""
    q = db.query(PropWithdrawal)
    if firm_id or currency:
        q = (
            q.join(PropStage, PropWithdrawal.prop_stage_id == PropStage.id)
            .join(PropAccount, PropStage.prop_account_id == PropAccount.id)
        )
        if firm_id:
            q = q.filter(PropAccount.prop_firm_id == firm_id)
        if currency:
            q = q.filter(PropAccount.currency == currency)
    # فاز ۴۶.۵: date_to شامل آخرین روز است
    q = filter_by_range(q, PropWithdrawal.withdrawal_date, date_from, date_to)
    return q


def _payout_eager():
    """گزینه‌های eager loading برداشت‌ها — به‌صورت تابع تا در زمان import، mapper پیکربندی نشود."""
    return (
        joinedload(PropWithdrawal.stage)
        .joinedload(PropStage.account)
        .joinedload(PropAccount.firm),
        joinedload(PropWithdrawal.destination_account),
    )


@router.get("/payouts")
def list_payouts(
    firm_id: Optional[int] = None,
    currency: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: Optional[int] = Query(None, ge=1, le=2000, description="فاز ۳۶ — حداکثر تعداد"),
    offset: int = Query(0, ge=0, description="فاز ۳۶ — جابه‌جایی (Pagination)"),
    db: Session = Depends(get_db),
):
    """لیست برداشت‌های پراپ با فیلتر شرکت/ارز/بازهٔ تاریخ (فاز ۱۶) + Pagination (فاز ۳۶)"""
    q = (
        _payout_filter_query(db, firm_id, currency, date_from, date_to)
        .options(*_payout_eager())
        .order_by(PropWithdrawal.withdrawal_date.desc(), PropWithdrawal.id.desc())
    )
    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    return [_serialize_payout(w) for w in q.all()]


@router.get("/payouts/stats")
def get_payout_stats(
    firm_id: Optional[int] = None,
    currency: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """آمار برداشت‌های پراپ (فاز ۱۶) — محاسبات در SQL"""
    q = _payout_filter_query(db, firm_id, currency, date_from, date_to)

    agg = q.with_entities(
        func.count(PropWithdrawal.id),
        func.coalesce(func.sum(PropWithdrawal.amount), 0.0),
        func.max(PropWithdrawal.amount),
    ).one()
    count = int(agg[0] or 0)
    total = float(agg[1] or 0.0)
    largest = float(agg[2] or 0.0)

    # فاز ۴۶.۴: گروه‌بندی ماهانه بر پایهٔ وقت تهران (نه UTC)
    monthly_map: dict[str, float] = {}
    for w in q.all():
        if not w.withdrawal_date:
            continue
        key = to_tehran(w.withdrawal_date).strftime("%Y-%m")
        monthly_map[key] = monthly_map.get(key, 0.0) + float(w.amount or 0.0)
    monthly = [
        {"month": k, "amount": round(v, 2)}
        for k, v in sorted(monthly_map.items())
    ]

    by_firm_rows = (
        db.query(PropFirm.name, func.sum(PropWithdrawal.amount), func.count(PropWithdrawal.id))
        .join(PropStage, PropWithdrawal.prop_stage_id == PropStage.id)
        .join(PropAccount, PropStage.prop_account_id == PropAccount.id)
        .join(PropFirm, PropAccount.prop_firm_id == PropFirm.id)
        .group_by(PropFirm.name)
        .all()
    )

    return {
        "total": round(total, 2),
        "count": count,
        "average": round((total / count) if count else 0.0, 2),
        "largest": round(largest, 2),
        "monthly": monthly,
        "by_firm": [
            {"name": n, "amount": round(float(a or 0), 2), "count": int(c or 0)}
            for n, a, c in by_firm_rows
        ],
    }


@router.post("/payouts")
def create_payout(data: PayoutCreate, db: Session = Depends(get_db)):
    """ثبت برداشت جدید پراپ (فاز ۱۶ → به‌روزرسانی فاز ۳۳).

    پیش‌فرض وضعیت `REQUESTED` است؛ درآمد فقط در `RECEIVED` ثبت می‌شود.
    """
    return _create_payout_record(
        db,
        stage_id=data.prop_stage_id,
        amount=data.amount,
        note=data.note,
        destination_account_id=data.destination_account_id,
        withdrawal_date=data.withdrawal_date,
        currency=data.currency,
        reference=data.reference,
        status=data.status,
    )


@router.put("/payouts/{payout_id}")
@router.patch("/payouts/{payout_id}")
def update_payout(payout_id: int, data: PayoutUpdate, db: Session = Depends(get_db)):
    """ویرایش برداشت پراپ (فاز ۱۶ → یکپارچگی کامل فاز ۳۳) — هم PUT و هم PATCH"""
    from ..services.payout_service import PayoutService

    w = db.query(PropWithdrawal).filter(PropWithdrawal.id == payout_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="برداشت پیدا نشد")

    payload = data.model_dump(exclude_unset=True)
    try:
        PayoutService.update(db, w, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"message": "برداشت به‌روزرسانی شد", "payout": _serialize_payout(w)}


@router.delete("/payouts/{payout_id}")
def delete_payout(payout_id: int, db: Session = Depends(get_db)):
    """حذف برداشت + برگشت کامل اثر مالی آن (فاز ۱۶ → فاز ۳۳)"""
    from ..services.payout_service import PayoutService

    w = db.query(PropWithdrawal).filter(PropWithdrawal.id == payout_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="برداشت پیدا نشد")

    PayoutService.delete_and_reverse(db, w)
    return {"message": "برداشت حذف و اثر مالی آن برگشت داده شد"}


@router.post("/payouts/{payout_id}/status")
def update_payout_status(
    payout_id: int, data: PayoutStatusUpdate, db: Session = Depends(get_db)
):
    """تغییر وضعیت برداشت (فاز ۳۳).

    فقط انتقال‌های مجاز؛ در نقطه‌ی `RECEIVED` برای اولین بار **درآمد**
    (`FinancialTransaction` از نوع `PROFIT`) ثبت می‌شود.
    """
    from ..services.payout_service import PayoutService

    w = db.query(PropWithdrawal).filter(PropWithdrawal.id == payout_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="برداشت پیدا نشد")

    if data.reference is not None:
        w.reference = data.reference

    try:
        w, posted = PayoutService.set_status(db, w, data.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "message": f"وضعیت برداشت به {enum_value(w.status)} تغییر کرد",
        "payout": _serialize_payout(w),
        "income_transaction_id": posted.id if posted else None,
    }


@router.post("/payouts/{payout_id}/transfer")
def create_payout_transfer(
    payout_id: int, data: TransferCreate, db: Session = Depends(get_db)
):
    """ثبت یک پرش انتقال بعد از دریافت (فاز ۳۳) — **درآمد نیست**.

    سناریو: Prop → Trust Wallet → Exchange → IRR → Bank Card.
    هر پرش با `type=exchange` ثبت می‌شود و در `finance/summary` در
    `total_transfers` می‌آید، نه `total_income`.
    """
    from ..services.payout_service import PayoutService

    w = db.query(PropWithdrawal).filter(PropWithdrawal.id == payout_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="برداشت پیدا نشد")

    from_account_id = data.from_account_id or w.destination_account_id
    stage = db.query(PropStage).filter(PropStage.id == w.prop_stage_id).first()

    try:
        tx = PayoutService.record_transfer(
            db,
            from_account_id=from_account_id,
            to_account_id=data.to_account_id,
            amount=data.amount,
            currency=data.currency,
            note=data.note,
            related_prop_account_id=stage.prop_account_id if stage else None,
            date=data.date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "message": "انتقال ثبت شد (درآمد نیست)",
        "transaction_id": tx.id,
        "from_account_id": from_account_id,
        "to_account_id": data.to_account_id,
        "amount": tx.amount,
    }



# ═════════════════════════════════════════════
# Prop Alert (هشدارها)
# ═════════════════════════════════════════════
def _generate_alerts_for_stage(db: Session, stage_id: int, evaluation: dict = None):
    """بررسی خودکار و ایجاد هشدار برای یک مرحله پراپ"""
    if not evaluation:
        from ..services.prop_rule_engine import PropRuleEngine
        evaluation = PropRuleEngine.evaluate_stage(db, stage_id)

    new_alerts = []
    stage = db.query(PropStage).filter(PropStage.id == stage_id).first()
    if not stage:
        return new_alerts

    # هشدار Daily DD نزدیک به حد
    dd_limit = evaluation.get("max_daily_dd_limit", 0)
    dd_current = evaluation.get("max_daily_loss", 0)
    if dd_limit > 0 and dd_current > 0:
        dd_percent = dd_current / dd_limit * 100
        if 80 <= dd_percent < 100:
            msg = f"⚠️ Daily DD به {dd_percent:.0f}% حد مجاز رسیده ({dd_current:.0f}$ از {dd_limit:.0f}$)"
            existing = db.query(PropAlert).filter(
                PropAlert.prop_stage_id == stage_id,
                PropAlert.message == msg,
                PropAlert.is_read == False,
            ).first()
            if not existing:
                new_alerts.append(PropAlert(prop_stage_id=stage_id, message=msg))
        elif dd_percent >= 100:
            msg = f"🚨 Daily DD نقض شده! ({dd_current:.0f}$ > {dd_limit:.0f}$)"
            existing = db.query(PropAlert).filter(
                PropAlert.prop_stage_id == stage_id,
                PropAlert.message.contains("Daily DD نقض"),
                PropAlert.is_read == False,
            ).first()
            if not existing:
                new_alerts.append(PropAlert(prop_stage_id=stage_id, message=msg))

    # هشدار Total DD نزدیک به حد
    td_limit = evaluation.get("max_total_dd_limit", 0)
    td_current = evaluation.get("max_total_dd", 0)
    if td_limit > 0 and td_current > 0:
        td_percent = td_current / td_limit * 100
        if 80 <= td_percent < 100:
            msg = f"⚠️ Total DD به {td_percent:.0f}% حد مجاز رسیده ({td_current:.0f}$ از {td_limit:.0f}$)"
            existing = db.query(PropAlert).filter(
                PropAlert.prop_stage_id == stage_id,
                PropAlert.message == msg,
                PropAlert.is_read == False,
            ).first()
            if not existing:
                new_alerts.append(PropAlert(prop_stage_id=stage_id, message=msg))
        elif td_percent >= 100:
            msg = f"🚨 Total DD نقض شده! ({td_current:.0f}$ > {td_limit:.0f}$)"
            existing = db.query(PropAlert).filter(
                PropAlert.prop_stage_id == stage_id,
                PropAlert.message.contains("Total DD نقض"),
                PropAlert.is_read == False,
            ).first()
            if not existing:
                new_alerts.append(PropAlert(prop_stage_id=stage_id, message=msg))

    # هشدار نزدیکی به هدف سود
    profit_target = evaluation.get("profit_target", 0)
    current_profit = evaluation.get("current_profit", 0)
    if profit_target > 0 and current_profit > 0:
        profit_percent = current_profit / profit_target * 100
        if profit_percent >= 90 and profit_percent < 100:
            msg = f"🎯 به {profit_percent:.0f}% هدف سود رسیده‌اید ({current_profit:.0f}$ از {profit_target:.0f}$)"
            existing = db.query(PropAlert).filter(
                PropAlert.prop_stage_id == stage_id,
                PropAlert.message.contains("هدف سود"),
                PropAlert.is_read == False,
            ).first()
            if not existing:
                new_alerts.append(PropAlert(prop_stage_id=stage_id, message=msg))

    if new_alerts:
        for a in new_alerts:
            db.add(a)
        db.commit()

    return new_alerts


@router.get("/alerts")
def get_alerts(
    stage_id: Optional[int] = None,
    unread_only: bool = False,
    db: Session = Depends(get_db),
):
    """لیست هشدارها (با قابلیت فیلتر بر اساس stage_id و unread_only)"""
    query = db.query(PropAlert).order_by(PropAlert.created_at.desc())
    if stage_id:
        query = query.filter(PropAlert.prop_stage_id == stage_id)
    if unread_only:
        query = query.filter(PropAlert.is_read == False)
    alerts = query.all()
    return [
        {
            "id": a.id,
            "prop_stage_id": a.prop_stage_id,
            "message": a.message,
            "is_read": a.is_read,
            "created_at": a.created_at,
        }
        for a in alerts
    ]


@router.patch("/alerts/{alert_id}/read")
def mark_alert_read(alert_id: int, db: Session = Depends(get_db)):
    """علامت‌گذاری هشدار به عنوان خوانده‌شده"""
    alert = db.query(PropAlert).filter(PropAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="هشدار پیدا نشد")
    alert.is_read = True
    db.commit()
    return {"message": "هشدار به‌عنوان خوانده‌شده علامت‌گذاری شد"}


@router.post("/alerts/generate")
def generate_alerts(db: Session = Depends(get_db)):
    """ایجاد خودکار هشدارها برای همه مراحل فعال"""
    from ..models.prop import StageStatus
    from ..services.prop_rule_engine import PropRuleEngine

    active_stages = db.query(PropStage).filter(PropStage.status == StageStatus.ACTIVE).all()
    total_new = 0
    for stage in active_stages:
        evaluation = PropRuleEngine.evaluate_stage(db, stage.id)
        new_alerts = _generate_alerts_for_stage(db, stage.id, evaluation)
        total_new += len(new_alerts)
    return {"message": f"{total_new} هشدار جدید ایجاد شد"}
# ═════════════════════════════════════════════
# Prop Cost
# ═════════════════════════════════════════════
@router.post("/costs")
def create_cost(cost: PropCostCreate, db: Session = Depends(get_db)):
    """ثبت هزینه پراپ + (برای purchase) ثبت خودکار تراکنش مالی"""
    # فاز ۳۸: cost_type نوعدار (lowercase — سازگار با قرارداد قبلی)
    try:
        cost_type = CostType((cost.cost_type or "").strip().lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="نوع هزینه نامعتبر است (مجاز: " + ", ".join(t.value for t in CostType) + ")",
        )

    is_purchase = cost.create_transaction and cost_type == CostType.PURCHASE

    # ── اعتبارسنجی قبل از هر درج (تا در صورت خطا هیچ رکوردی باقی نماند) ──
    prop_acc = None
    payer = None
    if is_purchase:
        prop_acc = db.query(PropAccount).filter(PropAccount.id == cost.prop_account_id).first()
        if cost.pay_from_account_id:
            payer = db.query(FinancialAccount).filter(FinancialAccount.id == cost.pay_from_account_id).first()
            if not payer:
                raise HTTPException(status_code=400, detail="حساب پرداخت‌کننده معتبر نیست")
        if not payer:
            raise HTTPException(
                status_code=400,
                detail="حساب پرداخت‌کننده الزامی است (pay_from_account_id)",
            )

    db_cost = PropCost(
        prop_account_id=cost.prop_account_id,
        cost_type=cost_type,
        amount=cost.amount,
        currency=_to_currency(cost.currency),
        description=cost.description,
    )
    db.add(db_cost)
    db.flush()

    # ── تراکنش خرید پراپ ──
    transaction_id = None
    if payer:
        cat = _get_or_create_category(db, "خرید پراپ", CategoryType.EXPENSE, "#E74C3C", "🛒")

        # فاز ۳۹: از مسیر WalletService (تنها نویسندهٔ موجودی) — با محافظ موجودی
        try:
            tx = WalletService.post(
                db,
                account_id=payer.id,
                type=TransactionType.PURCHASE,
                amount=cost.amount,
                currency=_to_currency(cost.currency),
                date=datetime.now(timezone.utc),
                category_id=cat.id,
                from_account_id=payer.id,
                description=cost.description or (
                    f"خرید پراپ {prop_acc.account_label}" if prop_acc else "خرید پراپ"
                ),
                related_prop_account_id=cost.prop_account_id,
                commit=False,
            )
        except WalletError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(exc))
        transaction_id = tx.id

    db.commit()
    db.refresh(db_cost)

    return {
        "id": db_cost.id,
        "transaction_id": transaction_id,
        "message": "هزینه ثبت شد",
    }


@router.get("/accounts/{account_id}/costs")
def get_costs(account_id: int, db: Session = Depends(get_db)):
    costs = db.query(PropCost).filter(PropCost.prop_account_id == account_id).all()
    return costs


# فاز ۲۸: endpointهای «حساب مالی متناظر پراپ» (/accounts/{id}/finance-account) حذف شدند.
# PropAccount حساب معاملاتی است؛ پول فقط هنگام برداشت (PropWithdrawal) وارد FINANCE می‌شود.


@router.get("/analytics")
def get_prop_analytics(db: Session = Depends(get_db)):
    """گزارش تحلیلی پراپ"""
    from ..models.prop import PropStage, StageType, StageStatus

    all_stages = db.query(PropStage).all()

    # آمار کلی
    total_stages = len(all_stages)
    passed_count = sum(1 for s in all_stages if s.status == StageStatus.PASSED)
    failed_count = sum(1 for s in all_stages if s.status == StageStatus.FAILED)
    active_count = sum(1 for s in all_stages if s.status == StageStatus.ACTIVE)

    # تفکیک بر اساس نوع
    by_type = {}
    for s in all_stages:
        type_key = s.stage_type.value if s.stage_type else "unknown"
        if type_key not in by_type:
            by_type[type_key] = {"total": 0, "passed": 0, "failed": 0, "active": 0}
        by_type[type_key]["total"] += 1
        if s.status == StageStatus.PASSED:
            by_type[type_key]["passed"] += 1
        elif s.status == StageStatus.FAILED:
            by_type[type_key]["failed"] += 1
        elif s.status == StageStatus.ACTIVE:
            by_type[type_key]["active"] += 1

    # دلایل فیل‌شدن
    failure_reasons = {}
    failed_stages = [s for s in all_stages if s.status == StageStatus.FAILED]
    for s in failed_stages:
        if s.failure_reason:
            reason = s.failure_reason.value
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

    # سود کل مرحله رییل
    total_profit = sum(s.current_profit or 0 for s in all_stages if s.stage_type == StageType.FUNDED_REAL)
    total_withdrawn = sum(s.total_withdrawn or 0 for s in all_stages if s.stage_type == StageType.FUNDED_REAL)

    # میانگین زمان پاس‌شدن
    passed_with_dates = [
        s for s in all_stages
        if s.status == StageStatus.PASSED and s.start_date and s.end_date
    ]
    avg_days_to_pass = 0
    if passed_with_dates:
        total_days = sum((s.end_date - s.start_date).days for s in passed_with_dates)
        avg_days_to_pass = round(total_days / len(passed_with_dates), 1)

    return {
        "summary": {
            "total_stages": total_stages,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "active_count": active_count,
            "pass_rate": round((passed_count / total_stages * 100) if total_stages > 0 else 0, 1),
            "total_profit": round(total_profit, 2),
            "total_withdrawn": round(total_withdrawn, 2),
            "avg_days_to_pass": avg_days_to_pass,
        },
        "by_type": by_type,
        "failure_reasons": failure_reasons,
    }