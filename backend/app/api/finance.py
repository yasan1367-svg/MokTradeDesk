from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from ..core.database import get_db
from ..models.finance import (
    Account,
    Category,
    Transaction,
    AccountType,
    Currency,
    CategoryType,
    TransactionType,
)

router = APIRouter()


# ═════════════════════════════════════════════
# Helpers — امنیت دادهٔ حساس
# ═════════════════════════════════════════════
def _mask_card_number(value: Optional[str]) -> Optional[str]:
    """ماسک‌کردن شمارهٔ کارت برای جلوگیری از افشای دادهٔ حساس در پاسخ API

    مثال: «6037 9911 2233 4455» → «****4455»
    """
    if not value:
        return value
    text = str(value).strip()
    if len(text) <= 4:
        return "****"
    return "****" + text[-4:]


def _is_masked(value) -> bool:
    """آیا مقدار، همان مقدار ماسک‌شدهٔ برگشتی از API است؟ (برای جلوگیری از ذخیرهٔ اشتباهی)"""
    return isinstance(value, str) and "*" in value


# ═════════════════════════════════════════════
# Schemas
# ═════════════════════════════════════════════
class AccountCreate(BaseModel):
    name: str
    type: AccountType
    currency: Currency = Currency.USD
    balance: float = 0.0
    card_number: Optional[str] = None
    broker_name: Optional[str] = None
    prop_firm_name: Optional[str] = None
    prop_firm_id: Optional[int] = None


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[AccountType] = None
    currency: Optional[Currency] = None
    balance: Optional[float] = None
    card_number: Optional[str] = None
    broker_name: Optional[str] = None
    prop_firm_name: Optional[str] = None
    prop_firm_id: Optional[int] = None


class CategoryCreate(BaseModel):
    name: str
    type: CategoryType
    color: Optional[str] = None
    icon: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[CategoryType] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class TransactionCreate(BaseModel):
    account_id: int
    category_id: Optional[int] = None
    amount: float
    currency: Currency = Currency.USD
    date: Optional[datetime] = None
    description: Optional[str] = None
    type: TransactionType
    from_account_id: Optional[int] = None
    to_account_id: Optional[int] = None
    related_trade_id: Optional[int] = None
    related_prop_account_id: Optional[int] = None


class TransactionUpdate(BaseModel):
    category_id: Optional[int] = None
    amount: Optional[float] = None
    currency: Optional[Currency] = None
    date: Optional[datetime] = None
    description: Optional[str] = None
    type: Optional[TransactionType] = None
    from_account_id: Optional[int] = None
    to_account_id: Optional[int] = None
    related_trade_id: Optional[int] = None
    related_prop_account_id: Optional[int] = None


# ── فاز ۱۵.۱۲: Schemas برداشت (Withdrawal) ──
class WithdrawalCreate(BaseModel):
    account_id: int
    amount: float
    currency: Currency = Currency.USD
    date: Optional[datetime] = None
    description: Optional[str] = None
    category_id: Optional[int] = None


class WithdrawalUpdate(BaseModel):
    account_id: Optional[int] = None
    amount: Optional[float] = None
    currency: Optional[Currency] = None
    date: Optional[datetime] = None
    description: Optional[str] = None
    category_id: Optional[int] = None


# ═════════════════════════════════════════════
# Accounts
# ═════════════════════════════════════════════
@router.get("/accounts")
def get_accounts(
    type: Optional[AccountType] = None,
    currency: Optional[Currency] = None,
    db: Session = Depends(get_db),
):
    """لیست همه حساب‌های مالی"""
    q = db.query(Account).order_by(Account.created_at.desc())
    if type:
        q = q.filter(Account.type == type)
    if currency:
        q = q.filter(Account.currency == currency)
    accounts = q.all()
    result = []
    for a in accounts:
        result.append({
            "id": a.id,
            "name": a.name,
            "type": a.type.value if a.type else None,
            "currency": a.currency.value if a.currency else None,
            "balance": a.balance,
            "card_number": _mask_card_number(a.card_number),
            "broker_name": a.broker_name,
            "prop_firm_name": a.prop_firm_name,
            "prop_firm_id": a.prop_firm_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return result


@router.post("/accounts")
def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    """ایجاد حساب مالی جدید"""
    db_account = Account(**account.model_dump())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return {
        "id": db_account.id,
        "message": "حساب مالی ساخته شد",
        "name": db_account.name,
    }


@router.patch("/accounts/{account_id}")
def update_account(account_id: int, data: AccountUpdate, db: Session = Depends(get_db)):
    """ویرایش حساب مالی"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="حساب مالی پیدا نشد")
    for field, value in data.model_dump(exclude_unset=True).items():
        # از ذخیرهٔ مقدار ماسک‌شده (مثل «****4455») جلوگیری کن تا شمارهٔ واقعی کارت خراب نشود
        if field == "card_number" and _is_masked(value):
            continue
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return {"message": "حساب مالی به‌روزرسانی شد"}


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    """حذف حساب مالی"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="حساب مالی پیدا نشد")
    db.delete(account)
    db.commit()
    return {"message": "حساب مالی حذف شد"}


# ═════════════════════════════════════════════
# Categories
# ═════════════════════════════════════════════
@router.get("/categories")
def get_categories(
    type: Optional[CategoryType] = None,
    db: Session = Depends(get_db),
):
    """لیست همه دسته‌بندی‌ها"""
    q = db.query(Category).order_by(Category.created_at.desc())
    if type:
        q = q.filter(Category.type == type)
    categories = q.all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "type": c.type.value if c.type else None,
            "color": c.color,
            "icon": c.icon,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in categories
    ]


@router.post("/categories")
def create_category(cat: CategoryCreate, db: Session = Depends(get_db)):
    """ایجاد دسته‌بندی جدید"""
    db_cat = Category(**cat.model_dump())
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return {"id": db_cat.id, "message": "دسته‌بندی ساخته شد"}


@router.patch("/categories/{category_id}")
def update_category(category_id: int, data: CategoryUpdate, db: Session = Depends(get_db)):
    """ویرایش دسته‌بندی"""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="دسته‌بندی پیدا نشد")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cat, field, value)
    db.commit()
    db.refresh(cat)
    return {"message": "دسته‌بندی به‌روزرسانی شد"}


@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """حذف دسته‌بندی"""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="دسته‌بندی پیدا نشد")
    db.delete(cat)
    db.commit()
    return {"message": "دسته‌بندی حذف شد"}


# ═════════════════════════════════════════════
# Transactions
# ═════════════════════════════════════════════
@router.get("/transactions")
def get_transactions(
    date_from: Optional[str] = Query(None, description="e.g. 2025-01-01"),
    date_to: Optional[str] = Query(None, description="e.g. 2025-12-31"),
    account_id: Optional[int] = None,
    type: Optional[TransactionType] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """لیست تراکنش‌ها با فیلتر"""
    q = db.query(Transaction).filter(Transaction.is_deleted == False).order_by(Transaction.date.desc())
    if date_from:
        q = q.filter(Transaction.date >= date_from)
    if date_to:
        q = q.filter(Transaction.date <= date_to)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if type:
        q = q.filter(Transaction.type == type)
    if category_id:
        q = q.filter(Transaction.category_id == category_id)

    transactions = q.all()
    result = []
    for t in transactions:
        result.append({
            "id": t.id,
            "account_id": t.account_id,
            "account_name": t.account.name if t.account else None,
            "category_id": t.category_id,
            "category_name": t.category.name if t.category else None,
            "amount": t.amount,
            "currency": t.currency.value if t.currency else None,
            "date": t.date.isoformat() if t.date else None,
            "description": t.description,
            "type": t.type.value if t.type else None,
            "from_account_id": t.from_account_id,
            "to_account_id": t.to_account_id,
            "related_trade_id": t.related_trade_id,
            "related_prop_account_id": t.related_prop_account_id,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return result


@router.post("/transactions")
def create_transaction(tx: TransactionCreate, db: Session = Depends(get_db)):
    """ایجاد تراکنش جدید"""
    data = tx.model_dump()
    if data.get("date") is None:
        data["date"] = datetime.now(timezone.utc)
    db_tx = Transaction(**data)
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return {"id": db_tx.id, "message": "تراکنش ثبت شد"}


@router.patch("/transactions/{transaction_id}")
def update_transaction(transaction_id: int, data: TransactionUpdate, db: Session = Depends(get_db)):
    """ویرایش تراکنش"""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="تراکنش پیدا نشد")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tx, field, value)
    db.commit()
    db.refresh(tx)
    return {"message": "تراکنش به‌روزرسانی شد"}


@router.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """حذف نرم تراکنش (soft delete)"""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="تراکنش پیدا نشد")
    tx.is_deleted = True
    db.commit()
    return {"message": "تراکنش حذف شد"}

# ═════════════════════════════════════════════
# Reports
# ═════════════════════════════════════════════

@router.get("/summary")
def get_finance_summary(db: Session = Depends(get_db)):
    """خلاصه مالی: مجموع دارایی‌ها، درآمد، هزینه، تعداد تراکنش‌ها"""
    from sqlalchemy import func

    # مجموع دارایی‌ها به تفکیک ارز
    accounts = db.query(Account).all()
    assets_by_currency: dict[str, float] = {}
    for a in accounts:
        cur = a.currency.value if a.currency else "USD"
        assets_by_currency[cur] = assets_by_currency.get(cur, 0.0) + (a.balance or 0.0)

    # انواع تراکنش‌ها (غیرحذف شده)
    income_types = [TransactionType.DEPOSIT, TransactionType.PROFIT]
    expense_types = [TransactionType.WITHDRAWAL, TransactionType.LOSS, TransactionType.FEE, TransactionType.PURCHASE]

    total_income = (
        db.query(func.sum(Transaction.amount))
        .filter(Transaction.is_deleted == False, Transaction.type.in_(income_types))
        .scalar() or 0.0
    )

    total_expense = (
        db.query(func.sum(Transaction.amount))
        .filter(Transaction.is_deleted == False, Transaction.type.in_(expense_types))
        .scalar() or 0.0
    )

    total_transfers = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.is_deleted == False,
            Transaction.type == TransactionType.EXCHANGE,
        )
        .scalar() or 0.0
    )

    tx_count = db.query(Transaction).filter(Transaction.is_deleted == False).count()

    return {
        "assets_by_currency": assets_by_currency,
        "total_income": total_income,
        "total_expense": total_expense,
        "total_transfers": total_transfers,
        "transaction_count": tx_count,
    }


@router.get("/accounts/{account_id}/stats")
def get_account_stats(account_id: int, db: Session = Depends(get_db)):
    """آمار یک حساب مالی: موجودی، درآمد، هزینه، آخرین تراکنش"""
    from sqlalchemy import func
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="حساب پیدا نشد")

    income_types = [TransactionType.DEPOSIT, TransactionType.PROFIT]
    expense_types = [TransactionType.WITHDRAWAL, TransactionType.LOSS, TransactionType.FEE, TransactionType.PURCHASE]

    base_q = db.query(Transaction).filter(
        Transaction.is_deleted == False,
        Transaction.account_id == account_id,
    )

    total_income = (
        base_q.filter(Transaction.type.in_(income_types))
        .with_entities(func.sum(Transaction.amount))
        .scalar() or 0.0
    )

    total_expense = (
        base_q.filter(Transaction.type.in_(expense_types))
        .with_entities(func.sum(Transaction.amount))
        .scalar() or 0.0
    )

    tx_count = base_q.count()

    last_tx = base_q.order_by(Transaction.date.desc()).first()

    return {
        "id": account.id,
        "name": account.name,
        "type": account.type.value if account.type else None,
        "currency": account.currency.value if account.currency else None,
        "balance": account.balance,
        "total_income": total_income,
        "total_expense": total_expense,
        "transaction_count": tx_count,
        "last_transaction": {
            "id": last_tx.id,
            "amount": last_tx.amount,
            "type": last_tx.type.value if last_tx.type else None,
            "date": last_tx.date.isoformat() if last_tx.date else None,
            "description": last_tx.description,
        } if last_tx else None,
    }


@router.get("/withdrawals/stats")
def get_withdrawal_stats(db: Session = Depends(get_db)):
    """آمار برداشت‌ها: از پراپ، از بروکر، تعداد، تاریخچه"""
    from sqlalchemy import func as sa_func

    # برداشت از حساب‌های پراپ
    prop_withdrawals = (
        db.query(sa_func.sum(Transaction.amount))
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.is_deleted == False,
            Transaction.type == TransactionType.WITHDRAWAL,
            Account.type == AccountType.PROP,
        )
        .scalar() or 0.0
    )

    # برداشت از حساب‌های بروکر
    broker_withdrawals = (
        db.query(sa_func.sum(Transaction.amount))
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.is_deleted == False,
            Transaction.type == TransactionType.WITHDRAWAL,
            Account.type == AccountType.BROKER,
        )
        .scalar() or 0.0
    )

    total_withdrawals = (
        db.query(sa_func.sum(Transaction.amount))
        .filter(
            Transaction.is_deleted == False,
            Transaction.type == TransactionType.WITHDRAWAL,
        )
        .scalar() or 0.0
    )

    withdrawal_count = (
        db.query(Transaction)
        .filter(
            Transaction.is_deleted == False,
            Transaction.type == TransactionType.WITHDRAWAL,
        )
        .count()
    )

    history = (
        db.query(Transaction)
        .filter(
            Transaction.is_deleted == False,
            Transaction.type == TransactionType.WITHDRAWAL,
        )
        .order_by(Transaction.date.desc())
        .limit(20)
        .all()
    )

    return {
        "total_withdrawals": total_withdrawals,
        "prop_withdrawals": prop_withdrawals,
        "broker_withdrawals": broker_withdrawals,
        "withdrawal_count": withdrawal_count,
        "history": [
            {
                "id": w.id,
                "amount": w.amount,
                "currency": w.currency.value if w.currency else None,
                "date": w.date.isoformat() if w.date else None,
                "description": w.description,
                "account_id": w.account_id,
                "account_name": w.account.name if w.account else None,
            }
            for w in history
        ],
    }


# ═════════════════════════════════════════════
# Withdrawals — CRUD (فاز ۱۵.۱۲)
# برداشت‌ها در همان مدل Transaction با type=withdrawal ذخیره می‌شوند.
# ═════════════════════════════════════════════
def _serialize_withdrawal(w: Transaction) -> dict:
    return {
        "id": w.id,
        "account_id": w.account_id,
        "account_name": w.account.name if w.account else None,
        "category_id": w.category_id,
        "category_name": w.category.name if w.category else None,
        "amount": w.amount,
        "currency": w.currency.value if w.currency else None,
        "date": w.date.isoformat() if w.date else None,
        "description": w.description,
        "type": w.type.value if w.type else None,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }


def _withdrawal_query(db: Session):
    """کوئری پایهٔ برداشت‌ها (فقط type=withdrawal و حذف‌نشده)"""
    return db.query(Transaction).filter(
        Transaction.is_deleted == False,
        Transaction.type == TransactionType.WITHDRAWAL,
    )


@router.get("/withdrawals")
def list_withdrawals(
    account_id: Optional[int] = None,
    date_from: Optional[str] = Query(None, description="e.g. 2025-01-01"),
    date_to: Optional[str] = Query(None, description="e.g. 2025-12-31"),
    db: Session = Depends(get_db),
):
    """لیست برداشت‌ها با فیلتر حساب و بازهٔ تاریخ (فاز ۱۵.۱۲)"""
    q = _withdrawal_query(db).order_by(Transaction.date.desc())
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if date_from:
        q = q.filter(Transaction.date >= date_from)
    if date_to:
        q = q.filter(Transaction.date <= date_to)
    return [_serialize_withdrawal(w) for w in q.all()]


@router.post("/withdrawals")
def create_withdrawal(data: WithdrawalCreate, db: Session = Depends(get_db)):
    """ایجاد برداشت جدید (Transaction با type=withdrawal) — فاز ۱۵.۱۲"""
    account = db.query(Account).filter(Account.id == data.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="حساب مالی پیدا نشد")

    w = Transaction(
        account_id=data.account_id,
        category_id=data.category_id,
        amount=data.amount,
        currency=data.currency,
        date=data.date or datetime.now(timezone.utc),
        description=data.description,
        type=TransactionType.WITHDRAWAL,
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return {"id": w.id, "message": "برداشت ثبت شد"}


# هم PUT و هم PATCH پذیرفته می‌شود (PUT طبق درخواست، PATCH طبق قرارداد بقیهٔ پروژه)
@router.put("/withdrawals/{withdrawal_id}")
@router.patch("/withdrawals/{withdrawal_id}")
def update_withdrawal(withdrawal_id: int, data: WithdrawalUpdate, db: Session = Depends(get_db)):
    """ویرایش برداشت (فاز ۱۵.۱۲)"""
    w = _withdrawal_query(db).filter(Transaction.id == withdrawal_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="برداشت پیدا نشد")

    payload = data.model_dump(exclude_unset=True)
    if "account_id" in payload:
        account = db.query(Account).filter(Account.id == payload["account_id"]).first()
        if not account:
            raise HTTPException(status_code=404, detail="حساب مالی پیدا نشد")

    for field, value in payload.items():
        setattr(w, field, value)
    db.commit()
    db.refresh(w)
    return {"message": "برداشت به‌روزرسانی شد", "withdrawal": _serialize_withdrawal(w)}


@router.delete("/withdrawals/{withdrawal_id}")
def delete_withdrawal(withdrawal_id: int, db: Session = Depends(get_db)):
    """حذف نرم برداشت (فاز ۱۵.۱۲)"""
    w = _withdrawal_query(db).filter(Transaction.id == withdrawal_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="برداشت پیدا نشد")
    w.is_deleted = True
    db.commit()
    return {"message": "برداشت حذف شد"}


@router.get("/charts/cashflow")
def get_cashflow_chart(
    year: Optional[int] = Query(None, description="سال (میلادی)"),
    db: Session = Depends(get_db),
):
    """نمودار جریان نقدی: درآمد vs هزینه به صورت ماهانه"""
    from sqlalchemy import func as sa_func, extract

    income_types = [TransactionType.DEPOSIT, TransactionType.PROFIT]
    expense_types = [TransactionType.WITHDRAWAL, TransactionType.LOSS, TransactionType.FEE, TransactionType.PURCHASE]

    base_filter = [Transaction.is_deleted == False]
    if year:
        base_filter.append(extract("year", Transaction.date) == year)

    # درآمد ماهانه
    income_rows = (
        db.query(
            extract("year", Transaction.date).label("year"),
            extract("month", Transaction.date).label("month"),
            sa_func.sum(Transaction.amount).label("amount"),
        )
        .filter(*base_filter, Transaction.type.in_(income_types))
        .group_by(extract("year", Transaction.date), extract("month", Transaction.date))
        .order_by(extract("year", Transaction.date), extract("month", Transaction.date))
        .all()
    )

    # هزینه ماهانه
    expense_rows = (
        db.query(
            extract("year", Transaction.date).label("year"),
            extract("month", Transaction.date).label("month"),
            sa_func.sum(Transaction.amount).label("amount"),
        )
        .filter(*base_filter, Transaction.type.in_(expense_types))
        .group_by(extract("year", Transaction.date), extract("month", Transaction.date))
        .order_by(extract("year", Transaction.date), extract("month", Transaction.date))
        .all()
    )

    income_map: dict[str, float] = {}
    for r in income_rows:
        key = f"{int(r.year)}-{int(r.month):02d}"
        income_map[key] = float(r.amount)

    expense_map: dict[str, float] = {}
    for r in expense_rows:
        key = f"{int(r.year)}-{int(r.month):02d}"
        expense_map[key] = float(r.amount)

    all_keys = sorted(set(list(income_map.keys()) + list(expense_map.keys())))

    result = []
    for key in all_keys:
        parts = key.split("-")
        result.append({
            "month": key,
            "year": int(parts[0]),
            "month_num": int(parts[1]),
            "income": income_map.get(key, 0.0),
            "expense": expense_map.get(key, 0.0),
        })

    return result


@router.get("/charts/distribution")
def get_distribution_chart(
    date_from: Optional[str] = Query(None, description="e.g. 2025-01-01"),
    date_to: Optional[str] = Query(None, description="e.g. 2025-12-31"),
    db: Session = Depends(get_db),
):
    """توزیع تراکنش‌ها بر اساس نوع (برای نمودار دایره‌ای)"""
    from sqlalchemy import func as sa_func

    q = db.query(
        Transaction.type.label("type"),
        sa_func.count(Transaction.id).label("count"),
        sa_func.sum(Transaction.amount).label("total_amount"),
    ).filter(Transaction.is_deleted == False)

    if date_from:
        q = q.filter(Transaction.date >= date_from)
    if date_to:
        q = q.filter(Transaction.date <= date_to)

    rows = q.group_by(Transaction.type).order_by(Transaction.type).all()

    return [
        {
            "type": r.type.value if hasattr(r.type, "value") else r.type,
            "count": int(r.count or 0),
            "total_amount": float(r.total_amount or 0.0),
        }
        for r in rows
    ]


# ═════════════════════════════════════════════
# Advanced Reports (فاز ۱۱)
# ═════════════════════════════════════════════
INCOME_TYPES = [TransactionType.DEPOSIT, TransactionType.PROFIT]
EXPENSE_TYPES = [
    TransactionType.WITHDRAWAL,
    TransactionType.LOSS,
    TransactionType.FEE,
    TransactionType.PURCHASE,
]

JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


def _jalali_to_gregorian(jy: int, jm: int, jd: int):
    """تبدیل تاریخ شمسی به میلادی (بازگشت: (year, month, day))"""
    jy += 1595
    days = -355668 + (365 * jy) + (jy // 33) * 8 + ((jy % 33 + 3) // 4) + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += (jm - 7) * 30 + 186

    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    sal_a = [0, 31, 29 if (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0 else 28,
             31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    for gm in range(13):
        if gd <= sal_a[gm]:
            break
        gd -= sal_a[gm]
    return gy, gm, gd


def _gregorian_to_jalali(gy: int, gm: int, gd: int):
    """تبدیل تاریخ میلادی به شمسی (بازگشت: (year, month, day))"""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    jy = 0 if gy <= 1600 else 979
    gy -= 621 if gy <= 1600 else 1600
    gy2 = gy + 1 if gm > 2 else gy
    days = ((365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100)
            + ((gy2 + 399) // 400) - 80 + gd + g_d_m[gm - 1])
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def _jalali_range(year: int, month: Optional[int] = None):
    """بازه میلادی (UTC) متناظر با سال/ماه شمسی"""
    if month:
        gy1, gm1, gd1 = _jalali_to_gregorian(year, month, 1)
        if month < 12:
            gy2, gm2, gd2 = _jalali_to_gregorian(year, month + 1, 1)
        else:
            gy2, gm2, gd2 = _jalali_to_gregorian(year + 1, 1, 1)
    else:
        gy1, gm1, gd1 = _jalali_to_gregorian(year, 1, 1)
        gy2, gm2, gd2 = _jalali_to_gregorian(year + 1, 1, 1)
    start = datetime(gy1, gm1, gd1, tzinfo=timezone.utc)
    end = datetime(gy2, gm2, gd2, tzinfo=timezone.utc)
    return start, end


def _current_jalali_year() -> int:
    now = datetime.now(timezone.utc)
    return _gregorian_to_jalali(now.year, now.month, now.day)[0]


@router.get("/reports/monthly")
def get_monthly_report(
    year: Optional[int] = Query(None, description="سال شمسی (مثلاً 1404)"),
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """گزارش ماهانه: درآمد vs هزینه، گروه‌بندی بر اساس ماه شمسی"""
    target_year = year or _current_jalali_year()
    start, end = _jalali_range(target_year)

    q = db.query(Transaction).filter(
        Transaction.is_deleted == False,
        Transaction.date >= start,
        Transaction.date < end,
    )
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    txs = q.all()

    buckets: dict[int, dict] = {
        m: {
            "month_num": m,
            "month_name": JALALI_MONTHS[m - 1],
            "income": 0.0,
            "expense": 0.0,
            "net": 0.0,
        }
        for m in range(1, 13)
    }

    for t in txs:
        if not t.date:
            continue
        jy, jm, _ = _gregorian_to_jalali(t.date.year, t.date.month, t.date.day)
        if jy != target_year or jm < 1 or jm > 12:
            continue
        if t.type in INCOME_TYPES:
            buckets[jm]["income"] += float(t.amount or 0.0)
        elif t.type in EXPENSE_TYPES:
            buckets[jm]["expense"] += float(t.amount or 0.0)

    months = []
    for m in range(1, 13):
        b = buckets[m]
        b["income"] = round(b["income"], 2)
        b["expense"] = round(b["expense"], 2)
        b["net"] = round(b["income"] - b["expense"], 2)
        months.append(b)

    return {"year": target_year, "months": months}


@router.get("/reports/category-breakdown")
def get_category_breakdown(
    year: Optional[int] = Query(None, description="سال شمسی"),
    month: Optional[int] = Query(None, ge=1, le=12, description="ماه شمسی"),
    type: Optional[str] = Query(None, description="income یا expense"),
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """تفکیک دسته‌بندی: مجموع درآمد/هزینه هر دسته + درصد از کل (نمودار دایره‌ای)"""
    q = db.query(Transaction).filter(Transaction.is_deleted == False)
    if year:
        start, end = _jalali_range(year, month)
        q = q.filter(Transaction.date >= start, Transaction.date < end)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    txs = q.all()

    agg: dict = {}
    total_income = 0.0
    total_expense = 0.0

    for t in txs:
        if t.type in INCOME_TYPES:
            kind = "income"
        elif t.type in EXPENSE_TYPES:
            kind = "expense"
        else:
            continue
        if type and type != kind:
            continue

        amount = float(t.amount or 0.0)
        if kind == "income":
            total_income += amount
        else:
            total_expense += amount

        key = (t.category_id, kind)
        if key not in agg:
            cat = t.category
            agg[key] = {
                "category_id": t.category_id,
                "category_name": cat.name if cat else "بدون دسته‌بندی",
                "color": cat.color if cat else None,
                "icon": cat.icon if cat else None,
                "type": kind,
                "total": 0.0,
                "count": 0,
            }
        agg[key]["total"] += amount
        agg[key]["count"] += 1

    items = []
    for item in agg.values():
        base = total_income if item["type"] == "income" else total_expense
        item["total"] = round(item["total"], 2)
        item["percent"] = round((item["total"] / base * 100) if base else 0.0, 2)
        items.append(item)
    items.sort(key=lambda x: x["total"], reverse=True)

    return {
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "items": items,
    }


@router.get("/reports/account-comparison")
def get_account_comparison(
    year: Optional[int] = Query(None, description="سال شمسی"),
    month: Optional[int] = Query(None, ge=1, le=12, description="ماه شمسی"),
    currency: Optional[Currency] = None,
    db: Session = Depends(get_db),
):
    """مقایسه حساب‌ها: موجودی، درآمد، هزینه و سود خالص هر حساب"""
    accounts_q = db.query(Account)
    if currency:
        accounts_q = accounts_q.filter(Account.currency == currency)
    accounts = accounts_q.all()

    txs_q = db.query(Transaction).filter(Transaction.is_deleted == False)
    if year:
        start, end = _jalali_range(year, month)
        txs_q = txs_q.filter(Transaction.date >= start, Transaction.date < end)
    txs = txs_q.all()

    income_map: dict = {}
    expense_map: dict = {}
    count_map: dict = {}
    for t in txs:
        if t.type in INCOME_TYPES:
            income_map[t.account_id] = income_map.get(t.account_id, 0.0) + float(t.amount or 0.0)
        elif t.type in EXPENSE_TYPES:
            expense_map[t.account_id] = expense_map.get(t.account_id, 0.0) + float(t.amount or 0.0)
        count_map[t.account_id] = count_map.get(t.account_id, 0) + 1

    result = []
    for a in accounts:
        inc = round(income_map.get(a.id, 0.0), 2)
        exp = round(expense_map.get(a.id, 0.0), 2)
        result.append({
            "id": a.id,
            "name": a.name,
            "type": a.type.value if a.type else None,
            "currency": a.currency.value if a.currency else None,
            "balance": a.balance,
            "total_income": inc,
            "total_expense": exp,
            "net": round(inc - exp, 2),
            "transaction_count": count_map.get(a.id, 0),
        })
    result.sort(key=lambda x: x["balance"] or 0.0, reverse=True)
    return result


@router.get("/reports/profit-loss")
def get_profit_loss(
    year: Optional[int] = Query(None, description="سال شمسی"),
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """سود و زیان: سود خالص (درآمد - هزینه) به تفکیک ماه/سال + روند"""
    q = db.query(Transaction).filter(Transaction.is_deleted == False)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    txs = q.all()

    yearly: dict = {}
    monthly_all: dict = {}
    total_income = 0.0
    total_expense = 0.0

    for t in txs:
        if t.type in INCOME_TYPES:
            amount = float(t.amount or 0.0)
        elif t.type in EXPENSE_TYPES:
            amount = -float(t.amount or 0.0)
        else:
            continue
        if not t.date:
            continue

        jy, jm, _ = _gregorian_to_jalali(t.date.year, t.date.month, t.date.day)
        if amount >= 0:
            total_income += amount
        else:
            total_expense += -amount

        if jy not in yearly:
            yearly[jy] = {"year": jy, "income": 0.0, "expense": 0.0}
        if amount >= 0:
            yearly[jy]["income"] += amount
        else:
            yearly[jy]["expense"] += -amount

        monthly_all[(jy, jm)] = monthly_all.get((jy, jm), 0.0) + amount

    yearly_list = []
    for y in sorted(yearly.keys()):
        v = yearly[y]
        v["income"] = round(v["income"], 2)
        v["expense"] = round(v["expense"], 2)
        v["net"] = round(v["income"] - v["expense"], 2)
        yearly_list.append(v)

    target_year = year or (max(yearly.keys()) if yearly else _current_jalali_year())

    monthly = []
    cumulative = 0.0
    for m in range(1, 13):
        net = round(monthly_all.get((target_year, m), 0.0), 2)
        cumulative = round(cumulative + net, 2)
        monthly.append({
            "month_num": m,
            "month_name": JALALI_MONTHS[m - 1],
            "net": net,
            "cumulative": cumulative,
        })

    trend = []
    running = 0.0
    for key in sorted(monthly_all.keys()):
        jy, jm = key
        running = round(running + monthly_all[key], 2)
        trend.append({
            "label": f"{jy}-{jm:02d}",
            "year": jy,
            "month_num": jm,
            "net": round(monthly_all[key], 2),
            "cumulative": running,
        })

    total_income = round(total_income, 2)
    total_expense = round(total_expense, 2)
    net_profit = round(total_income - total_expense, 2)
    margin = round((net_profit / total_income * 100) if total_income else 0.0, 2)

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_profit": net_profit,
        "margin": margin,
        "year": target_year,
        "yearly": yearly_list,
        "monthly": monthly,
        "trend": trend,
    }


# ═════════════════════════════════════════════
# Seed
# ═════════════════════════════════════════════
DEFAULT_CATEGORIES = [
    # درآمد
    {"name": "حقوق", "type": CategoryType.INCOME, "color": "#22c55e", "icon": "💼"},
    {"name": "سود معاملات", "type": CategoryType.INCOME, "color": "#10b981", "icon": "📈"},
    {"name": "پاداش/پورتفولیو", "type": CategoryType.INCOME, "color": "#34d399", "icon": "🎁"},
    # هزینه
    {"name": "خوراک و رستوران", "type": CategoryType.EXPENSE, "color": "#f97316", "icon": "🍔"},
    {"name": "حمل و نقل", "type": CategoryType.EXPENSE, "color": "#f59e0b", "icon": "🚗"},
    {"name": "قبوض و اشتراک", "type": CategoryType.EXPENSE, "color": "#eab308", "icon": "📄"},
    {"name": "خرید/کالا", "type": CategoryType.EXPENSE, "color": "#ef4444", "icon": "🛒"},
    {"name": "تفریح و سرگرمی", "type": CategoryType.EXPENSE, "color": "#ec4899", "icon": "🎮"},
    {"name": "سلامت و درمان", "type": CategoryType.EXPENSE, "color": "#f43f5e", "icon": "🏥"},
    # انتقال
    {"name": "انتقال بین حساب‌ها", "type": CategoryType.TRANSFER, "color": "#6366f1", "icon": "🔄"},
    # تبدیل
    {"name": "تبدیل ارز", "type": CategoryType.EXCHANGE, "color": "#8b5cf6", "icon": "💱"},
    # پراپ (فاز ۵)
    {"name": "خرید پراپ", "type": CategoryType.EXPENSE, "color": "#E74C3C", "icon": "🛒"},
    {"name": "برداشت پراپ", "type": CategoryType.INCOME, "color": "#27AE60", "icon": "💰"},
]


@router.post("/seed")
def seed_categories(db: Session = Depends(get_db)):
    """ایجاد ۱۳ دسته‌بندی پیش‌فرض (در صورت عدم وجود)"""
    created = 0
    skipped = 0
    for cat_data in DEFAULT_CATEGORIES:
        existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if existing:
            skipped += 1
            continue
        db.add(Category(**cat_data))
        created += 1
    db.commit()
    return {
        "message": "دسته‌بندی‌های پیش‌فرض ایجاد شدند",
        "created": created,
        "skipped": skipped,
        "total": len(DEFAULT_CATEGORIES),
    }