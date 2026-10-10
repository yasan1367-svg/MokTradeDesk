import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import DashboardPage from '../pages/DashboardPage';
import ToastProvider from '../components/ToastProvider';
import { getDashboardData, getPropAlerts, getAllVersions, getRealSummary, getTrades } from '../api/client';
import { formatEquityDate } from '../utils/formatEquityDate';

vi.mock('../api/client', () => ({
  getDashboardData: vi.fn(),
  getPropAlerts: vi.fn(),
  exportDashboardPdf: vi.fn(),
  markAlertRead: vi.fn(),
  getAllVersions: vi.fn(),
  getYesterdayData: vi.fn().mockResolvedValue({ data: null }),
  getRealSummary: vi.fn().mockResolvedValue({ data: null }),
  getFinanceSummary: vi.fn().mockResolvedValue({ data: {} }),
  getFinanceCashflow: vi.fn().mockResolvedValue({ data: [] }),
  getFinanceAccounts: vi.fn().mockResolvedValue({ data: [] }),
  getTrades: vi.fn().mockResolvedValue({ data: { trades: [] } }),
  getSpendableAssets: vi.fn().mockResolvedValue({ data: null }),
  getNetProfit: vi.fn().mockResolvedValue({ data: null }),
  getAssetTrend: vi.fn().mockResolvedValue({ data: { trend: [] } }),
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
  today: { pnl: 1234, trades_count: 20, win_rate: 55 },
  periods: { month: { pnl: 0 }, quarter: { pnl: 0 }, year: { pnl: 0 } },
  pnl_distribution: [],
  win_loss: { wins: 11, losses: 9 },
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
    vi.clearAllMocks();
    vi.mocked(getAllVersions).mockResolvedValue({ data: [] } as never);
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

  it('renders the dashboard with the stored date, scope and currency filters', async () => {
    render(
      <ToastProvider>
        <DashboardPage />
      </ToastProvider>,
    );

    expect(await screen.findByText('+1234 IRR')).toBeInTheDocument();
    expect(screen.getByTestId('equity-chart')).toHaveTextContent('IRR:2');

    expect(getDashboardData).toHaveBeenCalledWith({
      date_from: '2025-06-01',
      date_to: '2025-06-30',
      scope: 'forward',
      currency: 'IRR',
    });
  });

  function deferred() {
    let resolve!: (value: Awaited<ReturnType<typeof getDashboardData>>) => void;
    let reject!: (reason: Error) => void;
    const promise = new Promise<Awaited<ReturnType<typeof getDashboardData>>>((res, rej) => {
      resolve = res;
      reject = rej;
    });
    return { promise, resolve, reject };
  }

  const response = (pnl: number) => ({
    data: { ...dashboardResponse, today: { ...dashboardResponse.today, pnl },
      summary: { ...dashboardResponse.summary, avg_r_multiple: pnl } },
  } as Awaited<ReturnType<typeof getDashboardData>>);

  async function mountDashboard() {
    const view = render(<ToastProvider><DashboardPage /></ToastProvider>);
    await screen.findByText('+1234 IRR');
    return view;
  }

  it('test_stale_response_is_discarded', async () => {
    await mountDashboard();
    const older = deferred();
    const newer = deferred();
    vi.mocked(getDashboardData).mockReturnValueOnce(older.promise).mockReturnValueOnce(newer.promise);
    fireEvent.click(screen.getByRole('button', { name: 'USDT', exact: true }));
    fireEvent.click(screen.getByRole('button', { name: 'IRR', exact: true }));
    await act(async () => { newer.resolve(response(2222)); });
    expect(screen.getByText('+2222 IRR')).toBeInTheDocument();
    await act(async () => { older.resolve(response(1111)); });
    expect(screen.getByText('+2222 IRR')).toBeInTheDocument();
    expect(screen.queryByText(/1111/)).not.toBeInTheDocument();
  });

  it.each(['success', 'error'])('ignores stale %s while the newest request is loading', async (outcome) => {
    await mountDashboard();
    const older = deferred();
    const newer = deferred();
    vi.mocked(getDashboardData).mockReturnValueOnce(older.promise).mockReturnValueOnce(newer.promise);
    fireEvent.click(screen.getByRole('button', { name: 'به‌روزرسانی', exact: true }));
    fireEvent.click(screen.getByRole('button', { name: 'USDT', exact: true }));
    await act(async () => {
      if (outcome === 'success') older.resolve(response(1111));
      else older.reject(new Error('old failure'));
    });
    expect(screen.getByRole('button', { name: 'به‌روزرسانی', exact: true })).toBeDisabled();
    expect(screen.queryByText('داشبورد به‌روزرسانی شد')).not.toBeInTheDocument();
    expect(screen.queryByText('خطا در بارگذاری داشبورد')).not.toBeInTheDocument();
    expect(screen.queryByText(/1111/)).not.toBeInTheDocument();
    await act(async () => { newer.resolve(response(2222)); });
    expect(screen.getByText('+2222 USDT')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'به‌روزرسانی', exact: true })).toBeEnabled();
  });

  it.each(['success', 'error'])('discards stale backtest %s independently of main requests', async (outcome) => {
    vi.mocked(getAllVersions).mockResolvedValue({ data: [
      { id: 1, version_name: 'v1' }, { id: 2, version_name: 'v2' },
    ] } as never);
    localStorage.setItem('mok_dashboard_version', '1');
    const older = deferred();
    const newer = deferred();
    vi.mocked(getDashboardData).mockImplementation((params) => {
      if (params?.version_id === 1) return older.promise;
      if (params?.version_id === 2) return newer.promise;
      return Promise.resolve(response(1234));
    });
    await mountDashboard();
    fireEvent.change(screen.getByRole('combobox', { name: 'انتخاب نسخه برای عملکرد بک‌تست' }), { target: { value: '2' } });
    fireEvent.click(screen.getByRole('button', { name: 'USDT', exact: true }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'به‌روزرسانی', exact: true })).toBeEnabled());
    await act(async () => { newer.resolve(response(22)); });
    expect(screen.getByText(/R-Multiple: 22.00/)).toBeInTheDocument();
    await act(async () => {
      if (outcome === 'success') older.resolve(response(11));
      else older.reject(new Error('old backtest failure'));
    });
    expect(screen.getByText(/R-Multiple: 22.00/)).toBeInTheDocument();
  });

  it.each(['success', 'error'])('logically cancels main requests on unmount (%s)', async (outcome) => {
    const view = await mountDashboard();
    const pending = deferred();
    vi.mocked(getDashboardData).mockReturnValueOnce(pending.promise);
    fireEvent.click(screen.getByRole('button', { name: 'به‌روزرسانی', exact: true }));
    // Keep the provider mounted so late toasts would remain observable.
    view.rerender(<ToastProvider><div>Unmounted</div></ToastProvider>);
    await act(async () => {
      if (outcome === 'success') pending.resolve(response(1111));
      else pending.reject(new Error('late failure'));
    });
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.getByText('Unmounted')).toBeInTheDocument();
  });

  it('formats equity curve dates as Persian calendar dates', () => {
    expect(formatEquityDate('2025-06-11T10:00:00+00:00')).toBe(
      new Date('2025-06-11T12:00:00').toLocaleDateString('fa-IR'),
    );
  });

  it('keeps live data and navigation intact in the approved layout', async () => {
    vi.mocked(getRealSummary).mockResolvedValueOnce({ data: {
      total_trades: 12, net_pnl: 700, winning_trades: 8, losing_trades: 4,
      win_rate: 66.7, profit_factor: 1.8, gross_profit: 900, gross_loss: 200,
      max_dd: 80, sparkline: [0, 200, 700],
    } } as never);
    vi.mocked(getTrades)
      .mockResolvedValueOnce({ data: { trades: [{ id: 10, symbol: 'EURUSD', direction: 'buy', pnl: 100, commission: -2, swap: -3 }] } } as never)
      .mockResolvedValueOnce({ data: { trades: [{ id: 11, symbol: 'XAUUSD', direction: 'sell', pnl: null }] } } as never);
    vi.mocked(getPropAlerts).mockResolvedValueOnce({ data: [{ id: 5, message: '⚠️ هشدار واقعی پراپ' }] } as never);
    const onNavigate = vi.fn();
    const { container } = render(<ToastProvider><DashboardPage onNavigate={onNavigate} /></ToastProvider>);
    await screen.findByText('+1234 IRR');
    const pair = screen.getByTestId('prop-backtest-pair');
    expect(within(pair).getByText('وضعیت پراپ')).toBeInTheDocument();
    expect(within(pair).getByText('عملکرد بک‌تست')).toBeInTheDocument();
    expect(pair.closest('details')).toBeNull();
    const real = screen.getByTestId('real-performance-section');
    const trades = screen.getByTestId('dashboard-trades-section');
    expect(real.closest('details')).toBeNull();
    expect(real.compareDocumentPosition(trades) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(container.querySelector('.dashboard-root')?.lastElementChild).toBe(trades);
    expect(screen.getByText('⚠️ هشدار واقعی پراپ').closest('details')).toBeNull();
    expect(within(real).getByText(/700 IRR/)).toBeInTheDocument();
    expect(within(trades).getByText('+95.00 IRR')).toBeInTheDocument();
    const openCard = within(trades).getByText('📂 معاملات باز').closest('.app-card')!;
    expect(openCard.querySelector('tbody tr td:last-child')).toHaveTextContent('—');
    expect(screen.getByTestId('dashboard-finance-details')).not.toHaveAttribute('open');
    fireEvent.click(within(trades).getByRole('button', { name: /مشاهده همه/ }));
    expect(onNavigate).toHaveBeenCalledWith('trades');
  });
});
