from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional

from ..models.strategy import (
    Trade, AnalysisResult, AnalysisRun, CustomTimeInterval,
    StrategyVersion, Strategy, AnalysisScope, TestType,
    AnalysisScopeRecord, AnalysisStatus,
)
from ..utils.trade_scope import analysis_trades_filter, version_scope_key


class AnalysisService:
    """سرویس تحلیل معاملات — نسخه، پراپ و بروکر (فاز 20)"""

    def __init__(self, db: Session):
        self.db = db

    def analyze_version(self, version_id: int, test_type: Optional[TestType] = None) -> Dict[str, Any]:
        """تحلیل Backtest/Forward یک نسخه (معاملات REAL حذف می‌شوند).

        فاز ۲۳: Backtest و Forward مستقل ذخیره می‌شوند (کلید دامنه شامل test_type است).
        """
        q = self.db.query(Trade).filter(Trade.version_id == version_id, analysis_trades_filter())
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
            Trade.is_deleted == False,
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
            Trade.is_deleted == False,
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



    def compare_versions(self, version_ids: List[int], min_trades: int = 0) -> Dict[str, Any]:
        """
        مقایسه‌ی چند نسخه با پیشنهاد هوشمند و دلایل.
        min_trades: حداقل تعداد معامله برای ورود به مقایسه (فیلتر هوشمند) -
        نسخه‌های کمتر از این حد وارد مقایسه نمی‌شن ولی توی skipped با دلیل گزارش می‌شن.
        """
        items = []
        skipped = []  # [{"version_id", "version_name", "reason"}]

        for vid in version_ids:
            version = self.db.query(StrategyVersion).filter(
                StrategyVersion.id == vid
            ).first()
            if not version:
                skipped.append({"version_id": vid, "version_name": None, "reason": "نسخه پیدا نشد"})
                continue

            analysis = self.db.query(AnalysisResult).filter(
                AnalysisResult.scope == AnalysisScope.VERSION, AnalysisResult.scope_key == str(vid)
            ).first()
            if not analysis:
                skipped.append({
                    "version_id": vid,
                    "version_name": version.version_name,
                    "reason": "این نسخه هنوز تحلیل نشده - اول «تحلیل مجدد» رو بزن",
                })
                continue

            if min_trades and analysis.total_trades < min_trades:
                skipped.append({
                    "version_id": vid,
                    "version_name": version.version_name,
                    "reason": f"فقط {analysis.total_trades} معامله داره (کمتر از حد نصاب {min_trades} تا)",
                })
                continue

            strategy = self.db.query(Strategy).filter(
                Strategy.id == version.strategy_id
            ).first()

            trades = self.db.query(Trade).filter(Trade.version_id == vid, analysis_trades_filter()).all()
            symbols = list(set(t.symbol for t in trades if t.symbol))

            health_score = self._calculate_score(analysis)

            items.append({
                "version_id": vid,
                "version_name": version.version_name,
                "strategy_name": strategy.name if strategy else "نامشخص",
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
                "consistency_analysis": analysis.consistency_analysis or {},
                "health_score": round(health_score, 2),
                "symbols": symbols,
                "session_analysis": analysis.session_analysis or {},
                "weekday_analysis": analysis.weekday_analysis or {},
                "hour_analysis": analysis.hour_analysis or {},
                "custom_time_analysis": analysis.custom_time_analysis or {},
            })

        if not items:
            raise ValueError("هیچ نسخه‌ی قابل‌مقایسه‌ای یافت نشد (یا تحلیل نشده‌ن یا کمتر از حد نصاب معامله دارن)")

        items.sort(key=lambda x: x["health_score"], reverse=True)
        best = items[0]

        reasons = self._build_reasons(best, items)
        symbol_bests = self._find_symbol_bests(items)
        detail_bests = self._find_detail_bests(items)

        recommendation = (
            f"نسخه‌ی «{best['version_name']}» از استراتژی «{best['strategy_name']}» "
            f"با امتیاز سلامت {best['health_score']} بهترین عملکرد را داشته است."
        )

        return {
            "items": items,
            "skipped": skipped,
            "best_version_id": best["version_id"],
            "best_version_name": best["version_name"],
            "best_health_score": best["health_score"],
            "recommendation": recommendation,
            "reasons": reasons,
            "symbol_bests": symbol_bests,
            "detail_bests": detail_bests,
        }

    def _build_reasons(self, best: Dict, items: List[Dict]) -> List[Dict[str, str]]:
        """ساخت دلایل برتری بهترین نسخه"""
        reasons = []
        best_data = best

        highest_wr = max(items, key=lambda x: x["win_rate"])
        if highest_wr["version_id"] == best_data["version_id"]:
            second_wr = sorted(items, key=lambda x: x["win_rate"], reverse=True)[1] if len(items) > 1 else None
            reasons.append({
                "icon": "✅",
                "text": f"بالاترین نرخ برد ({best_data['win_rate']}٪" +
                        (f" در مقابل {second_wr['win_rate']}٪" if second_wr else "") + ")",
            })

        highest_pnl = max(items, key=lambda x: x["net_pnl"])
        if highest_pnl["version_id"] == best_data["version_id"]:
            second_pnl = sorted(items, key=lambda x: x["net_pnl"], reverse=True)[1] if len(items) > 1 else None
            reasons.append({
                "icon": "💰",
                "text": f"بالاترین سود خالص (+{best_data['net_pnl']}$" +
                        (f" در مقابل +{second_pnl['net_pnl']}$" if second_pnl else "") + ")",
            })

        lowest_dd = min(items, key=lambda x: x["max_dd"])
        if lowest_dd["version_id"] == best_data["version_id"]:
            second_dd = sorted(items, key=lambda x: x["max_dd"])[1] if len(items) > 1 else None
            reasons.append({
                "icon": "🛡️",
                "text": f"کمترین حداکثر افت سرمایه (-{best_data['max_dd']}$" +
                        (f" در مقابل -{second_dd['max_dd']}$" if second_dd else "") + ")",
            })

        highest_pf = max(items, key=lambda x: x["profit_factor"])
        if highest_pf["version_id"] == best_data["version_id"]:
            second_pf = sorted(items, key=lambda x: x["profit_factor"], reverse=True)[1] if len(items) > 1 else None
            reasons.append({
                "icon": "🏆",
                "text": f"بهترین فاکتور سود ({best_data['profit_factor']}" +
                        (f" در مقابل {second_pf['profit_factor']}" if second_pf else "") + ")",
            })

        if not reasons:
            reasons.append({
                "icon": "📊",
                "text": f"بهترین ترکیب کلی متریک‌ها با امتیاز سلامت {best_data['health_score']}",
            })

        return reasons

    def _find_symbol_bests(self, items: List[Dict]) -> List[Dict[str, Any]]:
        """پیدا کردن بهترین نسخه برای هر نماد"""
        symbols_data: Dict[str, List[Dict]] = {}

        for item in items:
            for symbol in item.get("symbols", []):
                if symbol not in symbols_data:
                    symbols_data[symbol] = []
                symbols_data[symbol].append(item)

        result = []
        for symbol, versions in symbols_data.items():
            versions_sorted = sorted(versions, key=lambda x: x["health_score"], reverse=True)
            best = versions_sorted[0]

            symbol_label = {
                "XAUUSD": "🥇 طلا (XAUUSD)",
                "DJIUSD": "📊 داوجونز (DJIUSD)",
                "DJIUSD.x": "📊 داوجونز (DJIUSD)",
            }.get(symbol, f"📈 {symbol}")

            result.append({
                "symbol": symbol,
                "symbol_label": symbol_label,
                "best_version_id": best["version_id"],
                "best_version_name": best["version_name"],
                "best_strategy": best["strategy_name"],
                "win_rate": best["win_rate"],
                "net_pnl": best["net_pnl"],
                "health_score": best["health_score"],
            })

        return result

    def _find_detail_bests(self, items: List[Dict]) -> Dict[str, Any]:
        """پیدا کردن بهترین نسخه در هر بخش تفکیکی"""
        result = {
            "session": [],
            "weekday": [],
            "hour": [],
            "custom_interval": [],
        }

        # سشن‌ها
        sessions = ["Asia", "Europe", "America"]
        for session in sessions:
            best_version = None
            best_wr = -1
            for item in items:
                session_data = item.get("session_analysis", {}).get(session, {})
                if session_data and session_data.get("win_rate", 0) > best_wr:
                    best_wr = session_data["win_rate"]
                    best_version = {
                        "version_name": item["version_name"],
                        "win_rate": session_data.get("win_rate", 0),
                        "net_pnl": session_data.get("net_pnl", 0),
                        "total_trades": session_data.get("total_trades", 0),
                    }
            if best_version:
                session_label = {
                    "Asia": "🌏 آسیا",
                    "Europe": "🌍 اروپا",
                    "America": "🌎 آمریکا",
                }.get(session, session)
                result["session"].append({
                    "name": session_label,
                    "best": best_version,
                })

        # روزهای هفته
        weekdays = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        weekday_labels = {
            "Saturday": "شنبه",
            "Sunday": "یک‌شنبه",
            "Monday": "دوشنبه",
            "Tuesday": "سه‌شنبه",
            "Wednesday": "چهارشنبه",
            "Thursday": "پنج‌شنبه",
            "Friday": "جمعه",
        }
        for day in weekdays:
            best_version = None
            best_wr = -1
            for item in items:
                day_data = item.get("weekday_analysis", {}).get(day, {})
                if day_data and day_data.get("win_rate", 0) > best_wr:
                    best_wr = day_data["win_rate"]
                    best_version = {
                        "version_name": item["version_name"],
                        "win_rate": day_data.get("win_rate", 0),
                        "net_pnl": day_data.get("net_pnl", 0),
                        "total_trades": day_data.get("total_trades", 0),
                    }
            if best_version:
                result["weekday"].append({
                    "name": weekday_labels.get(day, day),
                    "best": best_version,
                })

        # ساعت‌ها
        for hour in range(24):
            hour_str = str(hour)
            best_version = None
            best_wr = -1
            for item in items:
                hour_data = item.get("hour_analysis", {}).get(hour_str, {})
                if hour_data and hour_data.get("win_rate", 0) > best_wr:
                    best_wr = hour_data["win_rate"]
                    best_version = {
                        "version_name": item["version_name"],
                        "win_rate": hour_data.get("win_rate", 0),
                        "net_pnl": hour_data.get("net_pnl", 0),
                    }
            if best_version:
                result["hour"].append({
                    "name": f"ساعت {hour}",
                    "best": best_version,
                })

        # بازه‌های سفارشی
        all_intervals = set()
        for item in items:
            for key in item.get("custom_time_analysis", {}).keys():
                all_intervals.add(key)

        for interval in all_intervals:
            best_version = None
            best_wr = -1
            for item in items:
                interval_data = item.get("custom_time_analysis", {}).get(interval, {})
                if interval_data and interval_data.get("win_rate", 0) > best_wr:
                    best_wr = interval_data["win_rate"]
                    best_version = {
                        "version_name": item["version_name"],
                        "win_rate": interval_data.get("win_rate", 0),
                        "net_pnl": interval_data.get("net_pnl", 0),
                        "total_trades": interval_data.get("total_trades", 0),
                    }
            if best_version:
                result["custom_interval"].append({
                    "name": interval,
                    "best": best_version,
                })

        return result

    def _calculate_score(self, analysis: AnalysisResult) -> float:
        """
        محاسبه‌ی Health Score (۰ تا ۱۰۰) بر پایه‌ی نرخ برد، فاکتور سود، سود خالص و افت سرمایه.
        (فاکتور سود همیشه بین ۰ تا ۱۰۰ سقف داره - نگاه کن به _profit_factor - پس این فرمول
        همیشه بین ۰ و ۱۰۰ می‌مونه)
        """
        win_rate_score = min(analysis.win_rate, 100)
        profit_factor_score = min(analysis.profit_factor * 20, 100)
        net_pnl_score = min(max(analysis.net_pnl, 0) / 10, 100)
        dd_penalty = min(analysis.max_dd / 10, 50)

        score = (
            win_rate_score * 0.35 +
            profit_factor_score * 0.35 +
            net_pnl_score * 0.30 -
            dd_penalty * 0.20
        )

        return max(min(score, 100), 0)

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

        def _net_pnl(t: Trade) -> float:
            """PnL خالص یک معامله"""
            return (t.pnl or 0) + (t.commission or 0) + (t.swap or 0)

        total = len(trades)
        wins = [t for t in trades if _net_pnl(t) > 0]
        losses = [t for t in trades if _net_pnl(t) < 0]

        gross_profit = sum(_net_pnl(t) for t in wins) if wins else 0
        gross_loss = abs(sum(_net_pnl(t) for t in losses)) if losses else 0

        net_pnl = sum(_net_pnl(t) for t in trades)
        win_rate = (len(wins) / total * 100) if total > 0 else 0
        profit_factor = self._profit_factor(gross_profit, gross_loss)

        r_multiples = [t.r_multiple for t in trades if t.r_multiple is not None]
        net_r = sum(r_multiples) if r_multiples else 0

        max_dd = self._calculate_max_drawdown(trades)

        # اکسپکتنسی، میانگین/بزرگ‌ترین برد و باخت
        avg_win = (gross_profit / len(wins)) if wins else 0
        avg_loss = (gross_loss / len(losses)) if losses else 0  # مقدار مثبت
        largest_win = max((_net_pnl(t) for t in wins), default=0)
        largest_loss = abs(min((_net_pnl(t) for t in losses), default=0))  # مقدار مثبت

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
        فاکتور سود = سود ناخالص / ضرر ناخالص.
        اگه هیچ معامله‌ی بازنده‌ای نباشه (gross_loss == 0) ولی سود مثبت باشه،
        این عملاً بهترین حالت ممکنه - قبلاً اشتباهاً صفر برمی‌گشت که توی امتیازدهی
        باعث می‌شد این نسخه بدترین امتیاز رو بگیره. اینجا یه سقف منطقی (۱۰۰) می‌ذاریم
        تا هم عدد قابل‌نمایش/JSON-safe باشه، هم توی فرمول امتیاز درست حساب بشه.
        """
        if gross_loss > 0:
            return gross_profit / gross_loss
        if gross_profit > 0:
            return 100.0
        return 0.0

    def _calculate_max_consecutive_losses(self, trades: List[Trade]) -> int:
        sorted_trades = sorted(trades, key=lambda t: t.close_time or t.open_time)
        streak = 0
        max_streak = 0
        for t in sorted_trades:
            npnl = self._net_pnl(t)
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
        wins = [t for t in trades if self._net_pnl(t) > 0]
        losses = [t for t in trades if self._net_pnl(t) < 0]
        pnl_values = [self._net_pnl(t) for t in trades]

        if not pnl_values:
            return {
                "pnl_std_dev": 0,
                "top_trades_contribution_percent": 0,
                "avg_win_avg_loss_ratio": 0,
            }

        mean_pnl = sum(pnl_values) / len(pnl_values)
        variance = sum((p - mean_pnl) ** 2 for p in pnl_values) / len(pnl_values)
        pnl_std_dev = variance ** 0.5

        gross_profit = sum(self._net_pnl(t) for t in wins) if wins else 0
        top_n = sorted((self._net_pnl(t) for t in wins), reverse=True)[:3]
        top_trades_contribution = (sum(top_n) / gross_profit * 100) if gross_profit > 0 else 0

        avg_win = (gross_profit / len(wins)) if wins else 0
        gross_loss = abs(sum(self._net_pnl(t) for t in losses)) if losses else 0
        avg_loss = (gross_loss / len(losses)) if losses else 0
        avg_win_avg_loss_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0

        return {
            "pnl_std_dev": round(pnl_std_dev, 2),
            "top_trades_contribution_percent": round(top_trades_contribution, 1),
            "avg_win_avg_loss_ratio": round(avg_win_avg_loss_ratio, 2),
        }

    def _calculate_max_drawdown(self, trades: List[Trade]) -> float:
        """
        محاسبه‌ی حداکثر افت سرمایه (peak-to-valley).
        از net_pnl استفاده می‌کند (pnl + commission + swap)
        """
        sorted_trades = sorted(trades, key=lambda t: t.close_time or t.open_time)
        equity = 0
        peak = 0
        max_dd = 0

        for t in sorted_trades:
            equity += self._net_pnl(t)
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def _analyze_by_session(self, trades: List[Trade]) -> Dict[str, Any]:
        sessions = {"Asia": [], "Europe": [], "America": [], "Other": []}

        for t in trades:
            if not t.close_time:
                continue
            hour = t.close_time.hour
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
        weekdays = {
            0: "Monday", 1: "Tuesday", 2: "Wednesday",
            3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
        }
        by_day = {day: [] for day in weekdays.values()}

        for t in trades:
            if not t.close_time:
                continue
            day_name = weekdays[t.close_time.weekday()]
            by_day[day_name].append(t)

        return {name: self._summarize(trades) for name, trades in by_day.items() if trades}

    def _analyze_by_hour(self, trades: List[Trade]) -> Dict[str, Any]:
        by_hour = {str(h): [] for h in range(24)}

        for t in trades:
            if not t.close_time:
                continue
            hour = str(t.close_time.hour)
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
                if not t.close_time:
                    continue
                if t.symbol != interval.symbol:
                    continue
                hour = t.close_time.hour
                minute = t.close_time.minute
                start = interval.start_hour * 60 + interval.start_minute
                end = interval.end_hour * 60 + interval.end_minute
                current = hour * 60 + minute
                if start <= current <= end:
                    matched.append(t)

            if matched:
                result[f"{interval.name} [{interval.label or '-'}]"] = self._summarize(matched)

        return result

    @staticmethod
    def _net_pnl(trade: Trade) -> float:
        """محاسبه net_pnl با در نظر گرفتن کمیسیون و swap"""
        return (trade.pnl or 0) + (trade.commission or 0) + (trade.swap or 0)

    def _summarize(self, trades: List[Trade]) -> Dict[str, Any]:
        total = len(trades)
        wins = [t for t in trades if self._net_pnl(t) > 0]
        losses = [t for t in trades if self._net_pnl(t) < 0]

        gross_profit = sum(self._net_pnl(t) for t in wins) if wins else 0
        gross_loss = abs(sum(self._net_pnl(t) for t in losses)) if losses else 0

        net_pnl = sum(self._net_pnl(t) for t in trades) or 0
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