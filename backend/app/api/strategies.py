from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from math import sqrt

from ..core.database import get_db
from ..models.strategy import Strategy, StrategyVersion, Trade, StrategyStatus

router = APIRouter()


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


class VersionUpdate(BaseModel):
    version_name: Optional[str] = None
    rules_note: Optional[str] = None
    status: Optional[str] = None


# ═════════════════════════════════════════════
# Strategies
# ═════════════════════════════════════════════
@router.get("/")
def get_strategies(db: Session = Depends(get_db)):
    strategies = db.query(Strategy).all()
    result = []
    for s in strategies:
        versions = db.query(StrategyVersion).filter(StrategyVersion.strategy_id == s.id).all()
        result.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "created_at": s.created_at,
            "versions_count": len(versions),
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


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="استراتژی پیدا نشد")
    db.delete(strategy)
    db.commit()
    return {"message": "استراتژی حذف شد"}


# ═════════════════════════════════════════════
# Versions
# ═════════════════════════════════════════════
@router.get("/versions/all")
def get_all_versions(db: Session = Depends(get_db)):
    """دریافت لیست همه‌ی نسخه‌ها با نام استراتژی"""
    versions = db.query(StrategyVersion).all()
    result = []
    for v in versions:
        strategy = db.query(Strategy).filter(Strategy.id == v.strategy_id).first()
        trades_count = db.query(Trade).filter(Trade.version_id == v.id).count()
        result.append({
            "id": v.id,
            "version_name": v.version_name,
            "strategy_id": v.strategy_id,
            "strategy_name": strategy.name if strategy else "نامشخص",
            "status": v.status.value if hasattr(v.status, 'value') else str(v.status),
            "rules_note": v.rules_note,
            "trades_count": trades_count,
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

    result = []
    for v in versions:
        trades_count = db.query(Trade).filter(Trade.version_id == v.id).count()
        result.append({
            "id": v.id,
            "version_name": v.version_name,
            "strategy_id": v.strategy_id,
            "rules_note": v.rules_note,
            "status": v.status.value if hasattr(v.status, 'value') else str(v.status),
            "trades_count": trades_count,
            "created_at": v.created_at,
        })
    return result


@router.post("/{strategy_id}/versions")
def create_version(strategy_id: int, version: VersionCreate, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="استراتژی پیدا نشد")

    db_version = StrategyVersion(
        strategy_id=strategy_id,
        version_name=version.version_name,
        rules_note=version.rules_note,
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

    trades_count = db.query(Trade).filter(Trade.version_id == version_id).count()
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
def fork_version(version_id: int, db: Session = Depends(get_db)):
    """ایجاد یک نسخه جدید بر اساس نسخه موجود (Fork)"""
    original = db.query(StrategyVersion).filter(StrategyVersion.id == version_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="نسخه مبدأ پیدا نشد")

    forked = StrategyVersion(
        strategy_id=original.strategy_id,
        version_name=f"{original.version_name} - Fork",
        rules_note=original.rules_note,
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
        "forked_from_version_id": forked.forked_from_version_id,
        "status": forked.status.value if hasattr(forked.status, 'value') else str(forked.status),
        "created_at": forked.created_at,
        "trades_count": 0,
    }
# ═════════════════════════════════════════════
# Trades of a version
# ═════════════════════════════════════════════
@router.get("/versions/{version_id}/trades")
def get_version_trades(version_id: int, db: Session = Depends(get_db)):
    trades = db.query(Trade).filter(Trade.version_id == version_id).all()
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

    # 3. دریافت همه معاملات از همه نسخه‌ها
    version_ids = [v.id for v in versions]
    all_trades = db.query(Trade).filter(Trade.version_id.in_(version_ids)).all()

    if not all_trades:
        return {
            "strategy_id": strategy_id,
            "strategy_name": strategy.name,
            "versions_count": len(versions),
            "version_ids": version_ids,
            "total_trades": 0,
            "message": "هیچ معامله‌ای برای این استراتژی یافت نشد",
        }

    # ─── 4. Helper: net_pnl ───
    def _net_pnl(t: Trade) -> float:
        return (t.pnl or 0) + (t.commission or 0) + (t.swap or 0)

    total = len(all_trades)
    wins = [t for t in all_trades if _net_pnl(t) > 0]
    losses = [t for t in all_trades if _net_pnl(t) < 0]

    gross_profit = sum(_net_pnl(t) for t in wins) if wins else 0
    gross_loss = abs(sum(_net_pnl(t) for t in losses)) if losses else 0
    net_pnl = sum(_net_pnl(t) for t in all_trades)

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
    sorted_trades = sorted(all_trades, key=lambda t: t.close_time or t.open_time)
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in sorted_trades:
        equity += _net_pnl(t)
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
    max_dd = round(max_dd, 2)

    # ─── Sharpe Ratio ───
    pnl_values = [_net_pnl(t) for t in all_trades]
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
    largest_win = round(max((_net_pnl(t) for t in wins), default=0), 2)
    largest_loss = round(abs(min((_net_pnl(t) for t in losses), default=0)), 2)

    # ─── Max Consecutive Losses ───
    streak = 0
    max_streak = 0
    for t in sorted_trades:
        npnl = _net_pnl(t)
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