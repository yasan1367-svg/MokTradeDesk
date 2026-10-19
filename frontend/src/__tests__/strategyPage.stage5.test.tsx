import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import StrategyPage from '../pages/StrategyPage';

const { getStrategies, getStrategyVersions, getStrategyStats, getStrategyChartAggregate, getStrategyLivePerformance, createVersion, updateVersion, deleteStrategy, deleteVersion, forkVersion } = vi.hoisted(() => ({
  getStrategies: vi.fn(), getStrategyVersions: vi.fn(), getStrategyStats: vi.fn(),
  getStrategyChartAggregate: vi.fn(), getStrategyLivePerformance: vi.fn(),
  createVersion: vi.fn(), updateVersion: vi.fn(), deleteStrategy: vi.fn(), deleteVersion: vi.fn(), forkVersion: vi.fn(),
}));
vi.mock('../api/client', () => ({
  getStrategies: (...args: unknown[]) => getStrategies(...args),
  getStrategyVersions: (...args: unknown[]) => getStrategyVersions(...args),
  getStrategyStats: (...args: unknown[]) => getStrategyStats(...args),
  getStrategyChartAggregate: (...args: unknown[]) => getStrategyChartAggregate(...args),
  getStrategyLivePerformance: (...args: unknown[]) => getStrategyLivePerformance(...args),
  createVersion: (...args: unknown[]) => createVersion(...args),
  updateVersion: (...args: unknown[]) => updateVersion(...args),
  deleteVersion: (...args: unknown[]) => deleteVersion(...args), forkVersion: (...args: unknown[]) => forkVersion(...args), createStrategy: vi.fn(), updateStrategy: vi.fn(), deleteStrategy: (...args: unknown[]) => deleteStrategy(...args),
}));

vi.mock('../components/PersianDateInput', () => ({ default: ({ label }: { label: string }) => <div>{label}</div> }));

const deferred = <T,>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
};
const emptyStats = (id: number) => ({ data: { strategy_id: id, strategy_name: `S${id}`, total_trades: 1, summary: { net_pnl: 0, win_rate: 0, profit_factor: 0, max_drawdown: 0, sharpe_ratio: 0, expectancy: 0 }, trade_counts: { total: 1, winning: 0, losing: 0, breakeven: 1 }, averages: { avg_win: 0, avg_loss: 0, avg_trade: 0 }, extremes: { largest_win: 0, largest_loss: 0 }, consistency: { max_consecutive_losses: 0, pnl_std_dev: 0 }, per_version: [] } });
const aggregate = { data: { total_trades: 0, net_pnl: 0, test_type: 'BACKTEST', equity_curve: [], r_histogram: [] } };

describe('StrategyPage Stage 5 request ownership and version CRUD', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    getStrategies.mockResolvedValue({ data: [{ id: 1, name: 'A', versions_count: 1 }, { id: 2, name: 'B', versions_count: 0 }] });
    getStrategyVersions.mockImplementation(async (id: number) => ({ data: id === 1 ? [{ id: 11, strategy_id: 1, version_name: 'A-version', status: 'research', test_type: 'real', trades_count: 0, rules_note: null }] : [] }));
    getStrategyStats.mockImplementation(async (id: number) => emptyStats(id));
    getStrategyChartAggregate.mockImplementation((_id: number, params: { test_type?: string }) => params.test_type === 'forward' ? oldResponse.promise : Promise.resolve(aggregate));
    getStrategyLivePerformance.mockResolvedValue({ data: { strategy_id: 1, versions: [], currency: 'USDT' } });
    createVersion.mockResolvedValue({ data: {} });
    updateVersion.mockResolvedValue({ data: {} });
    deleteStrategy.mockResolvedValue({ data: {} });
    deleteVersion.mockResolvedValue({ data: {} });
    forkVersion.mockResolvedValue({ data: {} });
    vi.stubGlobal('confirm', () => true);
  });

  it('A→B ignores A versions, stats/chart late successes and delayed errors', async () => {
    const aStats = deferred<unknown>();
    const aChart = deferred<unknown>();
    getStrategyStats.mockImplementation((id: number) => id === 1 ? aStats.promise : Promise.resolve(emptyStats(2)));
    getStrategyChartAggregate.mockImplementation((id: number) => id === 1 ? aChart.promise : Promise.resolve(aggregate));
    const { container } = render(<StrategyPage />);
    await waitFor(() => expect(container.textContent).toContain('A'));
    const strategyCard = (name: string) => Array.from(container.querySelectorAll('[class*="cursor-pointer"]')).find((node) => node.textContent?.includes(name) && node.textContent?.includes('نسخه'));
    fireEvent.click(strategyCard('A')!);
    fireEvent.click(strategyCard('B')!);
    await waitFor(() => expect(getStrategyStats).toHaveBeenCalledWith(2));
    await act(async () => {
      aStats.reject(new Error('delayed A stats error'));
      aChart.resolve({ data: { total_trades: 99, net_pnl: 999, equity_curve: [{ period: '2025-01', cumulative_pnl: 999 }], r_histogram: [] } });
    });
    expect(container).not.toHaveTextContent('999');
    expect(container).not.toHaveTextContent('خطا در دریافت آمار استراتژی');
    expect(screen.getByText('نسخه‌های «B»')).toBeInTheDocument();
  });

  it('same-strategy refresh ownership rejects older version, stats, chart, and date-filter responses', async () => {
    const firstVersions = deferred<unknown>();
    const secondVersions = deferred<unknown>();
    const olderLive = deferred<unknown>();
    getStrategyVersions.mockImplementation((id: number) => id === 1 ? (getStrategyVersions.mock.calls.filter((call) => call[0] === 1).length === 1 ? firstVersions.promise : secondVersions.promise) : Promise.resolve({ data: [] }));
    const live = (version_id: number) => ({ data: { strategy_id: 1, versions: [{ version_id, version_name: 'live', total_trades: 0, net_pnl: 0, winning_trades: 0, losing_trades: 0, breakeven_trades: 0, win_rate: 0, profit_factor: 0, status: 'research', by_type: { real_personal: { trades: 0, net_pnl: 0 }, real_prop: { trades: 0, net_pnl: 0 } } }], currency: 'USDT' } });
    getStrategyLivePerformance.mockReturnValueOnce(olderLive.promise).mockResolvedValueOnce(live(2));
    const { container } = render(<StrategyPage />);
    await waitFor(() => expect(container.textContent).toContain('A'));
    fireEvent.click(Array.from(container.querySelectorAll('[class*="cursor-pointer"]')).find((node) => node.textContent?.includes('A') && node.textContent?.includes('نسخه'))!);
    fireEvent.click(Array.from(container.querySelectorAll('[class*="cursor-pointer"]')).find((node) => node.textContent?.includes('A') && node.textContent?.includes('نسخه'))!);
    await act(async () => { secondVersions.resolve({ data: [{ id: 12, strategy_id: 1, version_name: 'newest', status: 'research', test_type: 'backtest', trades_count: 0 }] }); });
    await act(async () => { firstVersions.resolve({ data: [{ id: 13, strategy_id: 1, version_name: 'stale', status: 'research', test_type: 'backtest', trades_count: 0 }] }); });
    expect(container.textContent).toContain('newest');
    expect(container.textContent).not.toContain('stale');
    await act(async () => { olderLive.resolve(live(999)); });
    expect(container.textContent).not.toContain('999');
  });

  it('A→B→A prevents older A stats and versions from applying', async () => {
    const staleAStats = deferred<unknown>();
    const staleAVersions = deferred<unknown>();
    const latestAStats = deferred<unknown>();
    const latestAVersions = deferred<unknown>();
    getStrategyStats.mockImplementation((id: number) => id === 1 ? (getStrategyStats.mock.calls.filter((call) => call[0] === 1).length === 1 ? staleAStats.promise : latestAStats.promise) : Promise.resolve(emptyStats(2)));
    getStrategyVersions.mockImplementation((id: number) => id === 1 ? (getStrategyVersions.mock.calls.filter((call) => call[0] === 1).length === 1 ? staleAVersions.promise : latestAVersions.promise) : Promise.resolve({ data: [] }));
    const { container } = render(<StrategyPage />);
    await waitFor(() => expect(container.textContent).toContain('A'));
    const card = (name: string) => Array.from(container.querySelectorAll('[class*="cursor-pointer"]')).find((node) => node.textContent?.includes(name) && node.textContent?.includes('نسخه'))!;
    fireEvent.click(card('A'));
    fireEvent.click(card('B'));
    fireEvent.click(card('A'));
    await waitFor(() => expect(getStrategyStats.mock.calls.filter((call) => call[0] === 1)).toHaveLength(2));
    await act(async () => {
      latestAStats.resolve(emptyStats(1));
      latestAVersions.resolve({ data: [{ id: 12, strategy_id: 1, version_name: 'latest-A', status: 'research', test_type: 'backtest', trades_count: 0 }] });
    });
    await act(async () => {
      staleAStats.resolve({ data: { ...emptyStats(1).data, strategy_name: 'stale-A', total_trades: 77 } });
      staleAVersions.resolve({ data: [{ id: 13, strategy_id: 1, version_name: 'stale-A-version', status: 'research', test_type: 'backtest', trades_count: 0 }] });
    });
    expect(container.textContent).toContain('latest-A');
    expect(container.textContent).not.toContain('stale-A-version');
  });

  it('mutation refresh generation ignores a stale earlier versions response', async () => {
    const oldVersions = deferred<unknown>();
    const refreshedVersions = deferred<unknown>();
    const save = deferred<unknown>();
    getStrategyVersions.mockImplementation((id: number) => {
      const calls = getStrategyVersions.mock.calls.filter((call) => call[0] === 1).length;
      if (id !== 1) return Promise.resolve({ data: [] });
      if (calls === 1) return Promise.resolve({ data: [{ id: 11, strategy_id: 1, version_name: 'A-version', status: 'research', test_type: 'real', trades_count: 0, rules_note: null }] });
      return calls === 2 ? oldVersions.promise : refreshedVersions.promise;
    });
    updateVersion.mockReturnValue(save.promise);
    const { container } = render(<StrategyPage />);
    await waitFor(() => expect(container.textContent).toContain('A'));
    fireEvent.click(Array.from(container.querySelectorAll('[class*="cursor-pointer"]')).find((node) => node.textContent?.includes('A') && node.textContent?.includes('نسخه'))!);
    await waitFor(() => expect(getStrategyVersions).toHaveBeenCalledWith(1));
    await waitFor(() => expect(container.textContent).toContain('A-version'));
    const edit = Array.from(container.querySelectorAll('button[title="ویرایش"]')).find((button) => button.parentElement?.parentElement?.textContent?.includes('A-version'))!;
    fireEvent.click(edit);
    fireEvent.change(screen.getByPlaceholderText('مثلاً SP2L_TP1.5'), { target: { value: 'mutated' } });
    fireEvent.click(screen.getByRole('button', { name: /ذخیره/ }));
    await act(async () => { save.resolve({ data: {} }); });
    await waitFor(() => expect(getStrategyVersions.mock.calls.filter((call) => call[0] === 1)).toHaveLength(3));
    await act(async () => { refreshedVersions.resolve({ data: [{ id: 12, strategy_id: 1, version_name: 'mutation-refresh', status: 'research', test_type: 'backtest', trades_count: 0 }] }); });
    await act(async () => { oldVersions.resolve({ data: [{ id: 13, strategy_id: 1, version_name: 'stale-refresh', status: 'research', test_type: 'backtest', trades_count: 0 }] }); });
    expect(container.textContent).toContain('mutation-refresh');
    expect(container.textContent).not.toContain('stale-refresh');
  });

  it('chart scope changes invalidate late results and show loading without previous chart', async () => {
    const forwardResponse = deferred<unknown>();
    getStrategyChartAggregate.mockResolvedValue(aggregate);
    const { container } = render(<StrategyPage />);
    await waitFor(() => expect(container.textContent).toContain('A'));
    fireEvent.click(Array.from(container.querySelectorAll('[class*="cursor-pointer"]')).find((node) => node.textContent?.includes('A') && node.textContent?.includes('نسخه'))!);
    await waitFor(() => expect(container.textContent).toContain('آمار استراتژی'));
    const forwardToggle = await waitFor(() => {
      const button = Array.from(container.querySelectorAll('button')).find((item) => item.textContent === 'Forward');
      expect(button).toBeTruthy();
      return button!;
    });
    getStrategyChartAggregate.mockImplementation((_id: number, params: { test_type?: string }) => params.test_type === 'forward' ? forwardResponse.promise : Promise.resolve(aggregate));
    await act(async () => { fireEvent.click(forwardToggle); });
    await waitFor(() => expect(getStrategyChartAggregate).toHaveBeenCalledWith(1, { test_type: 'forward' }));
    await waitFor(() => expect(screen.getByRole('status')).toBeInTheDocument());
    expect(getStrategyChartAggregate.mock.calls.filter((call) => call[0] === 1 && call[1]?.test_type === 'forward')).toHaveLength(1);
    await act(async () => { forwardResponse.resolve({ data: { total_trades: 2, net_pnl: 12, test_type: 'FORWARD', equity_curve: [{ period: '2025-02', cumulative_pnl: 12 }], r_histogram: [] } }); });
    expect(await screen.findByText(/2 معاملهٔ بسته · PnL خالص \+12\.00 USDT · FORWARD/)).toBeInTheDocument();
    expect(container.textContent).toContain('12');
  });

  it('chart refresh failure clears chart data and exposes an alert', async () => {
    const { container } = render(<StrategyPage />);
    await waitFor(() => expect(container.textContent).toContain('A'));
    fireEvent.click(Array.from(container.querySelectorAll('[class*="cursor-pointer"]')).find((node) => node.textContent?.includes('A') && node.textContent?.includes('نسخه'))!);
    await waitFor(() => expect(container.textContent).toContain('آمار استراتژی'));
    getStrategyChartAggregate.mockImplementation((_id: number, params: { test_type?: string }) => params.test_type === 'forward' ? Promise.reject(new Error('aggregate unavailable')) : Promise.resolve(aggregate));
    fireEvent.click(Array.from(container.querySelectorAll('button')).find((item) => item.textContent === 'Forward')!);
    await waitFor(() => expect(getStrategyChartAggregate).toHaveBeenCalledWith(1, { test_type: 'forward' }));
    await waitFor(() => expect(screen.getAllByRole('alert')[0]).toHaveTextContent('دریافت کامل آمار و نمودار نسخه‌ها ناموفق بود'));
    expect(container.textContent).not.toContain('0 معاملهٔ بسته');
  });

  it('ignores a superseded chart response that arrives last', async () => {
    const backtestResponse = deferred<unknown>();
    const forwardResponse = deferred<unknown>();
    getStrategyChartAggregate.mockResolvedValue(aggregate);
    const { container } = render(<StrategyPage />);
    await waitFor(() => expect(container.textContent).toContain('A'));
    fireEvent.click(Array.from(container.querySelectorAll('[class*="cursor-pointer"]')).find((node) => node.textContent?.includes('A') && node.textContent?.includes('نسخه'))!);
    await waitFor(() => expect(getStrategyChartAggregate).toHaveBeenCalledWith(1, { test_type: 'backtest' }));
    await waitFor(() => expect(container.textContent).toContain('مجموع تاریخی PnL ماهانهٔ Backtest'));
    getStrategyChartAggregate.mockImplementation((_id: number, params: { test_type?: string }) => params.test_type === 'backtest' ? backtestResponse.promise : forwardResponse.promise);
    await act(async () => { fireEvent.click(Array.from(container.querySelectorAll('button')).find((item) => item.textContent === 'Forward')!); });
    await waitFor(() => expect(getStrategyChartAggregate).toHaveBeenCalledWith(1, { test_type: 'forward' }));
    await act(async () => { forwardResponse.resolve({ data: { total_trades: 1, net_pnl: 8.25, test_type: 'FORWARD', equity_curve: [{ period: '2025-02', cumulative_pnl: 8.25 }], r_histogram: [] } }); });
    expect(await screen.findByText(/1 معاملهٔ بسته · PnL خالص \+8\.25 USDT · FORWARD/)).toBeInTheDocument();
    await act(async () => { backtestResponse.resolve({ data: { total_trades: 99, net_pnl: 99, test_type: 'BACKTEST', equity_curve: [{ period: '2025-01', cumulative_pnl: 99 }], r_histogram: [] } }); });
    expect(container.textContent).not.toContain('99 معاملهٔ بسته');
    expect(container.textContent).toContain('+8.25 USDT');
  });

  it('deleting A after selecting B preserves B and ignores stale mutation completion', async () => {
    const deletion = deferred<unknown>();
    deleteStrategy.mockReturnValue(deletion.promise);
    const { container } = render(<StrategyPage />);
    await waitFor(() => expect(container.textContent).toContain('A'));
    const card = (name: string) => Array.from(container.querySelectorAll('[class*="cursor-pointer"]')).find((node) => node.textContent?.includes(name) && node.textContent?.includes('نسخه'))!;
    fireEvent.click(card('A'));
    const deleteButton = Array.from(container.querySelectorAll('button[title="حذف"]')).find((button) => button.parentElement?.parentElement?.textContent?.includes('A'))!;
    fireEvent.click(deleteButton);
    await waitFor(() => expect(deleteStrategy).toHaveBeenCalledWith(1));
    fireEvent.click(card('B'));
    await act(async () => { deletion.resolve({ data: {} }); });
    expect(screen.getByText('نسخه‌های «B»')).toBeInTheDocument();
  });

  it('old version save completion cannot close a newly opened form', async () => {
    const save = deferred<unknown>();
    updateVersion.mockReturnValue(save.promise);
    const { container } = render(<StrategyPage />);
    await waitFor(() => expect(container.textContent).toContain('A'));
    fireEvent.click(Array.from(container.querySelectorAll('[class*="cursor-pointer"]')).find((node) => node.textContent?.includes('A') && node.textContent?.includes('نسخه'))!);
    await screen.findByRole('button', { name: /نسخه جدید/ });
    const edit = Array.from(container.querySelectorAll('button[title="ویرایش"]')).find((button) => button.parentElement?.parentElement?.textContent?.includes('A-version'))!;
    fireEvent.click(edit);
    fireEvent.change(screen.getByPlaceholderText('مثلاً SP2L_TP1.5'), { target: { value: 'old edit' } });
    fireEvent.click(screen.getByRole('button', { name: /ذخیره/ }));
    await waitFor(() => expect(updateVersion).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: /لغو/ }));
    fireEvent.click(screen.getByRole('button', { name: /نسخه جدید/ }));
    await act(async () => { save.resolve({ data: {} }); });
    expect(screen.getByPlaceholderText('مثلاً SP2L_TP1.5')).toBeInTheDocument();
  });

  it('deferred version delete refreshes selection-owned data', async () => {
    const deletion = deferred<unknown>();
    deleteVersion.mockReturnValue(deletion.promise);
    const { container } = render(<StrategyPage />);
    await waitFor(() => expect(container.textContent).toContain('A'));
    fireEvent.click(Array.from(container.querySelectorAll('[class*="cursor-pointer"]')).find((node) => node.textContent?.includes('A') && node.textContent?.includes('نسخه'))!);
    await waitFor(() => expect(container.textContent).toContain('A-version'));
    fireEvent.click(Array.from(container.querySelectorAll('button[title="حذف"]')).find((button) => button.parentElement?.parentElement?.textContent?.includes('A-version'))!);
    await waitFor(() => expect(deleteVersion).toHaveBeenCalledWith(11));
    expect(container.textContent).toContain('A-version');
    await act(async () => { deletion.resolve({ data: {} }); });
    await waitFor(() => expect(container.textContent).toContain('نسخه حذف شد'));
    expect(container.querySelector('button[title="حذف"]')).toBeInTheDocument();
    expect(getStrategyChartAggregate).toHaveBeenCalledWith(1, { test_type: 'backtest' });
  });

  it('deferred Fork refreshes versions and chart after completion', async () => {
    const fork = deferred<unknown>();
    forkVersion.mockReturnValue(fork.promise);
    const { container } = render(<StrategyPage />);
    await waitFor(() => expect(container.textContent).toContain('A'));
    fireEvent.click(Array.from(container.querySelectorAll('[class*="cursor-pointer"]')).find((node) => node.textContent?.includes('A') && node.textContent?.includes('نسخه'))!);
    await waitFor(() => expect(container.textContent).toContain('A-version'));
    fireEvent.click(container.querySelector('button[title="ایجاد نسخه مشتق (Fork)"]')!);
    fireEvent.click(screen.getByRole('button', { name: /ساخت Fork/ }));
    await waitFor(() => expect(forkVersion).toHaveBeenCalledWith(11, expect.any(Object)));
    expect(container.textContent).toContain('A-version');
    await act(async () => { fork.resolve({ data: { id: 12 } }); });
    await waitFor(() => expect(getStrategyChartAggregate.mock.calls.filter((call) => call[0] === 1)).toHaveLength(2));
    expect(getStrategyVersions).toHaveBeenCalledWith(1);
    expect(container.textContent).toContain('نسخه فورک ساخته شد');
  });

  it('reversed strategy-list refresh responses cannot restore stale list state', async () => {
    const { container } = render(<StrategyPage />);
    await waitFor(() => expect(container.textContent).toContain('A'));
    // A successful selection-triggered refresh starts another list request.
    const firstRefresh = deferred<unknown>();
    const secondRefresh = deferred<unknown>();
    getStrategies.mockImplementationOnce(() => firstRefresh.promise).mockImplementationOnce(() => secondRefresh.promise);
    deleteStrategy.mockResolvedValue({ data: {} });
    const deleteButton = Array.from(container.querySelectorAll('button[title="حذف"]')).find((button) => button.parentElement?.parentElement?.textContent?.includes('A'))!;
    fireEvent.click(deleteButton);
    await waitFor(() => expect(deleteStrategy).toHaveBeenCalled());
    await waitFor(() => expect(getStrategies).toHaveBeenCalledTimes(2));
    deleteStrategy.mockReturnValueOnce(Promise.resolve({ data: {} }));
    const deleteAgain = Array.from(container.querySelectorAll('button[title="حذف"]')).find((button) => button.parentElement?.parentElement?.textContent?.includes('A'))!;
    fireEvent.click(deleteAgain);
    await waitFor(() => expect(getStrategies).toHaveBeenCalledTimes(3));
    await act(async () => { firstRefresh.resolve({ data: [{ id: 1, name: 'A stale', versions_count: 1 }, { id: 2, name: 'B', versions_count: 0 }] }); });
    await act(async () => { secondRefresh.resolve({ data: [{ id: 1, name: 'A refreshed', versions_count: 1 }, { id: 2, name: 'B', versions_count: 0 }] }); });
    expect(container.textContent).toContain('A refreshed');
  });

  it('posts status/test_type for create and patch, refreshes selected data, and displays saved label', async () => {
    const { container } = render(<StrategyPage />);
    await waitFor(() => expect(container.textContent).toContain('A'));
    const strategyCard = Array.from(container.querySelectorAll('[class*="cursor-pointer"]')).find((node) => node.textContent?.includes('A') && node.textContent?.includes('نسخه'))!;
    fireEvent.click(strategyCard);
    fireEvent.click(await screen.findByRole('button', { name: /نسخه جدید/ }));
    fireEvent.change(screen.getByPlaceholderText('مثلاً SP2L_TP1.5'), { target: { value: 'new-v' } });
    fireEvent.change(screen.getByLabelText('برچسب نسخه'), { target: { value: 'real' } });
    fireEvent.click(screen.getByRole('button', { name: /ذخیره/ }));
    await waitFor(() => expect(createVersion).toHaveBeenCalledWith(1, expect.objectContaining({ version_name: 'new-v', status: 'research', test_type: 'real' })));
    await waitFor(() => expect(getStrategyChartAggregate).toHaveBeenCalledWith(1, { test_type: 'backtest' }));
    expect(await screen.findByText(/نسخه‌ی جدید ساخته شد/)).toBeInTheDocument();

    const versionCard = Array.from(container.querySelectorAll('div')).filter((node) => node.textContent?.includes('A-version') && node.querySelector('button[title="ویرایش"]')).sort((a, b) => a.querySelectorAll('div').length - b.querySelectorAll('div').length)[0];
    fireEvent.click(versionCard!.querySelector('button[title="ویرایش"]')!);
    fireEvent.change(screen.getByPlaceholderText('مثلاً SP2L_TP1.5'), { target: { value: 'renamed' } });
    fireEvent.change(screen.getByLabelText('برچسب نسخه'), { target: { value: 'forward' } });
    fireEvent.click(screen.getByRole('button', { name: /ذخیره/ }));
    await waitFor(() => expect(updateVersion).toHaveBeenCalledWith(11, expect.objectContaining({ version_name: 'renamed', status: 'research', test_type: 'forward' })));
    expect(screen.getByText(/برچسب، وضعیت، نوع برچسب و قوانین نسخه ذخیره شد/)).toBeInTheDocument();
  });
});