from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from ..core.database import get_db
from ..models.prop import (
    PropFirm, PropFirmDefaultRules, PropAccount, PropStage, PropWithdrawal, PropCost,
    StageType, StageStatus, FailureReason
)
from ..models.finance import (
    Account, AccountType, Category, CategoryType, Currency, Transaction, TransactionType
)

router = APIRouter()


# ═════════════════════════════════════════════
# Helpers — Prop ↔ Finance (فاز ۵)
# ═════════════════════════════════════════════
def _to_currency(value: Optional[str]) -> Currency:
    """تبدیل ارز رشته‌ای پراپ به Enum مالی (IRR|USD) با fallback امن"""
    try:
        return Currency((value or "USD").upper())
    except ValueError:
        return Currency.USD


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


def _ensure_finance_account(db: Session, prop_acc: PropAccount) -> Optional[Account]:
    """اگر اکانت پراپ حساب مالی ندارد، آن را می‌سازد و وصل می‌کند"""
    if prop_acc.finance_account_id:
        existing = db.query(Account).filter(Account.id == prop_acc.finance_account_id).first()
        if existing:
            return existing

    firm = db.query(PropFirm).filter(PropFirm.id == prop_acc.prop_firm_id).first()
    stage1 = (
        db.query(PropStage)
        .filter(PropStage.prop_account_id == prop_acc.id)
        .order_by(PropStage.id.asc())
        .first()
    )
    fin = Account(
        name=prop_acc.account_label,
        type=AccountType.PROP,
        currency=_to_currency(prop_acc.currency),
        balance=stage1.initial_balance if stage1 and stage1.initial_balance else 0.0,
        prop_firm_name=firm.name if firm else None,
        prop_firm_id=prop_acc.prop_firm_id,
    )
    db.add(fin)
    db.flush()
    prop_acc.finance_account_id = fin.id
    return fin


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
    create_finance_account: bool = True  # 🆕 فاز ۵ — ساخت خودکار حساب مالی


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
            "stage_type": r.stage_type.value if hasattr(r.stage_type, 'value') else str(r.stage_type),
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
    db.flush()  # ← گرفتن id بدون commit (تا کل عملیات اتمیک بماند)

    # 🆕 فاز ۵ — ساخت خودکار حساب مالی متناظر
    finance_account_id = None
    if account.create_finance_account:
        fin = Account(
            name=account.account_label,
            type=AccountType.PROP,
            currency=_to_currency(account.currency),
            balance=account.initial_balance or 0.0,
            prop_firm_name=firm.name,
            prop_firm_id=account.prop_firm_id,
        )
        db.add(fin)
        db.flush()
        db_account.finance_account_id = fin.id
        finance_account_id = fin.id

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
        "finance_account_id": finance_account_id,
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
    trades = db.query(Trade).filter(Trade.prop_stage_id == stage_id).all()
    total_pnl = sum(
        (t.pnl or 0) + (t.commission or 0) + (t.swap or 0)
        for t in trades
    )
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
    from ..services.prop_rule_engine import PropRuleEngine

    stage = db.query(PropStage).filter(PropStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="مرحله پیدا نشد")

    if stage.stage_type != StageType.FUNDED_REAL:
        raise HTTPException(status_code=400, detail="برداشت فقط در مرحله رییل مجاز است")

    # ✅ چک مجاز بودن برداشت با PropRuleEngine
    is_valid, error = PropRuleEngine.validate_withdrawal(db, stage_id, request.amount)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # 🆕 فاز ۵ — اعتبارسنجی حساب مالی مقصد
    dest = db.query(Account).filter(
        Account.id == request.destination_account_id,
        Account.type != AccountType.PROP,
    ).first()
    if not dest:
        raise HTTPException(
            status_code=400,
            detail="حساب مقصد معتبر نیست (باید بانک/صرافی/کیف‌پول/بروکر باشد)",
        )

    prop_acc = db.query(PropAccount).filter(PropAccount.id == stage.prop_account_id).first()

    # 🆕 فاز ۵ — اگر اکانت پراپ حساب مالی ندارد، خودکار ساخته می‌شود
    src_acct = _ensure_finance_account(db, prop_acc) if prop_acc else None

    # 🆕 فاز ۵.۱ — تاریخ برداشت (اختیاری؛ پیش‌فرض: الان)
    withdrawal_dt = datetime.now(timezone.utc)
    if request.withdrawal_date:
        try:
            parsed = datetime.fromisoformat(request.withdrawal_date.replace("Z", "+00:00"))
            withdrawal_dt = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="فرمت تاریخ برداشت نامعتبر است (ISO 8601: YYYY-MM-DD)",
            )

    withdrawal = PropWithdrawal(
        prop_stage_id=stage_id,
        amount=request.amount,
        note=request.note,
        destination_account_id=request.destination_account_id,
        withdrawal_date=withdrawal_dt,
    )
    db.add(withdrawal)

    # ✅ فقط total_withdrawn افزایش می‌یابد
    # current_profit دست نمی‌خورد (چون از روی trades محاسبه می‌شود)
    stage.total_withdrawn = (stage.total_withdrawn or 0) + request.amount

    # 🆕 فاز ۵ — ثبت تراکنش مالی (جایگزین LedgerTransaction شخصی)
    description = f"برداشت از {prop_acc.account_label if prop_acc else 'پراپ'}"
    if request.note:
        description += f" - {request.note}"

    cat = _get_or_create_category(db, "برداشت پراپ", CategoryType.INCOME, "#27AE60", "💰")

    tx = Transaction(
        account_id=request.destination_account_id,           # مقصد (تصمیم ۹.۱ — گزینه الف)
        category_id=cat.id,
        amount=request.amount,
        currency=_to_currency(prop_acc.currency if prop_acc else None),
        date=withdrawal_dt,                                  # 🆕 فاز ۵.۱ — تاریخ برداشت
        description=description,
        type=TransactionType.WITHDRAWAL,
        from_account_id=src_acct.id if src_acct else None,   # مبدأ = حساب مالی پراپ
        to_account_id=request.destination_account_id,         # مقصد
        related_prop_account_id=stage.prop_account_id,        # لینک به پراپ
    )
    db.add(tx)

    # 🆕 فاز ۵ — به‌روزرسانی موجودی‌ها
    if src_acct:
        src_acct.balance = (src_acct.balance or 0.0) - request.amount
    dest.balance = (dest.balance or 0.0) + request.amount

    db.commit()

    return {
        "message": f"{request.amount} دلار برداشت ثبت شد و به حساب مقصد واریز شد",
        "transaction_id": tx.id,
        "source_account_id": src_acct.id if src_acct else None,
        "destination_account_id": request.destination_account_id,
    }


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
# Prop Alert (هشدارها)
# ═════════════════════════════════════════════
def _generate_alerts_for_stage(db: Session, stage_id: int, evaluation: dict = None):
    """بررسی خودکار و ایجاد هشدار برای یک مرحله پراپ"""
    from ..models.prop import PropAlert

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
                PropAlert.is_read == 0,
            ).first()
            if not existing:
                new_alerts.append(PropAlert(prop_stage_id=stage_id, message=msg))
        elif dd_percent >= 100:
            msg = f"🚨 Daily DD نقض شده! ({dd_current:.0f}$ > {dd_limit:.0f}$)"
            existing = db.query(PropAlert).filter(
                PropAlert.prop_stage_id == stage_id,
                PropAlert.message.contains("Daily DD نقض"),
                PropAlert.is_read == 0,
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
                PropAlert.is_read == 0,
            ).first()
            if not existing:
                new_alerts.append(PropAlert(prop_stage_id=stage_id, message=msg))
        elif td_percent >= 100:
            msg = f"🚨 Total DD نقض شده! ({td_current:.0f}$ > {td_limit:.0f}$)"
            existing = db.query(PropAlert).filter(
                PropAlert.prop_stage_id == stage_id,
                PropAlert.message.contains("Total DD نقض"),
                PropAlert.is_read == 0,
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
                PropAlert.is_read == 0,
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
        query = query.filter(PropAlert.is_read == 0)
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
    alert.is_read = 1
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
    is_purchase = cost.create_transaction and (cost.cost_type or "").lower() == "purchase"

    # ── اعتبارسنجی قبل از هر درج (تا در صورت خطا هیچ رکوردی باقی نماند) ──
    prop_acc = None
    payer = None
    if is_purchase:
        prop_acc = db.query(PropAccount).filter(PropAccount.id == cost.prop_account_id).first()
        if cost.pay_from_account_id:
            payer = db.query(Account).filter(Account.id == cost.pay_from_account_id).first()
            if not payer:
                raise HTTPException(status_code=400, detail="حساب پرداخت‌کننده معتبر نیست")
        elif prop_acc:
            payer = _ensure_finance_account(db, prop_acc)
        if not payer:
            raise HTTPException(
                status_code=400,
                detail="حساب پرداخت‌کننده الزامی است (pay_from_account_id) وگرنه اکانت پراپ باید حساب مالی داشته باشد",
            )

    db_cost = PropCost(
        **cost.model_dump(exclude={"pay_from_account_id", "create_transaction"})
    )
    db.add(db_cost)
    db.flush()

    # ── تراکنش خرید پراپ ──
    transaction_id = None
    if payer:
        cat = _get_or_create_category(db, "خرید پراپ", CategoryType.EXPENSE, "#E74C3C", "🛒")

        tx = Transaction(
            account_id=payer.id,
            category_id=cat.id,
            amount=cost.amount,
            currency=_to_currency(cost.currency),
            date=datetime.now(timezone.utc),
            description=cost.description or (
                f"خرید پراپ {prop_acc.account_label}" if prop_acc else "خرید پراپ"
            ),
            type=TransactionType.PURCHASE,
            from_account_id=payer.id,
            related_prop_account_id=cost.prop_account_id,
        )
        db.add(tx)
        payer.balance = (payer.balance or 0.0) - cost.amount
        db.flush()
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


@router.get("/accounts/{account_id}/finance-account")
def get_prop_finance_account(account_id: int, db: Session = Depends(get_db)):
    """دریافت حساب مالی متناظر با یک اکانت پراپ (فاز ۵)"""
    prop_acc = db.query(PropAccount).filter(PropAccount.id == account_id).first()
    if not prop_acc:
        raise HTTPException(status_code=404, detail="اکانت پراپ پیدا نشد")

    if not prop_acc.finance_account_id:
        return {"linked": False, "account": None}

    fin = db.query(Account).filter(Account.id == prop_acc.finance_account_id).first()
    if not fin:
        return {"linked": False, "account": None}

    return {
        "linked": True,
        "account": {
            "id": fin.id,
            "name": fin.name,
            "type": fin.type.value if fin.type else None,
            "currency": fin.currency.value if fin.currency else None,
            "balance": fin.balance,
            "prop_firm_name": fin.prop_firm_name,
        },
    }


@router.post("/accounts/{account_id}/finance-account")
def create_prop_finance_account(account_id: int, db: Session = Depends(get_db)):
    """ساخت (یا اتصال) حساب مالی برای یک اکانت پراپ — 🆕 فاز ۵.۱"""
    prop_acc = db.query(PropAccount).filter(PropAccount.id == account_id).first()
    if not prop_acc:
        raise HTTPException(status_code=404, detail="اکانت پراپ پیدا نشد")

    fin = _ensure_finance_account(db, prop_acc)
    db.commit()

    if not fin:
        raise HTTPException(status_code=500, detail="ساخت حساب مالی ناموفق بود")

    return {
        "linked": True,
        "account": {
            "id": fin.id,
            "name": fin.name,
            "type": fin.type.value if fin.type else None,
            "currency": fin.currency.value if fin.currency else None,
            "balance": fin.balance,
            "prop_firm_name": fin.prop_firm_name,
        },
    }

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