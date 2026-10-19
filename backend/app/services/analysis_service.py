import hashlib
import json
from collections import defaultdict
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session

from ..models.strategy import (
    Trade, StrategyVersion, AnalysisResult, AnalysisRun, CustomTimeInterval,
    AnalysisScope, TestType,
    AnalysisScopeRecord, AnalysisStatus,
)
from ..utils.trade_scope import (
    analysis_trades_filter, closed_analysis_trades_filter, version_scope_key,
)
from ..utils.date_range import filter_by_range
from ..utils.time_utils import to_tehran
from . import metrics
from .version_score import calculate_version_score


class AnalysisStaleError(Exception):
    """تحلیل ذخیره‌شده کهنه شده — تحلیل مجدد لازم است."""


TRADE_FINGERPRINT_FORMAT = 3
ANALYSIS_ENGINE_VERSION = "analysis-engine-1"
SCORE_POLICY_VERSION = "score-policy-2"


def _trade_freshness_fingerprint(trades) -> str:
    """Versioned signature of all closed-trade inputs used by metrics/filters."""
    rows = sorted(
        (
            trade.id,
            trade.pnl,
            trade.commission,
            trade.swap,
            trade.r_multiple,
            trade.symbol,
            _normalized_timestamp(trade.open_time),
            _normalized_timestamp(trade.close_time),
        )
        for trade in trades
    )
    payload = json.dumps(
        {"format": TRADE_FINGERPRINT_FORMAT, "trades": rows},
        separators=(",", ":"), ensure_ascii=True, sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalized_timestamp(value):
    """Stable timestamp encoding; retain naive/aware distinction and no TZ policy."""
    if value is None:
        return None
    return value.isoformat(timespec="microseconds")


def check_analysis_freshness(
    db: Session,
    version_id: int,
    scope_key: str,
    result: "AnalysisResult",
) -> None:
    """بررسی تعداد و آخرین ویرایش معاملات دامنه؛ خطا با AnalysisStaleError."""
    from datetime import timezone
    from sqlalchemy import func

    # دامنه باید متعلق به snapshot باشد؛ کلید legacy شامل Backtest/Forward است.
    tt = None
    prefix = f"{version_id}:"
    if scope_key and scope_key.startswith(prefix):
        tt = _normalize_test_type(scope_key[len(prefix):])
    q = db.query(Trade).filter(
        Trade.version_id == version_id,
        closed_analysis_trades_filter(),
    )
    if tt is not None:
        q = q.filter(Trade.test_type == tt)
    count, max_updated = q.with_entities(
        func.count(Trade.id), func.max(Trade.updated_at)
    ).one()
    if count == 0:
        raise AnalysisStaleError(
            "تحلیل کهنه است؛ هیچ معامله‌ای برای دامنهٔ Backtest/Forward این تحلیل یافت نشد "
            "(معاملات REAL در تحلیل نسخه شمرده نمی‌شوند). دوباره تحلیل کنید."
        )

    run = getattr(result, "analysis_run", None)
    snapshot = getattr(run, "filters_snapshot", None) or {}
    stored_format = snapshot.get("trade_fingerprint_format")
    stored_fingerprint = snapshot.get("trade_freshness_fingerprint")
    if stored_fingerprint:
        if stored_format != TRADE_FINGERPRINT_FORMAT:
            raise AnalysisStaleError(
                "تحلیل فاقد نسخهٔ معتبر fingerprint است؛ برای تأیید تازگی دوباره تحلیل کنید."
            )
        current_fingerprint = _trade_freshness_fingerprint(q.all())
        if current_fingerprint != stored_fingerprint:
            raise AnalysisStaleError(
                "تحلیل کهنه است (دادهٔ معاملات پس از تحلیل تغییر کرده است). دوباره تحلیل کنید."
            )
    else:
        raise AnalysisStaleError(
            "تحلیل قدیمی فاقد fingerprint است؛ برای تأیید تازگی دوباره تحلیل کنید."
        )
    if result.total_trades != count:
        raise AnalysisStaleError(
            f"تحلیل کهنه است ({result.total_trades} در برابر {count} معامله). دوباره تحلیل کنید."
        )

    if snapshot.get("rules_hash"):
        current_rules = {"rules_note": db.query(StrategyVersion.rules_note).filter(
            StrategyVersion.id == version_id
        ).scalar()}
        current_rules_hash = hashlib.sha256(json.dumps(
            current_rules, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        ).encode("utf-8")).hexdigest()
        if current_rules_hash != snapshot["rules_hash"]:
            raise AnalysisStaleError("قواعد نسخه پس از تحلیل تغییر کرده‌اند؛ دوباره تحلیل کنید.")

    def as_utc_naive(value):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    if max_updated is not None and result.created_at is not None:
        if as_utc_naive(result.created_at) < as_utc_naive(max_updated):
            raise AnalysisStaleError(
                "تحلیل کهنه است (معاملات پس از تحلیل ویرایش شده‌اند). دوباره تحلیل کنید."
            )


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
    except ValueError as exc:
        raise ValueError(f"نوع تست نامعتبر است: {test_type}") from exc


def _extract_metrics(analysis: AnalysisResult) -> Dict[str, Any]:
    """متریک‌های ذخیره‌شدهٔ یک AnalysisResult به‌شکل دیکشنری."""
    full_metrics = getattr(
        getattr(analysis, "analysis_run", None), "full_metrics", None
    ) or {}
    basic_metrics = full_metrics.get("basic", {}) if isinstance(full_metrics, dict) else {}
    return {
        "version_id": analysis.version_id,
        "total_trades": analysis.total_trades,
        "win_rate": analysis.win_rate,
        "profit_factor": analysis.profit_factor,
        "gross_profit": basic_metrics.get("gross_profit"),
        "gross_loss": basic_metrics.get("gross_loss"),
        "profit_factor_status": basic_metrics.get("profit_factor_status"),
        "net_pnl": analysis.net_pnl,
        "net_r": analysis.net_r,
        "max_dd": analysis.max_dd,
        "max_dd_percent": basic_metrics.get(
            "max_dd_percent", getattr(analysis, "max_dd_percent", None)
        ),
        "expectancy": analysis.expectancy,
        "expectancy_r": analysis.expectancy_r,
        "r_valid_count": basic_metrics.get("r_valid_count", getattr(analysis, "r_valid_count", None)),
        "r_coverage_percent": basic_metrics.get("r_coverage_percent", getattr(analysis, "r_coverage_percent", None)),
        "avg_win": analysis.avg_win,
        "avg_loss": analysis.avg_loss,
        "largest_win": analysis.largest_win,
        "largest_loss": analysis.largest_loss,
        "max_consecutive_losses": analysis.max_consecutive_losses,
        "custom_time_analysis": analysis.custom_time_analysis or {},
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
    if test_type is None:
        tt = None
    q = db.query(Trade).filter(
        Trade.version_id == version_id,
        Trade.close_time.isnot(None),
    )
    if tt is None:
        q = q.filter(analysis_trades_filter())
    else:
        q = q.filter(Trade.test_type == tt)
    if symbol:
        q = q.filter(Trade.symbol == symbol)
    q = filter_by_range(q, Trade.close_time, date_from, date_to)

    trades = q.all()
    analysis_svc = AnalysisService(db)
    basic = analysis_svc._calculate_basic_metrics(trades)
    custom_time = analysis_svc._analyze_by_custom_intervals(trades)
    return {"version_id": version_id, "custom_time_analysis": custom_time, **basic}


def generate_reasons(
    version_id: int, metrics: Dict[str, Any], best_metrics: Dict[str, Any]
) -> List[Dict[str, str]]:
    """دلایل سادهٔ برتری/ضعف یک نسخه نسبت به بهترین نسخه (فاز 48a)."""
    if not best_metrics:
        return []
    if metrics.get("version_id") == best_metrics.get("version_id"):
        return [{"icon": "🏆", "text": "بالاترین امتیاز در دامنهٔ انتخاب‌شده"}]

    reasons: List[Dict[str, str]] = []
    if (metrics.get("net_pnl") or 0) > (best_metrics.get("net_pnl") or 0):
        reasons.append({"icon": "💰", "text": f"سود خالص بیشتر (+{metrics['net_pnl']}USDT )"})
    if (metrics.get("win_rate") or 0) > (best_metrics.get("win_rate") or 0):
        reasons.append({"icon": "✅", "text": f"نرخ برد بالاتر ({metrics['win_rate']}٪)"})
    if (metrics.get("max_dd") or 0) < (best_metrics.get("max_dd") or 0):
        reasons.append({"icon": "🛡️", "text": f"افت سرمایه کمتر (-{metrics['max_dd']}USDT )"})
    if metrics.get("profit_factor_status") == "finite" and best_metrics.get("profit_factor_status") == "finite" and (metrics.get("profit_factor") or 0) > (best_metrics.get("profit_factor") or 0):
        reasons.append({"icon": "🏆", "text": f"فاکتور سود بالاتر ({metrics['profit_factor']})"})
    if not reasons:
        reasons.append({"icon": "⚠️", "text": "در معیارهای مقایسه‌شده برتری مشخصی ندارد؛ Score و اجزا را بررسی کنید"})
    score = calculate_version_score(metrics)
    c = score["components"]
    if c["expectancy_score"] < 50:
        reasons.append({"icon": "📉", "text": "ضعف: Expectancy ناخالص R منفی یا پایین است"})
    if c["dd_fallback"]:
        reasons.append({"icon": "ℹ️", "text": "محدودیت داده: درصد DD موجود نیست؛ fallback خنثی اعمال شده"})
    if c["r_fallback"]:
        reasons.append({"icon": "ℹ️", "text": "محدودیت داده: پوشش R برای Expectancy کافی نیست"})
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
            if analysis is None:
                # نوع تست مشخص یعنی کلید legacy احتمالاً دامنهٔ ترکیبی دارد.
                if tt is not None:
                    results.append({
                        "version_id": vid,
                        "status": "missing_analysis",
                        "error": "تحلیل این نسخه با نوع مشخص وجود ندارد؛ تحلیل مجدد لازم است",
                    })
                    continue
                # فقط درخواست legacy بدون نوع مشخص اجازهٔ fallback دارد.
                if key != str(vid):
                    analysis = db.query(AnalysisResult).filter(
                        AnalysisResult.scope == AnalysisScope.VERSION,
                        AnalysisResult.scope_key == str(vid),
                    ).first()
                    if analysis:
                        legacy_snapshot = True
                        legacy_warning = "این تحلیل legacy است و ممکنه دامنه ترکیبی داشته باشد"
                    else:
                        legacy_snapshot = False
                else:
                    legacy_snapshot = False
            else:
                legacy_snapshot = False

            if not analysis:
                results.append({
                    "version_id": vid,
                    "error": "تحلیل نشده — اول «تحلیل مجدد» را بزن",
                })
                continue

            try:
                check_analysis_freshness(db, vid, analysis.scope_key, analysis)
            except AnalysisStaleError as exc:
                results.append({"version_id": vid, "error": str(exc), "stale": True})
                continue

            if symbol or date_from or date_to:
                metrics_d = _calculate_filtered_metrics(
                    vid, tt, symbol, date_from, date_to, db
                )
            else:
                metrics_d = _extract_metrics(analysis)

        # Repair old snapshots only from the exact currently selected trade scope.
        if not (symbol or date_from or date_to) and (metrics_d.get("gross_profit") is None or metrics_d.get("gross_loss") is None or not metrics_d.get("profit_factor_status")):
            metrics_d = _calculate_filtered_metrics(vid, tt, symbol, date_from, date_to, db)
        # A legacy numeric PF is a measurement only when no gross inputs are available;
        # never infer no_losses from numeric sentinels such as 100 or 999.
        if metrics_d.get("gross_profit") is not None and metrics_d.get("gross_loss") is not None:
            pf = metrics.profit_factor_status(metrics_d["gross_profit"], metrics_d["gross_loss"])
            metrics_d["profit_factor_status"] = pf["status"]
            metrics_d["profit_factor"] = pf["value"] if pf["value"] is not None else metrics.profit_factor_from_sums(metrics_d["gross_profit"], metrics_d["gross_loss"])
        else:
            metrics_d["profit_factor_status"] = "unavailable"
            metrics_d["profit_factor"] = None
        score_result = calculate_version_score(metrics_d)
        item = {
            "version_id": vid,
            "metrics": metrics_d,
            "score": score_result["score"],
            "sample_status": score_result["sample_status"],
            "warnings": score_result["warnings"],
            "components": score_result["components"],
        }
        if not is_real and legacy_snapshot:
            item["status"] = "legacy_snapshot"
            item["warning"] = legacy_warning
        if not metrics_d or metrics_d.get("total_trades", 0) == 0:
            # P1 #3: نسخه بدون معامله در رتبه‌بندی و انتخاب بهترین وارد نمی‌شود.
            item["status"] = "no_data"
            item["rank"] = None
            item["score"] = 0
        results.append(item)

    # Policy: valid rows first, ordered by score, finite PF (then no-loss), sample size,
    # and finally stable version id. Equal score remains a tie; secondary criteria are exposed.
    def _sort_key(item):
        item_metrics = item.get("metrics")
        if not item_metrics or item.get("status") in (
            "error", "no_data", "missing_analysis"
        ):
            return (0, 0, 0, 0, 0, item.get("version_id", 0))
        status = item_metrics.get("profit_factor_status")
        pf_order = 2 if status == "no_losses" else 1 if status == "finite" else -1
        pf_value = item_metrics.get("profit_factor") if status == "finite" else 0
        return (
            1,
            item.get("score", 0) or 0,
            pf_order,
            pf_value or 0,
            item_metrics.get("total_trades", 0) or 0,
            -item.get("version_id", 0),
        )

    results.sort(key=_sort_key, reverse=True)
    rank = 0
    previous_key = None
    tied_best = []
    for position, r in enumerate(results):
        if "metrics" in r and r.get("status") != "no_data":
            rank_key = (r.get("score"), r["metrics"].get("profit_factor_status"),
                        r["metrics"].get("profit_factor"), r["metrics"].get("total_trades"))
            if rank_key != previous_key:
                rank = sum(1 for x in results[:position] if x.get("metrics") and x.get("status") != "no_data") + 1
            r["rank"] = rank
            r["tie_count"] = sum(
                1 for x in results if x.get("metrics") and x.get("status") != "no_data"
                and (x.get("score"), x["metrics"].get("profit_factor_status"),
                     x["metrics"].get("profit_factor"), x["metrics"].get("total_trades")) == rank_key
            )
            r["rank_tie"] = r["tie_count"] > 1
            r["tie_break_criteria"] = ["profit_factor_status", "profit_factor", "total_trades"]
            previous_key = rank_key

    best = next((
        r for r in results
        if r.get("metrics")
        and r["metrics"].get("total_trades", 0) > 0
    ), None)
    best_ties = []
    if best:
        best_score = best.get("score", 0)
        best_pf = best["metrics"].get("profit_factor")
        best_trade_count = best["metrics"].get("total_trades")
        ties = [
            item for item in results
            if item is not best
            and item.get("metrics")
            and item.get("status") != "no_data"
            and item.get("score", 0) == best_score
            and item["metrics"].get("profit_factor_status") == best["metrics"].get("profit_factor_status")
            and item["metrics"].get("profit_factor") == best_pf
            and item["metrics"].get("total_trades") == best_trade_count
        ]
        if ties:
            best["is_tie"] = True
            for tie in ties:
                tie["is_tie"] = True
            best_ties = [best, *ties]
        else:
            best_ties = [best]
        # Explain when secondary criteria decide between equal primary scores.
        equal_score = [x for x in results if x.get("metrics") and x.get("status") != "no_data" and x.get("score") == best_score]
        if len(equal_score) > 1:
            for candidate in equal_score:
                explanations = []
                cm = candidate["metrics"]
                if candidate is best:
                    for other in equal_score:
                        if other is candidate:
                            continue
                        om = other["metrics"]
                        if cm.get("profit_factor_status") != om.get("profit_factor_status") or cm.get("profit_factor") != om.get("profit_factor"):
                            explanations.append(f"معیار تعیین‌کننده: PF؛ {cm.get('profit_factor_status')} {cm.get('profit_factor') if cm.get('profit_factor_status') == 'finite' else '—'} در برابر {om.get('profit_factor_status')} {om.get('profit_factor') if om.get('profit_factor_status') == 'finite' else '—'}")
                        elif cm.get("total_trades") != om.get("total_trades"):
                            explanations.append(f"معیار تعیین‌کننده: تعداد نمونه؛ {cm.get('total_trades')} در برابر {om.get('total_trades')} معامله")
                if candidate is best:
                    candidate.setdefault("reasons", []).extend([
                        {"icon": "📊", "text": f"اجزای امتیاز: Expectancy {candidate['components']['expectancy_score']}, نرخ برد {candidate['components']['win_rate_score']}, PF {candidate['components']['pf_score']}, DD {candidate['components']['dd_score']}"},
                        {"icon": "ℹ️", "text": "Expectancy بر پایهٔ gross price R است و DD در نبود مبنای درصدی خنثی است؛ امتیاز، عملکرد آینده را تضمین نمی‌کند."},
                    ])
    best_metrics = best["metrics"] if best else {}
    for r in results:
        if "metrics" in r and r.get("status") != "no_data":
            r["reasons"] = generate_reasons(r["version_id"], r["metrics"], best_metrics)

    # Append ranking explanations after ordinary metric reasons are generated.
    if best:
        equal_score = [x for x in results if x.get("metrics") and x.get("status") != "no_data" and x.get("score") == best.get("score")]
        for candidate in equal_score:
            if candidate is best:
                continue
            cm, om = candidate["metrics"], best["metrics"]
            if cm.get("profit_factor_status") != om.get("profit_factor_status") or cm.get("profit_factor") != om.get("profit_factor"):
                explanation = f"معیار تعیین‌کننده: PF؛ {cm.get('profit_factor_status')} {cm.get('profit_factor') if cm.get('profit_factor_status') == 'finite' else '—'} در برابر {om.get('profit_factor_status')} {om.get('profit_factor') if om.get('profit_factor_status') == 'finite' else '—'}"
            elif cm.get("total_trades") != om.get("total_trades"):
                explanation = f"معیار تعیین‌کننده: تعداد نمونه؛ {cm.get('total_trades')} در برابر {om.get('total_trades')} معامله"
            else:
                continue
            best.setdefault("reasons", []).append({"icon": "⚖️", "text": explanation})

    return {
        "comparison": results,
        "test_type": getattr(tt, "name", None),
        "filters": {
            "symbol": symbol,
            "date_from": date_from.isoformat() if hasattr(date_from, "isoformat") else date_from,
            "date_to": date_to.isoformat() if hasattr(date_to, "isoformat") else date_to,
        },
        "best": best,
        "best_ties": best_ties,
    }


class AnalysisService:
    """سرویس تحلیل معاملات — نسخه، پراپ و بروکر (فاز 20)"""

    def __init__(self, db: Session):
        self.db = db

    def analyze_version(self, version_id: int, test_type: Optional[TestType] = None) -> Dict[str, Any]:
        """تحلیل Backtest/Forward یک نسخه (معاملات REAL حذف می‌شوند).

        فاز ۲۳: Backtest و Forward مستقل ذخیره می‌شوند (کلید دامنه شامل test_type است).
        """
        caller_owned_transaction = self.db.in_transaction()
        q = self.db.query(Trade).filter(Trade.version_id == version_id, Trade.close_time.isnot(None), analysis_trades_filter())
        if test_type is not None:
            q = q.filter(Trade.test_type == test_type)
        return self._analyze(
            q.all(),
            scope=AnalysisScope.VERSION,
            scope_key=version_scope_key(version_id, test_type),
            version_id=version_id,
            test_type=test_type,
            caller_owned_transaction=caller_owned_transaction,
        )

    def analyze_prop_stage(self, prop_stage_id: int) -> Dict[str, Any]:
        """تحلیل کامل یک مرحله پراپ + PropRuleEngine.evaluate_stage()"""
        caller_owned_transaction = self.db.in_transaction()
        # فاز ۲۵: معاملات حذف‌شده از تحلیل کنار گذاشته می‌شوند
        trades = self.db.query(Trade).filter(
            Trade.prop_stage_id == prop_stage_id,
            Trade.close_time.isnot(None),
        ).all()
        result = self._analyze(trades, scope=AnalysisScope.PROP_STAGE, scope_key=str(prop_stage_id), prop_stage_id=prop_stage_id,
                               caller_owned_transaction=caller_owned_transaction)
        from ..services.prop_rule_engine import PropRuleEngine
        result["prop_rules"] = PropRuleEngine.evaluate_stage(self.db, prop_stage_id)
        return result

    def analyze_personal_account(self, personal_trading_account_id: int) -> Dict[str, Any]:
        """تحلیل کامل یک حساب معاملاتی شخصی (معاملات REAL_PERSONAL)."""
        caller_owned_transaction = self.db.in_transaction()
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
            caller_owned_transaction=caller_owned_transaction,
        )

    def _analyze(self, trades, scope, scope_key, version_id=None, prop_stage_id=None,
                 personal_trading_account_id=None, test_type=None, caller_owned_transaction=None) -> Dict[str, Any]:
        """موتور مشترک — محاسبه متریک و ذخیره AnalysisResult + AnalysisRun"""
        if not trades:
            caller_transaction = self.db.in_transaction() if caller_owned_transaction is None else caller_owned_transaction
            stale = self.db.query(AnalysisResult).filter(
                AnalysisResult.scope == scope, AnalysisResult.scope_key == scope_key
            ).first()
            if stale is not None:
                if caller_transaction:
                    connection = self.db.connection()
                    if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
                        connection.exec_driver_sql("BEGIN")
                    transaction = self.db.begin_nested()
                else:
                    transaction = self.db.get_transaction()
                try:
                    self.db.delete(stale)
                    self.db.flush()
                    if not caller_transaction:
                        transaction.commit()
                except Exception:
                    transaction.rollback()
                    raise
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

        # P1 #5: فقط تحلیل‌های متصل به حساب واقعی از سرمایهٔ اولیهٔ آن حساب استفاده می‌کنند.
        initial_balance: Optional[float] = None
        if personal_trading_account_id is not None:
            from ..models.trading import PersonalTradingAccount

            pta = self.db.query(PersonalTradingAccount).filter(
                PersonalTradingAccount.id == personal_trading_account_id
            ).first()
            if pta and pta.initial_balance and pta.initial_balance > 0:
                initial_balance = float(pta.initial_balance)
        elif prop_stage_id is not None:
            from ..models.prop import PropStage

            stage = self.db.query(PropStage).filter(
                PropStage.id == prop_stage_id
            ).first()
            if stage and stage.initial_balance and stage.initial_balance > 0:
                initial_balance = float(stage.initial_balance)

        basic = self._calculate_basic_metrics(trades, initial_balance=initial_balance)
        session_a = self._analyze_by_session(trades)
        weekday_a = self._analyze_by_weekday(trades)
        hour_a = self._analyze_by_hour(trades)
        custom_a = self._analyze_by_custom_intervals(trades)
        consist_a = self._calculate_consistency(trades)

        existing = self.db.query(AnalysisResult).filter(
            AnalysisResult.scope == scope, AnalysisResult.scope_key == scope_key
        ).first()
        # Reads above may autobegin SQLAlchemy without issuing SQLite BEGIN.
        # Ensure a caller's SQLite transaction exists in the DBAPI before SAVEPOINT.
        caller_transaction = self.db.in_transaction() if caller_owned_transaction is None else caller_owned_transaction
        if caller_transaction:
            # SQLite legacy transaction mode does not BEGIN for SELECT. A SAVEPOINT
            # can then become the outermost transaction and RELEASE commits it.
            connection = self.db.connection()
            if connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
                connection.exec_driver_sql("BEGIN")
            transaction = self.db.begin_nested()
        else:
            transaction = self.db.get_transaction()
        try:
            if existing:
                self.db.delete(existing)
                self.db.flush()

            open_times = [t.open_time for t in trades if t.open_time]
            close_times = [t.close_time for t in trades if t.close_time]
            scope_record = AnalysisScopeRecord(
                strategy_version_id=version_id,
                trade_type=self._resolve_trade_type(scope, test_type, trades),
                personal_trading_account_id=personal_trading_account_id,
                prop_stage_id=prop_stage_id,
                from_date=min(open_times) if open_times else None,
                to_date=max(close_times) if close_times else None,
                is_deleted_filter=True,
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
            rules_note = self.db.query(StrategyVersion.rules_note).filter(
                StrategyVersion.id == version_id
            ).scalar() if version_id is not None else None
            rules_snapshot = {"rules_note": rules_note}
            filters_snapshot = {
                "scope": scope.value if hasattr(scope, "value") else str(scope),
                "scope_key": scope_key,
                "version_id": version_id,
                "prop_stage_id": prop_stage_id,
                "personal_trading_account_id": personal_trading_account_id,
                "test_type": test_type.name if test_type is not None else None,
                "is_deleted_filter": True,
                "trade_freshness_fingerprint": _trade_freshness_fingerprint(trades)
                if scope == AnalysisScope.VERSION else None,
                "trade_fingerprint_format": TRADE_FINGERPRINT_FORMAT
                if scope == AnalysisScope.VERSION else None,
                "rules_snapshot": rules_snapshot,
                "rules_hash": hashlib.sha256(json.dumps(
                    rules_snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                ).encode("utf-8")).hexdigest(),
                "analysis_engine_version": ANALYSIS_ENGINE_VERSION,
                "score_policy_version": SCORE_POLICY_VERSION,
                "provenance_status": "complete",
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
                full_metrics=snap, scope_id=scope_record.id,
                filters_snapshot=filters_snapshot, trade_count=basic["total_trades"],
                status=AnalysisStatus.COMPLETED,
            )
            self.db.add(run)
            self.db.flush()
            result.analysis_run_id = run.id
            if not caller_transaction:
                transaction.commit()
                self.db.refresh(result)
        except Exception:
            transaction.rollback()
            raise

        if caller_transaction:
            return {"result": result, "run_id": run.id, "scope_id": scope_record.id,
                    "message": "تحلیل انجام شد و در تاریخچه ذخیره گردید"}

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
    def _calculate_basic_metrics(
        self,
        trades: List[Trade],
        initial_balance: Optional[float] = None,
    ) -> Dict[str, Any]:
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
        pf = metrics.profit_factor_status(gross_profit, gross_loss)
        profit_factor = pf["value"]

        r_multiples = [t.r_multiple for t in trades if t.r_multiple is not None]
        r_valid_count = len(r_multiples)
        r_coverage_percent = (r_valid_count / total * 100) if total > 0 else 0
        net_r = sum(r_multiples) if r_multiples else 0
        max_dd = metrics.calculate_max_drawdown(_chronological(trades))
        # P1 #5: DD درصدی بر اساس سرمایه واقعی
        if initial_balance is not None and initial_balance > 0:
            max_dd_percent = (max_dd / initial_balance) * 100.0
        else:
            max_dd_percent = None  # Backtest/Forward از ASSUMED_ACCOUNT_SIZE استفاده می‌کند.

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
            "profit_factor": profit_factor if profit_factor is not None else self._profit_factor(gross_profit, gross_loss),
            "profit_factor_status": pf["status"],
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "net_pnl": round(net_pnl, 2),
            "net_r": round(net_r, 2),
            "max_dd": round(max_dd, 2),
            "max_dd_percent": round(max_dd_percent, 2) if max_dd_percent is not None else None,
            "expectancy": round(expectancy, 2),
            "expectancy_r": round(expectancy_r, 3) if expectancy_r is not None else None,
            "r_valid_count": r_valid_count,
            "r_coverage_percent": round(r_coverage_percent, 2),
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
        """Exclusive Tehran entry-time buckets: start inclusive, end exclusive."""
        sessions = {"Early": [], "London Only": [], "London+NY": [], "NY Only": [], "Outside": []}

        for t in trades:
            if not t.open_time:
                continue
            tehran = to_tehran(t.open_time)
            seconds = tehran.hour * 3600 + tehran.minute * 60
            if 8 * 3600 <= seconds < 10 * 3600:
                sessions["Early"].append(t)
            elif 10 * 3600 <= seconds < 16 * 3600:
                sessions["London Only"].append(t)
            elif 16 * 3600 <= seconds < 19 * 3600:
                sessions["London+NY"].append(t)
            elif 19 * 3600 <= seconds < 23 * 3600:
                sessions["NY Only"].append(t)
            else:
                sessions["Outside"].append(t)

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
            day_name = weekdays[to_tehran(t.open_time).weekday()]
            by_day[day_name].append(t)

        return {name: self._summarize(trades) for name, trades in by_day.items() if trades}

    def _analyze_by_hour(self, trades: List[Trade]) -> Dict[str, Any]:
        """تحلیل ساعت بر پایهٔ **زمان ورود** (`open_time`) در بازه UTC — فاز 48a.3."""
        from datetime import timezone

        by_hour = {str(h): [] for h in range(24)}

        for t in trades:
            if not t.open_time:
                continue
            open_dt = t.open_time
            if open_dt.tzinfo is not None:
                open_dt = open_dt.astimezone(timezone.utc)
            hour = str(open_dt.hour)
            by_hour[hour].append(t)

        return {h: self._summarize(trades) for h, trades in by_hour.items() if trades}

    @staticmethod
    def _is_in_interval(hour: int, minute: int, start_h: int, start_m: int, end_h: int, end_m: int) -> bool:
        current = hour * 60 + minute
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        if start == end:
            return current == start
        elif start < end:
            return start <= current < end
        else:  # crosses midnight, e.g. 22:00 to 02:00
            return current >= start or current < end

    @staticmethod
    def _symbols_match(t_symbol: Optional[str], interval_symbol: Optional[str]) -> bool:
        if not t_symbol or not interval_symbol:
            return False
        s1 = t_symbol.strip().upper()
        s2 = interval_symbol.strip().upper()
        if s1 == s2:
            return True
        s1_clean = s1.split('.')[0].rstrip('_+')
        s2_clean = s2.split('.')[0].rstrip('_+')
        if s1_clean == s2_clean:
            return True
        aliases = {
            "GOLD": "XAUUSD",
            "US30": "DJIUSD",
            "DJ30": "DJIUSD",
            "WS30": "DJIUSD",
            "DJI": "DJIUSD",
            "US30CASH": "DJIUSD",
        }
        return aliases.get(s1_clean, s1_clean) == aliases.get(s2_clean, s2_clean)

    def _analyze_by_custom_intervals(self, trades: List[Trade]) -> Dict[str, Any]:
        intervals = self.db.query(CustomTimeInterval).filter(
            CustomTimeInterval.is_active == 1
        ).order_by(
            CustomTimeInterval.symbol,
            CustomTimeInterval.priority,
            CustomTimeInterval.start_hour,
            CustomTimeInterval.start_minute,
        ).all()

        if not intervals:
            return {}

        result = {}
        matched_trade_keys_by_symbol: Dict[str, set] = defaultdict(set)
        symbol_trades: Dict[str, List[Trade]] = defaultdict(list)

        for interval in intervals:
            matched = []
            for t in trades:
                if not t.open_time:
                    continue
                if not self._symbols_match(t.symbol, interval.symbol):
                    continue
                symbol_trades[interval.symbol].append(t)
                tehran = to_tehran(t.open_time)
                hour = tehran.hour
                minute = tehran.minute
                if self._is_in_interval(hour, minute, interval.start_hour, interval.start_minute, interval.end_hour, interval.end_minute):
                    matched.append(t)
                    t_key = t.id if t.id is not None else id(t)
                    matched_trade_keys_by_symbol[interval.symbol].add(t_key)

            if matched:
                result[f"{interval.name} [{interval.label or '-'}]"] = self._summarize(matched)

        # Calculate Outside-Window trades for each traded symbol that has intervals
        for sym, t_list in symbol_trades.items():
            seen = set()
            unique_t_list = []
            for t in t_list:
                key = t.id if t.id is not None else id(t)
                if key not in seen:
                    seen.add(key)
                    unique_t_list.append(t)

            matched_keys = matched_trade_keys_by_symbol[sym]
            outside = [t for t in unique_t_list if (t.id if t.id is not None else id(t)) not in matched_keys]
            if outside:
                sym_label = "طلا" if "XAU" in sym else ("داو" if "DJI" in sym or "US30" in sym else ("یورو" if "EUR" in sym else sym))
                result[f"{sym_label} — خارج از بازه [خارج]"] = self._summarize(outside)

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
