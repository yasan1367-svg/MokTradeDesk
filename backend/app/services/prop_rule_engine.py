from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ..models.prop import PropStage
from ..models.strategy import Trade


class PropRuleEngine:
    """واحد مرکزی بررسی آمادگی پاس شدن مرحله‌ی پراپ"""

    @staticmethod
    def evaluate_stage(db: Session, stage_id: int) -> Dict[str, Any]:
        stage = db.query(PropStage).filter(PropStage.id == stage_id).first()
        if not stage:
            return {"stage_id": stage_id, "ready_to_pass": False, "error": "مرحله پیدا نشد"}

        trades = db.query(Trade).filter(Trade.prop_stage_id == stage_id).all()
        total_pnl = sum(t.pnl or 0 for t in trades)
        initial = stage.initial_balance or 10000
        profit_percent = (total_pnl / initial * 100) if initial > 0 else 0

        daily_pnl: Dict[str, float] = {}
        for trade in trades:
            if not trade.close_time:
                continue
            day_key = trade.close_time.strftime('%Y-%m-%d')
            daily_pnl[day_key] = daily_pnl.get(day_key, 0) + (trade.pnl or 0)

        max_daily_loss = min(daily_pnl.values()) if daily_pnl else 0
        max_daily_dd_percent = abs(max_daily_loss / initial * 100) if initial > 0 else 0

        sorted_trades = sorted(trades, key=lambda t: t.close_time or t.open_time)
        equity = initial
        peak = initial
        max_dd = 0.0
        for trade in sorted_trades:
            equity += trade.pnl or 0
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
        max_total_dd_percent = (max_dd / initial * 100) if initial > 0 else 0

        trading_days = len(daily_pnl)
        profit_target = stage.profit_target or 0
        max_daily_dd_limit = stage.max_daily_dd or 0
        max_total_dd_limit = stage.max_total_dd or 0
        min_days = stage.min_trading_days or 0

        daily_dd_violated = max_daily_dd_percent > max_daily_dd_limit if max_daily_dd_limit > 0 else False
        total_dd_violated = max_total_dd_percent > max_total_dd_limit if max_total_dd_limit > 0 else False
        target_reached = profit_percent >= profit_target if profit_target > 0 else False
        min_days_met = trading_days >= min_days if min_days > 0 else True

        violations: List[str] = []
        if daily_dd_violated:
            violations.append('حد Daily DD نقض شده است')
        if total_dd_violated:
            violations.append('حد Total DD نقض شده است')
        if not target_reached:
            violations.append('هدف سود به‌دست نیامده است')
        if not min_days_met:
            violations.append('حداقل روزهای معاملاتی رعایت نشده است')

        return {
            "stage_id": stage_id,
            "stage_type": stage.stage_type.value if stage.stage_type else None,
            "status": stage.status.value if stage.status else None,
            "current_profit": round(total_pnl, 2),
            "current_profit_percent": round(profit_percent, 2),
            "profit_target": profit_target,
            "profit_target_percent": round(profit_target, 2),
            "max_daily_dd_percent": round(max_daily_dd_percent, 2),
            "max_daily_dd_limit": max_daily_dd_limit,
            "max_total_dd_percent": round(max_total_dd_percent, 2),
            "max_total_dd_limit": max_total_dd_limit,
            "trading_days": trading_days,
            "min_trading_days": min_days,
            "days_met": min_days_met,
            "daily_dd_violated": daily_dd_violated,
            "total_dd_violated": total_dd_violated,
            "target_reached": target_reached,
            "ready_to_pass": (not daily_dd_violated) and (not total_dd_violated) and target_reached and min_days_met,
            "violations": violations,
            "total_trades": len(trades),
        }
