from __future__ import annotations

from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from ..models.prop import PropStage, StageType
from ..models.strategy import Trade


class PropRuleEngine:
    """
    واحد مرکزی بررسی قوانین پراپ.

    تمام محاسبات مربوط به:
    - Daily DD / Total DD
    - Profit Target
    - Trading Days
    - Equity / Current Profit
    - Withdrawable Profit (برای مرحله رییل)
    - Rule Violations
    - Stage Status پیشنهادی

    اینجا متمرکز است. هیچ‌جای دیگه نباید این منطق رو دوباره پیاده کنه.

    ─────────────────────────────────────────────
    واحدها:
    - همه‌ی مبالغ (profit_target، max_daily_dd، max_total_dd، current_profit،
      equity، withdrawable_profit) بر حسب **دلار** هستند.
    - فیلدهای *_percent فقط برای نمایش در UI هستند.
    """

    @staticmethod
    def evaluate_stage(db: Session, stage_id: int) -> Dict[str, Any]:
        """ارزیابی کامل یک مرحله پراپ"""
        stage = db.query(PropStage).filter(PropStage.id == stage_id).first()
        if not stage:
            return {
                "stage_id": stage_id,
                "ready_to_pass": False,
                "error": "مرحله پیدا نشد",
            }

        # فاز ۲۵: معاملات حذف‌شده در ارزیابی قوانین پراپ لحاظ نمی‌شوند
        trades = db.query(Trade).filter(
            Trade.prop_stage_id == stage_id, Trade.is_deleted == False
        ).all()

        # ── مبالغ پایه (دلار) ──
        initial = stage.initial_balance or 10000.0
        total_pnl = sum(t.pnl or 0 for t in trades)
        equity = initial + total_pnl

        # ── Daily DD: بدترین روز (دلار) ──
        daily_pnl = PropRuleEngine._group_daily_pnl(trades)
        max_daily_loss = abs(min(daily_pnl.values())) if daily_pnl else 0.0  # مقدار مثبت

        # ── Total DD: بر اساس equity curve (دلار) ──
        max_total_dd = PropRuleEngine._calculate_max_drawdown(trades, initial)

        # ── روزهای معاملاتی ──
        trading_days = len(daily_pnl)

        # ── قوانین مرحله (دلار) ──
        profit_target = stage.profit_target or 0.0
        max_daily_dd_limit = stage.max_daily_dd or 0.0
        max_total_dd_limit = stage.max_total_dd or 0.0
        min_days = stage.min_trading_days or 0

        # ── بررسی نقض قوانین (مقایسه‌ی دلار با دلار) ──
        daily_dd_violated = (
            max_daily_loss > max_daily_dd_limit
            if max_daily_dd_limit > 0
            else False
        )
        total_dd_violated = (
            max_total_dd > max_total_dd_limit
            if max_total_dd_limit > 0
            else False
        )
        target_reached = (
            total_pnl >= profit_target if profit_target > 0 else True
        )
        min_days_met = trading_days >= min_days if min_days > 0 else True

        # ── violations: فقط نقض واقعی ──
        violations: List[str] = []
        if daily_dd_violated:
            violations.append(
                f"حد Daily DD نقض شده ({max_daily_loss:.2f}$ > {max_daily_dd_limit}$)"
            )
        if total_dd_violated:
            violations.append(
                f"حد Total DD نقض شده ({max_total_dd:.2f}$ > {max_total_dd_limit}$)"
            )

        # ── وضعیت پیشنهادی ──
        if daily_dd_violated:
            suggested_status = "failed_daily_dd"
        elif total_dd_violated:
            suggested_status = "failed_total_dd"
        elif target_reached and min_days_met:
            suggested_status = "ready_to_pass"
        else:
            suggested_status = "in_progress"

        # ── منطق مخصوص FUNDED_REAL ──
        is_funded = stage.stage_type == StageType.FUNDED_REAL
        total_withdrawn = stage.total_withdrawn or 0.0
        profit_share = stage.profit_share_percentage or 80.0
        withdrawable_profit = 0.0

        if is_funded:
            user_share = total_pnl * (profit_share / 100.0)
            withdrawable_profit = max(user_share - total_withdrawn, 0.0)
            ready_to_pass = False
        else:
            ready_to_pass = (
                (not daily_dd_violated)
                and (not total_dd_violated)
                and target_reached
                and min_days_met
            )

        # ── درصدها (فقط برای نمایش) ──
        current_profit_percent = (
            round(total_pnl / initial * 100, 2) if initial > 0 else 0.0
        )
        profit_progress_percent = (
            round(total_pnl / profit_target * 100, 2)
            if profit_target > 0
            else 0.0
        )
        daily_dd_progress_percent = (
            round(max_daily_loss / max_daily_dd_limit * 100, 2)
            if max_daily_dd_limit > 0
            else 0.0
        )
        total_dd_progress_percent = (
            round(max_total_dd / max_total_dd_limit * 100, 2)
            if max_total_dd_limit > 0
            else 0.0
        )

        return {
            "stage_id": stage_id,
            "stage_type": stage.stage_type.value if stage.stage_type else None,
            "status": stage.status.value if stage.status else None,

            # موجودی و سود (دلار)
            "initial_balance": round(initial, 2),
            "equity": round(equity, 2),
            "current_profit": round(total_pnl, 2),
            "current_profit_percent": current_profit_percent,

            # هدف سود (دلار)
            "profit_target": round(profit_target, 2),
            "profit_progress_percent": profit_progress_percent,

            # Daily DD (دلار)
            "max_daily_loss": round(max_daily_loss, 2),
            "max_daily_dd_limit": max_daily_dd_limit,
            "daily_dd_progress_percent": daily_dd_progress_percent,
            "daily_dd_violated": daily_dd_violated,

            # Total DD (دلار)
            "max_total_dd": round(max_total_dd, 2),
            "max_total_dd_limit": max_total_dd_limit,
            "total_dd_progress_percent": total_dd_progress_percent,
            "total_dd_violated": total_dd_violated,

            # روزهای معاملاتی
            "trading_days": trading_days,
            "min_trading_days": min_days,
            "days_met": min_days_met,

            # وضعیت
            "target_reached": target_reached,
            "ready_to_pass": ready_to_pass,
            "suggested_status": suggested_status,
            "violations": violations,

            # رییل
            "is_funded": is_funded,
            "total_withdrawn": round(total_withdrawn, 2),
            "profit_share_percentage": profit_share if is_funded else None,
            "withdrawable_profit": round(withdrawable_profit, 2),

            # آمار
            "total_trades": len(trades),
        }

    @staticmethod
    def validate_withdrawal(
        db: Session, stage_id: int, amount: float
    ) -> Tuple[bool, str]:
        """بررسی مجاز بودن برداشت"""
        if amount <= 0:
            return False, "مبلغ برداشت باید مثبت باشد"

        evaluation = PropRuleEngine.evaluate_stage(db, stage_id)

        if "error" in evaluation:
            return False, evaluation["error"]

        if not evaluation.get("is_funded"):
            return False, "برداشت فقط در مرحله رییل مجاز است"

        withdrawable = evaluation.get("withdrawable_profit", 0.0)
        if amount > withdrawable:
            return False, (
                f"مبلغ برداشت ({amount}$) بیشتر از سود قابل برداشت "
                f"({withdrawable}$) است"
            )

        return True, ""

    # ═════════════════════════════════════════════
    # Internal helpers
    # ═════════════════════════════════════════════
    @staticmethod
    def _group_daily_pnl(trades: List[Trade]) -> Dict[str, float]:
        daily: Dict[str, float] = {}
        for t in trades:
            if not t.close_time:
                continue
            day_key = t.close_time.strftime("%Y-%m-%d")
            daily[day_key] = daily.get(day_key, 0.0) + (t.pnl or 0.0)
        return daily

    @staticmethod
    def _calculate_max_drawdown(trades: List[Trade], initial: float) -> float:
        sorted_trades = sorted(
            trades, key=lambda t: t.close_time or t.open_time
        )
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
        return max_dd