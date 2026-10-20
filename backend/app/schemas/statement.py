from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class StatementCredentials(BaseModel):
    trader_name: str
    account_id: str
    audit_date: str
    period_from: Optional[str] = None
    period_to: Optional[str] = None
    initial_balance: float
    current_balance: float
    verification_hash: str
    currency: str


class KeyMetrics(BaseModel):
    net_pnl: float
    gross_profit: float
    gross_loss: float
    return_pct: float
    profit_factor: Optional[float] = None
    profit_factor_status: str
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    avg_win: float
    avg_loss: float
    win_loss_ratio: float
    largest_win: float
    largest_loss: float
    avg_trade_pnl: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: Optional[float] = None
    recovery_factor: Optional[float] = None
    max_drawdown: float
    max_drawdown_pct: float
    expectancy_usd: float
    expectancy_r: Optional[float] = None
    avg_r_multiple: Optional[float] = None
    total_r_multiple: Optional[float] = None
    max_consecutive_wins: int
    max_consecutive_losses: int


class LongShortProfile(BaseModel):
    long_trades: int
    long_wins: int
    long_win_rate: float
    long_pnl: float
    short_trades: int
    short_wins: int
    short_win_rate: float
    short_pnl: float


class MonthlyPerformance(BaseModel):
    year: int
    months: Dict[str, Optional[float]]       # e.g. "Jan": 2.45 (%)
    months_pnl: Dict[str, Optional[float]]   # e.g. "Jan": 245.0 (currency)
    ytd_return_pct: float
    ytd_pnl: float


class EquityPoint(BaseModel):
    trade_num: int
    close_time: Optional[str]
    equity: float
    drawdown: float
    drawdown_pct: float


class SymbolStats(BaseModel):
    symbol: str
    trades_count: int
    net_pnl: float
    win_rate: float
    profit_factor: Optional[float] = None


class StatementResponse(BaseModel):
    credentials: StatementCredentials
    metrics: KeyMetrics
    long_short: LongShortProfile
    monthly_matrix: List[MonthlyPerformance]
    equity_curve: List[EquityPoint]
    top_symbols: List[SymbolStats]
