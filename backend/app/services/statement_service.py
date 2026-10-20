import hashlib
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import asc

from ..models.strategy import Trade
from ..schemas.statement import (
    StatementCredentials,
    KeyMetrics,
    LongShortProfile,
    MonthlyPerformance,
    EquityPoint,
    SymbolStats,
    StatementResponse,
)
from .metrics import net_pnl, profit_factor_status, win_loss_streaks


MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class StatementService:
    @staticmethod
    def get_statement_data(
        db: Session,
        trader_name: str = "Chief Investment Officer",
        account_id: str = "MTD-ACT-001",
        initial_balance: float = 10000.0,
        currency: str = "USDT",
        scope: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        version_id: Optional[int] = None,
        broker_id: Optional[int] = None,
    ) -> StatementResponse:
        # 1. کوئری معاملات بسته
        q = db.query(Trade).filter(Trade.close_time.isnot(None))

        if scope and scope != "all":
            q = q.filter(Trade.scope == scope)
        if date_from:
            q = q.filter(Trade.close_time >= date_from)
        if date_to:
            q = q.filter(Trade.close_time <= date_to)
        if version_id:
            q = q.filter(Trade.version_id == version_id)
        if broker_id:
            q = q.filter(Trade.broker_id == broker_id)

        # مرتب‌سازی زمانی
        trades = q.order_by(asc(Trade.close_time), asc(Trade.id)).all()

        # محاسبه سودهای خالص
        trade_items = []
        for t in trades:
            npnl = net_pnl(t)
            trade_items.append({
                "id": t.id,
                "symbol": t.symbol or "UNKNOWN",
                "direction": (t.direction.value if hasattr(t.direction, "value") else str(t.direction)).lower() if t.direction else "buy",
                "net_pnl": npnl,
                "close_time": t.close_time,
                "r_multiple": t.r_multiple,
            })

        # 2. تولید هش اعتبارسنجی دیجیتال (Cryptographic Provenance Token)
        hash_seed = f"{trader_name}:{account_id}:{initial_balance:.2f}:{currency}:" + ";".join(
            f"{ti['id']},{ti['close_time'].isoformat() if ti['close_time'] else ''},{ti['net_pnl']:.2f}"
            for ti in trade_items
        )
        token_digest = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()
        verification_hash = f"MTD-AUDIT-{token_digest[:16].upper()}"

        audit_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        period_from_str = date_from.strftime("%Y-%m-%d") if date_from else (trade_items[0]["close_time"].strftime("%Y-%m-%d") if trade_items else "—")
        period_to_str = date_to.strftime("%Y-%m-%d") if date_to else (trade_items[-1]["close_time"].strftime("%Y-%m-%d") if trade_items else "—")

        # اگر معامله‌ای نبود
        if not trade_items:
            cred = StatementCredentials(
                trader_name=trader_name,
                account_id=account_id,
                audit_date=audit_date_str,
                period_from=period_from_str,
                period_to=period_to_str,
                initial_balance=initial_balance,
                current_balance=initial_balance,
                verification_hash=verification_hash,
                currency=currency,
            )
            empty_metrics = KeyMetrics(
                net_pnl=0.0,
                gross_profit=0.0,
                gross_loss=0.0,
                return_pct=0.0,
                profit_factor=None,
                profit_factor_status="no_usable_pnl",
                win_rate=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                breakeven_trades=0,
                avg_win=0.0,
                avg_loss=0.0,
                win_loss_ratio=0.0,
                largest_win=0.0,
                largest_loss=0.0,
                avg_trade_pnl=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                calmar_ratio=None,
                recovery_factor=None,
                max_drawdown=0.0,
                max_drawdown_pct=0.0,
                expectancy_usd=0.0,
                expectancy_r=None,
                avg_r_multiple=None,
                total_r_multiple=None,
                max_consecutive_wins=0,
                max_consecutive_losses=0,
            )
            empty_ls = LongShortProfile(
                long_trades=0, long_wins=0, long_win_rate=0.0, long_pnl=0.0,
                short_trades=0, short_wins=0, short_win_rate=0.0, short_pnl=0.0,
            )
            return StatementResponse(
                credentials=cred,
                metrics=empty_metrics,
                long_short=empty_ls,
                monthly_matrix=[],
                equity_curve=[EquityPoint(trade_num=0, close_time=None, equity=initial_balance, drawdown=0.0, drawdown_pct=0.0)],
                top_symbols=[],
            )

        # 3. منحنی سرمایه و دراوداون
        equity = initial_balance
        peak = equity
        max_dd = 0.0
        max_dd_pct = 0.0
        equity_curve: List[EquityPoint] = [
            EquityPoint(trade_num=0, close_time=trade_items[0]["close_time"].isoformat() if trade_items[0]["close_time"] else None, equity=round(initial_balance, 2), drawdown=0.0, drawdown_pct=0.0)
        ]

        # برای محاسبه بازده‌های روزانه
        daily_pnl: Dict[str, float] = {}

        for idx, ti in enumerate(trade_items, start=1):
            npnl = ti["net_pnl"]
            equity += npnl
            if equity > peak:
                peak = equity
            dd = peak - equity
            dd_pct = (dd / peak * 100.0) if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

            ct = ti["close_time"]
            iso_time = ct.isoformat() if ct else None
            equity_curve.append(EquityPoint(
                trade_num=idx,
                close_time=iso_time,
                equity=round(equity, 2),
                drawdown=round(dd, 2),
                drawdown_pct=round(dd_pct, 2),
            ))

            # تجمیع روزانه برای نسبت شارپ و سورتینو
            if ct:
                day_key = ct.strftime("%Y-%m-%d")
                daily_pnl[day_key] = daily_pnl.get(day_key, 0.0) + npnl

        current_balance = equity
        total_pnl = current_balance - initial_balance
        return_pct = (total_pnl / initial_balance * 100.0) if initial_balance > 0 else 0.0

        # 4. آمار سود و زیان
        pnls = [ti["net_pnl"] for ti in trade_items]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        be = [p for p in pnls if p == 0]

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        pf_res = profit_factor_status(gross_profit, gross_loss)
        pf_value = pf_res["value"]

        total_trades = len(pnls)
        winning_trades = len(wins)
        losing_trades = len(losses)
        breakeven_trades = len(be)
        win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

        avg_win = (gross_profit / winning_trades) if winning_trades > 0 else 0.0
        avg_loss = (gross_loss / losing_trades) if losing_trades > 0 else 0.0
        win_loss_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0
        largest_win = max(wins) if wins else 0.0
        largest_loss = min(losses) if losses else 0.0
        avg_trade_pnl = (total_pnl / total_trades) if total_trades > 0 else 0.0

        # امید ریاضی
        wr_fraction = win_rate / 100.0
        lr_fraction = losing_trades / total_trades if total_trades > 0 else 0.0
        expectancy_usd = (wr_fraction * avg_win) - (lr_fraction * avg_loss)

        # ضرایب R
        r_list = [ti["r_multiple"] for ti in trade_items if ti["r_multiple"] is not None]
        avg_r = (sum(r_list) / len(r_list)) if r_list else None
        total_r = sum(r_list) if r_list else None
        expectancy_r = None
        if r_list:
            r_wins = [r for r in r_list if r > 0]
            r_losses = [abs(r) for r in r_list if r < 0]
            avg_r_win = (sum(r_wins) / len(r_wins)) if r_wins else 0.0
            avg_r_loss = (sum(r_losses) / len(r_losses)) if r_losses else 0.0
            expectancy_r = (wr_fraction * avg_r_win) - (lr_fraction * avg_r_loss)

        # توالی‌ها
        max_w_streak, max_l_streak = win_loss_streaks(pnls)

        # 5. شارپ، سورتینو و کالمار
        # بازده‌های روزانه تقریبی بر مبنای بالانس اولیه
        daily_returns = [dp / initial_balance for dp in daily_pnl.values()] if daily_pnl else []
        sharpe_ratio = 0.0
        sortino_ratio = 0.0
        if len(daily_returns) >= 2:
            mean_r = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_r) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
            std_r = math.sqrt(variance) if variance > 0 else 0.0
            if std_r > 0:
                # سالانه‌سازی استاندارد ۲۵۲ روز معاملاتی
                sharpe_ratio = (mean_r / std_r) * math.sqrt(252)

            downside_sq = [min(0.0, r) ** 2 for r in daily_returns]
            downside_variance = sum(downside_sq) / len(downside_sq)
            downside_std = math.sqrt(downside_variance) if downside_variance > 0 else 0.0
            if downside_std > 0:
                sortino_ratio = (mean_r / downside_std) * math.sqrt(252)

        calmar_ratio = None
        recovery_factor = None
        if max_dd > 0:
            recovery_factor = round(total_pnl / max_dd, 2)
            if max_dd_pct > 0:
                calmar_ratio = round(return_pct / max_dd_pct, 2)

        # 6. تفکیک لانگ و شورت
        longs = [ti for ti in trade_items if ti["direction"] in ("buy", "long")]
        shorts = [ti for ti in trade_items if ti["direction"] in ("sell", "short")]
        long_wins = sum(1 for ti in longs if ti["net_pnl"] > 0)
        short_wins = sum(1 for ti in shorts if ti["net_pnl"] > 0)

        long_short = LongShortProfile(
            long_trades=len(longs),
            long_wins=long_wins,
            long_win_rate=round(long_wins / len(longs) * 100.0, 1) if longs else 0.0,
            long_pnl=round(sum(ti["net_pnl"] for ti in longs), 2),
            short_trades=len(shorts),
            short_wins=short_wins,
            short_win_rate=round(short_wins / len(shorts) * 100.0, 1) if shorts else 0.0,
            short_pnl=round(sum(ti["net_pnl"] for ti in shorts), 2),
        )

        # 7. ماتریس ماهانه عملکرد (Monthly Returns Matrix)
        # تفکیک ماه به ماه بر مبنای تاریخ خروج معامله
        year_months_pnl: Dict[int, Dict[int, float]] = {}
        for ti in trade_items:
            ct = ti["close_time"]
            if not ct:
                continue
            y = ct.year
            m = ct.month
            if y not in year_months_pnl:
                year_months_pnl[y] = {month_idx: 0.0 for month_idx in range(1, 13)}
            year_months_pnl[y][m] += ti["net_pnl"]

        monthly_matrix: List[MonthlyPerformance] = []
        for y in sorted(year_months_pnl.keys()):
            m_dict: Dict[str, Optional[float]] = {}
            m_pnl_dict: Dict[str, Optional[float]] = {}
            ytd_pnl = 0.0
            for m_num in range(1, 13):
                m_name = MONTH_NAMES[m_num - 1]
                pnl_val = year_months_pnl[y][m_num]
                if pnl_val != 0.0:
                    ret_pct = round((pnl_val / initial_balance) * 100.0, 2)
                    m_dict[m_name] = ret_pct
                    m_pnl_dict[m_name] = round(pnl_val, 2)
                    ytd_pnl += pnl_val
                else:
                    m_dict[m_name] = None
                    m_pnl_dict[m_name] = None
            ytd_ret = round((ytd_pnl / initial_balance) * 100.0, 2)
            monthly_matrix.append(MonthlyPerformance(
                year=y,
                months=m_dict,
                months_pnl=m_pnl_dict,
                ytd_return_pct=ytd_ret,
                ytd_pnl=round(ytd_pnl, 2),
            ))

        # 8. تفکیک نمادهای برتر (Top Traded Symbols)
        sym_map: Dict[str, Dict[str, Any]] = {}
        for ti in trade_items:
            s = ti["symbol"]
            if s not in sym_map:
                sym_map[s] = {"count": 0, "pnl": 0.0, "wins": 0, "losses_sum": 0.0, "wins_sum": 0.0}
            sym_map[s]["count"] += 1
            sym_map[s]["pnl"] += ti["net_pnl"]
            if ti["net_pnl"] > 0:
                sym_map[s]["wins"] += 1
                sym_map[s]["wins_sum"] += ti["net_pnl"]
            elif ti["net_pnl"] < 0:
                sym_map[s]["losses_sum"] += abs(ti["net_pnl"])

        top_symbols: List[SymbolStats] = []
        for s, d in sorted(sym_map.items(), key=lambda item: item[1]["count"], reverse=True)[:10]:
            w_rate = round((d["wins"] / d["count"] * 100.0), 1) if d["count"] > 0 else 0.0
            pf_sym = None
            if d["losses_sum"] > 0:
                pf_sym = round(d["wins_sum"] / d["losses_sum"], 2)
            elif d["wins_sum"] > 0:
                pf_sym = 999.0
            top_symbols.append(SymbolStats(
                symbol=s,
                trades_count=d["count"],
                net_pnl=round(d["pnl"], 2),
                win_rate=w_rate,
                profit_factor=pf_sym,
            ))

        cred = StatementCredentials(
            trader_name=trader_name,
            account_id=account_id,
            audit_date=audit_date_str,
            period_from=period_from_str,
            period_to=period_to_str,
            initial_balance=round(initial_balance, 2),
            current_balance=round(current_balance, 2),
            verification_hash=verification_hash,
            currency=currency,
        )

        km = KeyMetrics(
            net_pnl=round(total_pnl, 2),
            gross_profit=round(gross_profit, 2),
            gross_loss=round(gross_loss, 2),
            return_pct=round(return_pct, 2),
            profit_factor=pf_value,
            profit_factor_status=pf_res["status"],
            win_rate=round(win_rate, 1),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            breakeven_trades=breakeven_trades,
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            win_loss_ratio=round(win_loss_ratio, 2),
            largest_win=round(largest_win, 2),
            largest_loss=round(largest_loss, 2),
            avg_trade_pnl=round(avg_trade_pnl, 2),
            sharpe_ratio=round(sharpe_ratio, 2),
            sortino_ratio=round(sortino_ratio, 2),
            calmar_ratio=calmar_ratio,
            recovery_factor=recovery_factor,
            max_drawdown=round(max_dd, 2),
            max_drawdown_pct=round(max_dd_pct, 2),
            expectancy_usd=round(expectancy_usd, 2),
            expectancy_r=round(expectancy_r, 2) if expectancy_r is not None else None,
            avg_r_multiple=round(avg_r, 2) if avg_r is not None else None,
            total_r_multiple=round(total_r, 2) if total_r is not None else None,
            max_consecutive_wins=max_w_streak,
            max_consecutive_losses=max_l_streak,
        )

        return StatementResponse(
            credentials=cred,
            metrics=km,
            long_short=long_short,
            monthly_matrix=monthly_matrix,
            equity_curve=equity_curve,
            top_symbols=top_symbols,
        )
