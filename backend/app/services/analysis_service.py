import math
import random
from datetime import datetime, time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class TimePoint:
    hour: int
    minute: int

    def to_minutes(self) -> int:
        return self.hour * 60 + self.minute


@dataclass
class CustomTimeInterval:
    name: str
    start: TimePoint
    end: TimePoint

    def contains(self, t: time) -> bool:
        trade_mins = t.hour * 60 + t.minute
        start_mins = self.start.to_minutes()
        end_mins = self.end.to_minutes()

        if start_mins <= end_mins:
            return start_mins <= trade_mins <= end_mins
        else:
            # Overnight interval (e.g. 22:00 to 02:00)
            return trade_mins >= start_mins or trade_mins <= end_mins


class AnalysisService:
    # پیش‌فرض Sessions بر اساس UTC
    DEFAULT_SESSIONS = {
        "Asia": CustomTimeInterval("Asia", TimePoint(0, 0), TimePoint(8, 0)),
        "Europe": CustomTimeInterval("Europe", TimePoint(7, 0), TimePoint(15, 0)),
        "US": CustomTimeInterval("US", TimePoint(13, 0), TimePoint(21, 0)),
    }

    # بازه‌های اختصاصی طلا (XAUUSD) و داوجونز (US30)
    CUSTOM_SYMBOL_INTERVALS = {
        "XAUUSD": [
            CustomTimeInterval("London_Open_Gold", TimePoint(7, 0), TimePoint(10, 30)),
            CustomTimeInterval("NY_Overlap_Gold", TimePoint(13, 0), TimePoint(17, 0)),
            CustomTimeInterval("Asian_Liquidity_Gold", TimePoint(1, 0), TimePoint(5, 0)),
        ],
        "US30": [
            CustomTimeInterval("NYSE_Open", TimePoint(14, 30), TimePoint(17, 0)),
            CustomTimeInterval("NY_Power_Hour", TimePoint(19, 0), TimePoint(20, 0)),
            CustomTimeInterval("US_PreMarket", TimePoint(12, 0), TimePoint(14, 30)),
        ],
    }

    @staticmethod
    def calculate_basic_metrics(trades: List[Dict[str, Any]], initial_balance: float = 10000.0) -> Dict[str, Any]:
        """
        محاسبه متریک‌های پایه: Win Rate, Profit Factor, Net PnL, Net R, Max Drawdown, Expectancy
        هر trade در لیستی شامل: {'pnl': float, 'r_multiple': float, 'entry_time': datetime, ...} است.
        """
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "net_pnl": 0.0,
                "net_r": 0.0,
                "max_drawdown_abs": 0.0,
                "max_drawdown_pct": 0.0,
                "expectancy_r": 0.0,
                "expectancy_pnl": 0.0,
            }

        total_trades = len(trades)
        wins = [t for t in trades if t.get("pnl", 0) > 0]
        losses = [t for t in trades if t.get("pnl", 0) < 0]

        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0.0

        gross_profit = sum(t.get("pnl", 0) for t in wins)
        gross_loss = abs(sum(t.get("pnl", 0) for t in losses))
        
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
        net_pnl = sum(t.get("pnl", 0) for t in trades)
        net_r = sum(t.get("r_multiple", 0.0) for t in trades)

        # محاسبه Expectancy
        avg_win_r = (sum(t.get("r_multiple", 0.0) for t in wins) / win_count) if win_count > 0 else 0.0
        avg_loss_r = abs(sum(t.get("r_multiple", 0.0) for t in losses) / loss_count) if loss_count > 0 else 0.0
        win_prob = win_count / total_trades if total_trades > 0 else 0.0
        loss_prob = loss_count / total_trades if total_trades > 0 else 0.0
        
        expectancy_r = (win_prob * avg_win_r) - (loss_prob * avg_loss_r)
        expectancy_pnl = net_pnl / total_trades if total_trades > 0 else 0.0

        # محاسبه Max Drawdown (مطلق و درصدی)
        current_balance = initial_balance
        peak = initial_balance
        max_drawdown_abs = 0.0
        max_drawdown_pct = 0.0

        for t in trades:
            current_balance += t.get("pnl", 0)
            if current_balance > peak:
                peak = current_balance
            
            dd_abs = peak - current_balance
            dd_pct = (dd_abs / peak) * 100 if peak > 0 else 0.0

            if dd_abs > max_drawdown_abs:
                max_drawdown_abs = dd_abs
            if dd_pct > max_drawdown_pct:
                max_drawdown_pct = dd_pct

        return {
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "net_pnl": round(net_pnl, 2),
            "net_r": round(net_r, 2),
            "max_drawdown_abs": round(max_drawdown_abs, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "expectancy_r": round(expectancy_r, 2),
            "expectancy_pnl": round(expectancy_pnl, 2),
        }

    @classmethod
    def calculate_time_breakdowns(cls, trades: List[Dict[str, Any]], symbol: str = None) -> Dict[str, Any]:
        """
        تفکیک عملکرد بر اساس Sessions، روزهای هفته و ساعات شبانه‌روز
        """
        by_session = {"Asia": [], "Europe": [], "US": [], "Other": []}
        by_day_of_week = {i: [] for i in range(7)}  # 0=Mon, 6=Sun
        by_hour = {i: [] for i in range(24)}
        by_custom_interval = {}

        # تنظیم بازه‌های سفارشی در صورت مشخص بودن نماد
        custom_intervals = cls.CUSTOM_SYMBOL_INTERVALS.get(symbol.upper(), []) if symbol else []
        for interval in custom_intervals:
            by_custom_interval[interval.name] = []

        for t in trades:
            entry_dt: datetime = t.get("entry_time")
            if not isinstance(entry_dt, datetime):
                continue
            
            entry_time_obj = entry_dt.time()
            day_idx = entry_dt.weekday()
            hour_idx = entry_dt.hour

            by_day_of_week[day_idx].append(t)
            by_hour[hour_idx].append(t)

            # طبقه‌بندی جلسات اصلی
            matched_session = False
            for s_name, s_interval in cls.DEFAULT_SESSIONS.items():
                if s_interval.contains(entry_time_obj):
                    by_session[s_name].append(t)
                    matched_session = True
            if not matched_session:
                by_session["Other"].append(t)

            # طبقه‌بندی بازه‌های سفارشی
            for interval in custom_intervals:
                if interval.contains(entry_time_obj):
                    by_custom_interval[interval.name].append(t)

        def summarize(group_dict: Dict[Any, List[Dict[str, Any]]]):
            summary = {}
            for k, t_list in group_dict.items():
                metrics = cls.calculate_basic_metrics(t_list)
                summary[str(k)] = {
                    "trade_count": metrics["total_trades"],
                    "win_rate": metrics["win_rate"],
                    "net_pnl": metrics["net_pnl"],
                    "net_r": metrics["net_r"],
                    "profit_factor": metrics["profit_factor"]
                }
            return summary

        return {
            "sessions": summarize(by_session),
            "day_of_week": summarize(by_day_of_week),
            "hours": summarize(by_hour),
            "custom_intervals": summarize(by_custom_interval)
        }

    @staticmethod
    def run_monte_carlo(
        trades: List[Dict[str, Any]], 
        initial_balance: float = 10000.0, 
        num_simulations: int = 1000, 
        ruin_threshold_pct: float = 20.0
    ) -> Dict[str, Any]:
        """
        موتور شبیه‌سازی مونت‌کارلو با ۱۰۰۰ بار Resampling روی sequence معاملات.
        محاسبه Risk of Ruin و چارک‌های ۵٪، ۵۰٪ و ۹۵٪ رشد حساب.
        """
        pnls = [t.get("pnl", 0.0) for t in trades]
        if not pnls:
            return {"error": "No trade data available for Monte Carlo simulation."}

        num_trades = len(pnls)
        simulated_final_balances = []
        simulated_max_drawdowns_pct = []
        all_curves = []

        ruin_count = 0

        for _ in range(num_simulations):
            # نمونه‌گیری با جایگذاری (Resampling with replacement)
            resampled_pnls = np.random.choice(pnls, size=num_trades, replace=True)
            
            balance = initial_balance
            peak = initial_balance
            max_dd_pct = 0.0
            curve = [initial_balance]

            for pnl in resampled_pnls:
                balance += pnl
                curve.append(balance)

                if balance > peak:
                    peak = balance
                
                dd_pct = ((peak - balance) / peak) * 100 if peak > 0 else 0.0
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct

            simulated_final_balances.append(balance)
            simulated_max_drawdowns_pct.append(max_dd_pct)
            all_curves.append(curve)

            if max_dd_pct >= ruin_threshold_pct:
                ruin_count += 1

        risk_of_ruin_pct = (ruin_count / num_simulations) * 100

        # محاسبه چارک‌های ۵٪، ۵۰٪ و ۹۵٪ برای رشد حساب
        p5 = float(np.percentile(simulated_final_balances, 5))
        p50 = float(np.percentile(simulated_final_balances, 50))
        p95 = float(np.percentile(simulated_final_balances, 95))

        # ایجاد منحنی‌های چارکی زمان‌بندی‌شده جهت رسم نمودار
        curves_array = np.array(all_curves) # shape: (num_simulations, num_trades + 1)
        p5_curve = np.percentile(curves_array, 5, axis=0).round(2).tolist()
        p50_curve = np.percentile(curves_array, 50, axis=0).round(2).tolist()
        p95_curve = np.percentile(curves_array, 95, axis=0).round(2).tolist()

        return {
            "num_simulations": num_simulations,
            "ruin_threshold_pct": ruin_threshold_pct,
            "risk_of_ruin_pct": round(risk_of_ruin_pct, 2),
            "final_balance_percentiles": {
                "5th": round(p5, 2),
                "50th": round(p50, 2),
                "95th": round(p95, 2)
            },
            "growth_percentiles_pct": {
                "5th": round(((p5 - initial_balance) / initial_balance) * 100, 2),
                "50th": round(((p50 - initial_balance) / initial_balance) * 100, 2),
                "95th": round(((p95 - initial_balance) / initial_balance) * 100, 2)
            },
            "curves": {
                "p5": p5_curve,
                "p50": p50_curve,
                "p95": p95_curve
            }
        }