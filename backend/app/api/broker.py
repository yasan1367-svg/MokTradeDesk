"""
Endpointهای برداشت بروکر (فاز ۱۶ — Payout History)

فاز ۲۸: بروکر دیگر `FinancialAccount.type=BROKER` نیست (به `PersonalTradingAccount` منتقل شد).
برداشت‌های «غیرپراپ» به‌عنوان Payout بروکر در نظر گرفته می‌شوند
(یعنی `FinancialTransaction(type=WITHDRAWAL)` که `related_prop_account_id` ندارند).
UI صفحهٔ مستقل `Broker` در فاز بعدی اضافه می‌شود.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from ..core.database import get_db
from ..models.finance import FinancialAccount, FinancialTransaction, TransactionType

router = APIRouter()


def _broker_payout_query(
    db: Session,
    account_id: Optional[int] = None,
    currency: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """کوئری پایهٔ برداشت‌های بروکر (غیرپراپ) با فیلترهای اختیاری"""
    q = (
        db.query(FinancialTransaction)
        .join(FinancialAccount, FinancialTransaction.account_id == FinancialAccount.id)
        .filter(
            FinancialTransaction.is_deleted == False,
            FinancialTransaction.type == TransactionType.WITHDRAWAL,
            FinancialTransaction.related_prop_account_id.is_(None),
        )
    )
    if account_id:
        q = q.filter(FinancialTransaction.account_id == account_id)
    if currency:
        q = q.filter(FinancialAccount.currency == currency)
    if date_from:
        q = q.filter(FinancialTransaction.date >= date_from)
    if date_to:
        q = q.filter(FinancialTransaction.date <= date_to)
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
        .order_by(FinancialTransaction.date.desc())
        .all()
    )
    return [
        {
            "id": t.id,
            "account_id": t.account_id,
            "account_name": t.account.name if t.account else None,
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
        func.count(FinancialTransaction.id),
        func.coalesce(func.sum(FinancialTransaction.amount), 0.0),
        func.max(FinancialTransaction.amount),
    ).one()
    count = int(agg[0] or 0)
    total = float(agg[1] or 0.0)
    largest = float(agg[2] or 0.0)

    monthly_rows = (
        q.with_entities(
            func.strftime("%Y-%m", FinancialTransaction.date).label("ym"),
            func.sum(FinancialTransaction.amount),
        )
        .group_by("ym")
        .order_by("ym")
        .all()
    )

    by_account_rows = (
        q.with_entities(FinancialAccount.name, func.sum(FinancialTransaction.amount), func.count(FinancialTransaction.id))
        .group_by(FinancialAccount.name)
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
