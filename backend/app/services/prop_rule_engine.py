from __future__ import annotations

from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from ..models.prop import (
    PropStage,
    StageType,
    StageStatus,
    RuleType,
    Severity,
    RuleViolation,
)
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
        # فاز ۳۲: فقط روزهای منفی به‌عنوان زیان شمرده می‌شوند.
        # پیش‌تر `abs(min(...))` حتی روز پرسود را «زیان» می‌شمرد (باگ).
        max_daily_loss = (
            max(0.0, -min(daily_pnl.values())) if daily_pnl else 0.0
        )  # مقدار مثبت

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

        # ── فاز ۳۲: Rule Evaluation ساختاریافته (Pipeline) ──
        # هر قاعده یک نتیجه‌ی {rule_type, actual_value, limit_value, severity, message}
        # تولید می‌کند؛ severity ∈ {PASS, WARNING, VIOLATION}.
        floating_pnl = sum((t.pnl or 0.0) for t in trades if t.close_time is None)
        rule_checks = PropRuleEngine._build_rule_checks(
            stage=stage,
            initial=initial,
            equity=equity,
            total_pnl=total_pnl,
            max_daily_loss=max_daily_loss,
            max_daily_dd_limit=max_daily_dd_limit,
            max_total_dd=max_total_dd,
            max_total_dd_limit=max_total_dd_limit,
            profit_target=profit_target,
            trading_days=trading_days,
            min_days=min_days,
            floating_pnl=floating_pnl,
        )
        overall_severity = PropRuleEngine._overall_severity(rule_checks)

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

            # فاز ۳۲ — Rule Evaluation (خروجی Pipeline)
            "rule_checks": rule_checks,
            "overall_severity": overall_severity.value,
            "floating_pnl": round(floating_pnl, 2),

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
    # فاز ۳۲ — Rule Evaluation & Persistence
    # ═════════════════════════════════════════════
    @staticmethod
    def record_violations(
        db: Session,
        stage_id: int,
        checks: List[Dict[str, Any]] | None = None,
        commit: bool = True,
    ) -> List[RuleViolation]:
        """نتیجه‌ی ارزیابی قوانین یک مرحله را در `rule_violations` ثبت می‌کند.

        - اگر `checks` داده نشود، خودش `evaluate_stage` را اجرا می‌کند.
        - append-only است (هر اجرای ارزیابی یک ردیف برای هر قاعده) تا تاریخچه حفظ شود.
        """
        if checks is None:
            evaluation = PropRuleEngine.evaluate_stage(db, stage_id)
            if "error" in evaluation:
                return []
            checks = evaluation.get("rule_checks", [])

        rows: List[RuleViolation] = []
        for chk in checks:
            rule_type = chk["rule_type"]
            severity = chk["severity"]
            row = RuleViolation(
                prop_stage_id=stage_id,
                rule_type=rule_type if isinstance(rule_type, RuleType) else RuleType(rule_type),
                actual_value=float(chk["actual_value"]),
                limit_value=float(chk["limit_value"]),
                severity=severity if isinstance(severity, Severity) else Severity(severity),
            )
            db.add(row)
            rows.append(row)

        if commit:
            db.commit()
            for row in rows:
                db.refresh(row)
        else:
            db.flush()
        return rows

    @staticmethod
    def get_violations(
        db: Session,
        stage_id: int,
        severity: "Severity | str | None" = None,
        limit: int | None = None,
    ) -> List[RuleViolation]:
        """تاریخچه‌ی ارزیابی‌های ثبت‌شده یک مرحله (جدیدترین اول)."""
        q = db.query(RuleViolation).filter(RuleViolation.prop_stage_id == stage_id)
        if severity is not None:
            q = q.filter(
                RuleViolation.severity
                == (severity if isinstance(severity, Severity) else Severity(severity))
            )
        q = q.order_by(RuleViolation.occurred_at.desc(), RuleViolation.id.desc())
        if limit:
            q = q.limit(limit)
        return q.all()

    @staticmethod
    def _build_rule_checks(
        *,
        stage: PropStage,
        initial: float,
        equity: float,
        total_pnl: float,
        max_daily_loss: float,
        max_daily_dd_limit: float,
        max_total_dd: float,
        max_total_dd_limit: float,
        profit_target: float,
        trading_days: int,
        min_days: int,
        floating_pnl: float,
    ) -> List[Dict[str, Any]]:
        """۷ قاعده را ارزیابی و لیست نتایج ساختاریافته برمی‌گرداند."""
        checks: List[Dict[str, Any]] = []

        def add(rule_type, actual, limit_v, sev, msg) -> None:
            checks.append({
                "rule_type": rule_type,
                "actual_value": round(float(actual), 2),
                "limit_value": round(float(limit_v), 2),
                "severity": sev,
                "message": msg,
            })

        # ۱) Daily Drawdown
        add(
            RuleType.DAILY_DRAWDOWN, max_daily_loss, max_daily_dd_limit,
            PropRuleEngine._grade_loss(max_daily_loss, max_daily_dd_limit),
            f"Daily DD: {max_daily_loss:.2f}$ از حد {max_daily_dd_limit:.2f}$",
        )
        # ۲) Max (Total) Drawdown
        add(
            RuleType.MAX_DRAWDOWN, max_total_dd, max_total_dd_limit,
            PropRuleEngine._grade_loss(max_total_dd, max_total_dd_limit),
            f"Total DD: {max_total_dd:.2f}$ از حد {max_total_dd_limit:.2f}$",
        )
        # ۳) Profit Target
        if profit_target > 0 and total_pnl >= profit_target:
            tp_sev = Severity.PASS
        elif profit_target > 0:
            tp_sev = Severity.WARNING
        else:
            tp_sev = Severity.PASS
        add(
            RuleType.PROFIT_TARGET, total_pnl, profit_target, tp_sev,
            f"سود: {total_pnl:.2f}$ از هدف {profit_target:.2f}$",
        )
        # ۴) Min Trading Days
        add(
            RuleType.MIN_TRADING_DAYS, float(trading_days), float(min_days),
            Severity.PASS if (min_days <= 0 or trading_days >= min_days) else Severity.WARNING,
            f"روزهای معاملاتی: {trading_days} از حداقل {min_days}",
        )
        # ۵) Equity Balance — کف مجاز = initial - max_total_dd
        equity_floor = initial - max_total_dd_limit if max_total_dd_limit > 0 else initial
        if equity < equity_floor:
            eq_sev = Severity.VIOLATION
        elif equity < initial:
            eq_sev = Severity.WARNING
        else:
            eq_sev = Severity.PASS
        add(
            RuleType.EQUITY_BALANCE, equity, equity_floor, eq_sev,
            f"موجودی: {equity:.2f}$ (کف مجاز {equity_floor:.2f}$)",
        )
        # ۶) Floating PnL (معاملات باز) — زیان شناور مثبت
        floating_loss = max(-floating_pnl, 0.0)
        add(
            RuleType.FLOATING_PNL, floating_loss, max_daily_dd_limit,
            PropRuleEngine._grade_loss(floating_loss, max_daily_dd_limit),
            f"زیان شناور: {floating_loss:.2f}$ از حد {max_daily_dd_limit:.2f}$",
        )
        # ۷) Stage Status — ارزیابی فقط روی مرحله فعال مجاز است
        is_active = stage.status == StageStatus.ACTIVE
        add(
            RuleType.STAGE_STATUS,
            1.0 if is_active else 0.0,
            1.0,
            Severity.PASS if is_active else Severity.VIOLATION,
            f"وضعیت مرحله: {stage.status.value if stage.status else 'unknown'}",
        )
        return checks

    @staticmethod
    def _grade_loss(actual_loss: float, limit: float, warn_ratio: float = 0.8) -> Severity:
        """درجه‌بندی یک زیان در برابر حد مجاز (برای DD/Floating)."""
        if limit <= 0:
            return Severity.PASS
        if actual_loss > limit:
            return Severity.VIOLATION
        if actual_loss >= limit * warn_ratio:
            return Severity.WARNING
        return Severity.PASS

    @staticmethod
    def _overall_severity(checks: List[Dict[str, Any]]) -> Severity:
        """بدترین شدت میان همه‌ی بررسی‌ها."""
        severities = [c["severity"] for c in checks]
        if Severity.VIOLATION in severities:
            return Severity.VIOLATION
        if Severity.WARNING in severities:
            return Severity.WARNING
        return Severity.PASS

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