from __future__ import annotations

from datetime import timedelta, timezone
from datetime import datetime, timedelta, timezone
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
from . import metrics
from ..domain.risk.drawdown_engine import (
    calculate_peak_to_trough_dd,
    calculate_static_dd,
)
from ..domain.risk.equity_engine import (
    calculate_equity_curve,
    calculate_equity_with_floating,
)


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

        # ارزیابی قوانین فقط معاملات مرتبط با همین مرحله را می‌خواند.
        trades = db.query(Trade).filter(
            Trade.prop_stage_id == stage_id
        ).all()

        return PropRuleEngine._evaluate_stage_with_trades(stage, trades)

    @staticmethod
    def evaluate_stages(db: Session, stage_ids) -> Dict[int, Dict[str, Any]]:
        """فاز ۳۶ — ارزیابی گروهی چند مرحله با **یک** کوئری معاملات.

        جایگزین الگوی N+1 (یک `evaluate_stage` به‌ازای هر مرحله) در داشبورد.
        """
        ids = list(dict.fromkeys(stage_ids))
        out: Dict[int, Dict[str, Any]] = {}
        if not ids:
            return out

        stages = db.query(PropStage).filter(PropStage.id.in_(ids)).all()
        by_id = {s.id: s for s in stages}

        grouped: Dict[int, List[Trade]] = {sid: [] for sid in ids}
        rows = db.query(Trade).filter(
            Trade.prop_stage_id.in_(ids)
        ).all()
        for t in rows:
            grouped.setdefault(t.prop_stage_id, []).append(t)

        for sid in ids:
            stage = by_id.get(sid)
            if stage is None:
                out[sid] = {
                    "stage_id": sid,
                    "ready_to_pass": False,
                    "error": "مرحله پیدا نشد",
                }
            else:
                out[sid] = PropRuleEngine._evaluate_stage_with_trades(
                    stage, grouped.get(sid, [])
                )
        return out

    @staticmethod
    def _evaluate_stage_with_trades(
        stage: PropStage, trades: List[Trade]
    ) -> Dict[str, Any]:
        """محاسبهٔ کامل ارزیابی با معاملات از پیش بارگذاری‌شده (فاز ۳۶)."""
        # ── مبالغ پایه (دلار) ──
        # فاز ۴۳: کل محاسبات PnL روی net_pnl (= pnl + commission + swap) انجام می‌شود.
        initial = stage.initial_balance or 10000.0
        day_offset = int(stage.day_boundary_utc_offset or 0)
        closed_trades = [t for t in trades if t.close_time is not None]
        open_trades = [t for t in trades if t.close_time is None]
        ordered_closed = sorted(closed_trades, key=lambda t: t.close_time or t.open_time)
        closed_pnl = sum(metrics.net_pnl(t) for t in ordered_closed)
        floating_pnl = sum(metrics.net_pnl(t) for t in open_trades)
        total_pnl = closed_pnl + floating_pnl

        dd_basis = stage.dd_basis or "balance"
        daily_dd_mode = stage.daily_dd_mode or "static"
        total_dd_mode = stage.total_dd_mode or "static"
        valid_dd_basis = dd_basis in {"balance", "equity"}
        valid_daily_mode = daily_dd_mode in {"static", "trailing"}
        valid_total_mode = total_dd_mode in {"static", "trailing"}
        modes_configured = valid_dd_basis and valid_daily_mode and valid_total_mode
        dd_basis = dd_basis if valid_dd_basis else "balance"
        daily_dd_mode = daily_dd_mode if valid_daily_mode else "static"
        total_dd_mode = total_dd_mode if valid_total_mode else "static"

        # dd_basis selects the series used by both Total DD modes.
        equity_curve = (
            calculate_equity_with_floating(initial, ordered_closed, open_trades)
            if dd_basis == "equity"
            else calculate_equity_curve(initial, ordered_closed)
        )
        balance = equity_curve[-1]["balance"]
        equity = balance + floating_pnl

        # Daily static measures the net day result; trailing measures the largest
        # peak-to-trough move within each day. Open PnL is included only for equity basis.
        daily_losses = PropRuleEngine._daily_drawdowns(
            ordered_closed,
            day_offset,
            daily_dd_mode,
            floating_pnl if dd_basis == "equity" else 0.0,
        )
        daily_pnl = PropRuleEngine._group_daily_pnl(closed_trades, day_offset)
        trading_days = len(daily_pnl)
        max_daily_loss = max(daily_losses.values(), default=0.0)

        # ── Total DD: static floor or running-peak drawdown ──
        max_total_dd_limit = stage.max_total_dd or 0.0
        if total_dd_mode == "trailing":
            total_dd_result = calculate_peak_to_trough_dd(equity_curve)
            max_total_dd = total_dd_result["dd"]
            equity_floor = (
                total_dd_result["peak"] - max_total_dd_limit
                if max_total_dd_limit > 0 else initial
            )
        else:
            total_dd_result = calculate_static_dd(initial, equity_curve)
            max_total_dd = total_dd_result["dd"]
            equity_floor = initial - max_total_dd_limit if max_total_dd_limit > 0 else initial
        total_dd_violated = (
            max_total_dd > max_total_dd_limit if max_total_dd_limit > 0 else False
        )

        # ── قوانین مرحله (دلار) ──
        profit_target = stage.profit_target or 0.0
        max_daily_dd_limit = stage.max_daily_dd or 0.0
        min_days = stage.min_trading_days or 0

        # ── فاز 47a.2: Fail-closed — نبودِ حد ⇒ unconfigured (نه «آماده پاس») ──
        violations: List[str] = []
        unconfigured = False
        if max_daily_dd_limit <= 0:
            violations.append("قانون Daily DD تنظیم نشده")
            unconfigured = True
        if max_total_dd_limit <= 0:
            violations.append("قانون Max DD تنظیم نشده")
            unconfigured = True
        if profit_target <= 0:
            violations.append("هدف سود تنظیم نشده")
            unconfigured = True
        if not modes_configured:
            violations.append("حالت محاسبهٔ Drawdown نامعتبر است")
            unconfigured = True

        # ── بررسی نقض قوانین (مقایسه‌ی دلار با دلار) ──
        daily_dd_violated = (
            max_daily_loss > max_daily_dd_limit
            if max_daily_dd_limit > 0
            else False
        )
        target_pnl = closed_pnl
        target_reached = target_pnl >= profit_target if profit_target > 0 else True
        min_days_met = trading_days >= min_days if min_days > 0 else True

        # ── violations: نقض واقعی ──
        if daily_dd_violated:
            violations.append(
                f"حد Daily DD نقض شده ({max_daily_loss:.2f}USDT  > {max_daily_dd_limit}USDT )"
            )
        if total_dd_violated:
            violations.append(
                f"حد Total DD نقض شده ({max_total_dd:.2f}USDT  > {max_total_dd_limit}USDT )"
            )

        # ── وضعیت پیشنهادی ──
        if unconfigured:
            suggested_status = "unconfigured"
        elif daily_dd_violated:
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
            user_share = closed_pnl * (profit_share / 100.0)
            withdrawable_profit = max(user_share - total_withdrawn, 0.0)
            ready_to_pass = False
        else:
            ready_to_pass = (
                (not unconfigured)
                and (not daily_dd_violated)
                and (not total_dd_violated)
                and target_reached
                and min_days_met
            )

        # ── درصدها (فقط برای نمایش) ──
        current_profit_percent = (
            round(closed_pnl / initial * 100, 2) if initial > 0 else 0.0
        )
        profit_progress_percent = (
            round(target_pnl / profit_target * 100, 2)
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
        rule_checks = PropRuleEngine._build_rule_checks(
            stage=stage,
            initial=initial,
            equity=equity,
            dd_basis_value=equity if dd_basis == "equity" else balance,
            dd_basis=dd_basis,
            floating_enabled=(dd_basis == "equity"),
            total_pnl=target_pnl,
            max_daily_loss=max_daily_loss,
            max_daily_dd_limit=max_daily_dd_limit,
            max_total_dd=max_total_dd,
            max_total_dd_limit=max_total_dd_limit,
            equity_floor=equity_floor,
            profit_target=profit_target,
            trading_days=trading_days,
            min_days=min_days,
            floating_pnl=floating_pnl,
        )
        is_historical = stage.status != StageStatus.ACTIVE
        if is_historical:
            # ── وضعیت برای مراحل تکمیل‌شده ──
            dd_sevs = [
                c["severity"] for c in rule_checks
                if c["rule_type"] not in (
                    RuleType.STAGE_STATUS,
                    RuleType.PROFIT_TARGET,
                    RuleType.MIN_TRADING_DAYS,
                )
            ]
            if Severity.VIOLATION in dd_sevs:
                overall_severity = Severity.VIOLATION
            elif Severity.WARNING in dd_sevs:
                overall_severity = Severity.WARNING
            else:
                overall_severity = Severity.PASS
            ready_to_pass = None
            suggested_status = stage.status.value if stage.status else "unknown"
            if any(c["severity"] == Severity.VIOLATION for c in rule_checks):
                violations.extend(
                    c["message"] for c in rule_checks
                    if c["severity"] == Severity.VIOLATION
                    and c["message"] not in violations
                )
        else:
            overall_severity = PropRuleEngine._overall_severity(rule_checks)
            ready_to_pass = (
                not is_funded
                and not unconfigured
                and target_reached
                and min_days_met
                and all(check["severity"] != Severity.VIOLATION for check in rule_checks)
            )
            if not is_funded:
                if ready_to_pass:
                    suggested_status = "ready_to_pass"
                elif not unconfigured and not daily_dd_violated and not total_dd_violated:
                    suggested_status = "in_progress"
            if any(check["severity"] == Severity.VIOLATION for check in rule_checks):
                violations.extend(
                    check["message"]
                    for check in rule_checks
                    if check["severity"] == Severity.VIOLATION
                    and check["message"] not in violations
                )

        return {
            "stage_id": stage.id,
            "stage_type": stage.stage_type.value if stage.stage_type else None,
            "status": stage.status.value if stage.status else None,
            "is_historical": is_historical,

            # موجودی و سود (دلار)
            "initial_balance": round(initial, 2),
            "balance": round(balance, 2),
            "equity": round(equity, 2),
            "current_profit": round(closed_pnl, 2),
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
            # فاز 47a — کف مجاز (static) و وضعیت پیکربندی
            "equity_floor": round(equity_floor, 2),
            "unconfigured": unconfigured,
            "dd_basis": dd_basis,
            "daily_dd_mode": daily_dd_mode,
            "total_dd_mode": total_dd_mode,

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
                f"مبلغ برداشت ({amount}USDT ) بیشتر از سود قابل برداشت "
                f"({withdrawable}USDT ) است"
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
        dd_basis_value: float,
        dd_basis: str,
        floating_enabled: bool,
        total_pnl: float,
        max_daily_loss: float,
        max_daily_dd_limit: float,
        max_total_dd: float,
        max_total_dd_limit: float,
        equity_floor: float,
        profit_target: float,
        trading_days: int,
        min_days: int,
        floating_pnl: float,
    ) -> List[Dict[str, Any]]:
        """۷ قاعده را ارزیابی و لیست نتایج ساختاریافته برمی‌گرداند."""
        checks: List[Dict[str, Any]] = []
        is_historical = stage.status != StageStatus.ACTIVE

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
            f"Daily DD: {max_daily_loss:.2f}USDT  از حد {max_daily_dd_limit:.2f}USDT ",
        )
        # ۲) Max (Total) Drawdown
        add(
            RuleType.MAX_DRAWDOWN, max_total_dd, max_total_dd_limit,
            PropRuleEngine._grade_loss(max_total_dd, max_total_dd_limit),
            f"Total DD: {max_total_dd:.2f}USDT  از حد {max_total_dd_limit:.2f}USDT ",
        )
        # ۳) Profit Target — برای مراحل تکمیل‌شده بی‌ربط
        if is_historical:
            add(
                RuleType.PROFIT_TARGET, total_pnl, profit_target, Severity.PASS,
                "برای مراحل تکمیل‌شده بی‌ربط",
            )
        elif profit_target > 0 and total_pnl >= profit_target:
            add(
                RuleType.PROFIT_TARGET, total_pnl, profit_target, Severity.PASS,
                f"سود: {total_pnl:.2f}USDT  از هدف {profit_target:.2f}USDT ",
            )
        else:
            tp_sev = Severity.WARNING if profit_target > 0 else Severity.PASS
            add(
                RuleType.PROFIT_TARGET, total_pnl, profit_target, tp_sev,
                f"سود: {total_pnl:.2f}USDT  از هدف {profit_target:.2f}USDT ",
            )
        # ۴) Min Trading Days — برای مراحل تکمیل‌شده بی‌ربط
        if is_historical:
            md_sev = Severity.PASS
            md_msg = "برای مراحل تکمیل‌شده بی‌ربط"
        else:
            md_sev = Severity.PASS if (min_days <= 0 or trading_days >= min_days) else Severity.WARNING
            md_msg = f"روزهای معاملاتی: {trading_days} از حداقل {min_days}"
        add(
            RuleType.MIN_TRADING_DAYS, float(trading_days), float(min_days),
            md_sev, md_msg,
        )
        # ۵) Balance / Equity rule according to the configured basis.
        if dd_basis_value < equity_floor:
            eq_sev = Severity.VIOLATION
        elif dd_basis_value < initial:
            eq_sev = Severity.WARNING
        else:
            eq_sev = Severity.PASS
        add(
            RuleType.EQUITY_BALANCE, dd_basis_value, equity_floor, eq_sev,
            f"موجودی مبنا ({dd_basis}): {dd_basis_value:.2f}USDT  (کف مجاز {equity_floor:.2f}USDT )",
        )
        # ۶) Floating PnL (معاملات باز) — زیان شناور مثبت
        floating_loss = max(-floating_pnl, 0.0)
        add(
            RuleType.FLOATING_PNL, floating_loss, max_daily_dd_limit,
            PropRuleEngine._grade_loss(floating_loss, max_daily_dd_limit)
            if floating_enabled else Severity.PASS,
            f"زیان شناور: {floating_loss:.2f}USDT  از حد {max_daily_dd_limit:.2f}USDT ",
        )
        # ۷) Stage Status — برای مراحل تکمیل‌شده فقط PASS
        if is_historical:
            ss_sev = Severity.PASS
            ss_msg = "این مرحله تکمیل شده است"
        else:
            ss_sev = Severity.PASS
            ss_msg = f"وضعیت مرحله: {stage.status.value if stage.status else 'unknown'}"
        add(
            RuleType.STAGE_STATUS,
            1.0,
            1.0,
            ss_sev,
            ss_msg,
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
    def _group_daily_pnl(
        trades: List[Trade], day_boundary_offset_minutes: int = 0
    ) -> Dict[str, float]:
        """گروه‌بندی PnL روزانه با مرز روز مشخص (فاز ۴۷.۲).

        `day_boundary_offset_minutes` مرز روز را نسبت به UTC جابه‌جا می‌کند
        (پیش‌فرض 0 = 00:00 UTC مطابق تصمیم D2 کاربر). زمان naive به‌عنوان UTC
        تفسیر می‌شود.
        """
        from datetime import timedelta, timezone

        daily: Dict[str, float] = {}
        for t in trades:
            if not t.close_time:
                continue
            dt = t.close_time
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local = dt + timedelta(minutes=day_boundary_offset_minutes or 0)
            day_key = local.date().isoformat()
            daily[day_key] = daily.get(day_key, 0.0) + metrics.net_pnl(t)
        return daily

    @staticmethod
    def _daily_drawdowns(
        ordered_trades: List[Trade],
        day_boundary_offset_minutes: int,
        mode: str,
        floating_pnl: float = 0.0,
    ) -> Dict[str, float]:
        """Calculate intraday loss from day start (static) or running peak (trailing)."""
        from datetime import timedelta, timezone

        daily_trades: Dict[str, List[Trade]] = {}
        for trade in ordered_trades:
            if trade.close_time is None:
                continue
            closed_at = trade.close_time
            if closed_at.tzinfo is None:
                closed_at = closed_at.replace(tzinfo=timezone.utc)
            day = (closed_at + timedelta(minutes=day_boundary_offset_minutes or 0)).date().isoformat()
            daily_trades.setdefault(day, []).append(trade)

        drawdowns: Dict[str, float] = {}
        for day, trades in daily_trades.items():
            pnl_values = [metrics.net_pnl(trade) for trade in trades]
            if mode == "trailing":
                peak = 0.0
                equity = 0.0
                max_dd = 0.0
                for pnl in pnl_values:
                    equity += pnl
                    peak = max(peak, equity)
                    max_dd = max(max_dd, peak - equity)
                drawdowns[day] = max_dd
            else:
                # Normalize the start-of-day balance to zero: the absolute
                # balance cancels in balance_start_of_day - min_equity.
                cumulative = 0.0
                min_equity = 0.0
                for pnl in pnl_values:
                    cumulative += pnl
                    min_equity = min(min_equity, cumulative)
                drawdowns[day] = -min_equity

        if floating_pnl:
            now = datetime.now(timezone.utc)
            day = (now + timedelta(minutes=day_boundary_offset_minutes or 0)).date().isoformat()
            if mode == "trailing":
                # A floating equity snapshot is the latest point in today's curve.
                trades = daily_trades.get(day, [])
                running = 0.0
                peak = 0.0
                max_dd = 0.0
                for trade in trades:
                    running += metrics.net_pnl(trade)
                    peak = max(peak, running)
                    max_dd = max(max_dd, peak - running)
                current_equity = running + floating_pnl
                drawdowns[day] = max(drawdowns.get(day, 0.0), peak - current_equity, 0.0)
            else:
                realized = sum(metrics.net_pnl(trade) for trade in daily_trades.get(day, []))
                drawdowns[day] = max(drawdowns.get(day, 0.0), -(realized + floating_pnl), 0.0)
        return drawdowns

    @staticmethod
    def _total_drawdown(
        ordered_trades: List[Trade],
        initial: float,
        max_dd_limit: float,
    ) -> Tuple[float, float, bool]:
        """Static Drawdown — افت از **کف ثابت** (فاز 47a).

        Args:
            ordered_trades: فقط تریدهای بسته، مرتب‌شده به ترتیب زمانی.
            initial: موجودی اولیه.
            max_dd_limit: سقف DD (0 ⇒ تنظیم‌نشده ⇒ بدون نقض).

        Returns:
            `(total_dd, equity_floor, violated)`
            - `equity_floor = initial − max_dd_limit`
            - `total_dd     = max(0, initial − min_equity)`
            - `violated     = min_equity < equity_floor`
        """
        equity = initial
        min_equity = initial
        for trade in ordered_trades:
            equity += metrics.net_pnl(trade)
            if equity < min_equity:
                min_equity = equity

        total_dd = max(0.0, initial - min_equity)
        if max_dd_limit and max_dd_limit > 0:
            equity_floor = initial - max_dd_limit
            violated = min_equity < equity_floor
        else:  # تنظیم‌نشده ⇒ بدون نقض (fail-closed در لایهٔ unconfigured)
            equity_floor = initial
            violated = False
        return total_dd, equity_floor, violated

    @staticmethod
    def _calculate_max_drawdown(trades: List[Trade], initial: float) -> float:
        # فاز ۴۳: محاسبه در `metrics` متمرکز شده است (با ترتیب زمانی معاملات).
        ordered = sorted(trades, key=lambda t: t.close_time or t.open_time)
        return metrics.calculate_max_drawdown(ordered, initial)
