import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import DashboardPage from '../pages/DashboardPage';
import ToastProvider from '../components/ToastProvider';
import { getDashboardData, getPropAlerts } from '../api/client';
import { formatEquityDate } from '../utils/formatEquityDate';

vi.mock('../api/client', () => ({
  getDashboardData: vi.fn(),
  getPropAlerts: vi.fn(),
  exportDashboardPdf: vi.fn(),
  markAlertRead: vi.fn(),
}));

vi.mock('../components/MarketSessionWidget', () => ({
  default: () => <div data-testid="market-session-widget" />,
}));

vi.mock('../components/charts/EquityCurveChart', () => ({
  default: ({ currency, data }: { currency: string; data: { date: string | null }[] }) => (
    <div data-testid="equity-chart">{currency}:{data.length}</div>
  ),
}));

const dashboardResponse = {
  currency: 'IRR',
  summary: {
    net_pnl: 1250,
    win_rate: 55,
    max_dd: 175,
    profit_factor: 1.75,
    total_trades: 20,
    closed_trades: 20,
    winning_trades: 11,
    losing_trades: 9,
  },
  equity_curve: [
    { date: null, equity: 10000 },
    { date: '2025-06-11T10:00:00+00:00', equity: 11250 },
  ],
  recent_trades: [{
    id: 1,
    symbol: 'XAUUSD',
    direction: 'buy',
    strategy_name: 'Breakout',
    close_time: '2025-06-11T10:00:00+00:00',
    net_pnl: 1250,
  }],
  prop_progress: [],
};

describe('DashboardPage', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('mok_dashboard_range', 'custom');
    localStorage.setItem('mok_dashboard_custom_from', '2025-06-01');
    localStorage.setItem('mok_dashboard_custom_to', '2025-06-30');
    localStorage.setItem('mok_dashboard_scope', 'forward');
    localStorage.setItem('mok_dashboard_currency', 'IRR');
    vi.mocked(getDashboardData).mockResolvedValue(
      { data: dashboardResponse } as unknown as Awaited<ReturnType<typeof getDashboardData>>,
    );
    vi.mocked(getPropAlerts).mockResolvedValue(
      { data: [] } as unknown as Awaited<ReturnType<typeof getPropAlerts>>,
    );
  });

  it('renders filtered closed-trade KPIs, date/currency curve, and no open-trades section', async () => {
    render(
      <ToastProvider>
        <DashboardPage />
      </ToastProvider>,
    );

    expect(await screen.findByText('55.0٪')).toBeInTheDocument();
    expect(screen.queryByText(/5500/)).not.toBeInTheDocument();
    expect(screen.getByText('11 Win')).toBeInTheDocument();
    expect(screen.getByText('9 Loss')).toBeInTheDocument();
    expect(screen.getByText('Net PnL معاملات')).toBeInTheDocument();
    expect(screen.getByText('معاملات بسته‌شده')).toBeInTheDocument();
    expect(screen.getByTestId('equity-chart')).toHaveTextContent('IRR:2');
    expect(screen.getByText(/معاملات بسته‌شدهٔ اخیر/)).toBeInTheDocument();
    expect(screen.getByText('XAUUSD')).toBeInTheDocument();
    expect(screen.getByText('Breakout')).toBeInTheDocument();
    expect(screen.queryByText(/معاملات باز/)).not.toBeInTheDocument();
    expect(screen.queryByText('روز گذشته')).not.toBeInTheDocument();
    expect(screen.queryByText('جریان نقدی')).not.toBeInTheDocument();

    expect(getDashboardData).toHaveBeenCalledWith({
      date_from: '2025-06-01',
      date_to: '2025-06-30',
      scope: 'forward',
      currency: 'IRR',
    });
  });

  it('formats equity curve dates as Persian calendar dates', () => {
    expect(formatEquityDate('2025-06-11T10:00:00+00:00')).toBe(
      new Date('2025-06-11T12:00:00').toLocaleDateString('fa-IR'),
    );
  });
});