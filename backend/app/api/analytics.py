from fastapi import APIRouter, Depends, HTTPException, Query
import math
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, or_
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from types import SimpleNamespace

from ..core.database import get_db
from ..services.analysis_service import AnalysisService, compare_versions
from ..services import metrics
from ..models.strategy import Trade, AnalysisResult, AnalysisRun, CustomTimeInterval, AnalysisScope, TestType
from ..models.finance import Currency
from ..models.prop import PropAccount, PropStage, StageType
from ..models.trading import PersonalTradingAccount
from ..utils.trade_scope import analysis_trades_filter, version_scope_key
from ..utils import jalali
from ..utils.time_utils import to_tehran, TEHRAN
from ..utils.time_helpers import tehran_day_bounds
from ..schemas.analytics import (
    CustomTimeIntervalCreate,
    CustomTimeIntervalResponse,
    CompareRequest,
)
from ..domain.risk.drawdown_engine import (
    calculate_drawdown_curve,
    calculate_drawdown_duration,
    calculate_peak_to_trough_dd,
    calculate_static_dd,
)
from ..domain.risk.equity_engine import calculate_equity_curve
from ..domain.risk.r_engine import calculate_expectancy_r
from ..domain.risk.risk_engine import RiskEngine

router = APIRouter()


# ═════════════════════════════════════════════
# Helpers — فاز ۱۵.۳ (SQL Aggregation)
# ═════════════════════════════════════════════
def _net_expr():
    """عبارت SQL سود/زیان خالص — فاز ۴۳: از تعریف واحد `metrics.net_pnl_sql()`"""
    return metrics.net_pnl_sql()


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


# فاز ۴۴.۱ — دامنهٔ معاملات (scope) برای داشبورد/ریسک/تقویم
#   real      → فقط REAL_PERSONAL + REAL_PROP با مرحلهٔ FUNDED_REAL (پیش‌فرض)
#   backtest  → فقط BACKTEST
#   forward   → فقط FORWARD
#   all       → بدون فیلتر نوع
VALID_SCOPES = ("real", "backtest", "forward", "all")


def normalize_scope(scope: Optional[str]) -> str:
    """اعتبارسنجی و نرمال‌سازی پارامتر scope."""
    s = (scope or "real").strip().lower()
    if s not in VALID_SCOPES:
        raise HTTPException(
            status_code=400,
            detail="scope نامعتبر است (real / backtest / forward / all)",
        )
    return s


def _apply_scope(query, scope: str):
    """فیلتر test_type بر اساس scope (real = personal + funded prop)."""
    if scope == "real":
        real_personal = Trade.test_type == TestType.REAL_PERSONAL
        real_prop_funded = and_(
            Trade.test_type == TestType.REAL_PROP,
            PropStage.stage_type == StageType.FUNDED_REAL,
        )
        return (
            query.outerjoin(PropStage, Trade.prop_stage_id == PropStage.id)
            .filter(or_(real_personal, real_prop_funded))
        )
    if scope == "backtest":
        return query.filter(Trade.test_type == TestType.BACKTEST)
    if scope == "forward":
        return query.filter(Trade.test_type == TestType.FORWARD)
    return query  # all


def _scope_filter(query, df_bound, dt_bound, scope: str = "real", currency: Optional[Currency] = None):
    """اعمال فیلتر بازه + دامنه در سطح SQL به‌جای فیلتر در Python (فاز ۱۵.۳ / ۴۴.۱)"""
    query = _apply_scope(query, scope)
    if currency is not None:
        query = query.outerjoin(
            PersonalTradingAccount,
            Trade.personal_trading_account_id == PersonalTradingAccount.id,
        )
        if scope != "real":
            query = query.outerjoin(PropStage, Trade.prop_stage_id == PropStage.id)
        query = (
            query.outerjoin(PropAccount, PropStage.prop_account_id == PropAccount.id)
            .filter(or_(
                and_(Trade.test_type == TestType.REAL_PERSONAL, PersonalTradingAccount.currency == currency),
                and_(Trade.test_type == TestType.REAL_PROP, PropAccount.currency == currency),
                and_(Trade.test_type.in_([TestType.BACKTEST, TestType.FORWARD]), currency == Currency.USDT),
            ))
        )
    query = query.filter(Trade.close_time.isnot(None))
    if df_bound:
        query = query.filter(Trade.close_time >= df_bound)
    if dt_bound:
        query = query.filter(Trade.close_time <= dt_bound)
    return query


# ═════════════════════════════════════════════
# فاز ۵۳.۲ — ابزارهای ریسک
#   · Sharpe/Sortino روی بازده **روزانه** و **بدون سالانه‌سازی**
#   · سرمایهٔ مبنا بر اساس scope
# ═════════════════════════════════════════════
ASSUMED_BALANCE = 10000.0   # سرمایهٔ فرضی وقتی مبنای واقعی قابل تعیین نیست


def _daily_returns(closed) -> list:
    """بازده **دورهای روزانه**: جمع net_pnl معاملاتِ هر روزِ بسته‌شدن.

    ورودی: لیست دیکشنری‌هایی با کلیدهای `close_time` و `net`.
    خروجی: لیست اعداد (به ترتیب تاریخ).

    چرا؟ چون Sharpe/Sortino استاندارد روی بازده **دوره‌ای** تعریف می‌شوند؛
    ضریب سالانه‌سازی √252 فقط برای دادهٔ روزانه و سال کامل معتبر است.
    """
    daily: dict = {}
    for c in closed:
        ct = c.get("close_time")
        if ct is None:
            continue
        day = ct.date()
        daily[day] = daily.get(day, 0.0) + float(c.get("net", 0.0) or 0.0)
    return [daily[d] for d in sorted(daily)]


def _sharpe_sortino(series) -> tuple:
    """Sharpe و Sortino روی یک سری بازده دوره‌ای — **بدون سالانه‌سازی** (فاز ۵۳.۲).

    sharpe  = mean / (std of whole series)
    sortino = mean / (downside deviation)
    """
    n = len(series)
    if n < 2:
        return 0.0, 0.0
    mean = sum(series) / n
    std = (sum((x - mean) ** 2 for x in series) / n) ** 0.5
    sharpe = (mean / std) if std > 0 else 0.0
    neg = [x for x in series if x < 0]
    if not neg:
        return sharpe, 0.0
    ddev = (sum(x ** 2 for x in neg) / n) ** 0.5
    sortino = (mean / ddev) if ddev > 0 else 0.0
    return sharpe, sortino


def _scope_avg_balance(db, scope: str, account_ids) -> float:
    """سرمایهٔ مبنای محاسبات ریسک بر اساس scope (فاز ۵۳.۲).

    - `backtest`/`forward` → سرمایهٔ فرضی (حساب واقعی ندارد).
    - `real`              → میانگین موجودیِ حساب‌های شخصیِ **ارجاع‌شده در همان دامنه**
                            (در نبودشان → سرمایهٔ فرضی؛ `0` گمراه‌کننده است چون
                            `risk_of_ruin` را ۱۰۰٪ نشان می‌دهد).
    - `all`               → میانگین همهٔ حساب‌ها (fallback: فرضی).
    """
    if scope in ("backtest", "forward"):
        return ASSUMED_BALANCE
    if scope == "real":
        ids = [i for i in (account_ids or []) if i is not None]
        if not ids:
            return ASSUMED_BALANCE
        avg = (
            db.query(func.avg(PersonalTradingAccount.current_balance))
            .filter(PersonalTradingAccount.id.in_(ids))
            .scalar()
        )
        return float(avg) if avg else ASSUMED_BALANCE
    accts = db.query(PersonalTradingAccount).all()
    if not accts:
        return ASSUMED_BALANCE
    return sum(a.current_balance or 0 for a in accts) / len(accts)


ASSUMED_BALANCE = 10000.0


def _scope_initial_balance(db, scope: str, personal_account_ids, prop_stage_ids, currency=None) -> float:
    """Get initial equity for the trade scope, or use the simulation default.

    Personal account balances and prop-stage balances are summed once per
    referenced account/stage. Prop accounts themselves do not store an initial
    balance; their associated trading stage does.
    """
    if scope in ("backtest", "forward"):
        return ASSUMED_BALANCE

    balance = 0.0
    personal_ids = {account_id for account_id in (personal_account_ids or []) if account_id is not None}
    stage_ids = {stage_id for stage_id in (prop_stage_ids or []) if stage_id is not None}

    if personal_ids:
        personal_query = db.query(PersonalTradingAccount).filter(PersonalTradingAccount.id.in_(personal_ids))
        if currency is not None:
            personal_query = personal_query.filter(PersonalTradingAccount.currency == currency)
        balance += sum(float(account.initial_balance or 0.0) for account in personal_query.all())

    if stage_ids:
        prop_query = db.query(PropStage).filter(PropStage.id.in_(stage_ids))
        if currency is not None:
            prop_query = prop_query.join(PropAccount).filter(PropAccount.currency == currency)
        balance += sum(float(stage.initial_balance or 0.0) for stage in prop_query.all())

    return balance if balance > 0 else ASSUMED_BALANCE


def _equity_trade(close_time, net):
    """Adapt the SQL-projected net PnL row to the domain EquityEngine input."""
    return SimpleNamespace(
        close_time=close_time,
        pnl=net,
        commission=0.0,
        swap=0.0,
    )


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
        raise HTTPException(400, detail="نوع تست نامعتبر است (BACKTEST/FORWARD)")
    if tt in (TT.REAL_PERSONAL, TT.REAL_PROP):
        raise HTTPException(400, detail="تحلیل نسخه فقط برای BACKTEST یا FORWARD است؛ REAL از مسیر پراپ/حساب شخصی تحلیل می‌شود")
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


@router.post("/analyze/personal-account/{personal_trading_account_id}")
def analyze_personal_account_endpoint(personal_trading_account_id: int, db: Session = Depends(get_db)):
    """تحلیل کامل یک حساب معاملاتی شخصی — scope=PERSONAL_ACCOUNT"""
    try:
        r = AnalysisService(db).analyze_personal_account(personal_trading_account_id)
        return {"message": r["message"], "analysis_id": r["result"].id,
                "run_id": r["run_id"], "personal_trading_account_id": personal_trading_account_id}
    except ValueError as e:
        raise HTTPException(404, detail=str(e))


@router.get("/dashboard")
def get_dashboard_data(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    scope: str = Query("real", description="real | backtest | forward | all"),
    currency: Currency = Query(Currency.USDT),
    version_id: Optional[int] = Query(None, description="Optional strategy version filter"),
    db: Session = Depends(get_db),
):
    """داده‌های داشبورد — فاز ۱۵.۳: محاسبات در SQL (بدون لود کل جدول)

    فاز ۴۴.۱: پارامتر `scope` (پیش‌فرض `real`) — بک‌تست با نتایج واقعی قاطی نمی‌شود.
    """
    from ..services.prop_rule_engine import PropRuleEngine
    from ..models.prop import PropStage, StageStatus
    from sqlalchemy.orm import joinedload

    sc = normalize_scope(scope)
    df_bound = _parse_bound(date_from)
    dt_bound = _parse_bound(date_to, end=True)
    net = _net_expr()
    is_closed = Trade.close_time.isnot(None)
    win_cond = and_(is_closed, net > 0)
    loss_cond = and_(is_closed, net < 0)
    scoped_q = _scope_filter(db.query(Trade), df_bound, dt_bound, sc, currency)
    if version_id is not None:
        scoped_q = scoped_q.filter(Trade.version_id == version_id)
    closed_scope = scoped_q.filter(is_closed)

    # ── ۱) آمار کلی در یک کوئری (بدون لود ردیف‌ها) ──
    agg = scoped_q.with_entities(
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

    # API contract: win_rate is expressed as a percentage (0-100).
    wr = (wins_n / closed_count * 100) if closed_count else 0
    pf = metrics.profit_factor_from_sums(gp, gl)
    avg_win = (gp / wins_n) if wins_n else 0.0
    avg_loss = (gl / losses_n) if losses_n else 0.0
    win_ratio = (wins_n / closed_count) if closed_count else 0.0
    loss_ratio = (losses_n / closed_count) if closed_count else 0.0
    expectancy = (win_ratio * avg_win) - (loss_ratio * avg_loss)
    avg_r_multiple = closed_scope.with_entities(func.avg(Trade.r_multiple)).scalar()

    # ── ۲) سکانس مرتب برای streak و محاسبه‌های دامنه‌ای equity/drawdown ──
    narrow = (
        closed_scope.with_entities(
            Trade.close_time,
            net.label("net"),
            Trade.id,
            Trade.personal_trading_account_id,
            Trade.prop_stage_id,
        )
        .order_by(Trade.close_time.asc(), Trade.id.asc())
        .all()
    )
    seq = []
    personal_account_ids = set()
    prop_stage_ids = set()
    for _ct, _n, _id, _personal_id, _stage_id in narrow:
        if _ct is not None and _ct.tzinfo is None:
            _ct = _ct.replace(tzinfo=timezone.utc)
        seq.append((_ct, float(_n or 0.0)))
        if _personal_id is not None:
            personal_account_ids.add(_personal_id)
        if _stage_id is not None:
            prop_stage_ids.add(_stage_id)

    initial_balance = _scope_initial_balance(
        db, sc, personal_account_ids, prop_stage_ids, currency
    )
    equity_trades = [_equity_trade(close_time, net_pnl) for close_time, net_pnl in seq]
    equity_points = calculate_equity_curve(initial_balance, equity_trades)
    peak_to_trough = calculate_peak_to_trough_dd(equity_points)
    static_dd = calculate_static_dd(initial_balance, equity_points)
    max_drawdown = max(peak_to_trough["dd"], static_dd["dd"])
    sp = [round(point["equity"] - initial_balance, 2) for point in equity_points[1:]]
    spd = sp[-20:] if len(sp) >= 20 else sp
    max_wins_dash, max_losses_dash = metrics.win_loss_streaks([n for _, n in seq])
    max_consecutive_losses = max_losses_dash
    max_consecutive_wins = max_wins_dash

    now = datetime.now(timezone.utc)
    ts, _ = tehran_day_bounds(now)
    # فاز ۴۴.۱: شمارش معاملات باز نیز تابع scope است
    opn = _apply_scope(db.query(Trade), sc).filter(Trade.close_time.is_(None)).count()
    # The dashboard curve and max_dd now project the same domain equity points.
    equity_curve = [
        {
            "date": point["date"].isoformat() if point["date"] is not None else None,
            "equity": round(point["equity"], 2),
        }
        for point in equity_points
    ]
    md = max_drawdown

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

    # ── فاز ۲۸/۴۴.۴: پول قابل خرج — یک منبع حقیقت مشترک (finance_metrics) ──
    from ..services import finance_metrics
    broker_pnl = finance_metrics.broker_pnl(db, currency)
    broker_balance = finance_metrics.broker_balance(db, currency)
    init_capital = finance_metrics.initial_capital(db, currency)
    funded_pnl = finance_metrics.funded_pnl(db, currency)

    spendable_net = round(broker_pnl + funded_pnl, 2)

    # ── Prop Progress (فاز ۳۶: ارزیابی گروهی ⇒ بدون N+1) ──
    active_stages = db.query(PropStage).options(
        joinedload(PropStage.account).joinedload(PropAccount.firm)
    ).join(PropAccount).filter(
        PropStage.status == StageStatus.ACTIVE,
        PropAccount.currency == currency,
    ).all()
    stage_ids = [s.id for s in active_stages]
    bulk_eval = PropRuleEngine.evaluate_stages(db, stage_ids)
    prop_progress_data = []
    for stage in active_stages:
        result = bulk_eval.get(stage.id) or PropRuleEngine.evaluate_stage(db, stage.id)
        result["stage_name"] = stage.stage_type.value if stage.stage_type else "Unknown"
        result["account_label"] = stage.account.account_label if stage.account else ""
        result["firm_name"] = (
            stage.account.firm.name
            if stage.account and stage.account.firm
            else None
        )
        result["stage_type_icon"] = {
            "stage_1": "🥇",
            "stage_2": "🥈",
            "funded_real": "💰",
        }.get(result["stage_name"], "🏢")
        prop_progress_data.append(result)

    return {
        "currency": currency.value,
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
            "avg_r_multiple": round(float(avg_r_multiple), 4) if avg_r_multiple is not None else 0.0,
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "largest_win": round(largest_win, 2),
            "largest_loss": round(largest_loss, 2),
            "expectancy": round(expectancy, 2),
            "max_consecutive_losses": max_consecutive_losses,
            "max_consecutive_wins": max_consecutive_wins,
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
            # فاز ۴۴.۲: broker_balance خودش شامل broker_pnl است ⇒ اضافه‌کردن دوبارهٔ
            # broker_pnl باعث Double Counting می‌شد.
            "total_balance": round(broker_balance + funded_pnl, 2),
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
def get_yesterday_data(
    scope: str = Query("real", description="real | backtest | forward | all"),
    currency: Currency = Query(Currency.USDT),
    db: Session = Depends(get_db),
):
    """داده‌های عملکرد روز گذشته (بر اساس close_time، UTC) — فاز ۴۴.۱: scope"""
    from ..models.strategy import Trade
    from .finance import _gregorian_to_jalali

    sc = normalize_scope(scope)

    def _ensure_utc(dt):
        if dt is not None and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    today_start, _ = tehran_day_bounds()
    y_start, y_end = tehran_day_bounds(today_start - timedelta(microseconds=1))

    yt = []
    _yq = _scope_filter(db.query(Trade), None, None, sc, currency).filter(Trade.close_time != None)
    for t in _yq.all():
        ct = _ensure_utc(t.close_time)
        if ct is not None and y_start <= ct < y_end:
            t.close_time = ct
            yt.append(t)

    # تفکیک منبع بر اساس دامنهٔ معامله (فاز ۲۸) — فاز ۳۸.۵: کلیدها با قرارداد فاز ۲۷ هم‌نام شدند
    #   prop       → REAL_PROP
    #   personal   → REAL_PERSONAL   (قبلاً به‌اشتباه «broker» بود؛ حساب معاملاتی شخصی روی بروکر)
    #   simulation → BACKTEST / FORWARD  (بدون دامنهٔ واقعی؛ قبلاً «personal»)
    def classify(t):
        if t.prop_stage_id:
            return "prop"
        if t.personal_trading_account_id:
            return "personal"
        return "simulation"

    by_source = {
        "prop": {"trades": 0, "winning": 0, "losing": 0, "pnl": 0.0},
        "personal": {"trades": 0, "winning": 0, "losing": 0, "pnl": 0.0},
        "simulation": {"trades": 0, "winning": 0, "losing": 0, "pnl": 0.0},
    }
    winning = losing = 0
    net_total = 0.0
    for t in yt:
        p = metrics.net_pnl(t)
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
        "currency": currency.value,
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
def get_risk_metrics(
    scope: str = Query("real", description="real | backtest | forward | all"),
    db: Session = Depends(get_db),
):
    """محاسبه شاخص‌های مدیریت ریسک — فاز ۱۵.۳: SQL + واکشی ستونی · فاز ۴۴.۱: scope · فاز ۵۳.۲: بازده روزانه + مبنای scope"""
    sc = normalize_scope(scope)

    # فاز ۱۵.۳: فقط ستون‌های لازم، به ترتیب id (معادل ترتیب قبلی .all())
    _net = _net_expr()
    _rows = (
        _apply_scope(db.query(Trade).filter(Trade.close_time.isnot(None)), sc)
        .with_entities(
            Trade.close_time, _net.label("net"), Trade.r_multiple,
            Trade.personal_trading_account_id, Trade.prop_stage_id,
        )
        .order_by(Trade.close_time.asc(), Trade.id.asc())
        .all()
    )
    closed_trades = []
    personal_account_ids = set()
    prop_stage_ids = set()
    for _ct, _n, _r, _personal_id, _stage_id in _rows:
        if _ct is not None and _ct.tzinfo is None:
            _ct = _ct.replace(tzinfo=timezone.utc)
        closed_trades.append({"close_time": _ct, "net": float(_n or 0.0), "r_multiple": _r})
        if _personal_id is not None:
            personal_account_ids.add(_personal_id)
        if _stage_id is not None:
            prop_stage_ids.add(_stage_id)
    returns = [c["net"] for c in closed_trades]
    initial_balance = _scope_initial_balance(
        db, sc, personal_account_ids, prop_stage_ids
    )
    equity_trades = [_equity_trade(c["close_time"], c["net"]) for c in closed_trades]
    equity_points = calculate_equity_curve(initial_balance, equity_trades)
    peak_to_trough = calculate_peak_to_trough_dd(equity_points)
    static_dd = calculate_static_dd(initial_balance, equity_points)
    drawdown_duration = calculate_drawdown_duration(equity_points)
    # Preserve the response's existing duration-in-trades unit. The domain
    # engine determines the longest underwater interval; count its underwater
    # trade points (excluding the recovery point) for the legacy API field.
    drawdown_trade_count = 0
    if drawdown_duration["start_date"] is not None:
        point_drawdowns = calculate_drawdown_curve(equity_points)
        drawdown_trade_count = sum(
            point["date"] is not None
            and drawdown_duration["start_date"] <= point["date"] <= drawdown_duration["end_date"]
            and drawdown["drawdown"] > 0
            for point, drawdown in zip(equity_points, point_drawdowns)
        )
    # فاز ۵۳.۲: مبنای سرمایه برای risk of ruin و open risk بر اساس scope
    avg_b = _scope_avg_balance(db, sc, personal_account_ids)
    r_multiples = [c["r_multiple"] for c in closed_trades]
    expectancy_r = calculate_expectancy_r(r_multiples)
    ar = (sum(returns) / len(returns)) if returns else 0   # میانگین هر معامله (مبنای expectancy)
    # Return-based Sharpe/Sortino on daily PnL divided by opening equity.
    daily_returns = RiskEngine._daily_returns_from_trades(closed_trades, initial_balance)
    sharpe = RiskEngine._sharpe(daily_returns)
    sortino = RiskEngine._sortino(daily_returns)
    wins = [r for r in returns if r > 0]; losses = [r for r in returns if r < 0]
    # API contract: win_rate is expressed as a percentage (0-100).
    wr = len(wins) / len(returns) * 100 if returns else 0
    aw = sum(wins) / len(wins) if wins else 0
    al = abs(sum(losses) / len(losses)) if losses else 0
    rr = (aw / al) if al > 0 else 1
    valid_r = [r for r in r_multiples if r is not None]
    r_wins = [r for r in valid_r if r > 0]
    r_losses = [r for r in valid_r if r < 0]
    r_outcomes = len(r_wins) + len(r_losses)
    r_win_rate = len(r_wins) / r_outcomes if r_outcomes else 0.0
    avg_win_r = sum(r_wins) / len(r_wins) if r_wins else 0.0
    avg_loss_r = abs(sum(r_losses) / len(r_losses)) if r_losses else 0.0
    ror = (
        calculate_risk_of_ruin(r_win_rate, avg_win_r, avg_loss_r, 0.01)
        if r_outcomes >= 2 else None
    )
    arm = expectancy_r
    sorted_ret = sorted(returns)
    var_95_threshold = _percentile(sorted_ret, 0.05)
    var_95_dollar = max(0.0, -var_95_threshold)
    tail_losses = [r for r in sorted_ret if r <= var_95_threshold]
    cvar_95_dollar = max(
        0.0, -sum(tail_losses) / len(tail_losses)
    ) if tail_losses else var_95_dollar
    var_95_percent = var_95_dollar / initial_balance * 100 if initial_balance > 0 else 0.0
    cvar_95_percent = cvar_95_dollar / initial_balance * 100 if initial_balance > 0 else 0.0
    oe = float(_apply_scope(
        db.query(func.sum(func.abs(_net_expr()))).filter(Trade.close_time.is_(None)), sc
    ).scalar() or 0.0)
    orp = (oe / avg_b * 100) if avg_b > 0 else 0
    # ── برد/باخت متوالی ──
    mw, ml = metrics.win_loss_streaks(returns)
    dd_d = max(peak_to_trough["dd"], static_dd["dd"])
    md = drawdown_trade_count
    status = "danger" if (sharpe < 0.5 or (ror is not None and ror > 0.1) or orp > 20) else ("warning" if (sharpe < 1.0 or (ror is not None and ror > 0.05) or orp > 10) else "safe")
    return {"performance_ratios": {"sharpe_ratio": round(sharpe, 2), "sortino_ratio": round(sortino, 2),
            "profit_factor": round(metrics.profit_factor_from_sums(sum(wins), abs(sum(losses))), 2),
            "win_rate": round(wr, 2), "avg_r_multiple": round(arm, 2),
            "expectancy": round((ar) if returns else 0, 2), "expectancy_r": round(expectancy_r, 2),
            "avg_win": round(aw, 2), "avg_loss": round(al, 2), "rr_ratio": round(rr, 2)},
        "risk_metrics": {"risk_of_ruin": round(ror, 4) if ror is not None else None,
            "var_95": round(var_95_dollar, 2), "var_95_percent": round(var_95_percent, 4),
            "cvar_95": round(cvar_95_dollar, 2), "cvar_95_percent": round(cvar_95_percent, 4),
            "max_consecutive_losses": ml, "max_consecutive_wins": mw,
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


def calculate_risk_of_ruin(
    win_rate: float,
    avg_win_r: float,
    avg_loss_r: float,
    risk_per_trade: float,
    ruin_threshold: float = 0.5,
) -> float | None:
    """Estimate risk of losing ``ruin_threshold`` of equity using R-multiples.

    Returns ``None`` when the inputs do not describe a meaningful two-outcome
    strategy. ``risk_per_trade`` and ``ruin_threshold`` are equity fractions.
    """
    values = (win_rate, avg_win_r, avg_loss_r, risk_per_trade, ruin_threshold)
    if not all(isinstance(value, (int, float)) for value in values):
        return None
    if not all(math.isfinite(value) for value in values):
        return None
    if not 0.0 <= win_rate <= 1.0 or avg_win_r < 0 or avg_loss_r < 0:
        return None
    if risk_per_trade <= 0 or risk_per_trade >= 1.0 or not 0.0 < ruin_threshold < 1.0:
        return None
    if win_rate == 1.0 and avg_win_r > 0:
        return 0.0
    if win_rate == 0.0 and avg_loss_r > 0:
        return 1.0
    if avg_win_r <= 0 or avg_loss_r <= 0:
        return None

    loss_probability = 1.0 - win_rate
    win_probability = win_rate
    odds = (win_probability * avg_win_r) / (loss_probability * avg_loss_r)
    if odds <= 1.0:
        return 1.0

    # Classical gambler's-ruin approximation: odds against recovery raised to
    # the number of fixed-risk units between current equity and the ruin floor.
    units_to_ruin = math.log(ruin_threshold) / math.log1p(-risk_per_trade)
    return min(1.0, (1.0 / odds) ** units_to_ruin)


@router.get("/risk-advanced")
def get_risk_advanced(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    scope: str = Query("real", description="real | backtest | forward | all"),
    currency: Currency = Query(Currency.USDT),
    db: Session = Depends(get_db),
):
    """آمار ریسک پیشرفته (شارپ، سورتینو، کالمار، VaR/CVaR، کِلی، Ulcer، ...) — فاز ۴۴.۱: scope · فاز ۵۳.۲: بازده روزانه + مبنای scope"""
    sc = normalize_scope(scope)
    df_bound = _parse_bound(date_from)
    dt_bound = _parse_bound(date_to, end=True)

    # فاز ۱۵.۳: فیلتر بازه در SQL + واکشی فقط ستون‌های لازم (بدون لود ORM)
    _net = _net_expr()
    _rows = (
        _scope_filter(db.query(Trade), df_bound, dt_bound, sc, currency)
        .filter(Trade.close_time.isnot(None))
        .with_entities(
            Trade.close_time, _net.label("net"), Trade.r_multiple,
            Trade.personal_trading_account_id, Trade.prop_stage_id,
        )
        .order_by(Trade.close_time.asc(), Trade.id.asc())
        .all()
    )
    closed = []
    personal_account_ids = set()
    prop_stage_ids = set()
    for _ct, _n, _r, _personal_id, _stage_id in _rows:
        if _ct is not None and _ct.tzinfo is None:
            _ct = _ct.replace(tzinfo=timezone.utc)
        closed.append({"close_time": _ct, "net": float(_n or 0.0), "r_multiple": _r})
        if _personal_id is not None:
            personal_account_ids.add(_personal_id)
        if _stage_id is not None:
            prop_stage_ids.add(_stage_id)

    returns = [c["net"] for c in closed]
    total = len(returns)

    # ── پایه ──
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]
    # API contract: win_rate is expressed as a percentage (0-100).
    wr = (len(wins) / total * 100) if total else 0.0
    win_rate_fraction = wr / 100
    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (abs(sum(losses) / len(losses))) if losses else 0.0
    rr = (avg_win / avg_loss) if avg_loss > 0 else 0.0
    net = sum(returns)
    # ── Equity / Drawdown / Ulcer ──
    initial_balance = _scope_initial_balance(
        db, sc, personal_account_ids, prop_stage_ids, currency
    )
    daily_returns = RiskEngine._daily_returns_from_trades(closed, initial_balance)
    sharpe = RiskEngine._sharpe(daily_returns)
    sortino = RiskEngine._sortino(daily_returns)
    equity_trades = [_equity_trade(c["close_time"], c["net"]) for c in closed]
    equity_points = calculate_equity_curve(initial_balance, equity_trades)
    peak_to_trough = calculate_peak_to_trough_dd(equity_points)
    static_dd = calculate_static_dd(initial_balance, equity_points)
    max_dd = max(peak_to_trough["dd"], static_dd["dd"])
    ulcer_acc = 0.0
    drawdown_curve = []
    point_drawdowns = calculate_drawdown_curve(equity_points)
    for idx, (point, drawdown) in enumerate(zip(equity_points[1:], point_drawdowns[1:])):
        dd_abs = drawdown["drawdown"]
        dd_pct = drawdown["drawdown_pct"]
        ulcer_acc += dd_pct ** 2
        drawdown_curve.append({
            "index": idx + 1,
            "date": point["date"].date().isoformat(),
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
    var_95_threshold = _percentile(sorted_ret, 0.05)
    var_95_dollar = max(0.0, -var_95_threshold)
    tail_losses = [r for r in sorted_ret if r <= var_95_threshold]
    cvar_95_dollar = (
        max(0.0, -sum(tail_losses) / len(tail_losses)) if tail_losses else var_95_dollar
    )
    var_95_percent = var_95_dollar / initial_balance * 100 if initial_balance > 0 else 0.0
    cvar_95_percent = cvar_95_dollar / initial_balance * 100 if initial_balance > 0 else 0.0

    # ── برد/باخت متوالی ──
    # ── برد/باخت متوالی ──
    max_cw, max_cl = metrics.win_loss_streaks(returns)

    # ── R-Multiple ──
    r_multiples = [c["r_multiple"] for c in closed]
    valid_r = [r for r in r_multiples if r is not None]
    expectancy_r = calculate_expectancy_r(r_multiples)
    avg_r = expectancy_r

    # ── Kelly Criterion ──
    if rr <= 0:
        kelly = win_rate_fraction if win_rate_fraction > 0 else 0.0
    else:
        kelly = win_rate_fraction - ((1 - win_rate_fraction) / rr)

    # ── Risk of Ruin from valid R outcomes (1% assumed risk per trade) ──
    r_wins = [r for r in valid_r if r > 0]
    r_losses = [r for r in valid_r if r < 0]
    r_outcomes = len(r_wins) + len(r_losses)
    r_win_rate = len(r_wins) / r_outcomes if r_outcomes else 0.0
    avg_win_r = sum(r_wins) / len(r_wins) if r_wins else 0.0
    avg_loss_r = abs(sum(r_losses) / len(r_losses)) if r_losses else 0.0
    ror = (
        calculate_risk_of_ruin(r_win_rate, avg_win_r, avg_loss_r, 0.01)
        if r_outcomes >= 2 else None
    )

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
        {"range": label, "count": sum(1 for v in valid_r if fn(v))}
        for label, fn in _buckets
    ]

    return {
        "has_enough_data": total >= 2,
        "total_trades": total,
        "win_rate": round(wr, 2),
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "calmar_ratio": round(calmar, 3),
        "risk_of_ruin": round(ror, 4) if ror is not None else None,
        "var_95": round(var_95_dollar, 2),
        "var_95_percent": round(var_95_percent, 4),
        "cvar_95": round(cvar_95_dollar, 2),
        "cvar_95_percent": round(cvar_95_percent, 4),
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
    scope: str = Query("real", description="real | backtest | forward | all"),
    db: Session = Depends(get_db),
):
    """Get trades grouped by day for calendar view — فاز ۴۴.۱: scope"""
    sc = normalize_scope(scope)
    query = _apply_scope(db.query(Trade).filter(
        Trade.close_time.isnot(None)
    ), sc)

    # ── اگر سال و ماه شمسی داده شده ──
    if year is not None and month is not None:
        gy_start, gm_start, gd_start = jalali.jalali_to_gregorian_parts(year, month, 1)
        if month < 12:
            gy_end, gm_end, gd_end = jalali.jalali_to_gregorian_parts(year, month + 1, 1)
        else:
            gy_end, gm_end, gd_end = jalali.jalali_to_gregorian_parts(year + 1, 1, 1)
        # فاز ۴۶.۴: مرزهای ماه شمسی بر پایهٔ نیمه‌شب تهران
        dt_from = datetime(gy_start, gm_start, gd_start, tzinfo=TEHRAN).astimezone(timezone.utc)
        dt_to = datetime(gy_end, gm_end, gd_end, tzinfo=TEHRAN).astimezone(timezone.utc)
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
        # فاز ۴۶.۴: روز بر پایهٔ وقت تهران (نه UTC)
        day_key = to_tehran(_ct).strftime("%Y-%m-%d") if _ct else None
        days[day_key].append((_id, _sym, _dir, _size, _pnl, _ct, float(_netv or 0.0)))

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
    """تبدیل تاریخ شمسی به میلادی (بازگشت: (year, month, day)) — فاز ۴۶.۳: ابزار مشترک."""
    return jalali.jalali_to_gregorian_parts(jy, jm, jd)
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


@router.get("/analysis/personal-account/{personal_trading_account_id}")
def get_analysis_personal_account(personal_trading_account_id: int, db: Session = Depends(get_db)):
    """دریافت تحلیل یک حساب معاملاتی شخصی — scope=PERSONAL_ACCOUNT"""
    result = db.query(AnalysisResult).filter(
        AnalysisResult.scope == AnalysisScope.PERSONAL_ACCOUNT,
        AnalysisResult.scope_key == str(personal_trading_account_id),
    ).first()
    if not result:
        raise HTTPException(404, detail="تحلیلی برای این حساب معاملاتی یافت نشد.")
    _guard_analyzable(db, personal_trading_account_id=personal_trading_account_id, result=result)
    return _analysis_response(result)


def _as_naive(dt):
    """حذف `tzinfo` برای مقایسهٔ ایمن بین datetime آگاه و ناوابسته (SQLite).

    مقادیر در DB معمولاً UTC هستند؛ پس حذف tzinfo امن است و از خطای
    «can't compare offset-naive and offset-aware datetimes» جلوگیری می‌کند.
    """
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if getattr(dt, "tzinfo", None) is not None else dt


def _guard_analyzable(db, result, version_id=None, prop_stage_id=None, personal_trading_account_id=None, test_type=None):
    """گارد سازگاری فاز ۱۹/۲۳ — تحلیل کهنه سرو نشود (فاز ۲۳: به تفکیک test_type؛ فاز ۵۳.۱: updated_at)."""
    from ..models.strategy import Trade
    q = db.query(Trade)
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
    elif personal_trading_account_id is not None:
        q = q.filter(Trade.personal_trading_account_id == personal_trading_account_id)
        scope_label = "این حساب معاملاتی شخصی"
    count = q.count()
    if count == 0:
        raise HTTPException(404, detail=f"هیچ معامله‌ای برای {scope_label} یافت نشد.")
    if result.total_trades != count:
        raise HTTPException(404, detail=f"تحلیل کهنه است ({result.total_trades} در برابر {count} معامله). دوباره تحلیل کنید.")

    # فاز ۵۳.۱: تحلیل کهنه بر پایهٔ آخرین ویرایش معاملات (نه فقط تعداد).
    # اگر سود/حدضرر/زمان معامله‌ای پس از ثبت تحلیل تغییر کرده باشد، تحلیل کهنه است.
    max_updated = q.with_entities(func.max(Trade.updated_at)).scalar()
    if max_updated is not None and result.created_at is not None:
        if _as_naive(result.created_at) < _as_naive(max_updated):
            raise HTTPException(
                404,
                detail="تحلیل کهنه است (معاملات پس از تحلیل ویرایش شده‌اند). دوباره تحلیل کنید.",
            )


def _analysis_response(result):
    """تبدیل AnalysisResult به دیکشنری پاسخ"""
    return {
        "version_id": result.version_id,
        "prop_stage_id": result.prop_stage_id,
        "personal_trading_account_id": result.personal_trading_account_id,
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


def _tt_from_scope_key(version_id: int, scope_key: str):
    """استخراج `test_type` از کلید دامنه («12:BACKTEST» ⇒ BACKTEST)."""
    prefix = f"{version_id}:"
    if scope_key and scope_key.startswith(prefix):
        try:
            return TestType(scope_key[len(prefix):].strip().lower())
        except ValueError:
            return None
    return None


@router.get("/{version_id}")
def get_analysis(
    version_id: int,
    test_type: Optional[str] = "BACKTEST",
    db: Session = Depends(get_db),
):
    """دریافت تحلیل ذخیره‌شده‌ی یک نسخه — فاز 48a.2.

    `test_type` (پیش‌فرض BACKTEST) کلید دامنه را قطعی می‌کند (قبلاً `.first()`
    روی `version_id` بین Backtest/Forward نتیجه‌ی نامعین می‌داد). در نبود رکورد
    scoped، به جدیدترین تحلیل همان نسخه (legacy یا نوع دیگر) برمی‌گردد.
    """
    tt = None
    if test_type:
        try:
            tt = TestType(str(test_type).strip().lower())
        except ValueError:
            tt = None

    result = None
    if tt is not None:
        result = db.query(AnalysisResult).filter(
            AnalysisResult.scope == AnalysisScope.VERSION,
            AnalysisResult.scope_key == version_scope_key(version_id, tt),
        ).first()

    if result is None:
        # fallback قطعی: جدیدترین تحلیل همین نسخه
        result = (
            db.query(AnalysisResult)
            .filter(
                AnalysisResult.scope == AnalysisScope.VERSION,
                AnalysisResult.version_id == version_id,
            )
            .order_by(AnalysisResult.id.desc())
            .first()
        )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="تحلیلی برای این نسخه یافت نشد. ابتدا POST /analyze/{version_id} را اجرا کنید."
        )

    # ── گارد سازگاری (فاز ۱۹ / 48a.2) — شمارش هم‌نوع با رکورد سرو‌شده ──
    eff_tt = _tt_from_scope_key(version_id, result.scope_key)
    count_q = db.query(Trade).filter(
        Trade.version_id == version_id, analysis_trades_filter()
    )
    if eff_tt is not None:
        count_q = count_q.filter(Trade.test_type == eff_tt)
    analyzable_trades = count_q.count()

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

    # فاز ۵۳.۱: تحلیل کهنه بر پایهٔ آخرین ویرایش معاملات (نه فقط تعداد).
    # اگر سود/حدضرر/زمان معامله‌ای پس از ثبت تحلیل تغییر کرده باشد، تحلیل کهنه است.
    max_updated = count_q.with_entities(func.max(Trade.updated_at)).scalar()
    if max_updated is not None and result.created_at is not None:
        if _as_naive(result.created_at) < _as_naive(max_updated):
            raise HTTPException(
                status_code=404,
                detail="تحلیل ذخیره‌شده کهنه است (معاملات پس از تحلیل ویرایش شده‌اند). "
                       "دوباره «تحلیل مجدد» را بزنید.",
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


@router.post("/compare")
def compare_versions_endpoint(data: CompareRequest, db: Session = Depends(get_db)):
    """مقایسهٔ چند نسخه + فیلتر (نماد/تاریخ) + Score/Rank — فاز 48a.

    قرارداد جدید: `{comparison, test_type, filters, best}`.
    نسخهٔ تحلیل‌نشده با فیلد `error` گزارش می‌شود.
    """
    return compare_versions(
        version_ids=data.version_ids,
        test_type=data.test_type,
        symbol=data.symbol,
        date_from=data.date_from,
        date_to=data.date_to,
        db=db,
    )


@router.post("/rank")
def rank_versions(data: CompareRequest, db: Session = Depends(get_db)):
    """رتبه‌بندی Versionها بر پایهٔ Score — فاز 48a.5.

    خروجی: `{ranking: [...], best: {...}}` (مرتب‌شده نزولی بر اساس Score).
    """
    result = compare_versions(
        version_ids=data.version_ids,
        test_type=data.test_type,
        symbol=data.symbol,
        date_from=data.date_from,
        date_to=data.date_to,
        db=db,
    )
    return {
        "ranking": result["comparison"],
        "best": result["best"],
    }


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
# Seed (وارد کردن داده‌های اولیه پورصمدی)
# ═════════════════════════════════════════════
_POURSAMADI_GOLD = [
    {"symbol": "XAUUSD", "start_hour": 10, "start_minute": 30,
     "end_hour": 13, "end_minute": 30, "label": "A", "priority": 1},
    {"symbol": "XAUUSD", "start_hour": 16, "start_minute": 0,
     "end_hour": 17, "end_minute": 0, "label": "A", "priority": 1},
    {"symbol": "XAUUSD", "start_hour": 17, "start_minute": 0,
     "end_hour": 18, "end_minute": 30, "label": "A", "priority": 1},
]

_POURSAMADI_DJI = [
    {"symbol": "DJIUSD", "start_hour": 17, "start_minute": 0,
     "end_hour": 18, "end_minute": 30, "label": "A", "priority": 1},
    {"symbol": "DJIUSD", "start_hour": 18, "start_minute": 30,
     "end_hour": 21, "end_minute": 30, "label": "B", "priority": 2},
    {"symbol": "DJIUSD", "start_hour": 21, "start_minute": 30,
     "end_hour": 23, "end_minute": 30, "label": "C", "priority": 3},
]

_POURSAMADI_EUR = [
    {"symbol": "EURUSD", "start_hour": 10, "start_minute": 30,
     "end_hour": 13, "end_minute": 30, "label": "A", "priority": 1},
    {"symbol": "EURUSD", "start_hour": 16, "start_minute": 0,
     "end_hour": 17, "end_minute": 0, "label": "A", "priority": 1},
    {"symbol": "EURUSD", "start_hour": 17, "start_minute": 0,
     "end_hour": 18, "end_minute": 30, "label": "A", "priority": 1},
]

_POURSAMADI_NAMES = {
    ("XAUUSD", 0): "طلا — A1",
    ("XAUUSD", 1): "طلا — A2",
    ("XAUUSD", 2): "طلا — A3",
    ("DJIUSD", 0): "داو — A1",
    ("DJIUSD", 1): "داو — B1",
    ("DJIUSD", 2): "داو — C1",
    ("EURUSD", 0): "یورو — A1",
    ("EURUSD", 1): "یورو — A2",
    ("EURUSD", 2): "یورو — A3",
}


def _seed_intervals(db: Session, intervals: list, name_map: dict) -> list[str]:
    """Seed intervals idempotently. Returns names of newly created intervals."""
    created = []
    for idx, data in enumerate(intervals):
        name = name_map.get((data["symbol"], idx), data["symbol"])
        existing = db.query(CustomTimeInterval).filter(
            CustomTimeInterval.name == name,
            CustomTimeInterval.symbol == data["symbol"],
        ).first()
        if existing:
            continue
        db_interval = CustomTimeInterval(
            name=name, symbol=data["symbol"],
            start_hour=data["start_hour"], start_minute=data["start_minute"],
            end_hour=data["end_hour"], end_minute=data["end_minute"],
            label=data["label"], priority=data["priority"],
        )
        db.add(db_interval)
        created.append(name)
    db.commit()
    return created


@router.post("/intervals/seed-gold")
def seed_gold_intervals(db: Session = Depends(get_db)):
    """وارد کردن بازه‌های طلا (پورصمدی)"""
    created = _seed_intervals(db, _POURSAMADI_GOLD, _POURSAMADI_NAMES)
    return {"message": f"{len(created)} بازه طلا اضافه شد", "created": created}


@router.post("/intervals/seed-dji")
def seed_dji_intervals(db: Session = Depends(get_db)):
    """وارد کردن بازه‌های داوجونز (پورصمدی)"""
    created = _seed_intervals(db, _POURSAMADI_DJI, _POURSAMADI_NAMES)
    return {"message": f"{len(created)} بازه داو اضافه شد", "created": created}


@router.post("/intervals/seed-poursamadi")
def seed_poursamadi_intervals(db: Session = Depends(get_db)):
    """وارد کردن همهٔ بازه‌های پورصمدی (طلا + داو + یورو)"""
    created = []
    for intervals in (_POURSAMADI_GOLD, _POURSAMADI_DJI, _POURSAMADI_EUR):
        created.extend(_seed_intervals(db, intervals, _POURSAMADI_NAMES))
    return {"message": f"{len(created)} بازه پورصمدی اضافه شد", "created": created}


@router.get("/intervals/seed-status")
def get_seed_status(db: Session = Depends(get_db)):
    """وضعیت بازه‌های پورصمدی — آیا همهٔ ۹ بازه وجود دارند؟"""
    all_poursamadi = list(_POURSAMADI_NAMES.keys())
    by_symbol: dict[str, int] = {}
    total_found = 0
    for sym, idx in all_poursamadi:
        name = _POURSAMADI_NAMES[(sym, idx)]
        exists = db.query(CustomTimeInterval.id).filter(
            CustomTimeInterval.name == name,
            CustomTimeInterval.symbol == sym,
        ).first()
        if exists:
            by_symbol[sym] = by_symbol.get(sym, 0) + 1
            total_found += 1
    poursamadi_seeded = total_found == len(all_poursamadi)
    return {
        "poursamadi_seeded": poursamadi_seeded,
        "total_intervals": total_found,
        "by_symbol": by_symbol,
    }
