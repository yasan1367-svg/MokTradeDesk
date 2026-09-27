from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case, and_
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from ..core.database import get_db
from ..services.analysis_service import AnalysisService
from ..models.strategy import Trade, AnalysisResult, AnalysisRun, CustomTimeInterval, AnalysisScope
from ..utils.trade_scope import analysis_trades_filter
from ..schemas.analytics import (
    CustomTimeIntervalCreate,
    CustomTimeIntervalResponse,
    VersionComparisonRequest,
    VersionComparisonResponse,
)

router = APIRouter()


# ═════════════════════════════════════════════
# Helpers — فاز ۱۵.۳ (SQL Aggregation)
# ═════════════════════════════════════════════
def _net_expr():
    """عبارت SQL سود/زیان خالص: pnl + commission + swap (با COALESCE)"""
    return (
        func.coalesce(Trade.pnl, 0.0)
        + func.coalesce(Trade.commission, 0.0)
        + func.coalesce(Trade.swap, 0.0)
    )


def _parse_bound(value: Optional[str], end: bool = False):
    """تبدیل رشتهٔ ISO به datetime آگاه از timezone (UTC)"""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        if end and dt.hour == 0 and dt.minute == 0 and dt.second == 0:
            dt = dt.replace(hour=23, minute=59, second=59)
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _scope_filter(query, df_bound, dt_bound):
    """اعمال فیلتر بازه در سطح SQL به‌جای فیلتر در Python (فاز ۱۵.۳)"""
    # فاز ۲۵: معاملات حذف‌شده (Soft Delete) همیشه کنار گذاشته می‌شوند
    query = query.filter(Trade.is_deleted == False)
    if df_bound or dt_bound:
        query = query.filter(Trade.close_time.isnot(None))
    if df_bound:
        query = query.filter(Trade.close_time >= df_bound)
    if dt_bound:
        query = query.filter(Trade.close_time <= dt_bound)
    return query


# ═════════════════════════════════════════════
# تحلیل
# ═════════════════════════════════════════════
@router.post("/analyze/{version_id}")
def analyze_version(version_id: int, db: Session = Depends(get_db)):
    """تحلیل کامل یک نسخه و ذخیره‌ی نتیجه (با تاریخچه)"""
    try:
        service = AnalysisService(db)
        result = service.analyze_version(version_id)
        return {
            "message": result["message"],
            "analysis_id": result["result"].id,
            "run_id": result["run_id"],
            "version_id": result["result"].version_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در تحلیل: {str(e)}")


# ═════════════════════════════════════════════
# فاز ۲۰.۳ — تحلیل ۶گانه (POST)
# ═════════════════════════════════════════════
@router.post("/analyze/version/{version_id}")
def analyze_version_scoped(version_id: int, test_type: Optional[str] = None, db: Session = Depends(get_db)):
    """تحلیل Backtest/Forward یک نسخه — scope=VERSION (فاز ۲۳: مستقل از هم)"""
    from ..models.strategy import TestType as TT
    try:
        tt = TT(test_type.lower()) if test_type else None
    except ValueError:
        raise HTTPException(400, detail="نوع تست نامعتبر است (BACKTEST/FORWARD/REAL)")
    if tt == TT.REAL:
        raise HTTPException(400, detail="تحلیل نسخه فقط برای BACKTEST یا FORWARD است؛ REAL از مسیر پراپ/بروکر تحلیل می‌شود")
    try:
        r = AnalysisService(db).analyze_version(version_id, test_type=tt)
        return {"message": r["message"], "analysis_id": r["result"].id,
                "run_id": r["run_id"], "version_id": version_id,
                "test_type": tt.name if tt else None}
    except ValueError as e:
        raise HTTPException(404, detail=str(e))


@router.post("/analyze/prop/{prop_stage_id}")
def analyze_prop_stage(prop_stage_id: int, db: Session = Depends(get_db)):
    """تحلیل کامل یک مرحله پراپ — scope=PROP_STAGE"""
    try:
        r = AnalysisService(db).analyze_prop_stage(prop_stage_id)
        return {"message": r["message"], "analysis_id": r["result"].id,
                "run_id": r["run_id"], "prop_stage_id": prop_stage_id}
    except ValueError as e:
        raise HTTPException(404, detail=str(e))


@router.post("/analyze/broker/{finance_account_id}")
def analyze_broker(finance_account_id: int, db: Session = Depends(get_db)):
    """تحلیل کامل یک حساب بروکر — scope=BROKER"""
    try:
        r = AnalysisService(db).analyze_broker(finance_account_id)
        return {"message": r["message"], "analysis_id": r["result"].id,
                "run_id": r["run_id"], "finance_account_id": finance_account_id}
    except ValueError as e:
        raise HTTPException(404, detail=str(e))


@router.get("/dashboard")
def get_dashboard_data(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """داده‌های داشبورد — فاز ۱۵.۳: محاسبات در SQL (بدون لود کل جدول)"""
    from ..services.prop_rule_engine import PropRuleEngine
    from ..models.prop import PropStage, StageStatus

    df_bound = _parse_bound(date_from)
    dt_bound = _parse_bound(date_to, end=True)
    net = _net_expr()
    is_closed = Trade.close_time.isnot(None)
    win_cond = and_(is_closed, net > 0)
    loss_cond = and_(is_closed, net < 0)
    scope = _scope_filter(db.query(Trade), df_bound, dt_bound)
    closed_scope = scope.filter(is_closed)

    # ── ۱) آمار کلی در یک کوئری (بدون لود ردیف‌ها) ──
    agg = scope.with_entities(
        func.count(Trade.id),
        func.sum(case((is_closed, 1), else_=0)),
        func.sum(net),
        func.sum(case((win_cond, net), else_=0.0)),
        func.sum(case((loss_cond, net), else_=0.0)),
        func.sum(case((win_cond, 1), else_=0)),
        func.sum(case((loss_cond, 1), else_=0)),
        func.max(case((win_cond, net), else_=0.0)),
        func.min(case((loss_cond, net), else_=0.0)),
    ).one()
    total_trades = int(agg[0] or 0)
    closed_count = int(agg[1] or 0)
    tnp = float(agg[2] or 0.0)
    gp = float(agg[3] or 0.0)
    gl = abs(float(agg[4] or 0.0))
    wins_n = int(agg[5] or 0)
    losses_n = int(agg[6] or 0)
    largest_win = float(agg[7] or 0.0)
    largest_loss = abs(float(agg[8] or 0.0))

    wr = (wins_n / closed_count * 100) if closed_count else 0
    pf = (gp / gl) if gl > 0 else (100.0 if gp > 0 else 0.0)
    avg_win = (gp / wins_n) if wins_n else 0.0
    avg_loss = (gl / losses_n) if losses_n else 0.0
    win_ratio = (wins_n / closed_count) if closed_count else 0.0
    loss_ratio = (losses_n / closed_count) if closed_count else 0.0
    expectancy = (win_ratio * avg_win) - (loss_ratio * avg_loss)

    # ── ۲) سکانس مرتب با فقط ۲ ستون برای DD/streak/اکوییتی (بدون ORM) ──
    narrow = (
        closed_scope.with_entities(Trade.close_time, net.label("net"), Trade.id)
        .order_by(Trade.close_time.asc(), Trade.id.asc())
        .all()
    )
    seq = []
    for _ct, _n, _id in narrow:
        if _ct is not None and _ct.tzinfo is None:
            _ct = _ct.replace(tzinfo=timezone.utc)
        seq.append((_ct, float(_n or 0.0)))

    eq = 0.0; pk = 0.0; md = 0.0; sp = []
    for _ct, _n in seq:
        eq += _n
        if eq > pk: pk = eq
        d = pk - eq
        if d > md: md = d
        sp.append(round(eq, 2))
    spd = sp[-20:] if len(sp) >= 20 else sp
    max_consecutive_losses = 0; _streak = 0
    for _ct, _n in seq:
        if _n < 0:
            _streak += 1
            if _streak > max_consecutive_losses: max_consecutive_losses = _streak
        elif _n > 0:
            _streak = 0

    now = datetime.now(timezone.utc)
    ts = now.replace(hour=0, minute=0, second=0, microsecond=0)
    opn = db.query(Trade).filter(
        Trade.close_time.is_(None), Trade.is_deleted == False
    ).count()
    # ── ۳) منحنی اکوییتی روزانه ──
    daily_pnl = defaultdict(float)
    for _ct, _n in seq:
        if _ct is None:
            continue
        daily_pnl[_ct.astimezone(timezone.utc).date().isoformat()] += _n
    equity_curve = []
    _cum = 0.0
    for dkey in sorted(daily_pnl.keys()):
        _cum += daily_pnl[dkey]
        equity_curve.append({"date": dkey, "equity": round(_cum, 2)})

    # ── ۴) توزیع PnL (یک کوئری GROUP BY) ──
    _bucket_defs = [
        ("< -500", net < -500),
        ("-500..-200", and_(net >= -500, net < -200)),
        ("-200..-50", and_(net >= -200, net < -50)),
        ("-50..0", and_(net >= -50, net < 0)),
        ("0..50", and_(net >= 0, net < 50)),
        ("50..200", and_(net >= 50, net < 200)),
        ("200..500", and_(net >= 200, net < 500)),
        ("> 500", net >= 500),
    ]
    _bucket_case = case(*[(cond, label) for label, cond in _bucket_defs], else_="> 500")
    _bmap = {
        label: int(cnt)
        for label, cnt in closed_scope.with_entities(_bucket_case, func.count(Trade.id))
        .group_by(_bucket_case)
        .all()
    }
    pnl_distribution = [{"range": label, "count": _bmap.get(label, 0)} for label, _ in _bucket_defs]

    # ── ۵) دوره‌ها و امروز (یک کوئری) ──
    cm = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    qm = ((now.month - 1) // 3) * 3 + 1
    cq = now.replace(month=qm, day=1, hour=0, minute=0, second=0, microsecond=0)
    ys = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    pms = cm.replace(year=cm.year - 1, month=12) if cm.month == 1 else cm.replace(month=cm.month - 1)
    per = closed_scope.with_entities(
        func.sum(case((Trade.close_time >= ts, net), else_=0.0)),
        func.sum(case((Trade.close_time >= ts, 1), else_=0)),
        func.sum(case((and_(Trade.close_time >= ts, net > 0), 1), else_=0)),
        func.sum(case((Trade.close_time >= cm, net), else_=0.0)),
        func.sum(case((and_(Trade.close_time >= pms, Trade.close_time < cm), net), else_=0.0)),
        func.sum(case((Trade.close_time >= cq, net), else_=0.0)),
        func.sum(case((Trade.close_time >= ys, net), else_=0.0)),
    ).one()
    tdp = float(per[0] or 0.0)
    td_count = int(per[1] or 0)
    today_wins_n = int(per[2] or 0)
    mp = float(per[3] or 0.0)
    pv = float(per[4] or 0.0)
    qp = float(per[5] or 0.0)
    yp = float(per[6] or 0.0)
    mcp = ((mp - pv) / abs(pv) * 100) if pv != 0 else (100 if mp > 0 else -100 if mp < 0 else 0)
    today_wr = (today_wins_n / td_count * 100) if td_count else 0

    # ── برد/باخت ──
    win_loss = {"wins": wins_n, "losses": losses_n}

    # ── فاز ۲۱: پول قابل خرج (از Transactionها) ──
    from ..models.finance import Account as FinAccount, AccountType, Transaction, TransactionType
    from ..models.prop import PropStage as PS, StageType

    def _spendable_tx(type_name: AccountType):
        """سود خالص یک نوع حساب از Transactionهای PROFIT/LOSS"""
        return float(
            db.query(
                func.coalesce(func.sum(case((Transaction.type == TransactionType.PROFIT, Transaction.amount), else_=0.0)), 0) -
                func.coalesce(func.sum(case((Transaction.type == TransactionType.LOSS, Transaction.amount), else_=0.0)), 0)
            )
            .select_from(Transaction)
            .join(FinAccount, Transaction.account_id == FinAccount.id)
            .filter(FinAccount.type == type_name, Transaction.is_deleted == False)
            .scalar() or 0.0
        )

    broker_pnl = _spendable_tx(AccountType.BROKER)

    # سود خالص مرحله ۳ پراپ: Transaction → Account(id) → PropAccount(finance_account_id) → PropStage(prop_account_id)
    from ..models.prop import PropAccount as PropAcct
    funded_pnl = float(
        db.query(
            func.coalesce(func.sum(case((Transaction.type == TransactionType.PROFIT, Transaction.amount), else_=0.0)), 0) -
            func.coalesce(func.sum(case((Transaction.type == TransactionType.LOSS, Transaction.amount), else_=0.0)), 0)
        )
        .select_from(Transaction)
        .join(FinAccount, Transaction.account_id == FinAccount.id)
        .join(PropAcct, FinAccount.id == PropAcct.finance_account_id)
        .join(PS, PropAcct.id == PS.prop_account_id)
        .filter(PS.stage_type == StageType.FUNDED_REAL, Transaction.is_deleted == False)
        .scalar() or 0.0
    )

    spendable_net = round(broker_pnl + funded_pnl, 2)
    spendable_net = round(broker_pnl + funded_pnl, 2)

    broker_balance = float(
        db.query(func.coalesce(func.sum(FinAccount.balance), 0))
        .filter(FinAccount.type == AccountType.BROKER)
        .scalar() or 0.0
    )

    init_capital = float(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .select_from(Transaction)
        .join(FinAccount, Transaction.account_id == FinAccount.id)
        .filter(
            FinAccount.type == AccountType.BROKER,
            Transaction.type == TransactionType.DEPOSIT,
            Transaction.is_deleted == False,
        )
        .scalar() or 0.0
    )

    # ── Prop Progress ──
    active_stages = db.query(PropStage).filter(
        PropStage.status == StageStatus.ACTIVE
    ).all()
    prop_progress_data = []
    from ..models.prop import StageType
    for stage in active_stages:
        result = PropRuleEngine.evaluate_stage(db, stage.id)
        result["stage_name"] = stage.stage_type.value if stage.stage_type else "Unknown"
        prop_progress_data.append(result)

    return {
        "summary": {
            "net_pnl": round(tnp, 2),
            "win_rate": round(wr, 2),
            "max_dd": round(md, 2),
            "profit_factor": round(pf, 2),
            "total_trades": total_trades,
            "open_trades": opn,
            "closed_trades": closed_count,
            "gross_profit": round(gp, 2),
            "gross_loss": round(gl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "largest_win": round(largest_win, 2),
            "largest_loss": round(largest_loss, 2),
            "expectancy": round(expectancy, 2),
            "max_consecutive_losses": max_consecutive_losses,
        },
        "today": {
            "pnl": round(tdp, 2),
            "trades_count": td_count,
            "win_rate": round(today_wr, 2),
            "winning_trades": today_wins_n,
            "losing_trades": td_count - today_wins_n,
        },
        "sparkline": spd,
        "equity_curve": equity_curve,
        "pnl_distribution": pnl_distribution,
        "win_loss": win_loss,
        "spendable_money": {
            "net_pnl": spendable_net,
            "total_balance": round(broker_balance + broker_pnl + funded_pnl, 2),
            "initial_capital": round(init_capital, 2),
        },
        "periods": {
            "month": {
                "pnl": round(mp, 2),
                "change_percent": round(mcp, 2),
            },
            "quarter": {
                "pnl": round(qp, 2),
            },
            "year": {
                "pnl": round(yp, 2),
            },
        },
        "prop_progress": prop_progress_data,
    }


# ═════════════════════════════════════════════
# Yesterday (فاز ۱۴.۲)
# ═════════════════════════════════════════════
_WEEKDAYS_FA = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]


@router.get("/yesterday")
def get_yesterday_data(db: Session = Depends(get_db)):
    """داده‌های عملکرد روز گذشته (بر اساس close_time، UTC)"""
    from ..models.strategy import Trade
    from ..models.finance import Account as FinanceAccount, AccountType
    from .finance import _gregorian_to_jalali

    def _ensure_utc(dt):
        if dt is not None and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def net_pnl(t):
        return (t.pnl or 0) + (t.commission or 0) + (t.swap or 0)

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    y_start = today_start - timedelta(days=1)
    y_end = today_start

    yt = []
    for t in db.query(Trade).filter(
        Trade.close_time != None, Trade.is_deleted == False
    ).all():
        ct = _ensure_utc(t.close_time)
        if ct is not None and y_start <= ct < y_end:
            t.close_time = ct
            yt.append(t)

    # انواع حساب مالی برای تفکیک منبع
    acct_ids = {t.finance_account_id for t in yt if t.finance_account_id}
    acct_types = {}
    if acct_ids:
        for a in db.query(FinanceAccount).filter(FinanceAccount.id.in_(acct_ids)).all():
            acct_types[a.id] = a.type

    def classify(t):
        if t.prop_stage_id:
            return "prop"
        at = acct_types.get(t.finance_account_id) if t.finance_account_id else None
        if at == AccountType.PROP:
            return "prop"
        if at == AccountType.BROKER:
            return "broker"
        return "personal"

    by_source = {
        "prop": {"trades": 0, "winning": 0, "losing": 0, "pnl": 0.0},
        "broker": {"trades": 0, "winning": 0, "losing": 0, "pnl": 0.0},
        "personal": {"trades": 0, "winning": 0, "losing": 0, "pnl": 0.0},
    }
    winning = losing = 0
    net_total = 0.0
    for t in yt:
        p = net_pnl(t)
        net_total += p
        src = classify(t)
        by_source[src]["trades"] += 1
        by_source[src]["pnl"] += p
        if p > 0:
            winning += 1
            by_source[src]["winning"] += 1
        elif p < 0:
            losing += 1
            by_source[src]["losing"] += 1

    total = len(yt)
    jy, jm, jd = _gregorian_to_jalali(y_start.year, y_start.month, y_start.day)

    return {
        "date": f"{jy}/{jm:02d}/{jd:02d}",
        "day_of_week": _WEEKDAYS_FA[y_start.weekday()],
        "total_trades": total,
        "winning_trades": winning,
        "losing_trades": losing,
        "win_rate": round((winning / total * 100) if total else 0.0, 2),
        "net_pnl": round(net_total, 2),
        "by_source": {
            k: {
                "trades": v["trades"],
                "winning": v["winning"],
                "losing": v["losing"],
                "pnl": round(v["pnl"], 2),
            }
            for k, v in by_source.items()
        },
    }


@router.get("/risk-metrics")
def get_risk_metrics(db: Session = Depends(get_db)):
    """محاسبه شاخص‌های مدیریت ریسک — فاز ۱۵.۳: SQL + واکشی ستونی"""
    import math
    from ..models.finance import Account as FinanceAccount, AccountType

    # فاز ۱۵.۳: فقط ۵ ستون لازم، به ترتیب id (معادل ترتیب قبلی .all())
    _net = _net_expr()
    _rows = (
        db.query(Trade)
        .filter(Trade.close_time.isnot(None), Trade.is_deleted == False)
        .with_entities(Trade.close_time, _net.label("net"), Trade.r_multiple, Trade.sl, Trade.open_price)
        .order_by(Trade.id.asc())
        .all()
    )
    closed_trades = []
    for _ct, _n, _r, _sl, _op in _rows:
        if _ct is not None and _ct.tzinfo is None:
            _ct = _ct.replace(tzinfo=timezone.utc)
        closed_trades.append({"close_time": _ct, "net": float(_n or 0.0), "r_multiple": _r, "sl": _sl, "open_price": _op})
    returns = [c["net"] for c in closed_trades]
    accts = db.query(FinanceAccount).filter(FinanceAccount.type == AccountType.BROKER).all()
    avg_b = sum(a.balance or 0 for a in accts) / len(accts) if accts else 10000
    ps = []
    for rp in [1, 2, 3]:
        ra = avg_b * rp / 100
        st = [c for c in closed_trades if c["sl"] and c["open_price"] and c["sl"] > 0]
        asp = sum(abs((c["sl"] - c["open_price"]) / c["open_price"]) * 100 for c in st) / len(st) if st else 0
        ss = ra / (asp / 100 * avg_b) if asp > 0 else 0
        ps.append({"risk_percent": rp, "risk_amount": round(ra, 2), "avg_sl_percent": round(asp, 2),
            "suggested_size": round(ss, 4), "suggested_lots": round(ss * 10, 2)})
    ar = 0
    if len(returns) > 1:
        ar = sum(returns) / len(returns)
        std = (sum((r - ar) ** 2 for r in returns) / len(returns)) ** 0.5
        sharpe = (ar / std) * math.sqrt(252) if std > 0 else 0
    else: sharpe = 0
    neg = [r for r in returns if r < 0]
    if len(returns) > 1 and neg:
        ddev = (sum(r ** 2 for r in neg) / len(returns)) ** 0.5
        sortino = (ar / ddev) * math.sqrt(252) if ddev > 0 else 0
    else: sortino = 0
    wins = [r for r in returns if r > 0]; losses = [r for r in returns if r < 0]
    wr = len(wins) / len(returns) if returns else 0
    aw = sum(wins) / len(wins) if wins else 0
    al = abs(sum(losses) / len(losses)) if losses else 0
    rr = (aw / al) if al > 0 else 1
    bu = avg_b / al if al > 0 else 100
    if wr > 0 and rr > 0:
        p = (1 - wr) / (rr * wr) if (rr * wr) > 0 else 1
        ror = min(p ** bu, 1) if rr * wr > 1 - wr else 0
    else: ror = 0.5
    rv = [c["r_multiple"] for c in closed_trades if c["r_multiple"] and c["r_multiple"] != 0]
    arm = sum(rv) / len(rv) if rv else 0
    oe = float(db.query(func.sum(func.abs(func.coalesce(Trade.pnl, 0.0))))
               .filter(Trade.close_time.is_(None), Trade.is_deleted == False).scalar() or 0.0)
    orp = (oe / avg_b * 100) if avg_b > 0 else 0
    streak = 0; ms = 0
    for r in returns:
        if r < 0: streak += 1; ms = max(ms, streak)
        elif r > 0: streak = 0
    eq = 0; pk = 0; dd_d = 0; md = 0; cd = 0
    for c in sorted(closed_trades, key=lambda c: c["close_time"]):
        eq += c["net"]
        if eq > pk: pk = eq; cd = 0
        elif eq < pk:
            d = pk - eq
            if d > dd_d: dd_d = d
            cd += 1
            if cd > md: md = cd
    status = "danger" if (sharpe < 0.5 or ror > 0.1 or orp > 20) else ("warning" if (sharpe < 1.0 or ror > 0.05 or orp > 10) else "safe")
    return {"position_sizing": {"avg_balance": round(avg_b, 2), "suggestions": ps},
        "performance_ratios": {"sharpe_ratio": round(sharpe, 2), "sortino_ratio": round(sortino, 2),
            "profit_factor": round((sum(wins) / abs(sum(losses))) if losses else (100 if wins else 0), 2),
            "win_rate": round(wr * 100, 2), "avg_r_multiple": round(arm, 2),
            "expectancy": round((ar) if returns else 0, 2), "expectancy_r": round((ar / al) if al > 0 else 0, 2),
            "avg_win": round(aw, 2), "avg_loss": round(al, 2), "rr_ratio": round(rr, 2)},
        "risk_metrics": {"risk_of_ruin": round(ror, 4), "max_consecutive_losses": ms,
            "max_drawdown_depth": round(dd_d, 2), "max_drawdown_duration": md,
            "open_exposure": round(oe, 2), "open_risk_percent": round(orp, 2), "total_trades": len(returns)},
        "status": status}


# ═════════════════════════════════════════════
# Advanced Risk (فاز ۱۴.۴)
# ═════════════════════════════════════════════
def _percentile(sorted_vals, p: float) -> float:
    """درصدک با درون‌یابی خطی (بدون numpy)"""
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    if n == 1:
        return float(sorted_vals[0])
    k = (n - 1) * p
    f = int(k)
    c = min(f + 1, n - 1)
    if f == k:
        return float(sorted_vals[f])
    return float(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f))


@router.get("/risk-advanced")
def get_risk_advanced(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """آمار ریسک پیشرفته (شارپ، سورتینو، کالمار، VaR/CVaR، کِلی، Ulcer، ...)"""
    import math
    from ..models.finance import Account as FinanceAccount, AccountType

    df_bound = _parse_bound(date_from)
    dt_bound = _parse_bound(date_to, end=True)

    # فاز ۱۵.۳: فیلتر بازه در SQL + واکشی فقط ۳ ستون (بدون لود ORM)
    _net = _net_expr()
    _rows = (
        _scope_filter(db.query(Trade), df_bound, dt_bound)
        .filter(Trade.close_time.isnot(None))
        .with_entities(Trade.close_time, _net.label("net"), Trade.r_multiple)
        .order_by(Trade.close_time.asc(), Trade.id.asc())
        .all()
    )
    closed = []
    for _ct, _n, _r in _rows:
        if _ct is not None and _ct.tzinfo is None:
            _ct = _ct.replace(tzinfo=timezone.utc)
        closed.append({"close_time": _ct, "net": float(_n or 0.0), "r_multiple": _r})

    returns = [c["net"] for c in closed]
    total = len(returns)

    # ── پایه ──
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]
    wr = (len(wins) / total) if total else 0.0
    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (abs(sum(losses) / len(losses))) if losses else 0.0
    rr = (avg_win / avg_loss) if avg_loss > 0 else 0.0
    net = sum(returns)
    mean_ret = (net / total) if total else 0.0

    # ── Sharpe / Sortino ──
    sharpe = 0.0
    sortino = 0.0
    if total > 1:
        std = (sum((r - mean_ret) ** 2 for r in returns) / total) ** 0.5
        sharpe = (mean_ret / std) * math.sqrt(252) if std > 0 else 0.0
        neg = [r for r in returns if r < 0]
        if neg:
            ddev = (sum(r ** 2 for r in neg) / total) ** 0.5
            sortino = (mean_ret / ddev) * math.sqrt(252) if ddev > 0 else 0.0

    # ── Equity / Drawdown / Ulcer ──
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    ulcer_acc = 0.0
    drawdown_curve = []
    for idx, c in enumerate(closed):
        equity += c["net"]
        if equity > peak:
            peak = equity
        dd_abs = peak - equity
        dd_pct = (dd_abs / peak * 100) if peak > 0 else 0.0
        if dd_abs > max_dd:
            max_dd = dd_abs
        ulcer_acc += dd_pct ** 2
        drawdown_curve.append({
            "index": idx + 1,
            "date": c["close_time"].date().isoformat(),
            "drawdown": round(dd_abs, 2),
            "drawdown_pct": round(dd_pct, 2),
        })
    ulcer_index = (ulcer_acc / total) ** 0.5 if total else 0.0

    # ── Calmar (سالیانه) / Recovery Factor ──
    if closed:
        span_days = max((closed[-1]["close_time"] - closed[0]["close_time"]).days, 1)
    else:
        span_days = 1
    annual_return = net * (365.0 / span_days) if total else 0.0
    calmar = (annual_return / max_dd) if max_dd > 0 else 0.0
    recovery_factor = (net / max_dd) if max_dd > 0 else 0.0

    # ── VaR / CVaR 95% ──
    sorted_ret = sorted(returns)
    var_95 = _percentile(sorted_ret, 0.05)
    tail = [r for r in sorted_ret if r <= var_95]
    cvar_95 = (sum(tail) / len(tail)) if tail else var_95

    # ── برد/باخت متوالی ──
    max_cl = 0
    max_cw = 0
    cur_l = 0
    cur_w = 0
    for r in returns:
        if r < 0:
            cur_l += 1
            cur_w = 0
            if cur_l > max_cl:
                max_cl = cur_l
        elif r > 0:
            cur_w += 1
            cur_l = 0
            if cur_w > max_cw:
                max_cw = cur_w
        else:
            cur_l = 0
            cur_w = 0

    # ── R-Multiple ──
    rv = [c["r_multiple"] for c in closed if c["r_multiple"] is not None and c["r_multiple"] != 0]
    avg_r = (sum(rv) / len(rv)) if rv else 0.0
    expectancy_r = (mean_ret / avg_loss) if avg_loss > 0 else 0.0

    # ── Kelly Criterion ──
    kelly = (wr - ((1 - wr) / rr)) if rr > 0 else 0.0

    # ── Risk of Ruin ──
    accts = db.query(FinanceAccount).filter(FinanceAccount.type == AccountType.BROKER).all()
    avg_b = (sum(a.balance or 0 for a in accts) / len(accts)) if accts else 10000.0
    if wr > 0 and rr > 0:
        p = (1 - wr) / (rr * wr) if (rr * wr) > 0 else 1.0
        units = (avg_b / avg_loss) if avg_loss > 0 else 100.0
        ror = min(p ** units, 1.0) if rr * wr > 1 - wr else 0.0
    else:
        ror = 0.5

    # ── توزیع R-Multiple ──
    _buckets = [
        ("< -2R", lambda x: x < -2),
        ("-2..-1R", lambda x: -2 <= x < -1),
        ("-1..0R", lambda x: -1 <= x < 0),
        ("0..1R", lambda x: 0 <= x < 1),
        ("1..2R", lambda x: 1 <= x < 2),
        ("2..3R", lambda x: 2 <= x < 3),
        ("> 3R", lambda x: x >= 3),
    ]
    r_distribution = [
        {"range": label, "count": sum(1 for v in rv if fn(v))}
        for label, fn in _buckets
    ]

    return {
        "has_enough_data": total >= 2,
        "total_trades": total,
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "calmar_ratio": round(calmar, 3),
        "risk_of_ruin": round(ror, 4),
        "var_95": round(var_95, 2),
        "cvar_95": round(cvar_95, 2),
        "max_consecutive_losses": max_cl,
        "max_consecutive_wins": max_cw,
        "avg_r_multiple": round(avg_r, 3),
        "expectancy_r": round(expectancy_r, 3),
        "kelly_criterion": round(kelly, 4),
        "recovery_factor": round(recovery_factor, 2),
        "ulcer_index": round(ulcer_index, 2),
        "max_drawdown": round(max_dd, 2),
        "r_multiple_distribution": r_distribution,
        "drawdown_curve": drawdown_curve,
    }


# ═════════════════════════════════════════════
# Calendar (تقویم شمسی معاملات)
# ═════════════════════════════════════════════
@router.get("/calendar")
def get_calendar_data(
    year: Optional[int] = Query(None, description="سال شمسی (مثال: 1404)"),
    month: Optional[int] = Query(None, description="ماه شمسی (1-12)"),
    from_date: Optional[str] = Query(None, description="تاریخ شروع میلادی (ISO)"),
    to_date: Optional[str] = Query(None, description="تاریخ پایان میلادی (ISO)"),
    db: Session = Depends(get_db),
):
    """Get trades grouped by day for calendar view (supports Jalali year/month or Gregorian range)"""
    now = datetime.now(timezone.utc)
    query = db.query(Trade).filter(
        Trade.close_time.isnot(None), Trade.is_deleted == False
    )

    # ── اگر سال و ماه شمسی داده شده ──
    if year is not None and month is not None:
        gy_start, gm_start, gd_start = _jalali_to_gregorian(year, month, 1)
        if month < 12:
            gy_end, gm_end, gd_end = _jalali_to_gregorian(year, month + 1, 1)
        else:
            gy_end, gm_end, gd_end = _jalali_to_gregorian(year + 1, 1, 1)
        dt_from = datetime(gy_start, gm_start, gd_start, tzinfo=timezone.utc)
        dt_to = datetime(gy_end, gm_end, gd_end, tzinfo=timezone.utc)
        query = query.filter(Trade.close_time >= dt_from, Trade.close_time < dt_to)

    # فاز ۱۵.۳: واکشی فقط ستون‌های لازم (بدون لود ORM)
    _net = _net_expr()
    trades = (
        query.with_entities(
            Trade.id, Trade.symbol, Trade.direction, Trade.size,
            Trade.pnl, Trade.close_time, _net.label("net"),
        )
        .order_by(Trade.close_time.asc())
        .all()
    )

    days = defaultdict(list)
    for _id, _sym, _dir, _size, _pnl, _ct, _netv in trades:
        days[_ct.strftime("%Y-%m-%d")].append((_id, _sym, _dir, _size, _pnl, _ct, float(_netv or 0.0)))

    result = []
    for day_key, day_trades in sorted(days.items()):
        pnl = sum(d[6] for d in day_trades)
        wins = sum(1 for d in day_trades if d[6] > 0)
        total = len(day_trades)
        result.append({
            "date": day_key,
            "trade_count": total,
            "total_pnl": round(pnl, 2),
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            "trades": [
                {
                    "id": d[0],
                    "symbol": d[1],
                    "direction": d[2],
                    "size": d[3],
                    "pnl": round(d[4], 2) if d[4] else 0,
                    "close_time": d[5].isoformat() if d[5] else None,
                }
                for d in day_trades
            ],
        })

    return result


# ─────────────────────────────────────────────
# تبدیل شمسی به میلادی (برای Calendar)
# ─────────────────────────────────────────────
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
# ═════════════════════════════════════════════
# فاز ۲۰.۳ — تحلیل ۶گانه (GET) + گارد سازگاری
# ═════════════════════════════════════════════
@router.get("/analysis/version/{version_id}")
def get_analysis_version(version_id: int, test_type: Optional[str] = None, db: Session = Depends(get_db)):
    """دریافت تحلیل Backtest/Forward یک نسخه (فاز ۲۰/۲۳ — مستقل از هم)"""
    from ..models.strategy import TestType as TT
    from ..utils.trade_scope import version_scope_key
    tt = None
    if test_type:
        try:
            tt = TT(test_type.lower())
        except ValueError:
            raise HTTPException(400, detail="نوع تست نامعتبر است (BACKTEST/FORWARD)")
    result = db.query(AnalysisResult).filter(
        AnalysisResult.scope == AnalysisScope.VERSION,
        AnalysisResult.scope_key == version_scope_key(version_id, tt),
    ).first()
    if not result:
        raise HTTPException(404, detail="تحلیلی برای این نسخه یافت نشد. ابتدا POST analyze را اجرا کنید.")
    _guard_analyzable(db, version_id=version_id, result=result, test_type=tt)
    return _analysis_response(result)


@router.get("/analysis/prop/{prop_stage_id}")
def get_analysis_prop(prop_stage_id: int, db: Session = Depends(get_db)):
    """دریافت تحلیل یک مرحله پراپ — scope=PROP_STAGE"""
    result = db.query(AnalysisResult).filter(
        AnalysisResult.scope == AnalysisScope.PROP_STAGE,
        AnalysisResult.scope_key == str(prop_stage_id),
    ).first()
    if not result:
        raise HTTPException(404, detail="تحلیلی برای این مرحله پراپ یافت نشد.")
    _guard_analyzable(db, prop_stage_id=prop_stage_id, result=result)
    return _analysis_response(result)


@router.get("/analysis/broker/{finance_account_id}")
def get_analysis_broker(finance_account_id: int, db: Session = Depends(get_db)):
    """دریافت تحلیل یک حساب بروکر — scope=BROKER"""
    result = db.query(AnalysisResult).filter(
        AnalysisResult.scope == AnalysisScope.BROKER,
        AnalysisResult.scope_key == str(finance_account_id),
    ).first()
    if not result:
        raise HTTPException(404, detail="تحلیلی برای این حساب بروکر یافت نشد.")
    _guard_analyzable(db, finance_account_id=finance_account_id, result=result)
    return _analysis_response(result)


def _guard_analyzable(db, result, version_id=None, prop_stage_id=None, finance_account_id=None, test_type=None):
    """گارد سازگاری فاز ۱۹/۲۳ — تحلیل کهنه سرو نشود (فاز ۲۳: به تفکیک test_type)"""
    from ..models.strategy import Trade
    q = db.query(Trade)
    # فاز ۲۵: حذف‌شده‌ها در گارد سازگاری شمرده نمی‌شوند
    q = q.filter(Trade.is_deleted == False)
    scope_label = "این دامنه"
    if version_id is not None:
        from ..utils.trade_scope import analysis_trades_filter
        q = q.filter(Trade.version_id == version_id, analysis_trades_filter())
        if test_type is not None:
            q = q.filter(Trade.test_type == test_type)
            scope_label = "فوروارد" if test_type.name == "FORWARD" else "بک‌تست"
        else:
            scope_label = "بک‌تست/فوروارد"
    elif prop_stage_id is not None:
        q = q.filter(Trade.prop_stage_id == prop_stage_id)
        scope_label = "این مرحله پراپ"
    elif finance_account_id is not None:
        q = q.filter(Trade.finance_account_id == finance_account_id)
        scope_label = "این حساب بروکر"
    count = q.count()
    if count == 0:
        raise HTTPException(404, detail=f"هیچ معامله‌ای برای {scope_label} یافت نشد.")
    if result.total_trades != count:
        raise HTTPException(404, detail=f"تحلیل کهنه است ({result.total_trades} در برابر {count} معامله). دوباره تحلیل کنید.")


def _analysis_response(result):
    """تبدیل AnalysisResult به دیکشنری پاسخ"""
    return {
        "version_id": result.version_id,
        "prop_stage_id": result.prop_stage_id,
        "finance_account_id": result.finance_account_id,
        "total_trades": result.total_trades,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor,
        "net_pnl": result.net_pnl,
        "net_r": result.net_r,
        "max_dd": result.max_dd,
        "expectancy": result.expectancy,
        "expectancy_r": result.expectancy_r,
        "avg_win": result.avg_win,
        "avg_loss": result.avg_loss,
        "largest_win": result.largest_win,
        "largest_loss": result.largest_loss,
        "max_consecutive_losses": result.max_consecutive_losses,
        "consistency_analysis": result.consistency_analysis,
        "session_analysis": result.session_analysis,
        "weekday_analysis": result.weekday_analysis,
        "hour_analysis": result.hour_analysis,
        "custom_time_analysis": result.custom_time_analysis,
        "created_at": result.created_at,
    }


@router.get("/{version_id}")
def get_analysis(version_id: int, db: Session = Depends(get_db)):
    """دریافت آخرین تحلیل ذخیره‌شده‌ی یک نسخه

    فاز ۱۹: تحلیل نسخه فقط روی معاملات Backtest/Forward انجام می‌شود؛ پس نتیجه‌ای
    سرو می‌شود که با مجموعه‌ی معاملات قابل‌تحلیل فعلی نسخه هم‌خوان باشد.
    """
    result = db.query(AnalysisResult).filter(
        AnalysisResult.version_id == version_id
    ).first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="تحلیلی برای این نسخه یافت نشد. ابتدا POST /analyze/{version_id} را اجرا کنید."
        )

    # ── گارد سازگاری (فاز ۱۹) ──
    # تعداد معاملات قابل‌تحلیل = غیر-REAL (BACKTEST / FORWARD)
    analyzable_trades = (
        db.query(Trade)
        .filter(Trade.version_id == version_id, analysis_trades_filter())
        .count()
    )

    if analyzable_trades == 0:
        raise HTTPException(
            status_code=404,
            detail="این نسخه معامله‌ی Backtest/Forward ندارد "
                   "(معاملات REAL در تحلیل نسخه شمرده نمی‌شوند)",
        )

    if result.total_trades != analyzable_trades:
        raise HTTPException(
            status_code=404,
            detail=f"تحلیل ذخیره‌شده کهنه است ({result.total_trades} معامله در تحلیل "
                   f"در برابر {analyzable_trades} معامله‌ی قابل‌تحلیل فعلی). "
                   f"دوباره «تحلیل مجدد» را بزنید.",
        )

    return {
        "version_id": result.version_id,
        "total_trades": result.total_trades,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor,
        "net_pnl": result.net_pnl,
        "net_r": result.net_r,
        "max_dd": result.max_dd,
        "expectancy": result.expectancy,
        "expectancy_r": result.expectancy_r,
        "avg_win": result.avg_win,
        "avg_loss": result.avg_loss,
        "largest_win": result.largest_win,
        "largest_loss": result.largest_loss,
        "max_consecutive_losses": result.max_consecutive_losses,
        "consistency_analysis": result.consistency_analysis,
        "session_analysis": result.session_analysis,
        "weekday_analysis": result.weekday_analysis,
        "hour_analysis": result.hour_analysis,
        "custom_time_analysis": result.custom_time_analysis,
        "created_at": result.created_at,
    }


@router.get("/{version_id}/history")
def get_analysis_history(version_id: int, db: Session = Depends(get_db)):
    """دریافت تاریخچه‌ی تحلیل‌های یک نسخه"""
    runs = db.query(AnalysisRun).filter(
        AnalysisRun.version_id == version_id
    ).order_by(AnalysisRun.created_at.desc()).all()

    if not runs:
        raise HTTPException(
            status_code=404,
            detail="تاریخچه‌ای برای این نسخه یافت نشد. ابتدا POST /analyze/{version_id} را اجرا کنید."
        )

    return [
        {
            "run_id": r.id,
            "version_id": r.version_id,
            "total_trades": r.total_trades,
            "win_rate": r.win_rate,
            "profit_factor": r.profit_factor,
            "net_pnl": r.net_pnl,
            "net_r": r.net_r,
            "max_dd": r.max_dd,
            "expectancy": r.expectancy,
            "avg_win": r.avg_win,
            "avg_loss": r.avg_loss,
            "largest_win": r.largest_win,
            "largest_loss": r.largest_loss,
            "max_consecutive_losses": r.max_consecutive_losses,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]


@router.post("/compare", response_model=VersionComparisonResponse)
def compare_versions(request: VersionComparisonRequest, db: Session = Depends(get_db)):
    """مقایسه‌ی چند نسخه و پیشنهاد بهترین"""
    try:
        service = AnalysisService(db)
        service = AnalysisService(db)
        result = service.compare_versions(request.version_ids, min_trades=request.min_trades or 0)
        return result
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در مقایسه: {str(e)}")


# ═════════════════════════════════════════════
# CustomTimeInterval (بازه‌های سفارشی)
# ═════════════════════════════════════════════
@router.get("/intervals/", response_model=List[CustomTimeIntervalResponse])
def get_intervals(symbol: str = None, db: Session = Depends(get_db)):
    """دریافت لیست بازه‌های سفارشی"""
    query = db.query(CustomTimeInterval)
    if symbol:
        query = query.filter(CustomTimeInterval.symbol == symbol)
    return query.all()


@router.post("/intervals/", response_model=CustomTimeIntervalResponse)
def create_interval(interval: CustomTimeIntervalCreate, db: Session = Depends(get_db)):
    """ایجاد بازه‌ی سفارشی جدید"""
    db_interval = CustomTimeInterval(**interval.model_dump())
    db.add(db_interval)
    db.commit()
    db.refresh(db_interval)
    return db_interval


@router.delete("/intervals/{interval_id}")
def delete_interval(interval_id: int, db: Session = Depends(get_db)):
    """حذف یک بازه‌ی سفارشی"""
    db_interval = db.query(CustomTimeInterval).filter(
        CustomTimeInterval.id == interval_id
    ).first()
    if not db_interval:
        raise HTTPException(status_code=404, detail="بازه یافت نشد")
    db.delete(db_interval)
    db.commit()
    return {"message": "بازه با موفقیت حذف شد"}


# ═════════════════════════════════════════════
# Seed (وارد کردن داده‌های اولیه)
# ═════════════════════════════════════════════
@router.post("/intervals/seed-gold")
def seed_gold_intervals(db: Session = Depends(get_db)):
    """وارد کردن بازه‌های پیش‌فرض طلا"""
    gold_intervals = [
        {"name": "بازه طلا A1", "symbol": "XAUUSD", "start_hour": 1, "start_minute": 0,
         "end_hour": 17, "end_minute": 0, "label": "A", "priority": 1},
        {"name": "بازه طلا C1", "symbol": "XAUUSD", "start_hour": 17, "start_minute": 0,
         "end_hour": 18, "end_minute": 30, "label": "C", "priority": 3},
        {"name": "بازه طلا B1", "symbol": "XAUUSD", "start_hour": 16, "start_minute": 20,
         "end_hour": 16, "end_minute": 30, "label": "B", "priority": 2},
        {"name": "بازه طلا A2", "symbol": "XAUUSD", "start_hour": 15, "start_minute": 50,
         "end_hour": 16, "end_minute": 30, "label": "A", "priority": 1},
        {"name": "بازه طلا B2", "symbol": "XAUUSD", "start_hour": 11, "start_minute": 0,
         "end_hour": 12, "end_minute": 30, "label": "B", "priority": 2},
    ]
    created = []
    for data in gold_intervals:
        existing = db.query(CustomTimeInterval).filter(
            CustomTimeInterval.name == data["name"]
        ).first()
        if not existing:
            db_interval = CustomTimeInterval(**data)
            db.add(db_interval)
            created.append(data["name"])
    db.commit()
    return {"message": f"{len(created)} بازه اضافه شد", "created": created}


@router.post("/intervals/seed-dji")
def seed_dji_intervals(db: Session = Depends(get_db)):
    """وارد کردن بازه‌های پیش‌فرض داوجونز"""
    dji_intervals = [
        {"name": "داو A1", "symbol": "DJIUSD", "start_hour": 1, "start_minute": 0,
         "end_hour": 17, "end_minute": 0, "label": "A", "priority": 1},
        {"name": "داو C1", "symbol": "DJIUSD", "start_hour": 17, "start_minute": 0,
         "end_hour": 18, "end_minute": 30, "label": "C", "priority": 3},
        {"name": "داو B1", "symbol": "DJIUSD", "start_hour": 16, "start_minute": 20,
         "end_hour": 16, "end_minute": 30, "label": "B", "priority": 2},
        {"name": "داو A2", "symbol": "DJIUSD", "start_hour": 15, "start_minute": 50,
         "end_hour": 16, "end_minute": 30, "label": "A", "priority": 1},
        {"name": "داو B2", "symbol": "DJIUSD", "start_hour": 11, "start_minute": 0,
         "end_hour": 12, "end_minute": 30, "label": "B", "priority": 2},
    ]
    created = []
    for data in dji_intervals:
        existing = db.query(CustomTimeInterval).filter(
            CustomTimeInterval.name == data["name"]
        ).first()
        if not existing:
            db_interval = CustomTimeInterval(**data)
            db.add(db_interval)
            created.append(data["name"])
    db.commit()
    return {"message": f"{len(created)} بازه اضافه شد", "created": created}
