import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import StatementPage from '../pages/StatementPage';
import ToastProvider from '../components/ToastProvider';
import * as client from '../api/client';

const mockStatementResponse = {
  data: {
    credentials: {
      trader_name: 'Lead Trader',
      account_id: 'ACT-777',
      audit_date: '2026-10-20 12:00 UTC',
      period_from: '2026-01-01',
      period_to: '2026-10-20',
      initial_balance: 10000,
      current_balance: 12500,
      verification_hash: 'MTD-AUDIT-ABC1234567890DEF',
      currency: 'USDT',
    },
    metrics: {
      net_pnl: 2500,
      gross_profit: 3500,
      gross_loss: 1000,
      return_pct: 25.0,
      profit_factor: 3.5,
      profit_factor_status: 'finite',
      win_rate: 65.5,
      total_trades: 40,
      winning_trades: 26,
      losing_trades: 14,
      breakeven_trades: 0,
      avg_win: 134.6,
      avg_loss: 71.4,
      win_loss_ratio: 1.88,
      largest_win: 450,
      largest_loss: -150,
      avg_trade_pnl: 62.5,
      sharpe_ratio: 1.85,
      sortino_ratio: 2.45,
      calmar_ratio: 3.12,
      recovery_factor: 3.12,
      max_drawdown: 800,
      max_drawdown_pct: 7.2,
      expectancy_usd: 62.5,
      expectancy_r: 1.25,
      avg_r_multiple: 1.35,
      total_r_multiple: 54.0,
      max_consecutive_wins: 6,
      max_consecutive_losses: 2,
    },
    long_short: {
      long_trades: 25,
      long_wins: 17,
      long_win_rate: 68.0,
      long_pnl: 1800,
      short_trades: 15,
      short_wins: 9,
      short_win_rate: 60.0,
      short_pnl: 700,
    },
    monthly_matrix: [
      {
        year: 2026,
        months: { Jan: 5.2, Feb: 8.1, Mar: -1.5 },
        months_pnl: { Jan: 520, Feb: 810, Mar: -150 },
        ytd_return_pct: 25.0,
        ytd_pnl: 2500,
      },
    ],
    equity_curve: [
      { trade_num: 0, close_time: '2026-01-01', equity: 10000, drawdown: 0, drawdown_pct: 0 },
      { trade_num: 1, close_time: '2026-01-10', equity: 10520, drawdown: 0, drawdown_pct: 0 },
    ],
    top_symbols: [
      { symbol: 'XAUUSD', trades_count: 22, net_pnl: 1600, win_rate: 68.2, profit_factor: 3.2 },
      { symbol: 'EURUSD', trades_count: 18, net_pnl: 900, win_rate: 61.1, profit_factor: 2.8 },
    ],
  },
};

describe('StatementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(client, 'getStatementData').mockResolvedValue(mockStatementResponse as any);
  });

  it('renders statement audit dossier with verification hash and key metrics', async () => {
    render(
      <ToastProvider>
        <StatementPage />
      </ToastProvider>,
    );

    expect(screen.getByText(/در حال حسابرسی و تحلیل دفتر کل معاملات/)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('MTD-AUDIT-ABC1234567890DEF')).toBeInTheDocument();
    });

    expect(screen.getByText('صورت‌حساب رسمی حسابرسی عملکرد معاملاتی')).toBeInTheDocument();
    expect(screen.getByText('+25.00%')).toBeInTheDocument();
    expect(screen.getByText('1.85')).toBeInTheDocument(); // Sharpe
    expect(screen.getByText('2.45')).toBeInTheDocument(); // Sortino
    expect(screen.getByText('3.12')).toBeInTheDocument(); // Calmar
    expect(screen.getByText(/VERIFIED LEDGER/)).toBeInTheDocument();
    expect(screen.getByText('XAUUSD')).toBeInTheDocument();
  });
});
