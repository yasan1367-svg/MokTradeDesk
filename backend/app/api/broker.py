"""
Endpointهای برداشت بروکر (فاز ۱۶ — Payout History)

بروکر در این پروژه مدل جداگانه ندارد؛ حساب بروکر همان `Account` با
`AccountType.BROKER` است و برداشت‌های آن `Transaction(type=WITHDRAWAL)` هستند.
(ثبت/ویرایش/حذف از همان `/api/finance/withdrawals` انجام می‌شود.)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from ..core.database import get_db
from ..models.finance import Account, AccountType, Transaction, TransactionType

router = APIRouter()


def _broker_payout_query(
    db: Session,
    account_id: Optional[int] = None,
    currency: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """کوئری پایهٔ برداشت‌های بروکر با فیلترهای اختیاری"""
    q = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.is_deleted == False,
            Transaction.type == TransactionType.WITHDRAWAL,
            Account.type == AccountType.BROKER,
        )
    )
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if currency:
        q = q.filter(Account.currency == currency)
    if date_from:
        q = q.filter(Transaction.date >= date_from)
    if date_to:
        q = q.filter(Transaction.date <= date_to)
    return q


@router.get("/payouts")
def list_broker_payouts(
    account_id: Optional[int] = None,
    currency: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """لیست برداشت‌های بروکر (فاز ۱۶)"""
    rows = (
        _broker_payout_query(db, account_id, currency, date_from, date_to)
        .order_by(Transaction.date.desc())
        .all()
    )
    return [
        {
            "id": t.id,
            "account_id": t.account_id,
            "account_name": t.account.name if t.account else None,
            "broker_name": t.account.broker_name if t.account else None,
            "amount": t.amount,
            "currency": t.currency.value if t.currency else None,
            "date": t.date.isoformat() if t.date else None,
            "description": t.description,
            "type": t.type.value if t.type else None,
        }
        for t in rows
    ]


@router.get("/payouts/stats")
def get_broker_payout_stats(
    account_id: Optional[int] = None,
    currency: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """آمار برداشت‌های بروکر (فاز ۱۶) — محاسبات در SQL"""
    q = _broker_payout_query(db, account_id, currency, date_from, date_to)

    agg = q.with_entities(
        func.count(Transaction.id),
        func.coalesce(func.sum(Transaction.amount), 0.0),
        func.max(Transaction.amount),
    ).one()
    count = int(agg[0] or 0)
    total = float(agg[1] or 0.0)
    largest = float(agg[2] or 0.0)

    monthly_rows = (
        q.with_entities(
            func.strftime("%Y-%m", Transaction.date).label("ym"),
            func.sum(Transaction.amount),
        )
        .group_by("ym")
        .order_by("ym")
        .all()
    )

    by_account_rows = (
        q.with_entities(Account.name, func.sum(Transaction.amount), func.count(Transaction.id))
        .group_by(Account.name)
        .all()
    )

    return {
        "total": round(total, 2),
        "count": count,
        "average": round((total / count) if count else 0.0, 2),
        "largest": round(largest, 2),
        "monthly": [{"month": m, "amount": round(float(a or 0), 2)} for m, a in monthly_rows],
        "by_account": [
            {"name": n, "amount": round(float(a or 0), 2), "count": int(c or 0)}
            for n, a, c in by_account_rows
        ],
    }
