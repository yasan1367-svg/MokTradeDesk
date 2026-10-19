import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, act } from '@testing-library/react';
import ComparisonPage from '../pages/ComparisonPage';

const compare = vi.fn();
vi.mock('../api/client', () => ({
  getAllVersions: vi.fn().mockResolvedValue({ data: [
    { id: 1, version_name: 'v1', strategy_id: 1, strategy_name: 'S', status: 'active', trades_count: 2 },
    { id: 2, version_name: 'v2', strategy_id: 1, strategy_name: 'S', status: 'active', trades_count: 2 },
  ] }),
  getStrategies: vi.fn().mockResolvedValue({ data: [{ id: 1, name: 'S' }] }),
  compareVersions: (...args: unknown[]) => compare(...args),
}));
vi.mock('../components/ToastProvider', () => ({ useToast: () => ({ warning: vi.fn(), error: vi.fn(), success: vi.fn() }) }));
vi.mock('../components/charts/ComparisonBarChart', () => ({ default: () => <div /> }));
vi.mock('../components/charts/ComparisonRadarChart', () => ({ default: () => <div /> }));

describe('ComparisonPage Stage 3 display contract', () => {
  beforeEach(() => {
    compare.mockReset();
    window.history.replaceState({}, '', '/comparison');
  });

  it('renders no-loss PF by status, not sentinel', async () => {
    compare.mockResolvedValue({ data: {
      test_type: 'BACKTEST', filters: {}, best: { version_id: 1, score: 70 },
      best_ties: [{ version_id: 1 }],
      comparison: [1, 2].map((version_id) => ({
        version_id, rank: version_id, rank_tie: false, tie_count: 1, score: 70, sample_status: 'کافی',
        metrics: { total_trades: 2, profit_factor: 999, profit_factor_status: 'no_losses', net_pnl: 100, win_rate: 100, max_dd: 0 },
        components: { pf_status: 'no_losses', pf_score: 100 }, reasons: [],
      })),
    } });
    render(<ComparisonPage />);
    await waitFor(() => expect(screen.getByRole('button', { name: /مقایسه/ })).toBeInTheDocument());
    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: /مقایسه/ }));
    await waitFor(() => expect(compare).toHaveBeenCalled());
    expect(screen.getAllByText('بدون باخت')).toHaveLength(2);
  });

  it('renders the returned PF deciding explanation and keeps full ties shared', async () => {
    compare.mockResolvedValue({ data: {
      test_type: 'BACKTEST', filters: {}, best: { version_id: 1, score: 70, reasons: [
        { icon: '⚖️', text: 'معیار تعیین‌کننده: PF؛ finite 2 در برابر finite 1' },
      ] },
      best_ties: [{ version_id: 1 }, { version_id: 2 }],
      comparison: [1, 2].map((version_id) => ({
        version_id, rank: 1, rank_tie: true, tie_count: 2, score: 70, sample_status: 'کافی',
        metrics: { total_trades: 2, profit_factor: 1, profit_factor_status: 'finite', net_pnl: 0, win_rate: 50, max_dd: 0 },
        reasons: [],
      })),
    } });
    render(<ComparisonPage />);
    await waitFor(() => expect(screen.getByRole('button', { name: /مقایسه/ })).toBeInTheDocument());
    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: /مقایسه/ }));
    expect(await screen.findByText(/PF؛ finite 2 در برابر finite 1/)).toBeInTheDocument();
    expect(screen.getByText('نسخه‌های هم‌رتبهٔ نخست')).toBeInTheDocument();
  });

  it('ignores superseded late success/failure, and Clear cancels pending work', async () => {
    let rejectFirst!: (reason: unknown) => void;
    let resolveSecond!: (value: unknown) => void;
    compare
      .mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectFirst = reject; }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveSecond = resolve; }));
    render(<ComparisonPage />);
    await screen.findByRole('button', { name: /مقایسه/ });
    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: /مقایسه/ }));
    await waitFor(() => expect(compare).toHaveBeenCalledTimes(1));
    fireEvent.change(screen.getByPlaceholderText('XAUUSD'), { target: { value: 'BTCUSDT' } });
    expect(screen.queryByTestId('applied-filters')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /مقایسه/ }));
    await waitFor(() => expect(compare).toHaveBeenCalledTimes(2));

    await act(async () => {
      rejectFirst({ response: { data: { detail: 'late old failure' } } });
    });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await act(async () => {
      resolveSecond({ data: { test_type: 'BACKTEST', filters: {}, best: null, comparison: [] } });
    });
    expect(screen.getByTestId('applied-filters')).toHaveTextContent('BTCUSDT');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();

    let resolveCleared!: (value: unknown) => void;
    compare.mockImplementationOnce(() => new Promise((resolve) => { resolveCleared = resolve; }));
    fireEvent.click(screen.getByRole('button', { name: /مقایسه/ }));
    await waitFor(() => expect(compare).toHaveBeenCalledTimes(3));

    fireEvent.click(screen.getByRole('button', { name: /پاک کردن/ }));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByTestId('applied-filters')).not.toBeInTheDocument();
    await act(async () => resolveCleared({ data: { test_type: 'BACKTEST', filters: {}, best: null, comparison: [] } }));
    expect(screen.queryByTestId('applied-filters')).not.toBeInTheDocument();
  });

  it('invalidates an in-flight comparison when filters change and never displays its response', async () => {
    let resolve!: (value: unknown) => void;
    compare.mockImplementation(() => new Promise((done) => { resolve = done; }));
    render(<ComparisonPage />);
    await screen.findByRole('button', { name: /مقایسه/ });
    await waitFor(() => expect(screen.getAllByRole('checkbox')).toHaveLength(2));
    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: /مقایسه/ }));
    await waitFor(() => expect(compare).toHaveBeenCalledTimes(1));
    fireEvent.change(screen.getByPlaceholderText('XAUUSD'), { target: { value: 'ETHUSDT' } });
    expect(screen.queryByTestId('applied-filters')).not.toBeInTheDocument();
    await act(async () => resolve({ data: { test_type: 'BACKTEST', filters: {}, best: null, comparison: [] } }));
    expect(screen.queryByTestId('applied-filters')).not.toBeInTheDocument();
  });

  it('renders poursamadi comparative table when custom_time_analysis is present', async () => {
    compare.mockResolvedValue({
      data: {
        test_type: 'BACKTEST',
        filters: {},
        best: { version_id: 1, score: 85 },
        best_ties: [{ version_id: 1 }],
        comparison: [
          {
            version_id: 1,
            rank: 1,
            score: 85,
            metrics: {
              total_trades: 10,
              profit_factor: 2.5,
              profit_factor_status: 'finite',
              net_pnl: 500,
              win_rate: 70,
              max_dd: 50,
              custom_time_analysis: {
                'طلا — A1 [A]': { total_trades: 6, wins: 5, losses: 1, win_rate: 83.33, net_pnl: 450, profit_factor: 3.2 },
                'طلا — خارج از بازه [خارج]': { total_trades: 4, wins: 2, losses: 2, win_rate: 50, net_pnl: 50, profit_factor: 1.1 },
              },
            },
            components: { pf_status: 'finite', pf_score: 80 },
            reasons: [],
          },
          {
            version_id: 2,
            rank: 2,
            score: 65,
            metrics: {
              total_trades: 8,
              profit_factor: 1.4,
              profit_factor_status: 'finite',
              net_pnl: 150,
              win_rate: 50,
              max_dd: 80,
              custom_time_analysis: {
                'طلا — A1 [A]': { total_trades: 5, wins: 3, losses: 2, win_rate: 60, net_pnl: 200, profit_factor: 1.8 },
                'طلا — خارج از بازه [خارج]': { total_trades: 3, wins: 1, losses: 2, win_rate: 33.33, net_pnl: -50, profit_factor: 0.7 },
              },
            },
            components: { pf_status: 'finite', pf_score: 60 },
            reasons: [],
          },
        ],
      },
    });

    render(<ComparisonPage />);
    await screen.findByRole('button', { name: /مقایسه/ });
    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: /مقایسه/ }));

    expect(await screen.findByText('بررسی تطبیقی بازه‌های زمانی (پورصمدی)')).toBeInTheDocument();
    expect(screen.getByText('طلا — A1')).toBeInTheDocument();
    expect(screen.getAllByText('A')).toHaveLength(1);
    expect(screen.getByText('طلا — خارج از بازه')).toBeInTheDocument();
    expect(screen.getByText('خارج از بازه')).toBeInTheDocument();
    expect(screen.getByText('+450 USDT')).toBeInTheDocument();
    expect(screen.getAllByText('-50 USDT').length).toBeGreaterThanOrEqual(1);
  });
});
