from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# Schemas
class MonteCarloRequest(BaseModel):
    version_id: Optional[int] = None
    trades_pnl: Optional[List[float]] = None
    initial_balance: float = Field(default=10000.0, gt=0)
    num_simulations: int = Field(default=1000, ge=100, le=10000)
    ruin_threshold_pct: float = Field(default=20.0, gt=0, le=100)


class CompareRequest(BaseModel):
    version_ids: List[int]
    initial_balance: float = 10000.0


# Mock DB Fetcher (در صورت عدم اتصال دیتابیس جایگزین می‌شود)
def get_trades_by_version(version_id: int) -> List[Dict[str, Any]]:
    # نمونه معاملات موقت برای تست و اجرای مستقل
    return [
        {"pnl": 150.0, "r_multiple": 1.5, "entry_time": datetime(2026, 3, 1, 8, 30)},
        {"pnl": -100.0, "r_multiple": -1.0, "entry_time": datetime(2026, 3, 1, 14, 15)},
        {"pnl": 200.0, "r_multiple": 2.0, "entry_time": datetime(2026, 3, 2, 9, 0)},
        {"pnl": -100.0, "r_multiple": -1.0, "entry_time": datetime(2026, 3, 2, 16, 45)},
        {"pnl": 300.0, "r_multiple": 3.0, "entry_time": datetime(2026, 3, 3, 10, 0)},
    ]


@router.get("/{version_id}")
async def get_analytics_for_version(version_id: int, symbol: Optional[str] = None):
    """
    محاسبه کامل متریک‌های پایه و تفکیک‌های زمانی برای نسخه استراتژی مشخص
    """
    trades = get_trades_by_version(version_id)
    if not trades:
        raise HTTPException(
            status_code=status.HTTP_444_NOT_FOUND, 
            detail=f"No trades found for strategy version_id {version_id}"
        )

    basic_metrics = AnalysisService.calculate_basic_metrics(trades)
    time_breakdowns = AnalysisService.calculate_time_breakdowns(trades, symbol=symbol)

    return {
        "version_id": version_id,
        "symbol": symbol,
        "basic_metrics": basic_metrics,
        "time_breakdowns": time_breakdowns
    }


@router.post("/compare")
async def compare_strategy_versions(payload: CompareRequest):
    """
    دریافت چندین version_id و برگرداندن جدول مقایسه‌ای از عملکرد آن‌ها
    """
    if not payload.version_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="version_ids list cannot be empty."
        )

    comparison_table = []
    for vid in payload.version_ids:
        trades = get_trades_by_version(vid)
        metrics = AnalysisService.calculate_basic_metrics(trades, initial_balance=payload.initial_balance)
        metrics["version_id"] = vid
        comparison_table.append(metrics)

    return {
        "count": len(comparison_table),
        "comparison": comparison_table
    }


@router.post("/monte-carlo")
async def run_monte_carlo_simulation(payload: MonteCarloRequest):
    """
    اجرای شبیه‌سازی مونت‌کارلو بر اساس version_id یا آرایه مستقیم PnL
    """
    trades = []
    if payload.version_id is not None:
        trades = get_trades_by_version(payload.version_id)
    elif payload.trades_pnl is not None:
        trades = [{"pnl": pnl} for pnl in payload.trades_pnl]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either version_id or trades_pnl must be provided."
        )

    if not trades:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trade data found to run simulation."
        )

    results = AnalysisService.run_monte_carlo(
        trades=trades,
        initial_balance=payload.initial_balance,
        num_simulations=payload.num_simulations,
        ruin_threshold_pct=payload.ruin_threshold_pct
    )

    return results