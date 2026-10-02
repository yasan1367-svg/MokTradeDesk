from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import case, func
from typing import List, Optional
from pydantic import BaseModel
from math import sqrt
from datetime import date

from ..core.database import get_db
from ..models.strategy import Strategy, StrategyVersion, Trade, StrategyStatus, TestType, AnalysisResult
from ..utils.enums import enum_value
from ..utils.trade_scope import analysis_trades_filter
from ..utils.date_range import filter_by_range
from ..services import metrics

router = APIRouter()


def _net_expr():
    """عبارت SQL سود/زیان خالص — فاز ۴۳: از تعریف واحد `metrics.net_pnl_sql()`"""
    return metrics.net_pnl_sql()


def _trades_count_by_version(db: Session, version_ids: List[int]) -> dict:
    """شمارش معاملات هر نسخه در یک کوئری گروهی (رفع N+1 — فاز ۱۵.۲)"""
    if not version_ids:
        return {}
    rows = (
        db.query(Trade.version_id, func.count(Trade.id))
        .filter(Trade.version_id.in_(version_ids), Trade.is_deleted == False)
        .group_by(Trade.version_id)
        .all()
    )
    return {version_id: count for version_id, count in rows}


# ═════════════════════════════════════════════
# Schemas
# ═════════════════════════════════════════════
class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class VersionCreate(BaseModel):
    version_name: str
    rules_note: Optional[str] = None
    test_type: Optional[str] = None          # فاز 24: BACKTEST / FORWARD / REAL
    status: Optional[str] = None             # فاز 24: وضعیت نسخه


class ForkRequest(BaseModel):
    """فاز 24: بدنهٔ درخواست Fork - همه فیلدها اختیاری"""
    version_name: Optional[str] = None
    rules_note: Optional[str] = None
    test_type: Optional[str] = None          # پیش‌فرض: NULL
    status: Optional[str] = None             # پیش‌فرض: research (از main)


class VersionUpdate(BaseModel):
    version_name: Optional[str] = None
    rules_note: Optional[str] = None
    status: Optional[str] = None


# ═════════════════════════════════════════════
# Strategies
# ═════════════════════════════════════════════
@router.get("/")
def get_strategies(db: Session = Depends(get_db)):
    # selectinload: شمارش نسخه‌ها در یک کوئری (رفع N+1 — فاز ۱۵.۲)
    strategies = db.query(Strategy).options(selectinload(Strategy.versions)).all()
    result = []
    for s in strategies:
        result.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "created_at": s.created_at,
            "versions_count": len(s.versions),
        })
    return result


@router.post("/")
def create_strategy(strategy: StrategyCreate, db: Session = Depends(get_db)):
    db_strategy = Strategy(name=strategy.name, description=strategy.description)
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    return db_strategy


@router.get("/{strategy_id}")
def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="استراتژی پیدا نشد")
    return {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "created_at": strategy.created_at,
    }


@router.patch("/{strategy_id}")
def update_strategy(strategy_id: int, data: StrategyUpdate, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="استراتژی پیدا نشد")
    if data.name is not None:
        strategy.name = data.name
    if data.description is not None:
        strategy.description = data.description
    db.commit()
    db.refresh(strategy)
    return {"message": "استراتژی به‌روزرسانی شد"}


def _check_strategy_deletable(db: Session, strategy_id: int):
    """شمارش وابستگی‌های یک استراتژی برای گارد حذف امن (فاز ۵۳.۱).

    برمی‌گرداند `(trade_count, analysis_count)`:
    - `trade_count`: معاملاتِ حذف‌نشده‌ی همهٔ نسخه‌های استراتژی.
    - `analysis_count`: نتایج تحلیل ذخیره‌شده‌ی همهٔ نسخه‌های استراتژی.
    """
    trade_count = (
        db.query(Trade)
        .join(StrategyVersion, Trade.version_id == StrategyVersion.id)
        .filter(
            StrategyVersion.strategy_id == strategy_id,
            Trade.is_deleted == False,
        )
        .count()
    )
    analysis_count = (
        db.query(AnalysisResult)
        .join(StrategyVersion, AnalysisResult.version_id == StrategyVersion.id)
        .filter(StrategyVersion.strategy_id == strategy_id)
        .count()
    )
    return trade_count, analysis_count


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """حذف استراتژی — فاز ۵۳.۱: گارد از دست رفتن داده.

    اگر استراتژی معامله یا تحلیل داشته باشد، حذف نمی‌شود (۴۰۹) تا cascade
    به‌طور خاموش، معاملات/تحلیل‌ها را پاک نکند.
    """
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="استراتژی پیدا نشد")

    trade_count, analysis_count = _check_strategy_deletable(db, strategy_id)
    if trade_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"این استراتژی {trade_count} معامله دارد و قابل حذف نیست. "
                "ابتدا معاملات آن را حذف کنید."
            ),
        )
    if analysis_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"این استراتژی {analysis_count} تحلیل ذخیره‌شده دارد و قابل حذف نیست. "
                "ابتدا تحلیل‌ها را پاک کنید."
            ),
        )

    db.delete(strategy)
    db.commit()
    return {"message": "استراتژی حذف شد"}


# ═════════════════════════════════════════════
# Versions
# ═════════════════════════════════════════════
@router.get("/versions/all")
def get_all_versions(db: Session = Depends(get_db)):
    """دریافت لیست همه‌ی نسخه‌ها با نام استراتژی"""
    # selectinload برای استراتژی + یک کوئری گروهی برای شمارش معاملات (رفع N+1 — فاز ۱۵.۲)
    versions = db.query(StrategyVersion).options(selectinload(StrategyVersion.strategy)).all()
    counts = _trades_count_by_version(db, [v.id for v in versions])
    result = []
    for v in versions:
        strategy = v.strategy
        result.append({
            "id": v.id,
            "version_name": v.version_name,
            "strategy_id": v.strategy_id,
            "strategy_name": strategy.name if strategy else "نامشخص",
            "status": enum_value(v.status),
            "rules_note": v.rules_note,
            "trades_count": counts.get(v.id, 0),
            "created_at": v.created_at,
        })
    return result


@router.get("/{strategy_id}/versions")
def get_strategy_versions(strategy_id: int, db: Session = Depends(get_db)):
    """دریافت همه‌ی نسخه‌های یک استراتژی"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="استراتژی پیدا نشد")

    versions = db.query(StrategyVersion).filter(
        StrategyVersion.strategy_id == strategy_id
    ).all()

    # یک کوئری گروهی برای شمارش معاملات همه‌ی نسخه‌ها (رفع N+1 — فاز ۱۵.۲)
    counts = _trades_count_by_version(db, [v.id for v in versions])
    result = []
    for v in versions:
        result.append({
            "id": v.id,
            "version_name": v.version_name,
            "strategy_id": v.strategy_id,
            "rules_note": v.rules_note,
            "status": enum_value(v.status),
            "test_type": v.test_type,
            "forked_from_version_id": v.forked_from_version_id,
            "trades_count": counts.get(v.id, 0),
            "created_at": v.created_at,
        })
    return result


@router.post("/{strategy_id}/versions")
def create_version(strategy_id: int, version: VersionCreate, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="استراتژی پیدا نشد")

    # فاز 24: test_type + status
    test_type_val = version.test_type.lower() if version.test_type else None
    status_val = version.status if version.status else None

    db_version = StrategyVersion(
        strategy_id=strategy_id,
        version_name=version.version_name,
        rules_note=version.rules_note,
        test_type=test_type_val,
        status=status_val,
    )
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    return db_version


@router.patch("/versions/{version_id}")
def update_version(version_id: int, data: VersionUpdate, db: Session = Depends(get_db)):
    version = db.query(StrategyVersion).filter(StrategyVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="نسخه پیدا نشد")

    if data.version_name is not None:
        version.version_name = data.version_name
    if data.rules_note is not None:
        version.rules_note = data.rules_note
    if data.status is not None:
        try:
            version.status = StrategyStatus(data.status)
        except ValueError:
            raise HTTPException(status_code=400, detail="وضعیت نامعتبر")

    db.commit()
    db.refresh(version)
    return {"message": "نسخه به‌روزرسانی شد"}


@router.delete("/versions/{version_id}")
def delete_version(version_id: int, db: Session = Depends(get_db)):
    version = db.query(StrategyVersion).filter(StrategyVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="نسخه پیدا نشد")

    trades_count = db.query(Trade).filter(
        Trade.version_id == version_id, Trade.is_deleted == False
    ).count()
    if trades_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"این نسخه {trades_count} معامله دارد و قابل حذف نیست"
        )

    db.delete(version)
    db.commit()
    return {"message": "نسخه حذف شد"}


# ═════════════════════════════════════════════
# Fork Version
# ═════════════════════════════════════════════



@router.post("/versions/{version_id}/fork")
def fork_version(version_id: int, body: Optional[ForkRequest] = None, db: Session = Depends(get_db)):
    """Create a new version based on existing version (Fork) - Phase 24"""
    original = db.query(StrategyVersion).filter(StrategyVersion.id == version_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Source version not found")

    # Phase 24: optional parameters from body
    if body is None:
        body = ForkRequest()

    _raw_test_type = body.test_type or original.test_type
    test_type_val = _raw_test_type.lower() if _raw_test_type else None

    forked = StrategyVersion(
        strategy_id=original.strategy_id,
        version_name=body.version_name or f"{original.version_name} - Fork",
        rules_note=body.rules_note if body.rules_note is not None else original.rules_note,
        test_type=test_type_val,
        status=body.status or original.status,
        forked_from_version_id=version_id,
    )
    db.add(forked)
    db.commit()
    db.refresh(forked)
    return {
        "id": forked.id,
        "version_name": forked.version_name,
        "strategy_id": forked.strategy_id,
        "rules_note": forked.rules_note,
        "test_type": forked.test_type,
        "forked_from_version_id": forked.forked_from_version_id,
        "status": enum_value(forked.status),
        "created_at": forked.created_at,
        "trades_count": 0,
    }
# ═════════════════════════════════════════════
# Trades of a version
# ═════════════════════════════════════════════
@router.get("/versions/{version_id}/trades")
def get_version_trades(version_id: int, db: Session = Depends(get_db)):
    trades = db.query(Trade).filter(
        Trade.version_id == version_id, Trade.is_deleted == False
    ).all()
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "test_type": t.test_type.value if t.test_type else None,
            "source": t.source.value if t.source else None,
            "direction": t.direction,
            "open_time": t.open_time,
            "close_time": t.close_time,
            "open_price": t.open_price,
            "close_price": t.close_price,
            "size": t.size,
            "pnl": t.pnl,
            "commission": t.commission,
            "swap": t.swap,
            "r_multiple": t.r_multiple,
        }
        for t in trades
    ]


# ═════════════════════════════════════════════
# Strategy Stats
# ═════════════════════════════════════════════
@router.get("/{strategy_id}/stats")
def get_strategy_stats(strategy_id: int, db: Session = Depends(get_db)):
    """آمار تفصیلی یک استراتژی از مجموع معاملات همه نسخه‌ها"""
    # 1. بررسی وجود استراتژی
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="استراتژی پیدا نشد")

    # 2. دریافت همه نسخه‌های استراتژی
    versions = db.query(StrategyVersion).filter(
        StrategyVersion.strategy_id == strategy_id
    ).all()

    if not versions:
        return {
            "strategy_id": strategy_id,
            "strategy_name": strategy.name,
            "versions_count": 0,
            "total_trades": 0,
            "message": "این استراتژی هیچ نسخه‌ای ندارد",
        }

    # 3. دریافت معاملات — فاز ۱۵.۳: فقط ۳ ستون لازم (بدون لود ORM)
    # معاملات REAL در آمار Backtest/Forward شمرده نمی‌شوند
    version_ids = [v.id for v in versions]
    _net = _net_expr()
    _rows = (
        db.query(Trade)
        .filter(Trade.version_id.in_(version_ids), analysis_trades_filter())
        .with_entities(Trade.close_time, Trade.open_time, _net.label("net"))
        .order_by(Trade.id.asc())
        .all()
    )
    all_trades = [(ct, ot, float(n or 0.0)) for ct, ot, n in _rows]

    if not all_trades:
        return {
            "strategy_id": strategy_id,
            "strategy_name": strategy.name,
            "versions_count": len(versions),
            "version_ids": version_ids,
            "total_trades": 0,
            "message": "هیچ معامله‌ای برای این استراتژی یافت نشد",
        }

    total = len(all_trades)
    wins = [t for t in all_trades if t[2] > 0]
    losses = [t for t in all_trades if t[2] < 0]

    gross_profit = sum(t[2] for t in wins) if wins else 0
    gross_loss = abs(sum(t[2] for t in losses)) if losses else 0
    net_pnl = sum(t[2] for t in all_trades)

    # ─── Win Rate ───
    win_rate = round((len(wins) / total * 100), 2) if total > 0 else 0

    # ─── Profit Factor ───
    if gross_loss > 0:
        profit_factor = round(gross_profit / gross_loss, 2)
    elif gross_profit > 0:
        profit_factor = 100.0
    else:
        profit_factor = 0.0

    # ─── Max Drawdown ───
    sorted_trades = sorted(all_trades, key=lambda t: t[0] or t[1])
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in sorted_trades:
        equity += t[2]
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
    max_dd = round(max_dd, 2)

    # ─── Sharpe Ratio ───
    pnl_values = [t[2] for t in all_trades]
    mean_pnl = sum(pnl_values) / len(pnl_values) if pnl_values else 0
    if len(pnl_values) > 1:
        variance = sum((p - mean_pnl) ** 2 for p in pnl_values) / (len(pnl_values) - 1)
        std_pnl = sqrt(variance) if variance > 0 else 0
    else:
        std_pnl = 0

    # Sharpe = (mean / std) * sqrt(num_trades) — فرض می‌کنیم هر معامله یک روز معاملاتی است
    sharpe_ratio = round((mean_pnl / std_pnl * sqrt(total)) if std_pnl > 0 else 0, 3)

    # ─── Expectancy ───
    win_rate_ratio = (len(wins) / total) if total > 0 else 0
    loss_rate_ratio = (len(losses) / total) if total > 0 else 0
    avg_win = (gross_profit / len(wins)) if wins else 0
    avg_loss = (gross_loss / len(losses)) if losses else 0  # مقدار مثبت
    expectancy = round((win_rate_ratio * avg_win) - (loss_rate_ratio * avg_loss), 2)

    # ─── Largest Win / Loss ───
    largest_win = round(max((t[2] for t in wins), default=0), 2)
    largest_loss = round(abs(min((t[2] for t in losses), default=0)), 2)

    # ─── Max Consecutive Losses ───
    streak = 0
    max_streak = 0
    for t in sorted_trades:
        npnl = t[2]
        if npnl < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        elif npnl > 0:
            streak = 0

    # ─── Return ───
    return {
        "strategy_id": strategy_id,
        "strategy_name": strategy.name,
        "versions_count": len(versions),
        "version_ids": version_ids,
        "total_trades": total,
        "summary": {
            "net_pnl": round(net_pnl, 2),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown": max_dd,
            "sharpe_ratio": sharpe_ratio,
            "expectancy": expectancy,
        },
        "trade_counts": {
            "total": total,
            "winning": len(wins),
            "losing": len(losses),
            "breakeven": total - len(wins) - len(losses),
        },
        "averages": {
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "avg_trade": round(mean_pnl, 2),
        },
        "extremes": {
            "largest_win": largest_win,
            "largest_loss": largest_loss,
        },
        "consistency": {
            "max_consecutive_losses": max_streak,
            "pnl_std_dev": round(std_pnl, 2),
        },
    }


@router.get("/{strategy_id}/live-performance")
def get_strategy_live_performance(
    strategy_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """عملکرد معاملات بسته‌شدهٔ Real هر نسخه، در بازهٔ انتخابی.

    Backtest/Forward عمداً در این گزارش وارد نمی‌شوند. سود خالص از تعریف واحد
    metrics.net_pnl_sql() می‌آید و شامل PnL، کمیسیون و سواپ است.
    """
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="تاریخ شروع باید قبل از تاریخ پایان باشد")

    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="استراتژی پیدا نشد")

    versions = (
        db.query(StrategyVersion)
        .filter(StrategyVersion.strategy_id == strategy_id)
        .order_by(StrategyVersion.id.asc())
        .all()
    )
    version_rows = {
        version.id: {
            "version_id": version.id,
            "version_name": version.version_name,
            "status": enum_value(version.status),
            "forked_from_version_id": version.forked_from_version_id,
            "total_trades": 0,
            "net_pnl": 0.0,
            "winning_trades": 0,
            "losing_trades": 0,
            "breakeven_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "by_type": {
                "real_personal": {"trades": 0, "net_pnl": 0.0},
                "real_prop": {"trades": 0, "net_pnl": 0.0},
            },
        }
        for version in versions
    }

    if version_rows:
        net = _net_expr()
        query = db.query(
            Trade.version_id,
            Trade.test_type,
            func.count(Trade.id),
            func.coalesce(func.sum(net), 0.0),
            func.coalesce(func.sum(case((net > 0, 1), else_=0)), 0),
            func.coalesce(func.sum(case((net < 0, 1), else_=0)), 0),
            func.coalesce(func.sum(case((net > 0, net), else_=0.0)), 0.0),
            func.coalesce(func.sum(case((net < 0, net), else_=0.0)), 0.0),
        ).filter(
            Trade.version_id.in_(version_rows),
            Trade.test_type.in_([TestType.REAL_PERSONAL, TestType.REAL_PROP]),
            Trade.close_time.isnot(None),
            Trade.is_deleted == False,
        )
        query = filter_by_range(query, Trade.close_time, date_from, date_to)
        for version_id, test_type, count, total_net, wins, losses, gross_wins, gross_losses in (
            query.group_by(Trade.version_id, Trade.test_type).all()
        ):
            row = version_rows[version_id]
            type_key = "real_personal" if test_type == TestType.REAL_PERSONAL else "real_prop"
            trade_count = int(count or 0)
            net_total = float(total_net or 0.0)
            win_count = int(wins or 0)
            loss_count = int(losses or 0)
            type_stats = row["by_type"][type_key]
            type_stats["trades"] = trade_count
            type_stats["net_pnl"] = round(net_total, 2)
            row["total_trades"] += trade_count
            row["net_pnl"] += net_total
            row["winning_trades"] += win_count
            row["losing_trades"] += loss_count
            gross_loss_abs = abs(float(gross_losses or 0.0))
            type_stats["gross_profit"] = round(float(gross_wins or 0.0), 2)
            type_stats["gross_loss"] = round(gross_loss_abs, 2)

    results = []
    for row in version_rows.values():
        total_count = row["total_trades"]
        gross_profit = sum(item.get("gross_profit", 0.0) for item in row["by_type"].values())
        gross_loss = sum(item.get("gross_loss", 0.0) for item in row["by_type"].values())
        row["breakeven_trades"] = total_count - row["winning_trades"] - row["losing_trades"]
        row["win_rate"] = round(row["winning_trades"] / total_count * 100, 2) if total_count else 0.0
        row["profit_factor"] = round(gross_profit / gross_loss, 2) if gross_loss else (100.0 if gross_profit else 0.0)
        row["net_pnl"] = round(row["net_pnl"], 2)
        for type_stats in row["by_type"].values():
            type_stats.pop("gross_profit", None)
            type_stats.pop("gross_loss", None)
        results.append(row)

    return {
        "strategy_id": strategy.id,
        "strategy_name": strategy.name,
        "currency": "USDT",
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "basis": "closed_trades",
        "versions": results,
    }
