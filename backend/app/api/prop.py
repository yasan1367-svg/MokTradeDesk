from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from ..core.database import get_db
from ..models.prop import (
    PropFirm, PropAccount, PropStage, PropWithdrawal, PropCost,
    StageType, StageStatus, FailureReason
)

router = APIRouter()


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
    target_personal_account_id: Optional[int] = None  # ← اکانت شخصی مقصد


class PropCostCreate(BaseModel):
    prop_account_id: int
    cost_type: str
    amount: float
    currency: str = "USD"
    description: Optional[str] = None


# ═════════════════════════════════════════════
# Prop Firm
# ═════════════════════════════════════════════
@router.get("/firms")
def get_firms(db: Session = Depends(get_db)):
    firms = db.query(PropFirm).all()
    result = []
    for f in firms:
        accounts = db.query(PropAccount).filter(PropAccount.prop_firm_id == f.id).all()
        result.append({
            "id": f.id,
            "name": f.name,
            "default_profit_share": f.default_profit_share,
            "website": f.website,
            "notes": f.notes,
            "created_at": f.created_at,
            "accounts_count": len(accounts),
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
# Prop Account
# ═════════════════════════════════════════════
@router.get("/accounts")
def get_accounts(db: Session = Depends(get_db)):
    accounts = db.query(PropAccount).all()
    result = []
    for a in accounts:
        firm = db.query(PropFirm).filter(PropFirm.id == a.prop_firm_id).first()
        stages = db.query(PropStage).filter(PropStage.prop_account_id == a.id).all()
        result.append({
            "id": a.id,
            "account_label": a.account_label,
            "account_number": a.account_number,
            "currency": a.currency,
            "is_active": a.is_active,
            "firm_id": a.prop_firm_id,
            "firm_name": firm.name if firm else "نامشخص",
            "stages_count": len(stages),
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
        currency=account.currency,
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)

    # ایجاد خودکار Stage 1
    stage1 = PropStage(
        prop_account_id=db_account.id,
        stage_type=StageType.STAGE_1,
        status=StageStatus.ACTIVE,
        start_date=datetime.utcnow(),
        initial_balance=account.initial_balance,
        profit_target=account.profit_target,
        max_daily_dd=account.max_daily_dd,
        max_total_dd=account.max_total_dd,
        min_trading_days=account.min_trading_days,
    )
    db.add(stage1)
    db.commit()

    return {"id": db_account.id, "message": "اکانت و مرحله ۱ ایجاد شد"}


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
    """بررسی وضعیت مرحله قبل از پاس کردن"""
    from ..services.prop_rule_engine import PropRuleEngine
    return PropRuleEngine.evaluate_stage(db, stage_id)


@router.post("/stages/{stage_id}/pass")
def pass_stage(stage_id: int, request: PassStageWithRulesRequest, db: Session = Depends(get_db)):
    """پاس کردن مرحله با قوانین مرحله‌ی بعدی"""
    stage = db.query(PropStage).filter(PropStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="مرحله پیدا نشد")

    if stage.stage_type == StageType.FUNDED_REAL:
        raise HTTPException(status_code=400, detail="مرحله رییل قابل پاس شدن نیست")

    # محاسبه‌ی موجودی نهایی از معاملات
    from ..models.strategy import Trade
    trades = db.query(Trade).filter(Trade.prop_stage_id == stage_id).all()
    total_pnl = sum(t.pnl or 0 for t in trades)
    final_balance = (stage.initial_balance or 0) + total_pnl

    # به‌روزرسانی مرحله‌ی فعلی
    stage.status = StageStatus.PASSED
    stage.end_date = datetime.utcnow()
    stage.final_balance = final_balance
    db.commit()

    # تعیین نوع مرحله‌ی بعدی
    next_stage_type = None
    if stage.stage_type == StageType.STAGE_1:
        next_stage_type = StageType.STAGE_2
    elif stage.stage_type == StageType.STAGE_2:
        next_stage_type = StageType.FUNDED_REAL

    # ایجاد مرحله‌ی بعدی با قوانین وارد شده
    if next_stage_type:
        rules = request.next_stage_rules or StageRules()
        next_stage = PropStage(
            prop_account_id=stage.prop_account_id,
            stage_type=next_stage_type,
            status=StageStatus.ACTIVE,
            start_date=datetime.utcnow(),
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
    stage.end_date = datetime.utcnow()
    
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
    trades = db.query(Trade).filter(Trade.prop_stage_id == stage_id).all()
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
# Withdrawal
# ═════════════════════════════════════════════
@router.post("/stages/{stage_id}/withdraw")
def withdraw(stage_id: int, request: WithdrawalCreate, db: Session = Depends(get_db)):
    stage = db.query(PropStage).filter(PropStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="مرحله پیدا نشد")

    if stage.stage_type != StageType.FUNDED_REAL:
        raise HTTPException(status_code=400, detail="برداشت فقط در مرحله رییل مجاز است")

    withdrawal = PropWithdrawal(
        prop_stage_id=stage_id,
        amount=request.amount,
        note=request.note,
    )
    db.add(withdrawal)

    stage.total_withdrawn = (stage.total_withdrawn or 0) + request.amount
    stage.current_profit = (stage.current_profit or 0) - request.amount

    try:
        from ..models.personal import LedgerTransaction, TransactionType
        account = db.query(PropAccount).filter(PropAccount.id == stage.prop_account_id).first()

        description = f"برداشت از {account.account_label if account else 'پراپ'}"
        if request.note:
            description += f" - {request.note}"

        ledger = LedgerTransaction(
            transaction_type=TransactionType.PROP_PAYOUT,
            source_type="prop_stage",
            source_id=stage_id,
            prop_account_id=stage.prop_account_id,
            personal_account_id=request.target_personal_account_id,
            amount=request.amount,
            description=description,
        )
        db.add(ledger)
    except Exception as e:
        print(f"⚠️ خطا در ثبت Ledger: {e}")

    db.commit()

    return {"message": f"{request.amount} دلار برداشت ثبت شد و به درآمد اضافه شد"}


# ═════════════════════════════════════════════
# Prop Cost
# ═════════════════════════════════════════════
@router.post("/costs")
def create_cost(cost: PropCostCreate, db: Session = Depends(get_db)):
    db_cost = PropCost(**cost.model_dump())
    db.add(db_cost)
    db.commit()
    db.refresh(db_cost)
    return db_cost


@router.get("/accounts/{account_id}/costs")
def get_costs(account_id: int, db: Session = Depends(get_db)):
    costs = db.query(PropCost).filter(PropCost.prop_account_id == account_id).all()
    return costs

@router.get("/analytics")
def get_prop_analytics(db: Session = Depends(get_db)):
    """گزارش تحلیلی پراپ"""
    from ..models.prop import PropStage, StageType, StageStatus, FailureReason

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