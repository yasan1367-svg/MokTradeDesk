from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional

from ..models.strategy import (
    Trade, AnalysisResult, AnalysisRun, CustomTimeInterval,
    AnalysisScope, TestType,
    AnalysisScopeRecord, AnalysisStatus,
)
from ..utils.trade_scope import analysis_trades_filter, version_scope_key
from ..utils.date_range import filter_by_range
from ..utils.time_utils import to_tehran
from . import metrics
from .version_score import calculate_version_score


def _chronological(trades: List[Trade]) -> List[Trade]:
    """ترتیب زمانی معاملات (مبنای محاسبهٔ drawdown/streak)."""
    return sorted(trades, key=lambda t: t.close_time or t.open_time)



# ═════════════════════════════════════════════
# فاز 48a — مقایسه و رتبه‌بندی نسخه‌ها (Comparison & Ranking)
# ═════════════════════════════════════════════
def _normalize_test_type(test_type) -> Optional[TestType]:
    """تبدیل رشته/Enum نوع تست به Enum (نامعتبر/خالی ⇒ None)."""
    if test_type is None:
        return None
    if isinstance(test_type, TestType):
        return test_type
    try:
        return TestType(str(test_type).strip().lower())
    except ValueError:
        return None


def _extract_metrics(analysis: AnalysisResult) -> Dict[str, Any]:
    """متریک‌های ذخیره‌شدهٔ یک AnalysisResult به‌شکل دیکشنری."""
    return {
        "version_id": analysis.version_id,
        "total_trades": analysis.total_trades,
        "win_rate": analysis.win_rate,
        "profit_factor": analysis.profit_factor,
        "net_pnl": analysis.net_pnl,
        "net_r": analysis.net_r,
        "max_dd": analysis.max_dd,
        "expectancy": analysis.expectancy,
        "expectancy_r": analysis.expectancy_r,
        "avg_win": analysis.avg_win,
        "avg_loss": analysis.avg_loss,
        "largest_win": analysis.largest_win,
        "largest_loss": analysis.largest_loss,
        "max_consecutive_losses": analysis.max_consecutive_losses,
    }


def _calculate_filtered_metrics(
    version_id: int,
    test_type,
    symbol: Optional[str],
    date_from,
    date_to,
    db: Session,
) -> Dict[str, Any]:
    """محاسبهٔ مجدد متریک‌ها روی تریدهای فیلترشده (نماد/بازهٔ تاریخ) — فاز 48a/53.4.

    - `test_type` مشخص (BACKTEST/FORWARD/REAL_*) ⇒ همان نوع (بدون قید غیر-REAL).
      این اجازه می‌دهد **مقایسهٔ REAL** هم کار کند (فاز ۵۳.۴.۱).
    - `test_type=None` (legacy) ⇒ فقط معاملات غیر-REAL (`analysis_trades_filter`).
    - بازهٔ تاریخ **شامل آخرین روز** است و روی `close_time` اعمال می‌شود
      (قابل‌اعمال بر REAL که open/close مستقل دارند).
    """
    tt = _normalize_test_type(test_type)
    q = db.query(Trade).filter(
        Trade.version_id == version_id,
    )
    if tt is None:
        q = q.filter(analysis_trades_filter())
    else:
        q = q.filter(Trade.test_type == tt)
    if symbol:
        q = q.filter(Trade.symbol == symbol)
    q = filter_by_range(q, Trade.close_time, date_from, date_to)

    trades = q.all()
    basic = AnalysisService(db)._calculate_basic_metrics(trades)
    return {"version_id": version_id, **basic}


def generate_reasons(
    version_id: int, metrics: Dict[str, Any], best_metrics: Dict[str, Any]
) -> List[Dict[str, str]]:
    """دلایل سادهٔ برتری/ضعف یک نسخه نسبت به بهترین نسخه (فاز 48a)."""
    if not best_metrics or metrics.get("version_id") == best_metrics.get("version_id"):
        return [{"icon": "🏆", "text": "بهترین نسخه بر اساس امتیاز"}]

    reasons: List[Dict[str, str]] = []
    if (metrics.get("net_pnl") or 0) > (best_metrics.get("net_pnl") or 0):
        reasons.append({"icon": "💰", "text": f"سود خالص بیشتر (+{metrics['net_pnl']}USDT )"})
    if (metrics.get("win_rate") or 0) > (best_metrics.get("win_rate") or 0):
        reasons.append({"icon": "✅", "text": f"نرخ برد بالاتر ({metrics['win_rate']}٪)"})
    if (metrics.get("max_dd") or 0) < (best_metrics.get("max_dd") or 0):
        reasons.append({"icon": "🛡️", "text": f"افت سرمایه کمتر (-{metrics['max_dd']}USDT )"})
    if (metrics.get("profit_factor") or 0) > (best_metrics.get("profit_factor") or 0):
        reasons.append({"icon": "🏆", "text": f"فاکتور سود بالاتر ({metrics['profit_factor']})"})
    if not reasons:
        reasons.append({"icon": "📊", "text": "عملکرد نزدیک به بهترین نسخه"})
    return reasons


def compare_versions(
    version_ids: List[int],
    test_type: str = "BACKTEST",
    symbol: Optional[str] = None,
    date_from=None,
    date_to=None,
    db: Session = None,
) -> Dict[str, Any]:
    """مقایسهٔ چند نسخه + فیلتر (نماد/تاریخ) + Score/Rank — فاز 48a.

    نسخهٔ تحلیل‌نشده با فیلد `error` گزارش می‌شود (بدون خطا/۴۰۴).
    خروجی: `{comparison, test_type, filters, best}`.
    """
    results: List[Dict[str, Any]] = []
    tt = _normalize_test_type(test_type)
    # فاز ۵۳.۴.۱: معاملات REAL تحلیلِ ذخیره‌شده ندارند ⇒ همیشه زنده محاسبه می‌شوند
    is_real = tt in (TestType.REAL_PERSONAL, TestType.REAL_PROP)

    for vid in version_ids:
        if is_real:
            metrics_d = _calculate_filtered_metrics(
                vid, tt, symbol, date_from, date_to, db
            )
            if not metrics_d.get("total_trades"):
                results.append({
                    "version_id": vid,
                    "error": "هیچ معاملهٔ REAL برای این نسخه یافت نشد",
                })
                continue
        else:
            key = version_scope_key(vid, tt)
            analysis = db.query(AnalysisResult).filter(
                AnalysisResult.scope == AnalysisScope.VERSION,
                AnalysisResult.scope_key == key,
            ).first()
            # سازگاری: رکوردهای legacy که با کلید `str(vid)` ذخیره شده‌اند
            if analysis is None and key != str(vid):
                analysis = db.query(AnalysisResult).filter(
                    AnalysisResult.scope == AnalysisScope.VERSION,
                    AnalysisResult.scope_key == str(vid),
                ).first()

            if not analysis:
                results.append({
                    "version_id": vid,
                    "error": "تحلیل نشده — اول «تحلیل مجدد» را بزن",
                })
                continue

            if symbol or date_from or date_to:
                metrics_d = _calculate_filtered_metrics(
                    vid, tt, symbol, date_from, date_to, db
                )
            else:
                metrics_d = _extract_metrics(analysis)

        score_result = calculate_version_score(metrics_d)
        results.append({
            "version_id": vid,
            "metrics": metrics_d,
            "score": score_result["score"],
            "sample_status": score_result["sample_status"],
            "warnings": score_result["warnings"],
            "components": score_result["components"],
        })

    # مرتب‌سازی بر پایهٔ Score (نسخه‌های تحلیل‌نشده با امتیاز ۰ در انتها)
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    best = next((r for r in results if "metrics" in r), None)
    best_metrics = best["metrics"] if best else {}
    for r in results:
        if "metrics" in r:
            r["reasons"] = generate_reasons(r["version_id"], r["metrics"], best_metrics)

    return {
        "comparison": results,
        "test_type": getattr(tt, "name", None) or test_type,
        "filters": {"symbol": symbol, "date_from": date_from, "date_to": date_to},
        "best": best,
    }


class AnalysisService:
    """سرویس تحلیل معاملات — نسخه، پراپ و بروکر (فاز 20)"""

    def __init__(self, db: Session):
        self.db = db

    def analyze_version(self, version_id: int, test_type: Optional[TestType] = None) -> Dict[str, Any]:
        """تحلیل Backtest/Forward یک نسخه (معاملات REAL حذف می‌شوند).

        فاز ۲۳: Backtest و Forward مستقل ذخیره می‌شوند (کلید دامنه شامل test_type است).
        """
        q = self.db.query(Trade).filter(Trade.version_id == version_id, Trade.close_time.isnot(None), analysis_trades_filter())
        if test_type is not None:
            q = q.filter(Trade.test_type == test_type)
        return self._analyze(
            q.all(),
            scope=AnalysisScope.VERSION,
            scope_key=version_scope_key(version_id, test_type),
            version_id=version_id,
            test_type=test_type,
        )

    def analyze_prop_stage(self, prop_stage_id: int) -> Dict[str, Any]:
        """تحلیل کامل یک مرحله پراپ + PropRuleEngine.evaluate_stage()"""
        # فاز ۲۵: معاملات حذف‌شده از تحلیل کنار گذاشته می‌شوند
        trades = self.db.query(Trade).filter(
            Trade.prop_stage_id == prop_stage_id,
            Trade.close_time.isnot(None),
        ).all()
        result = self._analyze(trades, scope=AnalysisScope.PROP_STAGE, scope_key=str(prop_stage_id), prop_stage_id=prop_stage_id)
        from ..services.prop_rule_engine import PropRuleEngine
        result["prop_rules"] = PropRuleEngine.evaluate_stage(self.db, prop_stage_id)
        return result

    def analyze_personal_account(self, personal_trading_account_id: int) -> Dict[str, Any]:
        """تحلیل کامل یک حساب معاملاتی شخصی (معاملات REAL_PERSONAL)."""
        # فاز ۲۵: معاملات حذف‌شده از تحلیل کنار گذاشته می‌شوند
        trades = self.db.query(Trade).filter(
            Trade.personal_trading_account_id == personal_trading_account_id,
            Trade.close_time.isnot(None),
        ).all()
        return self._analyze(
            trades,
            scope=AnalysisScope.PERSONAL_ACCOUNT,
            scope_key=str(personal_trading_account_id),
            personal_trading_account_id=personal_trading_account_id,
        )

    def _analyze(self, trades, scope, scope_key, version_id=None, prop_stage_id=None,
                 personal_trading_account_id=None, test_type=None) -> Dict[str, Any]:
        """موتور مشترک — محاسبه متریک و ذخیره AnalysisResult + AnalysisRun"""
        if not trades:
            stale = self.db.query(AnalysisResult).filter(AnalysisResult.scope == scope, AnalysisResult.scope_key == scope_key).first()
            if stale:
                self.db.delete(stale)
                self.db.commit()
            if scope == AnalysisScope.VERSION:
                if test_type is not None:
                    label = {
                        TestType.BACKTEST: "بک‌تست",
                        TestType.FORWARD: "فوروارد",
                        TestType.REAL_PERSONAL: "رییل شخصی",
                        TestType.REAL_PROP: "رییل پراپ",
                    }.get(test_type, test_type.name)
                    raise ValueError(f"این استراتژی معاملات {label} ندارد")
                raise ValueError("هیچ معامله‌ای برای تحلیل این نسخه یافت نشد (معاملات REAL در تحلیل Backtest/Forward شمرده نمی‌شوند)")
            raise ValueError("هیچ معامله‌ای برای این دامنه یافت نشد")

        basic = self._calculate_basic_metrics(trades)
        session_a = self._analyze_by_session(trades)
        weekday_a = self._analyze_by_weekday(trades)
        hour_a = self._analyze_by_hour(trades)
        custom_a = self._analyze_by_custom_intervals(trades)
        consist_a = self._calculate_consistency(trades)

        existing = self.db.query(AnalysisResult).filter(AnalysisResult.scope == scope, AnalysisResult.scope_key == scope_key).first()
        if existing:
            self.db.delete(existing)
            self.db.commit()

        # ── فاز ۳۴: ساخت AnalysisScopeRecord (دامنهٔ این اجرا) ──
        open_times = [t.open_time for t in trades if t.open_time]
        close_times = [t.close_time for t in trades if t.close_time]
        scope_record = AnalysisScopeRecord(
            strategy_version_id=version_id,
            trade_type=self._resolve_trade_type(scope, test_type, trades),
            personal_trading_account_id=personal_trading_account_id,
            prop_stage_id=prop_stage_id,
            from_date=min(open_times) if open_times else None,
            to_date=max(close_times) if close_times else None,
            is_deleted_filter=True,  # در تحلیل، معاملات حذف‌شده کنار گذاشته می‌شوند
        )
        self.db.add(scope_record)
        self.db.flush()

        result = AnalysisResult(
            scope=scope, scope_key=scope_key, version_id=version_id,
            prop_stage_id=prop_stage_id,
            personal_trading_account_id=personal_trading_account_id,
            total_trades=basic["total_trades"], win_rate=basic["win_rate"],
            profit_factor=basic["profit_factor"], net_pnl=basic["net_pnl"],
            net_r=basic["net_r"], max_dd=basic["max_dd"],
            expectancy=basic["expectancy"], expectancy_r=basic["expectancy_r"],
            avg_win=basic["avg_win"], avg_loss=basic["avg_loss"],
            largest_win=basic["largest_win"], largest_loss=basic["largest_loss"],
            max_consecutive_losses=basic["max_consecutive_losses"],
            consistency_analysis=consist_a, session_analysis=session_a,
            weekday_analysis=weekday_a, hour_analysis=hour_a,
            custom_time_analysis=custom_a,
        )
        self.db.add(result)
        self.db.flush()

        snap = {"basic": basic, "consistency": consist_a, "session": session_a,
                "weekday": weekday_a, "hour": hour_a, "custom_time": custom_a}
        # ── فاز ۳۵: هر اجرا یک Run جدید (Run #1 ثابت، Run #2 جدا) ──
        filters_snapshot = {
            "scope": scope.value if hasattr(scope, "value") else str(scope),
            "scope_key": scope_key,
            "version_id": version_id,
            "prop_stage_id": prop_stage_id,
            "personal_trading_account_id": personal_trading_account_id,
            "test_type": test_type.name if test_type is not None else None,
            "is_deleted_filter": True,
        }
        run = AnalysisRun(
            scope=scope, scope_key=scope_key, version_id=version_id,
            prop_stage_id=prop_stage_id,
            personal_trading_account_id=personal_trading_account_id,
            total_trades=basic["total_trades"], win_rate=basic["win_rate"],
            profit_factor=basic["profit_factor"], net_pnl=basic["net_pnl"],
            net_r=basic["net_r"], max_dd=basic["max_dd"],
            expectancy=basic["expectancy"], expectancy_r=basic["expectancy_r"],
            avg_win=basic["avg_win"], avg_loss=basic["avg_loss"],
            largest_win=basic["largest_win"], largest_loss=basic["largest_loss"],
            max_consecutive_losses=basic["max_consecutive_losses"],
            full_metrics=snap,
            # فاز ۳۴/۳۵ (افزودنی)
            scope_id=scope_record.id,
            filters_snapshot=filters_snapshot,
            trade_count=basic["total_trades"],
            status=AnalysisStatus.COMPLETED,
        )
        self.db.add(run)
        self.db.flush()

        # اتصال نتیجهٔ جاری به اجرای همین بار
        result.analysis_run_id = run.id

        self.db.commit()
        self.db.refresh(result)

        return {"result": result, "run_id": run.id, "scope_id": scope_record.id,
                "message": "تحلیل انجام شد و در تاریخچه ذخیره گردید"}

    @staticmethod
    def _resolve_trade_type(scope, test_type, trades) -> TestType:
        """نوع معاملهٔ دامنه را تعیین می‌کند (فاز ۳۴).

        - VERSION          : test_type داده‌شده، وگرنه نوع غالب معاملات، وگرنه BACKTEST
        - PROP_STAGE       : REAL_PROP
        - PERSONAL_ACCOUNT : REAL_PERSONAL
        """
        if scope == AnalysisScope.PROP_STAGE:
            return TestType.REAL_PROP
        if scope == AnalysisScope.PERSONAL_ACCOUNT:
            return TestType.REAL_PERSONAL
        if test_type is not None:
            return test_type
        for t in trades:
            if t.test_type is not None:
                return t.test_type
        return TestType.BACKTEST



    # ═════════════════════════════════════════════
    # ═════════════════════════════════════════════
    # متریک‌های پایه
    # ═════════════════════════════════════════════
    def _calculate_basic_metrics(self, trades: List[Trade]) -> Dict[str, Any]:
        """
        محاسبه‌ی متریک‌های پایه.

        نکته: تمام محاسبات PnL بر اساس **net_pnl** هست:
            net_pnl = pnl + commission + swap
        (چون commission معمولاً منفی ذخیره می‌شه، جمعش یعنی کم شدن)
        """

        total = len(trades)
        wins = [t for t in trades if metrics.net_pnl(t) > 0]
        losses = [t for t in trades if metrics.net_pnl(t) < 0]

        gross_profit = sum(metrics.net_pnl(t) for t in wins) if wins else 0
        gross_loss = abs(sum(metrics.net_pnl(t) for t in losses)) if losses else 0

        net_pnl = sum(metrics.net_pnl(t) for t in trades)
        win_rate = (len(wins) / total * 100) if total > 0 else 0
        profit_factor = self._profit_factor(gross_profit, gross_loss)

        r_multiples = [t.r_multiple for t in trades if t.r_multiple is not None]
        net_r = sum(r_multiples) if r_multiples else 0

        max_dd = metrics.calculate_max_drawdown(_chronological(trades))

        # اکسپکتنسی، میانگین/بزرگ‌ترین برد و باخت
        avg_win = (gross_profit / len(wins)) if wins else 0
        avg_loss = (gross_loss / len(losses)) if losses else 0  # مقدار مثبت
        largest_win = max((metrics.net_pnl(t) for t in wins), default=0)
        largest_loss = abs(min((metrics.net_pnl(t) for t in losses), default=0))  # مقدار مثبت

        win_rate_ratio = (len(wins) / total) if total > 0 else 0
        loss_rate_ratio = (len(losses) / total) if total > 0 else 0
        expectancy = (win_rate_ratio * avg_win) - (loss_rate_ratio * avg_loss)
        expectancy_r = (sum(r_multiples) / len(r_multiples)) if r_multiples else None

        max_consecutive_losses = self._calculate_max_consecutive_losses(trades)

        return {
            "total_trades": total,
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "net_pnl": round(net_pnl, 2),
            "net_r": round(net_r, 2),
            "max_dd": round(max_dd, 2),
            "expectancy": round(expectancy, 2),
            "expectancy_r": round(expectancy_r, 3) if expectancy_r is not None else None,
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "largest_win": round(largest_win, 2),
            "largest_loss": round(largest_loss, 2),
            "max_consecutive_losses": max_consecutive_losses,
        }

    def _profit_factor(self, gross_profit: float, gross_loss: float) -> float:
        """
        Profit factor with the shared edge-case sentinel from metrics.
        """
        return metrics.profit_factor_from_sums(gross_profit, gross_loss)

    def _calculate_max_consecutive_losses(self, trades: List[Trade]) -> int:
        sorted_trades = _chronological(trades)
        streak = 0
        max_streak = 0
        for t in sorted_trades:
            npnl = metrics.net_pnl(t)
            if npnl < 0:
                streak += 1
                max_streak = max(max_streak, streak)
            elif npnl > 0:
                streak = 0
            # معامله‌ی سربه‌سر (pnl == 0) استریک رو نمی‌شکنه و اضافه‌ش هم نمی‌کنه
        return max_streak

    def _calculate_consistency(self, trades: List[Trade]) -> Dict[str, Any]:
        """
        تحلیل پایداری:
        - pnl_std_dev: انحراف معیار سود/زیان معاملات (یکنواختی سودها)
        - top_trades_contribution_percent: چند درصد از کل سود ناخالص از چند معامله‌ی برتر اومده
          (وابستگی به معاملات بزرگ)
        - avg_win_avg_loss_ratio: نسبت میانگین برد به میانگین باخت
        """
        wins = [t for t in trades if metrics.net_pnl(t) > 0]
        losses = [t for t in trades if metrics.net_pnl(t) < 0]
        pnl_values = [metrics.net_pnl(t) for t in trades]

        if not pnl_values:
            return {
                "pnl_std_dev": 0,
                "top_trades_contribution_percent": 0,
                "top_trades_contribution_label": "Top 3 share of gross winning PnL",
                "avg_win_avg_loss_ratio": 0,
            }

        mean_pnl = sum(pnl_values) / len(pnl_values)
        variance = sum((p - mean_pnl) ** 2 for p in pnl_values) / len(pnl_values)
        pnl_std_dev = variance ** 0.5

        gross_profit = sum(metrics.net_pnl(t) for t in wins) if wins else 0
        top_n = sorted((metrics.net_pnl(t) for t in wins), reverse=True)[:3]
        top_trades_contribution = (sum(top_n) / gross_profit * 100) if gross_profit > 0 else 0

        avg_win = (gross_profit / len(wins)) if wins else 0
        gross_loss = abs(sum(metrics.net_pnl(t) for t in losses)) if losses else 0
        avg_loss = (gross_loss / len(losses)) if losses else 0
        avg_win_avg_loss_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0

        return {
            "pnl_std_dev": round(pnl_std_dev, 2),
            "top_trades_contribution_percent": round(top_trades_contribution, 1),
            "top_trades_contribution_label": "Top 3 share of gross winning PnL",
            "avg_win_avg_loss_ratio": round(avg_win_avg_loss_ratio, 2),
        }

    def _analyze_by_session(self, trades: List[Trade]) -> Dict[str, Any]:
        """تحلیل سشن بر پایهٔ **زمان ورود** (`open_time`) — فاز 48a.3."""
        sessions = {"Asia": [], "Europe": [], "America": [], "Other": []}

        for t in trades:
            if not t.open_time:
                continue
            hour = t.open_time.hour
            if 0 <= hour < 8:
                sessions["Asia"].append(t)
            elif 8 <= hour < 16:
                sessions["Europe"].append(t)
            elif 16 <= hour < 24:
                sessions["America"].append(t)
            else:
                sessions["Other"].append(t)

        return {name: self._summarize(trades) for name, trades in sessions.items() if trades}

    def _analyze_by_weekday(self, trades: List[Trade]) -> Dict[str, Any]:
        """تحلیل روز هفته بر پایهٔ **زمان ورود** (`open_time`) — فاز 48a.3."""
        weekdays = {
            0: "Monday", 1: "Tuesday", 2: "Wednesday",
            3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
        }
        by_day = {day: [] for day in weekdays.values()}

        for t in trades:
            if not t.open_time:
                continue
            day_name = weekdays[t.open_time.weekday()]
            by_day[day_name].append(t)

        return {name: self._summarize(trades) for name, trades in by_day.items() if trades}

    def _analyze_by_hour(self, trades: List[Trade]) -> Dict[str, Any]:
        """تحلیل ساعت بر پایهٔ **زمان ورود** (`open_time`) — فاز 48a.3."""
        by_hour = {str(h): [] for h in range(24)}

        for t in trades:
            if not t.open_time:
                continue
            hour = str(t.open_time.hour)
            by_hour[hour].append(t)

        return {h: self._summarize(trades) for h, trades in by_hour.items() if trades}

    def _analyze_by_custom_intervals(self, trades: List[Trade]) -> Dict[str, Any]:
        intervals = self.db.query(CustomTimeInterval).filter(
            CustomTimeInterval.is_active == 1
        ).all()

        result = {}
        for interval in intervals:
            matched = []
            for t in trades:
                if not t.open_time:
                    continue
                if t.symbol != interval.symbol:
                    continue
                tehran = to_tehran(t.open_time)
                hour = tehran.hour
                minute = tehran.minute
                start = interval.start_hour * 60 + interval.start_minute
                end = interval.end_hour * 60 + interval.end_minute
                current = hour * 60 + minute
                if start <= current <= end:
                    matched.append(t)

            if matched:
                result[f"{interval.name} [{interval.label or '-'}]"] = self._summarize(matched)

        return result

    def _summarize(self, trades: List[Trade]) -> Dict[str, Any]:
        total = len(trades)
        wins = [t for t in trades if metrics.net_pnl(t) > 0]
        losses = [t for t in trades if metrics.net_pnl(t) < 0]

        gross_profit = sum(metrics.net_pnl(t) for t in wins) if wins else 0
        gross_loss = abs(sum(metrics.net_pnl(t) for t in losses)) if losses else 0

        net_pnl = sum(metrics.net_pnl(t) for t in trades) or 0
        win_rate = (len(wins) / total * 100) if total > 0 else 0
        profit_factor = self._profit_factor(gross_profit, gross_loss)

        return {
            "total_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 2),
            "net_pnl": round(net_pnl, 2),
            "profit_factor": round(profit_factor, 2),
        }
