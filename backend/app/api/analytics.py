from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timezone
from collections import defaultdict

from ..core.database import get_db
from ..services.analysis_service import AnalysisService
from ..models.strategy import AnalysisResult, AnalysisRun, CustomTimeInterval
from ..schemas.analytics import (
    CustomTimeIntervalCreate,
    CustomTimeIntervalResponse,
    VersionComparisonRequest,
    VersionComparisonResponse,
)

router = APIRouter()


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


@router.get("/dashboard")
def get_dashboard_data(db: Session = Depends(get_db)):
    """داده‌های مورد نیاز برای صفحه داشبورد"""
    from ..models.strategy import Trade
    from ..services.prop_rule_engine import PropRuleEngine
    from ..models.prop import PropStage, StageStatus

    def _ensure_utc(dt):
        """اگر datetime بدون timezone باشد، آن را UTC در نظر بگیر (سازگاری با داده‌های قدیمی)"""
        if dt is not None and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    all_trades = db.query(Trade).all()
    # استانداردسازی datetime داده‌های قدیمی (که ممکن است naive ذخیره شده باشند)
    for _t in all_trades:
        _t.close_time = _ensure_utc(_t.close_time)
        _t.open_time = _ensure_utc(_t.open_time)

    closed_trades = [t for t in all_trades if t.close_time is not None]
    def net_pnl(t): return (t.pnl or 0) + (t.commission or 0) + (t.swap or 0)
    tnp = sum(net_pnl(t) for t in all_trades)
    wins = [t for t in closed_trades if net_pnl(t) > 0]
    losses = [t for t in closed_trades if net_pnl(t) < 0]
    wr = (len(wins) / len(closed_trades) * 100) if closed_trades else 0
    gp = sum(net_pnl(t) for t in wins) if wins else 0
    gl = abs(sum(net_pnl(t) for t in losses)) if losses else 0
    pf = (gp / gl) if gl > 0 else (100.0 if gp > 0 else 0.0)
    st = sorted(closed_trades, key=lambda t: t.close_time)
    eq = 0; pk = 0; md = 0; sp = []
    for t in st:
        eq += net_pnl(t)
        if eq > pk: pk = eq
        d = pk - eq
        if d > md: md = d
        sp.append(round(eq, 2))
    now = datetime.now(timezone.utc)
    ts = now.replace(hour=0, minute=0, second=0, microsecond=0)
    td_t = [t for t in closed_trades if t.close_time >= ts]
    tdp = sum(net_pnl(t) for t in td_t)
    opn = db.query(Trade).filter(Trade.close_time == None).count()
    spd = sp[-20:] if len(sp) >= 20 else sp
    cm = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mp = sum(net_pnl(t) for t in closed_trades if t.close_time >= cm)
    qm = ((now.month - 1) // 3) * 3 + 1
    cq = now.replace(month=qm, day=1, hour=0, minute=0, second=0, microsecond=0)
    qp = sum(net_pnl(t) for t in closed_trades if t.close_time >= cq)
    ys = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    yp = sum(net_pnl(t) for t in closed_trades if t.close_time >= ys)
    pms = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if pms.month == 1: pms = pms.replace(year=pms.year - 1, month=12)
    else: pms = pms.replace(month=pms.month - 1)
    pv = sum(net_pnl(t) for t in closed_trades if pms <= t.close_time < cm)
    mcp = ((mp - pv) / abs(pv) * 100) if pv != 0 else (100 if mp > 0 else -100 if mp < 0 else 0)

    # ── Today ──
    today_wins = [t for t in td_t if net_pnl(t) > 0]
    today_wr = (len(today_wins) / len(td_t) * 100) if td_t else 0

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
        },
        "today": {
            "pnl": round(tdp, 2),
            "trades_count": len(td_t),
            "win_rate": round(today_wr, 2),
        },
        "sparkline": spd,
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


@router.get("/risk-metrics")
def get_risk_metrics(db: Session = Depends(get_db)):
    """محاسبه شاخص‌های مدیریت ریسک"""
    import math
    from ..models.strategy import Trade
    from ..models.finance import Account as FinanceAccount, AccountType
    all_trades = db.query(Trade).all()
    # استانداردسازی datetime داده‌های قدیمی (که ممکن است naive ذخیره شده باشند)
    for _t in all_trades:
        if _t.close_time is not None and _t.close_time.tzinfo is None:
            _t.close_time = _t.close_time.replace(tzinfo=timezone.utc)
    closed_trades = [t for t in all_trades if t.close_time is not None]
    open_trades = [t for t in all_trades if t.close_time is None]
    def net_pnl(t): return (t.pnl or 0) + (t.commission or 0) + (t.swap or 0)
    returns = [net_pnl(t) for t in closed_trades]
    accts = db.query(FinanceAccount).filter(FinanceAccount.type == AccountType.BROKER).all()
    avg_b = sum(a.balance or 0 for a in accts) / len(accts) if accts else 10000
    ps = []
    for rp in [1, 2, 3]:
        ra = avg_b * rp / 100
        st = [t for t in closed_trades if t.sl and t.open_price and t.sl > 0]
        asp = sum(abs((t.sl - t.open_price) / t.open_price) * 100 for t in st) / len(st) if st else 0
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
    rv = [t.r_multiple for t in closed_trades if t.r_multiple and t.r_multiple != 0]
    arm = sum(rv) / len(rv) if rv else 0
    oe = sum(abs(t.pnl or 0) for t in open_trades)
    orp = (oe / avg_b * 100) if avg_b > 0 else 0
    streak = 0; ms = 0
    for r in returns:
        if r < 0: streak += 1; ms = max(ms, streak)
        elif r > 0: streak = 0
    eq = 0; pk = 0; dd_d = 0; md = 0; cd = 0
    for t in sorted(closed_trades, key=lambda t: t.close_time):
        eq += net_pnl(t)
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
    from ..models.strategy import Trade

    now = datetime.now(timezone.utc)
    query = db.query(Trade).filter(Trade.close_time.isnot(None))

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

    trades = query.order_by(Trade.close_time).all()

    days = defaultdict(list)
    for t in trades:
        day_key = t.close_time.strftime("%Y-%m-%d")
        days[day_key].append(t)

    result = []
    for day_key, day_trades in sorted(days.items()):
        pnl = sum((t.pnl or 0) + (t.commission or 0) + (t.swap or 0) for t in day_trades)
        wins = sum(1 for t in day_trades if (t.pnl or 0) + (t.commission or 0) + (t.swap or 0) > 0)
        total = len(day_trades)
        result.append({
            "date": day_key,
            "trade_count": total,
            "total_pnl": round(pnl, 2),
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            "trades": [
                {
                    "id": t.id,
                    "symbol": t.symbol,
                    "direction": t.direction,
                    "size": t.size,
                    "pnl": round(t.pnl, 2) if t.pnl else 0,
                    "close_time": t.close_time.isoformat() if t.close_time else None,
                }
                for t in day_trades
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
@router.get("/{version_id}")
def get_analysis(version_id: int, db: Session = Depends(get_db)):
    """دریافت آخرین تحلیل ذخیره‌شده‌ی یک نسخه"""
    result = db.query(AnalysisResult).filter(
        AnalysisResult.version_id == version_id
    ).first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="تحلیلی برای این نسخه یافت نشد. ابتدا POST /analyze/{version_id} را اجرا کنید."
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
