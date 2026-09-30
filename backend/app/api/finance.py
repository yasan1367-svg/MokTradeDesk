from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from ..core.database import get_db
from ..models.finance import (
    FinancialAccount,
    Category,
    FinancialTransaction,
    AccountType,
    Currency,
    CategoryType,
    TransactionType,
)
# فاز ۳۹: تنها نویسندهٔ FinancialAccount.balance
from ..services.wallet_service import WalletService, WalletError
from ..services import metrics, finance_metrics
from ..utils import jalali
from ..utils.time_utils import to_tehran, TEHRAN
from ..utils.date_range import filter_by_range

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


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[AccountType] = None
    currency: Optional[Currency] = None
    # فاز ۴۵.۱: `balance` از این schema حذف شد — تغییر موجودی فقط از مسیر
    # WalletService (تراکنش) مجاز است تا «تنها نویسنده» نقض نشود.
    card_number: Optional[str] = None


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


class ConvertRequest(BaseModel):
    """فاز ۴۵.۵ — تبدیل ارز بین دو حساب با ارز متفاوت."""
    from_account_id: int
    to_account_id: int
    amount: float
    to_amount: Optional[float] = None
    rate: Optional[float] = None
    date: Optional[datetime] = None
    description: Optional[str] = None


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
    """لیست همه حساب‌های مالی (حساب‌های آرشیوشده پنهان می‌شوند — فاز ۴۵.۳)"""
    q = (
        db.query(FinancialAccount)
        .filter(FinancialAccount.is_archived == False)  # noqa: E712
        .order_by(FinancialAccount.created_at.desc())
    )
    if type:
        q = q.filter(FinancialAccount.type == type)
    if currency:
        q = q.filter(FinancialAccount.currency == currency)
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
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return result


@router.post("/accounts")
def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    """ایجاد حساب مالی جدید.

    فاز ۴۵.۱: موجودی اولیه دیگر مستقیم روی ستون نوشته نمی‌شود؛ از مسیر
    `WalletService` به‌صورت یک تراکنش `ADJUSTMENT` («موجودی اولیه») ثبت می‌گردد
    تا دفتر کل و موجودی هم‌یشه هم‌خوان بمانند (reconcile.delta == 0).
    """
    data = account.model_dump()
    initial_balance = data.pop("balance", 0.0) or 0.0
    db_account = FinancialAccount(balance=0.0, **data)
    db.add(db_account)
    db.flush()
    if initial_balance != 0:
        try:
            WalletService.post(
                db,
                account_id=db_account.id,
                type=TransactionType.ADJUSTMENT,
                amount=abs(initial_balance),
                signed_amount=initial_balance,
                currency=db_account.currency,
                description="موجودی اولیه",
                commit=False,
            )
        except WalletError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(exc))
    db.commit()
    db.refresh(db_account)
    return {
        "id": db_account.id,
        "message": "حساب مالی ساخته شد",
        "name": db_account.name,
    }


@router.patch("/accounts/{account_id}")
def update_account(account_id: int, data: AccountUpdate, db: Session = Depends(get_db)):
    """ویرایش حساب مالی.

    فاز ۴۵.۲: اگر حساب حتی یک تراکنش (به‌عنوان account/from/to) داشته باشد،
    تغییر ارز مجاز نیست چون همهٔ تراکنش‌های قدیمی ناسازگار می‌شوند.
    """
    account = db.query(FinancialAccount).filter(FinancialAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="حساب مالی پیدا نشد")

    payload = data.model_dump(exclude_unset=True)
    new_currency = payload.get("currency")
    if new_currency and new_currency != account.currency:
        tx_count = (
            db.query(FinancialTransaction)
            .filter(
                (FinancialTransaction.account_id == account.id)
                | (FinancialTransaction.from_account_id == account.id)
                | (FinancialTransaction.to_account_id == account.id),
                FinancialTransaction.is_deleted == False,  # noqa: E712
            )
            .count()
        )
        if tx_count > 0:
            raise HTTPException(
                status_code=409,
                detail="تغییر ارز حساب دارای تراکنش مجاز نیست",
            )

    for field, value in payload.items():
        # از ذخیرهٔ مقدار ماسک‌شده (مثل «****4455») جلوگیری کن تا شمارهٔ واقعی کارت خراب نشود
        if field == "card_number" and _is_masked(value):
            continue
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return {"message": "حساب مالی به‌روزرسانی شد"}


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    """حذف نرم (آرشیو) حساب مالی — فاز ۴۵.۳.

    فقط حسابِ **بدون تراکنش و با موجودی صفر** قابل آرشیو است؛ در غیر این صورت
    `409` برمی‌گردد تا دفتر کل هرگز ناتراز/ناقص نشود. حذف سخت و cascade حذف شدند
    تا تراکنش‌های طرف مقابلِ انتقال‌ها از بین نروند.
    """
    account = db.get(FinancialAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="حساب مالی پیدا نشد")

    tx_count = (
        db.query(FinancialTransaction)
        .filter(
            (FinancialTransaction.account_id == account.id)
            | (FinancialTransaction.from_account_id == account.id)
            | (FinancialTransaction.to_account_id == account.id),
        )
        .count()
    )
    if tx_count > 0 or abs(float(account.balance or 0.0)) > 0.0049:
        raise HTTPException(
            status_code=409,
            detail="حساب دارای تراکنش یا موجودی غیرصفر است",
        )

    account.is_archived = True
    db.commit()
    return {"ok": True, "message": "حساب مالی آرشیو شد"}


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
    limit: Optional[int] = Query(None, ge=1, le=2000, description="فاز ۳۶ — حداکثر تعداد ردیف"),
    offset: int = Query(0, ge=0, description="فاز ۳۶ — جابه‌جایی (Pagination)"),
    db: Session = Depends(get_db),
):
    """لیست تراکنش‌ها با فیلتر + Pagination اختیاری (فاز ۳۶)"""
    from sqlalchemy.orm import joinedload

    q = (
        db.query(FinancialTransaction)
        # فاز ۳۶: رفع N+1 — account/category با یک JOIN بارگذاری می‌شوند
        .options(joinedload(FinancialTransaction.account), joinedload(FinancialTransaction.category))
        .filter(FinancialTransaction.is_deleted == False)
        .order_by(FinancialTransaction.date.desc(), FinancialTransaction.id.desc())
    )
    # فاز ۴۶.۵: date_to شامل آخرین روز است (نیمه‌باز تا نیمه‌شب روز بعد)
    q = filter_by_range(q, FinancialTransaction.date, date_from, date_to)
    if account_id:
        q = q.filter(FinancialTransaction.account_id == account_id)
    if type:
        q = q.filter(FinancialTransaction.type == type)
    if category_id:
        q = q.filter(FinancialTransaction.category_id == category_id)

    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)

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
    """ایجاد تراکنش جدید (فاز ۳۹: از مسیر WalletService ⇒ موجودی هم به‌روز می‌شود).

    `allow_overdraft=True`: این endpoint یک «دفتر کل دستی» است و پیش از فاز ۳۹ هم
    موجودی را کنترل نمی‌کرد ⇒ برای حفظ سازگاری، محافظ موجودی روی آن اعمال نمی‌شود.
    """
    data = tx.model_dump()
    try:
        db_tx = WalletService.post(
            db,
            account_id=data["account_id"],
            type=data["type"],
            amount=data["amount"],
            currency=data.get("currency"),
            date=data.get("date") or datetime.now(timezone.utc),
            category_id=data.get("category_id"),
            from_account_id=data.get("from_account_id"),
            to_account_id=data.get("to_account_id"),
            description=data.get("description"),
            related_trade_id=data.get("related_trade_id"),
            related_prop_account_id=data.get("related_prop_account_id"),
            allow_overdraft=True,
        )
    except WalletError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return {"id": db_tx.id, "message": "تراکنش ثبت شد"}


@router.patch("/transactions/{transaction_id}")
def update_transaction(transaction_id: int, data: TransactionUpdate, db: Session = Depends(get_db)):
    """ویرایش تراکنش (فاز ۳۹: اثر قبلی برگردانده و اثر جدید اعمال می‌شود).

    فاز ۴۵.۴: فقط تراکنش‌های غیرحذف‌شده قابل ویرایش‌اند (وگرنه اثر یک تراکنش
    حذف‌شده دوباره برگردانده و سپس اعمال می‌شد) و برای `TRANSFER` مقدار
    `account_id` با `to_account_id` هم‌گام می‌شود.
    """
    tx = (
        db.query(FinancialTransaction)
        .filter(
            FinancialTransaction.id == transaction_id,
            FinancialTransaction.is_deleted == False,  # noqa: E712  ← فاز ۴۵.۴
        )
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="تراکنش پیدا نشد")
    try:
        # برگشت اثر مقدارهای قبلی (mutation بعدی اثر جدید را اعمال می‌کند)
        WalletService.apply_effects(db, tx, sign=-1)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(tx, field, value)
        if tx.date is None:
            tx.date = datetime.now(timezone.utc)
        # فاز ۴۵.۴: قرارداد فاز ۳۳ — برای TRANSFER، account_id همان مقصد است
        if tx.type == TransactionType.TRANSFER and tx.to_account_id is not None:
            if tx.from_account_id == tx.to_account_id:
                raise WalletError("حساب مبدأ و مقصد نباید یکی باشد")
            tx.account_id = tx.to_account_id
        # چک مبلغ جدید (وگرنه ویرایش به صفر، اثر قبلی را بی‌صدا حذف می‌کرد)
        WalletService.validate_amount(tx.type, tx.amount)
        WalletService.apply_effects(db, tx, sign=+1)
    except (WalletError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    db.commit()
    db.refresh(tx)
    return {"message": "تراکنش به‌روزرسانی شد"}


@router.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """حذف نرم تراکنش + برگشت اثر آن روی موجودی (فاز ۳۹)."""
    tx = db.query(FinancialTransaction).filter(FinancialTransaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="تراکنش پیدا نشد")
    try:
        WalletService.reverse(db, tx)
    except WalletError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "تراکنش حذف شد"}


@router.post("/wallets/convert")
def convert_currency(data: ConvertRequest, db: Session = Depends(get_db)):
    """تبدیل ارز بین دو حساب با ارز متفاوت (فاز ۴۵.۵).

    دو تراکنش `ADJUSTMENT` ثبت می‌شود: خروج از مبدأ و ورود به مقصد. چون انواع
    برداشت/واریز در گزارش‌های درآمد/هزینه شمرده می‌شوند، از `ADJUSTMENT` استفاده
    می‌کنیم تا تبدیل ارز، سود/هزینهٔ کاذب نسازد. موجودی مبدأ دستی کنترل می‌شود.
    """
    src = db.get(FinancialAccount, data.from_account_id)
    dst = db.get(FinancialAccount, data.to_account_id)
    if not src or not dst:
        raise HTTPException(status_code=404, detail="حساب مالی پیدا نشد")
    if src.id == dst.id:
        raise HTTPException(status_code=400, detail="حساب مبدأ و مقصد نباید یکی باشد")
    if src.currency == dst.currency:
        raise HTTPException(status_code=400, detail="ارز دو حساب یکسان است؛ از transfer استفاده کن")

    amount = float(data.amount or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="مبلغ تبدیل باید بزرگ‌تر از صفر باشد")

    if data.to_amount is not None:
        to_amount = float(data.to_amount)
    elif data.rate:
        to_amount = amount * float(data.rate)
    else:
        raise HTTPException(status_code=400, detail="to_amount یا rate الزامی است")
    if to_amount <= 0:
        raise HTTPException(status_code=400, detail="مبلغ مقصد باید بزرگ‌تر از صفر باشد")

    if float(src.balance or 0.0) + 0.0049 < amount:
        raise HTTPException(status_code=400, detail="موجودی حساب مبدأ کافی نیست")

    when = data.date or datetime.now(timezone.utc)
    desc = data.description or f"تبدیل ارز {src.currency.value}→{dst.currency.value}"
    try:
        out_tx = WalletService.post(
            db, account_id=src.id, type=TransactionType.ADJUSTMENT,
            amount=amount, signed_amount=-amount, currency=src.currency,
            date=when, description=desc, commit=False,
        )
        in_tx = WalletService.post(
            db, account_id=dst.id, type=TransactionType.ADJUSTMENT,
            amount=to_amount, signed_amount=to_amount, currency=dst.currency,
            date=when, description=desc, commit=False,
        )
    except WalletError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    db.commit()
    db.refresh(out_tx)
    db.refresh(in_tx)
    return {
        "ok": True,
        "out_transaction_id": out_tx.id,
        "in_transaction_id": in_tx.id,
        "amount": amount,
        "to_amount": round(to_amount, 2),
        "effective_rate": round(to_amount / amount, 6) if amount else None,
    }

@router.get("/accounts/{account_id}/reconcile")
def reconcile_account(account_id: int, db: Session = Depends(get_db)):
    """مغایرت‌یابی حساب مالی (فاز ۴۵.۹): `balance` ذخیره‌شده vs دفتر کل محاسبه‌شده.

    `delta == 0` ⇒ تراز است. `delta != 0` ⇒ بخشی از موجودی «موجودی اولیهٔ ضمنی»
    است و تراکنش متناظر ندارد (باید اصلاح شود).
    """
    try:
        return WalletService.reconcile(db, account_id)
    except WalletError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ═════════════════════════════════════════════
# Reports
# ═════════════════════════════════════════════

@router.get("/summary")
def get_finance_summary(
    currency: Optional[Currency] = None,
    db: Session = Depends(get_db),
):
    """خلاصه مالی: مجموع دارایی‌ها، درآمد، هزینه، تعداد تراکنش‌ها.

    فاز ۴۴.۵: اعداد دیگر IRR و USD را با هم جمع نمی‌کنند — مقدار پیش‌فرض USD است و
    تفکیک کامل هر ارز در `by_currency` برمی‌گردد.
    """
    target = currency or Currency.USD

    # مجموع دارایی‌ها به تفکیک ارز
    accounts = db.query(FinancialAccount).all()
    assets_by_currency: dict[str, float] = {}
    for a in accounts:
        cur = a.currency.value if a.currency else "USD"
        assets_by_currency[cur] = assets_by_currency.get(cur, 0.0) + (a.balance or 0.0)

    by_currency: dict[str, dict] = {}
    for c in (Currency.USD, Currency.IRR):
        by_currency[c.value] = {
            "total_income": round(_tx_sum(db, INCOME_TYPES_F, c), 2),
            "total_expense": round(_tx_sum(db, EXPENSE_TYPES_F, c), 2),
            "total_transfers": round(_tx_sum(db, [TransactionType.TRANSFER], c), 2),
            "transaction_count": _tx_count(db, c),
        }

    sel = by_currency[target.value]
    return {
        "assets_by_currency": assets_by_currency,
        "total_income": sel["total_income"],
        "total_expense": sel["total_expense"],
        "total_transfers": sel["total_transfers"],
        "transaction_count": sel["transaction_count"],
        # فاز ۴۴.۵
        "currency": target.value,
        "by_currency": by_currency,
    }


@router.get("/accounts/{account_id}/stats")
def get_account_stats(account_id: int, db: Session = Depends(get_db)):
    """آمار یک حساب مالی: موجودی، درآمد، هزینه، آخرین تراکنش"""
    from sqlalchemy import func
    account = db.query(FinancialAccount).filter(FinancialAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="حساب پیدا نشد")

    income_types = [TransactionType.DEPOSIT, TransactionType.PROFIT]
    expense_types = [TransactionType.WITHDRAWAL, TransactionType.LOSS, TransactionType.FEE, TransactionType.PURCHASE]

    base_q = db.query(FinancialTransaction).filter(
        FinancialTransaction.is_deleted == False,
        FinancialTransaction.account_id == account_id,
    )

    total_income = (
        base_q.filter(FinancialTransaction.type.in_(income_types))
        .with_entities(func.sum(FinancialTransaction.amount))
        .scalar() or 0.0
    )

    total_expense = (
        base_q.filter(FinancialTransaction.type.in_(expense_types))
        .with_entities(func.sum(FinancialTransaction.amount))
        .scalar() or 0.0
    )

    tx_count = base_q.count()

    last_tx = base_q.order_by(FinancialTransaction.date.desc()).first()

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


@router.post("/sync/trades")
def sync_trades(db: Session = Depends(get_db)):
    """همگام‌سازی دستی معاملات بسته‌شده با حسابداری (فاز ۲۱)"""
    from ..services.finance_sync_service import FinanceSyncService
    created = FinanceSyncService(db).sync_closed_trades()
    return {"message": f"{created} تراکنش ساخته شد", "created": created}


@router.get("/withdrawals/stats")
def get_withdrawal_stats(
    currency: Optional[Currency] = None,
    db: Session = Depends(get_db),
):
    """آمار برداشت‌ها: از پراپ، از بروکر، تعداد، تاریخچه — فاز ۴۴.۵: یک ارز"""
    from sqlalchemy import func as sa_func

    target = currency or Currency.USD
    _cur = FinancialTransaction.currency == target

    # برداشت‌های مرتبط با پراپ (فاز ۲۸: بر اساس related_prop_account_id، نه نوع حساب)
    prop_withdrawals = (
        db.query(sa_func.sum(FinancialTransaction.amount))
        .filter(
            FinancialTransaction.is_deleted == False,
            FinancialTransaction.type == TransactionType.WITHDRAWAL,
            FinancialTransaction.related_prop_account_id.isnot(None),
            _cur,
        )
        .scalar() or 0.0
    )

    # برداشت‌های غیرپراپ (بروکر شخصی و ...)
    broker_withdrawals = (
        db.query(sa_func.sum(FinancialTransaction.amount))
        .filter(
            FinancialTransaction.is_deleted == False,
            FinancialTransaction.type == TransactionType.WITHDRAWAL,
            FinancialTransaction.related_prop_account_id.is_(None),
            _cur,
        )
        .scalar() or 0.0
    )

    total_withdrawals = (
        db.query(sa_func.sum(FinancialTransaction.amount))
        .filter(
            FinancialTransaction.is_deleted == False,
            FinancialTransaction.type == TransactionType.WITHDRAWAL,
            _cur,
        )
        .scalar() or 0.0
    )

    withdrawal_count = (
        db.query(FinancialTransaction)
        .filter(
            FinancialTransaction.is_deleted == False,
            FinancialTransaction.type == TransactionType.WITHDRAWAL,
            _cur,
        )
        .count()
    )

    history = (
        db.query(FinancialTransaction)
        .filter(
            FinancialTransaction.is_deleted == False,
            FinancialTransaction.type == TransactionType.WITHDRAWAL,
            _cur,
        )
        .order_by(FinancialTransaction.date.desc())
        .limit(20)
        .all()
    )

    return {
        "total_withdrawals": total_withdrawals,
        "prop_withdrawals": prop_withdrawals,
        "broker_withdrawals": broker_withdrawals,
        "withdrawal_count": withdrawal_count,
        "currency": target.value,
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
# برداشت‌ها در همان مدل FinancialTransaction با type=withdrawal ذخیره می‌شوند.
# ═════════════════════════════════════════════
def _serialize_withdrawal(w: FinancialTransaction) -> dict:
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
    return db.query(FinancialTransaction).filter(
        FinancialTransaction.is_deleted == False,
        FinancialTransaction.type == TransactionType.WITHDRAWAL,
    )


@router.get("/withdrawals")
def list_withdrawals(
    account_id: Optional[int] = None,
    date_from: Optional[str] = Query(None, description="e.g. 2025-01-01"),
    date_to: Optional[str] = Query(None, description="e.g. 2025-12-31"),
    db: Session = Depends(get_db),
):
    """لیست برداشت‌ها با فیلتر حساب و بازهٔ تاریخ (فاز ۱۵.۱۲)"""
    q = _withdrawal_query(db).order_by(FinancialTransaction.date.desc())
    if account_id:
        q = q.filter(FinancialTransaction.account_id == account_id)
    # فاز ۴۶.۵: date_to شامل آخرین روز است (نیمه‌باز تا نیمه‌شب روز بعد)
    q = filter_by_range(q, FinancialTransaction.date, date_from, date_to)
    return [_serialize_withdrawal(w) for w in q.all()]


@router.post("/withdrawals")
def create_withdrawal(data: WithdrawalCreate, db: Session = Depends(get_db)):
    """ایجاد برداشت جدید (FinancialTransaction با type=withdrawal) — فاز ۱۵.۱۲

    فاز ۳۹ (رفع G1): از مسیر `WalletService` ⇒ موجودی کیف‌پول هم به‌روز می‌شود.
    `allow_overdraft=True` مثل `POST /finance/transactions` (مسیر دستی/انعطاف‌پذیر).
    """
    account = db.query(FinancialAccount).filter(FinancialAccount.id == data.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="حساب مالی پیدا نشد")

    try:
        w = WalletService.post(
            db,
            account_id=data.account_id,
            type=TransactionType.WITHDRAWAL,
            amount=data.amount,
            currency=data.currency,
            date=data.date or datetime.now(timezone.utc),
            category_id=data.category_id,
            description=data.description,
            allow_overdraft=True,
        )
    except WalletError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return {"id": w.id, "message": "برداشت ثبت شد"}


# هم PUT و هم PATCH پذیرفته می‌شود (PUT طبق درخواست، PATCH طبق قرارداد بقیهٔ پروژه)
@router.put("/withdrawals/{withdrawal_id}")
@router.patch("/withdrawals/{withdrawal_id}")
def update_withdrawal(withdrawal_id: int, data: WithdrawalUpdate, db: Session = Depends(get_db)):
    """ویرایش برداشت (فاز ۱۵.۱۲) — فاز ۳۹: اثر قبلی برگردانده و اثر جدید اعمال می‌شود."""
    w = _withdrawal_query(db).filter(FinancialTransaction.id == withdrawal_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="برداشت پیدا نشد")

    payload = data.model_dump(exclude_unset=True)
    if "account_id" in payload:
        account = db.query(FinancialAccount).filter(FinancialAccount.id == payload["account_id"]).first()
        if not account:
            raise HTTPException(status_code=404, detail="حساب مالی پیدا نشد")

    try:
        WalletService.apply_effects(db, w, sign=-1)          # برگشت اثر مقدارهای قبلی
        for field, value in payload.items():
            setattr(w, field, value)
        if w.date is None:
            w.date = datetime.now(timezone.utc)
        WalletService.validate_amount(w.type, w.amount)      # مبلغ صفر/منفی مجاز نیست
        WalletService.apply_effects(db, w, sign=+1)          # اعمال اثر مقدارهای جدید
    except (WalletError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    db.commit()
    db.refresh(w)
    return {"message": "برداشت به‌روزرسانی شد", "withdrawal": _serialize_withdrawal(w)}


@router.delete("/withdrawals/{withdrawal_id}")
def delete_withdrawal(withdrawal_id: int, db: Session = Depends(get_db)):
    """حذف نرم برداشت + برگشت اثر آن روی موجودی (فاز ۱۵.۱۲ / فاز ۳۹)."""
    w = _withdrawal_query(db).filter(FinancialTransaction.id == withdrawal_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="برداشت پیدا نشد")
    try:
        WalletService.reverse(db, w)
    except WalletError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "برداشت حذف شد"}


@router.get("/charts/cashflow")
def get_cashflow_chart(
    year: Optional[int] = Query(None, description="سال (میلادی)"),
    currency: Optional[Currency] = None,
    db: Session = Depends(get_db),
):
    """نمودار جریان نقدی: درآمد vs هزینه به صورت ماهانه.

    فاز ۴۴.۵: فقط یک ارز (پیش‌فرض USD) — IRR و USD با هم جمع نمی‌شوند.
    """
    from sqlalchemy import func as sa_func, extract

    target = currency or Currency.USD
    base_filter = [
        FinancialTransaction.is_deleted == False,
        FinancialTransaction.currency == target,
    ]
    if year:
        base_filter.append(extract("year", FinancialTransaction.date) == year)

    # درآمد ماهانه
    income_rows = (
        db.query(
            extract("year", FinancialTransaction.date).label("year"),
            extract("month", FinancialTransaction.date).label("month"),
            sa_func.sum(FinancialTransaction.amount).label("amount"),
        )
        .filter(*base_filter, FinancialTransaction.type.in_(INCOME_TYPES_F))
        .group_by(extract("year", FinancialTransaction.date), extract("month", FinancialTransaction.date))
        .order_by(extract("year", FinancialTransaction.date), extract("month", FinancialTransaction.date))
        .all()
    )

    # هزینه ماهانه
    expense_rows = (
        db.query(
            extract("year", FinancialTransaction.date).label("year"),
            extract("month", FinancialTransaction.date).label("month"),
            sa_func.sum(FinancialTransaction.amount).label("amount"),
        )
        .filter(*base_filter, FinancialTransaction.type.in_(EXPENSE_TYPES_F))
        .group_by(extract("year", FinancialTransaction.date), extract("month", FinancialTransaction.date))
        .order_by(extract("year", FinancialTransaction.date), extract("month", FinancialTransaction.date))
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
        FinancialTransaction.type.label("type"),
        sa_func.count(FinancialTransaction.id).label("count"),
        sa_func.sum(FinancialTransaction.amount).label("total_amount"),
    ).filter(FinancialTransaction.is_deleted == False)

    # فاز ۴۶.۵: date_to شامل آخرین روز است (نیمه‌باز تا نیمه‌شب روز بعد)
    q = filter_by_range(q, FinancialTransaction.date, date_from, date_to)

    rows = q.group_by(FinancialTransaction.type).order_by(FinancialTransaction.type).all()

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

# فاز ۴۶.۳: تنها مرجع تبدیل، `utils/jalali.py` است (نام برای سازگاری حفظ شده).
JALALI_MONTHS = jalali.JALALI_MONTHS


def _jalali_to_gregorian(jy: int, jm: int, jd: int):
    """تبدیل تاریخ شمسی به میلادی (بازگشت: (year, month, day)) — فاز ۴۶.۳: ابزار مشترک."""
    return jalali.jalali_to_gregorian_parts(jy, jm, jd)


def _gregorian_to_jalali(gy: int, gm: int, gd: int):
    """تبدیل تاریخ میلادی به شمسی (بازگشت: (year, month, day)) — فاز ۴۶.۳: ابزار مشترک."""
    return jalali.gregorian_to_jalali_parts(gy, gm, gd)


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
    start = datetime(gy1, gm1, gd1, tzinfo=TEHRAN).astimezone(timezone.utc)
    end = datetime(gy2, gm2, gd2, tzinfo=TEHRAN).astimezone(timezone.utc)
    return start, end


def _current_jalali_year() -> int:
    now = datetime.now(timezone.utc)
    return _gregorian_to_jalali(now.year, now.month, now.day)[0]


@router.get("/reports/monthly")
def get_monthly_report(
    year: Optional[int] = Query(None, description="سال شمسی (مثلاً 1404)"),
    account_id: Optional[int] = None,
    currency: Optional[Currency] = None,
    db: Session = Depends(get_db),
):
    """گزارش ماهانه: درآمد vs هزینه، گروه‌بندی بر اساس ماه شمسی — فاز ۴۴.۵: یک ارز"""
    target = currency or Currency.USD
    target_year = year or _current_jalali_year()
    start, end = _jalali_range(target_year)

    q = db.query(FinancialTransaction).filter(
        FinancialTransaction.is_deleted == False,
        FinancialTransaction.currency == target,
        FinancialTransaction.date >= start,
        FinancialTransaction.date < end,
    )
    if account_id:
        q = q.filter(FinancialTransaction.account_id == account_id)
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
    currency: Optional[Currency] = None,
    db: Session = Depends(get_db),
):
    """تفکیک دسته‌بندی: مجموع درآمد/هزینه هر دسته + درصد از کل (نمودار دایره‌ای) — فاز ۴۴.۵: یک ارز"""
    target = currency or Currency.USD
    q = db.query(FinancialTransaction).filter(
        FinancialTransaction.is_deleted == False,
        FinancialTransaction.currency == target,
    )
    if year:
        start, end = _jalali_range(year, month)
        q = q.filter(FinancialTransaction.date >= start, FinancialTransaction.date < end)
    if account_id:
        q = q.filter(FinancialTransaction.account_id == account_id)
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
    accounts_q = db.query(FinancialAccount)
    if currency:
        accounts_q = accounts_q.filter(FinancialAccount.currency == currency)
    accounts = accounts_q.all()

    txs_q = db.query(FinancialTransaction).filter(FinancialTransaction.is_deleted == False)
    if year:
        start, end = _jalali_range(year, month)
        txs_q = txs_q.filter(FinancialTransaction.date >= start, FinancialTransaction.date < end)
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
    currency: Optional[Currency] = None,
    db: Session = Depends(get_db),
):
    """سود و زیان: سود خالص (درآمد - هزینه) به تفکیک ماه/سال + روند — فاز ۴۴.۵: یک ارز"""
    target = currency or Currency.USD
    q = db.query(FinancialTransaction).filter(
        FinancialTransaction.is_deleted == False,
        FinancialTransaction.currency == target,
    )
    if account_id:
        q = q.filter(FinancialTransaction.account_id == account_id)
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
# فاز ۲۲ — گزارش‌های مالی (توابع کمکی)
# ═════════════════════════════════════════════
def _trade_net_expr():
    """net_pnl معامله — فاز ۴۳: از تعریف واحد `metrics.net_pnl_sql()`"""
    return metrics.net_pnl_sql()


# ═════════════════════════════════════════════
# فاز ۴۴.۵ — جداکردن ارزها (IRR ≠ USD)
# ═════════════════════════════════════════════
def _tx_sum(db: Session, types, currency: Currency) -> float:
    """مجموع مبلغ تراکنش‌های غیرحذف‌شده از انواع داده‌شده، فقط در یک ارز."""
    from sqlalchemy import func
    return float(
        db.query(func.coalesce(func.sum(FinancialTransaction.amount), 0.0))
        .filter(
            FinancialTransaction.is_deleted == False,
            FinancialTransaction.type.in_(types),
            FinancialTransaction.currency == currency,
        )
        .scalar() or 0.0
    )


def _tx_count(db: Session, currency: Currency) -> int:
    """تعداد تراکنش‌های غیرحذف‌شده در یک ارز."""
    return int(
        db.query(FinancialTransaction)
        .filter(
            FinancialTransaction.is_deleted == False,
            FinancialTransaction.currency == currency,
        )
        .count()
    )


INCOME_TYPES_F = [TransactionType.DEPOSIT, TransactionType.PROFIT]
EXPENSE_TYPES_F = [
    TransactionType.WITHDRAWAL, TransactionType.LOSS,
    TransactionType.FEE, TransactionType.PURCHASE,
]


def _jalali_date_str(dt) -> Optional[str]:
    """تاریخ شمسی به قالب YYYY/MM/DD — فاز ۴۶.۴: بر پایهٔ وقت تهران"""
    if not dt:
        return None
    dt = to_tehran(dt)
    try:
        jy, jm, jd = _gregorian_to_jalali(dt.year, dt.month, dt.day)
    except Exception:
        return None
    return f"{jy}/{jm:02d}/{jd:02d}"


def _balance_sum(db: Session, acc_type: AccountType) -> float:
    """مجموع موجودی همهٔ حساب‌های یک نوع"""
    from sqlalchemy import func
    return float(
        db.query(func.coalesce(func.sum(FinancialAccount.balance), 0.0))
        .filter(FinancialAccount.type == acc_type)
        .scalar() or 0.0
    )


def _balance_sum_currency(db: Session, currency: Currency) -> float:
    """مجموع موجودی همهٔ کیف‌پول‌های یک ارز — فاز ۳۹ (رفع G6).

    پیش از فاز ۳۹، `total.irr` هاردکد روی سبد `bank` بود ⇒ IRR موجود در
    صرافی/نقد/کارت از جمع IRR **حذف** می‌شد.
    """
    from sqlalchemy import func
    return float(
        db.query(func.coalesce(func.sum(FinancialAccount.balance), 0.0))
        .filter(FinancialAccount.currency == currency)
        .scalar() or 0.0
    )


def _compute_real_pnl(db: Session) -> dict:
    """سود/زیان Real: مرحلهٔ ۳ پراپ + بروکر (از معاملات، net_pnl)"""
    from sqlalchemy import func
    from ..models.strategy import Trade
    from ..models.prop import PropStage as PS, StageType

    net = _trade_net_expr()

    prop_row = (
        db.query(func.coalesce(func.sum(net), 0.0), func.count(Trade.id))
        .select_from(Trade)
        .join(PS, Trade.prop_stage_id == PS.id)
        .filter(
            PS.stage_type == StageType.FUNDED_REAL,
            Trade.pnl.isnot(None),
            Trade.is_deleted == False,  # فاز ۲۵
        )
        .one()
    )
    prop_pnl = round(float(prop_row[0] or 0.0), 2)
    prop_trades = int(prop_row[1] or 0)

    from ..models.trading import PersonalTradingAccount
    broker_row = (
        db.query(func.coalesce(func.sum(net), 0.0), func.count(Trade.id))
        .select_from(Trade)
        .join(PersonalTradingAccount, Trade.personal_trading_account_id == PersonalTradingAccount.id)
        .filter(
            Trade.pnl.isnot(None),
            Trade.is_deleted == False,  # فاز ۲۵
        )
        .one()
    )
    broker_pnl = round(float(broker_row[0] or 0.0), 2)
    broker_trades = int(broker_row[1] or 0)

    return {
        "prop_stage_3": {"pnl": prop_pnl, "trades": prop_trades},
        "broker": {"pnl": broker_pnl, "trades": broker_trades},
        "total": {"pnl": round(prop_pnl + broker_pnl, 2), "trades": prop_trades + broker_trades},
    }


def _expenses_total(db: Session, currency: Optional[Currency] = None) -> float:
    """مجموع هزینه‌ها = SUM(amount WHERE type in FEE/PURCHASE) — فاز ۴۴.۵: یک ارز (پیش‌فرض USD)"""
    from sqlalchemy import func
    target = currency or Currency.USD
    return float(
        db.query(func.coalesce(func.sum(FinancialTransaction.amount), 0.0))
        .filter(
            FinancialTransaction.is_deleted == False,
            FinancialTransaction.type.in_([TransactionType.FEE, TransactionType.PURCHASE]),
            FinancialTransaction.currency == target,
        )
        .scalar() or 0.0
    )


# ═════════════════════════════════════════════
# فاز ۲۲.۱ — گزارش «دارایی قابل برداشت» / «سود/زیان Real» / «سود خالص»
# ═════════════════════════════════════════════
@router.get("/spendable-assets")
def get_spendable_assets(db: Session = Depends(get_db)):
    """دارایی قابل برداشت: پراپ مرحلهٔ ۳، بروکر، صرافی، Trust Wallet، کیف‌پول دیجیتال،
    کارت، نقد، بانک + مجموع به تفکیک ارز.

    فاز ۳۹ (رفع G6):
    - سبد `trust_wallet` از `AccountType.TRUST_WALLET` پر می‌شود. پیش‌تر اشتباهاً
      `CRYPTO_WALLET` بود (فاز ۳۸ نوع `TRUST_WALLET` را اضافه کرد ولی این endpoint
      آپدیت نشد) ⇒ هیچ موجودی تراست‌ولت واقعی دیده نمی‌شد.
    - سبدهای `crypto_wallet` / `card` / `cash` افزوده شدند (پیش‌تر کاملاً غایب بودند).
    - `total.irr` = Σ موجودی **همهٔ** کیف‌پول‌های IRR (پیش‌تر هاردکد = سبد `bank`).

    کلیدهای قدیمی (`prop_stage_3`, `broker`, `exchange`, `trust_wallet`, `bank`,
    `total.usd`, `total.irr`) دست‌نخورده حفظ شده‌اند ⇒ سازگاری فرانت‌اند.
    """
    prop_stage_3 = finance_metrics.prop_stage_3(db)
    # فاز ۲۸: موجودی بروکر از حساب‌های معاملاتی شخصی (نه FinancialAccount مالی)
    from ..models.trading import PersonalTradingAccount as _PTA
    from sqlalchemy import func as _f
    broker = round(float(
        db.query(_f.coalesce(_f.sum(_PTA.current_balance), 0.0)).scalar() or 0.0
    ), 2)
    exchange = round(_balance_sum(db, AccountType.EXCHANGE), 2)
    trust_wallet = round(_balance_sum(db, AccountType.TRUST_WALLET), 2)      # فاز ۳۹: رفع G6
    crypto_wallet = round(_balance_sum(db, AccountType.CRYPTO_WALLET), 2)    # فاز ۳۹: جدید
    card = round(_balance_sum(db, AccountType.CARD), 2)                      # فاز ۳۹: جدید
    cash = round(_balance_sum(db, AccountType.CASH), 2)                      # فاز ۳۹: جدید
    bank = round(_balance_sum(db, AccountType.BANK), 2)

    total_usd = round(prop_stage_3 + broker + exchange + trust_wallet + crypto_wallet, 2)
    total_irr = round(_balance_sum_currency(db, Currency.IRR), 2)            # فاز ۳۹: رفع G6

    return {
        # ── کلیدهای موجود (بدون تغییر) ──
        "prop_stage_3": {"amount": prop_stage_3, "currency": "USD"},
        "broker": {"amount": broker, "currency": "USD"},
        "exchange": {"amount": exchange, "currency": "USD"},
        "trust_wallet": {"amount": trust_wallet, "currency": "USD"},
        "bank": {"amount": bank, "currency": "IRR"},
        "total": {"usd": total_usd, "irr": total_irr},
        # ── کلیدهای جدید فاز ۳۹ ──
        "crypto_wallet": {"amount": crypto_wallet, "currency": "USD"},
        "card": {"amount": card, "currency": "IRR"},
        "cash": {"amount": cash, "currency": "IRR"},
    }


@router.get("/real-pnl")
def get_real_pnl(db: Session = Depends(get_db)):
    """سود/زیان Real: مرحلهٔ ۳ پراپ + بروکر (pnl + تعداد معاملات)"""
    return _compute_real_pnl(db)


@router.get("/net-profit")
def get_net_profit(
    currency: Optional[Currency] = None,
    db: Session = Depends(get_db),
):
    """سود خالص = سود Real − هزینه‌ها (FEE/PURCHASE) — فاز ۴۴.۵: یک ارز (پیش‌فرض USD)"""
    target = currency or Currency.USD
    real = _compute_real_pnl(db)
    expenses = round(_expenses_total(db, target), 2)
    real_pnl = real["total"]["pnl"]
    return {
        "real_pnl": real_pnl,
        "expenses": expenses,
        "net_profit": round(real_pnl - expenses, 2),
        "currency": target.value,
        "by_currency": {
            c.value: {
                "expenses": round(_expenses_total(db, c), 2),
            }
            for c in (Currency.USD, Currency.IRR)
        },
    }


# ═════════════════════════════════════════════
# فاز ۲۲.۲ — «جریان پول» / «هزینه‌ها» / «چرخه پول»
# ═════════════════════════════════════════════
@router.get("/money-flow")
def get_money_flow(db: Session = Depends(get_db)):
    """جریان پول: تراکنش‌های واریز/برداشت/تبدیل و هر تراکنش دارای مبدأ/مقصد"""
    from sqlalchemy.orm import joinedload
    flow_types = [
        TransactionType.DEPOSIT,
        TransactionType.WITHDRAWAL,
        TransactionType.TRANSFER,  # فاز ۳۸.۴: جایگزین EXCHANGE حذف‌شده
    ]
    txs = (
        db.query(FinancialTransaction)
        .options(
            joinedload(FinancialTransaction.account),
            joinedload(FinancialTransaction.from_account),
            joinedload(FinancialTransaction.to_account),
        )
        .filter(FinancialTransaction.is_deleted == False)
        .order_by(FinancialTransaction.date.desc())
        .all()
    )

    flows = []
    for t in txs:
        has_link = t.from_account_id is not None or t.to_account_id is not None
        if t.type not in flow_types and not has_link:
            continue
        own = t.account.type.value if t.account and t.account.type else None
        from_side = t.from_account.type.value if t.from_account and t.from_account.type else None
        to_side = t.to_account.type.value if t.to_account and t.to_account.type else None
        flows.append({
            "from": from_side or own,
            "to": to_side or own,
            "amount": t.amount,
            "currency": t.currency.value if t.currency else None,
            "type": t.type.value if t.type else None,
            "date": t.date.isoformat() if t.date else None,
        })
    return {"flows": flows}


@router.get("/expenses")
def get_expenses(
    currency: Optional[Currency] = None,
    db: Session = Depends(get_db),
):
    """گزارش هزینه‌ها — فاز ۴۴.۵: یک ارز (پیش‌فرض USD) + تفکیک by_currency"""
    from sqlalchemy.orm import joinedload
    target = currency or Currency.USD
    txs = (
        db.query(FinancialTransaction)
        .options(joinedload(FinancialTransaction.category), joinedload(FinancialTransaction.account))
        .filter(
            FinancialTransaction.is_deleted == False,
            FinancialTransaction.type.in_([TransactionType.FEE, TransactionType.PURCHASE]),
            FinancialTransaction.currency == target,
        )
        .all()
    )

    buckets = {
        "prop_purchase": 0.0,
        "prop_subscription": 0.0,
        "exchange_fee": 0.0,
        "withdrawal_fee": 0.0,
        "other": 0.0,
    }

    for t in txs:
        amount = float(t.amount or 0.0)
        cat_name = (t.category.name if t.category else "") or ""
        text = f"{cat_name} {t.description or ''}"
        acc_type = t.account.type if t.account else None

        if t.type == TransactionType.PURCHASE and "پراپ" in text:
            buckets["prop_purchase"] += amount
        elif "اشتراک" in text:
            buckets["prop_subscription"] += amount
        elif acc_type == AccountType.EXCHANGE or "تبدیل" in text or "صرافی" in text:
            buckets["exchange_fee"] += amount
        elif "برداشت" in text:
            buckets["withdrawal_fee"] += amount
        else:
            buckets["other"] += amount

    total = round(sum(buckets.values()), 2)
    result = {k: round(v, 2) for k, v in buckets.items()}
    result["total"] = total
    # فاز ۴۴.۵
    result["currency"] = target.value
    result["by_currency"] = {
        c.value: round(_tx_sum(db, [TransactionType.FEE, TransactionType.PURCHASE], c), 2)
        for c in (Currency.USD, Currency.IRR)
    }
    return result


@router.get("/money-cycle")
def get_money_cycle(
    currency: Optional[Currency] = None,
    db: Session = Depends(get_db),
):
    """چرخهٔ پول: مجموع واریز/برداشت/تبدیل/انتقال + موجودی فعلی — فاز ۴۴.۵: یک ارز."""
    from sqlalchemy import func

    target = currency or Currency.USD

    def _transfers(curr) -> float:
        return float(
            db.query(func.coalesce(func.sum(FinancialTransaction.amount), 0.0))
            .filter(
                FinancialTransaction.is_deleted == False,
                FinancialTransaction.currency == curr,
                FinancialTransaction.from_account_id.isnot(None),
                FinancialTransaction.to_account_id.isnot(None),
            )
            .scalar() or 0.0
        )

    def _balance(curr) -> float:
        return float(
            db.query(func.coalesce(func.sum(FinancialAccount.balance), 0.0))
            .filter(FinancialAccount.currency == curr)
            .scalar() or 0.0
        )

    by_currency: dict[str, dict] = {}
    for c in (Currency.USD, Currency.IRR):
        by_currency[c.value] = {
            "total_deposits": round(_tx_sum(db, [TransactionType.DEPOSIT], c), 2),
            "total_withdrawals": round(_tx_sum(db, [TransactionType.WITHDRAWAL], c), 2),
            # فاز ۳۸.۴: کلید JSON (`total_exchanges`) برای سازگاری فرانت حفظ شد؛
            # مقدارش از `TRANSFER` (جانشین EXCHANGE حذف‌شده) محاسبه می‌شود.
            "total_exchanges": round(_tx_sum(db, [TransactionType.TRANSFER], c), 2),
            "total_transfers": round(_transfers(c), 2),
            "current_balance": round(_balance(c), 2),
        }

    sel = dict(by_currency[target.value])
    sel["currency"] = target.value
    sel["by_currency"] = by_currency
    return sel


# ═════════════════════════════════════════════
# فاز ۲۲.۳ — «تقویم مالی» / «روند دارایی» / «نرخ تبدیل»
# ═════════════════════════════════════════════
@router.get("/financial-calendar")
def get_financial_calendar(db: Session = Depends(get_db)):
    """تقویم مالی: به تفکیک روز شمسی — سود/زیان معاملات + واریز/برداشت"""
    from collections import defaultdict
    from ..models.strategy import Trade

    days: dict = defaultdict(
        lambda: {"pnl": 0.0, "trades": 0, "deposits": 0.0, "withdrawals": 0.0}
    )

    for t in db.query(Trade).filter(
        Trade.close_time.isnot(None),
        Trade.is_deleted == False,  # فاز ۲۵
    ).all():
        d = _jalali_date_str(t.close_time)
        if not d:
            continue
        days[d]["pnl"] += metrics.net_pnl(t)
        days[d]["trades"] += 1

    txs = (
        db.query(FinancialTransaction)
        .filter(
            FinancialTransaction.is_deleted == False,
            FinancialTransaction.type.in_([TransactionType.DEPOSIT, TransactionType.WITHDRAWAL]),
        )
        .all()
    )
    for tx in txs:
        d = _jalali_date_str(tx.date)
        if not d:
            continue
        if tx.type == TransactionType.DEPOSIT:
            days[d]["deposits"] += float(tx.amount or 0.0)
        else:
            days[d]["withdrawals"] += float(tx.amount or 0.0)

    result = [
        {
            "date": d,
            "pnl": round(v["pnl"], 2),
            "trades": v["trades"],
            "deposits": round(v["deposits"], 2),
            "withdrawals": round(v["withdrawals"], 2),
        }
        for d, v in sorted(days.items())
    ]
    return {"days": result}


@router.get("/asset-trend")
def get_asset_trend(
    date_from: Optional[str] = Query(None, description="e.g. 2025-01-01"),
    date_to: Optional[str] = Query(None, description="e.g. 2025-12-31"),
    db: Session = Depends(get_db),
):
    """روند دارایی: مجموع تجمعی USD و IRR به تفکیک روز شمسی (از جریان تراکنش‌ها)"""
    from collections import defaultdict

    sign = {
        TransactionType.DEPOSIT: 1,
        TransactionType.PROFIT: 1,
        TransactionType.WITHDRAWAL: -1,
        TransactionType.LOSS: -1,
        TransactionType.FEE: -1,
        TransactionType.PURCHASE: -1,
    }

    q = db.query(FinancialTransaction).filter(FinancialTransaction.is_deleted == False)
    # فاز ۴۶.۵: date_to شامل آخرین روز است (نیمه‌باز تا نیمه‌شب روز بعد)
    q = filter_by_range(q, FinancialTransaction.date, date_from, date_to)

    per_day: dict = defaultdict(lambda: {"USD": 0.0, "IRR": 0.0})
    for t in q.order_by(FinancialTransaction.date).all():
        d = _jalali_date_str(t.date)
        if not d:
            continue
        factor = sign.get(t.type, 0)
        if factor == 0:
            continue  # تبدیل، سنتی است و خالص آن صفر فرض می‌شود
        cur = t.currency.value if t.currency else "USD"
        per_day[d][cur] = per_day[d].get(cur, 0.0) + factor * float(t.amount or 0.0)

    trend = []
    run_usd = 0.0
    run_irr = 0.0
    for d in sorted(per_day):
        run_usd += per_day[d].get("USD", 0.0)
        run_irr += per_day[d].get("IRR", 0.0)
        trend.append({
            "date": d,
            "total_usd": round(run_usd, 2),
            "total_irr": round(run_irr, 2),
        })
    return {"trend": trend}


@router.get("/exchange-rates")
def get_exchange_rates(db: Session = Depends(get_db)):
    """نرخ تبدیل: نرخ ضمنی روزانهٔ IRR→USD از تراکنش‌های تبدیل

    چون هر تراکنش تبدیل فقط یک مبلغ/ارز ذخیره می‌کند، نرخ از نسبت مجموع
    مبلغ‌های IRR به مجموع مبلغ‌های USD در همان روز شمسی استخراج می‌شود.
    """
    from collections import defaultdict

    txs = (
        db.query(FinancialTransaction)
        .filter(FinancialTransaction.is_deleted == False, FinancialTransaction.type == TransactionType.TRANSFER)  # فاز ۳۸.۴: EXCHANGE → TRANSFER
        .all()
    )
    per_day: dict = defaultdict(lambda: {"IRR": 0.0, "USD": 0.0})
    for t in txs:
        d = _jalali_date_str(t.date)
        if not d:
            continue
        cur = t.currency.value if t.currency else "USD"
        per_day[d][cur] = per_day[d].get(cur, 0.0) + float(t.amount or 0.0)

    rates = []
    for d in sorted(per_day):
        irr = per_day[d].get("IRR", 0.0)
        usd = per_day[d].get("USD", 0.0)
        if irr > 0 and usd > 0:
            rates.append({
                "date": d,
                "from": "IRR",
                "to": "USD",
                "rate": round(irr / usd, 2),
            })
    return {"rates": rates}


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
    {"name": "تبدیل ارز", "type": CategoryType.CONVERSION, "color": "#8b5cf6", "icon": "💱"},  # فاز ۳۸.۴: EXCHANGE → CONVERSION
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