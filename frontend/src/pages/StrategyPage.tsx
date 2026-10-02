import { useState, useEffect } from 'react';
import {
  getStrategies,
  createStrategy,
  updateStrategy,
  deleteStrategy,
  getStrategyVersions,
  createVersion,
  updateVersion,
  deleteVersion,
  forkVersion,
  getStrategyStats,
  getStrategyLivePerformance,
  getVersionTrades,
} from '../api/client';
import PersianDateInput from '../components/PersianDateInput';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar,
} from 'recharts';

interface Strategy {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  versions_count: number;
}

interface Version {
  id: number;
  version_name: string;
  strategy_id: number;
  rules_note: string | null;
  status: string;
  test_type: string | null;
  forked_from_version_id: number | null;
  trades_count: number;
  created_at: string;
}

interface StrategyStats {
  strategy_id: number;
  strategy_name: string;
  versions_count: number;
  version_ids: number[];
  total_trades: number;
  summary: {
    net_pnl: number;
    win_rate: number;
    profit_factor: number;
    max_drawdown: number;
    sharpe_ratio: number;
    expectancy: number;
  };
  trade_counts: {
    total: number;
    winning: number;
    losing: number;
    breakeven: number;
  };
  averages: {
    avg_win: number;
    avg_loss: number;
    avg_trade: number;
  };
  extremes: {
    largest_win: number;
    largest_loss: number;
  };
  consistency: {
    max_consecutive_losses: number;
    pnl_std_dev: number;
  };
}

interface TradeItem {
  id: number;
  symbol: string;
  direction: string;
  test_type: string | null;
  close_time: string | null;
  pnl: number | null;
  commission: number | null;
  swap: number | null;
  r_multiple: number | null;
}

interface EquityPoint {
  index: number;
  equity: number;
}

interface LivePerformanceVersion {
  version_id: number;
  version_name: string;
  status: string;
  forked_from_version_id: number | null;
  total_trades: number;
  net_pnl: number;
  winning_trades: number;
  losing_trades: number;
  breakeven_trades: number;
  win_rate: number;
  profit_factor: number;
  by_type: {
    real_personal: { trades: number; net_pnl: number };
    real_prop: { trades: number; net_pnl: number };
  };
}

interface LivePerformance {
  strategy_id: number;
  strategy_name: string;
  currency: 'USDT';
  date_from: string | null;
  date_to: string | null;
  basis: 'closed_trades';
  versions: LivePerformanceVersion[];
}

const STATUS_OPTIONS = [
  { value: 'research', label: '🔬 تحقیق' },
  { value: 'backtest', label: '🧪 بک‌تست' },
  { value: 'optimization', label: '⚙️ بهینه‌سازی' },
  { value: 'forward', label: '🔭 فوروارد' },
  { value: 'approved', label: '✅ تأییدشده' },
  { value: 'live', label: '💰 لایو' },
  { value: 'review', label: '🔍 بازنگری' },
  { value: 'deprecated', label: '⛔ منسوخ' },
  { value: 'archived', label: '📦 آرشیو' },
  { value: 'rejected', label: '❌ ردشده' },
];

const getStatusLabel = (status: string) => {
  const found = STATUS_OPTIONS.find((o) => o.value === status);
  return found ? found.label : status;
};

const getStatusStyle = (status: string) => {
  const styles: Record<string, string> = {
    research: 'bg-[var(--purple-soft)] text-[var(--purple)] border-[var(--purple-border)]',
    backtest: 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--border-accent)]',
    optimization: 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--border-accent)]',
    forward: 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--border-accent)]',
    approved: 'bg-[var(--profit-soft)] text-[var(--profit)] border-[var(--profit-border)]',
    live: 'bg-[var(--profit-soft)] text-[var(--profit)] border-[var(--profit-border)]',
    review: 'bg-[var(--warning-soft-alt)] text-[var(--warning-strong)] border-[var(--warning-border)]',
    deprecated: 'bg-[var(--loss-soft)] text-[var(--loss)] border-[var(--loss-border)]',
    archived: 'bg-[var(--bg-elevated)] text-[var(--text-secondary)] border-[var(--border-subtle)]',
    rejected: 'bg-[var(--loss-soft)] text-[var(--loss)] border-[var(--loss-border)]',
  };
  return styles[status] || styles.archived;
};

const TEST_TYPE_OPTIONS = [
  { value: 'backtest', label: '🧪 بک تست', badge: 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--border-accent)]' },
  { value: 'forward', label: '🔭 فوروارد', badge: 'bg-[var(--purple-soft)] text-[var(--purple)] border-[var(--purple-border)]' },
  { value: 'real', label: '💰 ریل', badge: 'bg-[var(--profit-soft)] text-[var(--profit)] border-[var(--profit-border)]' },
];
const getTestTypeLabel = (testType: string | null) => {
  if (!testType) return 'نامشخص';
  const found = TEST_TYPE_OPTIONS.find((o) => o.value === testType.toLowerCase());
  return found ? found.label : testType;
};
const getTestTypeStyle = (testType: string | null) => {
  if (!testType) return 'bg-[var(--bg-elevated)] text-[var(--text-secondary)] border-[var(--border-subtle)]';
  const found = TEST_TYPE_OPTIONS.find((o) => o.value === testType.toLowerCase());
  return found ? found.badge : 'bg-[var(--bg-elevated)] text-[var(--text-secondary)] border-[var(--border-subtle)]';
};

export default function StrategyPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);

  const [showStrategyForm, setShowStrategyForm] = useState(false);
  const [editingStrategyId, setEditingStrategyId] = useState<number | null>(null);
  const [strategyName, setStrategyName] = useState('');
  const [strategyDescription, setStrategyDescription] = useState('');

  const [showVersionForm, setShowVersionForm] = useState(false);
  const [editingVersionId, setEditingVersionId] = useState<number | null>(null);
  const [versionName, setVersionName] = useState('');
  const [versionRules, setVersionRules] = useState('');
  const [versionStatus, setVersionStatus] = useState('research');
  const [versionTestType, setVersionTestType] = useState('');
  const [showForkModal, setShowForkModal] = useState(false);
  const [forkFromVersion, setForkFromVersion] = useState<Version | null>(null);
  const [forkVersionName, setForkVersionName] = useState('');
  const [forkTestType, setForkTestType] = useState('');
  const [forkStatus, setForkStatus] = useState('research');
  const [forkRulesNote, setForkRulesNote] = useState('');
  const [versionTypeFilter, setVersionTypeFilter] = useState('');

  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // ─── Stats ───
  const [stats, setStats] = useState<StrategyStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [showStats, setShowStats] = useState(false);
  const [equityData, setEquityData] = useState<EquityPoint[]>([]);
  const [rMultipleHistogram, setRMultipleHistogram] = useState<{ range: string; count: number; fill: string }[]>([]);
  const [livePerformance, setLivePerformance] = useState<LivePerformance | null>(null);
  const [livePerformanceLoading, setLivePerformanceLoading] = useState(false);
  const [livePerformanceError, setLivePerformanceError] = useState<string | null>(null);
  const [liveDateFrom, setLiveDateFrom] = useState('');
  const [liveDateTo, setLiveDateTo] = useState('');

  useEffect(() => {
    loadStrategies();
  }, []);

  const loadStrategies = async () => {
    try {
      const res = await getStrategies();
      setStrategies(res.data);
    } catch (err) {
      console.error('خطا:', err);
    }
  };

  const loadVersions = async (strategyId: number) => {
    try {
      const res = await getStrategyVersions(strategyId);
      setVersions(res.data);
    } catch (err) {
      console.error('خطا:', err);
    }
  };

  const handleSelectStrategy = (strategy: Strategy) => {
    setSelectedStrategy(strategy);
    setLiveDateFrom('');
    setLiveDateTo('');
    setLivePerformance(null);
    loadVersions(strategy.id);
    loadStats(strategy.id);
    setShowVersionForm(false);
  };

  // ═════════════════════════════════════════════
  // Strategy CRUD
  // ═════════════════════════════════════════════
  const handleOpenStrategyForm = (strategy?: Strategy) => {
    if (strategy) {
      setEditingStrategyId(strategy.id);
      setStrategyName(strategy.name);
      setStrategyDescription(strategy.description || '');
    } else {
      setEditingStrategyId(null);
      setStrategyName('');
      setStrategyDescription('');
    }
    setShowStrategyForm(true);
  };

  const handleSaveStrategy = async () => {
    if (!strategyName.trim()) {
      setError('نام استراتژی نمی‌تواند خالی باشد');
      return;
    }
    try {
      if (editingStrategyId) {
        await updateStrategy(editingStrategyId, {
          name: strategyName,
          description: strategyDescription,
        });
        setSuccessMessage('استراتژی به‌روزرسانی شد');
      } else {
        await createStrategy({
          name: strategyName,
          description: strategyDescription,
        });
        setSuccessMessage('استراتژی جدید ساخته شد');
      }
      setShowStrategyForm(false);
      await loadStrategies();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در ذخیره‌ی استراتژی');
    }
  };

  const handleDeleteStrategy = async (strategy: Strategy) => {
    if (!confirm(`آیا مطمئنید که می‌خواهید «${strategy.name}» را حذف کنید؟\nتمام نسخه‌های آن نیز حذف می‌شوند.`)) return;
    try {
      await deleteStrategy(strategy.id);
      setSuccessMessage('استراتژی حذف شد');
      if (selectedStrategy?.id === strategy.id) {
        setSelectedStrategy(null);
        setVersions([]);
      }
      await loadStrategies();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در حذف استراتژی');
    }
  };

  // ═════════════════════════════════════════════
  // Version CRUD
  // ═════════════════════════════════════════════
  const handleOpenVersionForm = (version?: Version) => {
    if (version) {
      setEditingVersionId(version.id);
      setVersionName(version.version_name);
      setVersionRules(version.rules_note || '');
      setVersionStatus(version.status);
      setVersionTestType(version.test_type || '');
    } else {
      setEditingVersionId(null);
      setVersionName('');
      setVersionRules('');
      setVersionStatus('research');
      setVersionTestType('');
    }
    setShowVersionForm(true);
  };

  const handleSaveVersion = async () => {
    if (!versionName.trim()) {
      setError('نام نسخه نمی‌تواند خالی باشد');
      return;
    }
    if (!selectedStrategy) return;
    try {
      if (editingVersionId) {
        await updateVersion(editingVersionId, {
          version_name: versionName,
          rules_note: versionRules,
          status: versionStatus,
        });
        setSuccessMessage('نسخه به‌روزرسانی شد');
      } else {
        await createVersion(selectedStrategy.id, {
          version_name: versionName,
          rules_note: versionRules,
          test_type: versionTestType || undefined,
        });
        setSuccessMessage('نسخه‌ی جدید ساخته شد');
      }
      setShowVersionForm(false);
      await loadVersions(selectedStrategy.id);
      await loadStrategies();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در ذخیره‌ی نسخه');
    }
  };

  const handleDeleteVersion = async (version: Version) => {
    if (version.trades_count > 0) {
      setError(`این نسخه ${version.trades_count} معامله دارد و قابل حذف نیست`);
      return;
    }
    if (!confirm(`آیا مطمئنید که می‌خواهید «${version.version_name}» را حذف کنید؟`)) return;
    try {
      await deleteVersion(version.id);
      setSuccessMessage('نسخه حذف شد');
      if (selectedStrategy) await loadVersions(selectedStrategy.id);
      await loadStrategies();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در حذف نسخه');
    }
  };
const handleForkVersion = (version: Version) => {
    setForkFromVersion(version);
    setForkVersionName(`${version.version_name} - Fork}`);
    setForkTestType(version.test_type || '');
    setForkStatus(version.status || 'research');
    setForkRulesNote(version.rules_note || '');
    setShowForkModal(true);
  };
  const handleSubmitFork = async () => {
    if (!forkFromVersion) return;
    try {
      await forkVersion(forkFromVersion.id, {
        version_name: forkVersionName || undefined,
        rules_note: forkRulesNote || undefined,
        test_type: forkTestType || undefined,
        status: forkStatus || undefined,
      });
      setSuccessMessage('نسخه فورک ساخته شد');
      setShowForkModal(false);
      if (selectedStrategy) await loadVersions(selectedStrategy.id);
      await loadStrategies();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در ایجاد Fork');
    }
  };

  // ═════════════════════════════════════════════
  // Strategy Stats
  // ═════════════════════════════════════════════
  const loadLivePerformance = async (strategyId: number, dateFrom = '', dateTo = '') => {
    if (dateFrom && dateTo && dateFrom > dateTo) {
      setLivePerformanceError('تاریخ شروع باید قبل از تاریخ پایان باشد');
      return;
    }
    setLivePerformanceLoading(true);
    setLivePerformanceError(null);
    try {
      const response = await getStrategyLivePerformance(strategyId, {
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      });
      setLivePerformance(response.data);
    } catch (err: any) {
      setLivePerformanceError(err.response?.data?.detail || 'دریافت عملکرد معاملات Real ناموفق بود');
    } finally {
      setLivePerformanceLoading(false);
    }
  };

  const loadStats = async (strategyId: number) => {
    setStatsLoading(true);
    setShowStats(true);
    void loadLivePerformance(strategyId);
    try {
      // 1. Get summary stats
      const statsRes = await getStrategyStats(strategyId);
      setStats(statsRes.data);

      // 2. Get all trades for charts
      const versionsRes = await getStrategyVersions(strategyId);
      const versionIds = (versionsRes.data as Version[]).map((v: Version) => v.id);
      const allTrades: TradeItem[] = [];

      for (const vid of versionIds) {
        try {
          const tradesRes = await getVersionTrades(vid);
          allTrades.push(...tradesRes.data.filter((trade: TradeItem) =>
            trade.test_type === 'backtest' || trade.test_type === 'forward',
          ));
        } catch { /* skip */ }
      }

      // 3. Compute equity curve (cumulative net_pnl)
      const sorted = [...allTrades].sort((a, b) => {
        const ta = a.close_time || '';
        const tb = b.close_time || '';
        return ta.localeCompare(tb);
      });

      let cumEquity = 0;
      const equityPoints: EquityPoint[] = sorted.map((t, idx) => {
        const netPnl = (t.pnl || 0) + (t.commission || 0) + (t.swap || 0);
        cumEquity += netPnl;
        return { index: idx + 1, equity: Math.round(cumEquity * 100) / 100 };
      });
      setEquityData(equityPoints);

      // 4. Compute R-Multiple histogram
      const rValues = allTrades
        .map(t => t.r_multiple)
        .filter((r): r is number => r !== null && r !== undefined);

      if (rValues.length > 0) {
        const maxR = Math.max(...rValues.map(Math.abs), 1);
        const binCount = 8;
        const binSize = (maxR * 2) / binCount;
        const bins: { range: string; count: number; fill: string }[] = [];

        for (let i = 0; i < binCount; i++) {
          const low = -maxR + i * binSize;
          const high = low + binSize;
          const count = rValues.filter(r => r >= low && (i === binCount - 1 ? r <= high : r < high)).length;
          bins.push({
            range: `${low.toFixed(1)}-${high.toFixed(1)}`,
            count,
            fill: low + binSize / 2 >= 0 ? '#13AE81' : '#E45D72',
          });
        }
        setRMultipleHistogram(bins);
      } else {
        setRMultipleHistogram([]);
      }
    } catch (err) {
      console.error('خطا در دریافت آمار:', err);
      setError('خطا در دریافت آمار استراتژی');
    } finally {
      setStatsLoading(false);
    }
  };

  const filteredVersions = versionTypeFilter
    ? versions.filter((v) => (v.test_type || '').toLowerCase() === versionTypeFilter)
    : versions;
  const filteredStrategies = strategies.filter((s) =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-[var(--loss-soft)] border border-[var(--loss-border)] text-[var(--loss)] p-4 rounded-[14px] text-sm font-semibold shadow-sm">
          ❌ {error}
          <button onClick={() => setError(null)} className="float-left text-xs font-bold">✕</button>
        </div>
      )}
      {successMessage && (
        <div className="bg-[var(--profit-soft)] border border-[var(--profit-border)] text-[var(--profit)] p-4 rounded-[14px] text-sm font-semibold shadow-sm">
          ✅ {successMessage}
        </div>
      )}

      {/* دکمه‌ها و جستجو */}
      <div className="flex gap-3 flex-wrap items-center">
        <button
          onClick={() => handleOpenStrategyForm()}
          className="text-white px-6 py-3 rounded-[12px] text-sm font-extrabold transition-all shadow-[0_6px_16px_rgba(63,124,255,0.3)] hover:shadow-[0_10px_24px_rgba(63,124,255,0.4)] hover:-translate-y-0.5"
          style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}
        >
          ➕ استراتژی جدید
        </button>
        <div className="flex-1 min-w-[220px] relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="🔍 جستجوی استراتژی..."
            className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[12px] px-5 py-3 text-[var(--text-primary)] text-sm font-medium shadow-sm focus:border-[var(--accent)] focus:outline-none focus:ring-4 focus:ring-[var(--accent-soft)] transition-all"
          />
        </div>
      </div>

      {/* فرم استراتژی */}
      {showStrategyForm && (
        <div className="bg-[var(--bg-card)] border-2 border-[var(--accent)] rounded-[22px] p-6 shadow-lg">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[var(--border-subtle)]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
              style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}>
              {editingStrategyId ? '✏️' : '➕'}
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-[var(--text-primary)]">
                {editingStrategyId ? 'ویرایش استراتژی' : 'ساخت استراتژی جدید'}
              </h3>
              <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">نام و توضیحات را وارد کنید</p>
            </div>
          </div>

          <div className="space-y-5 mb-6">
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">
                نام استراتژی <span className="text-[var(--loss)]">*</span>
              </label>
              <input
                type="text"
                value={strategyName}
                onChange={(e) => setStrategyName(e.target.value)}
                placeholder="مثلاً SP2L"
                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3.5 text-[var(--text-primary)] text-sm font-semibold focus:border-[var(--accent)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-4 focus:ring-[var(--accent-soft)] transition-all"
              />
            </div>
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">
                توضیحات
              </label>
              <textarea
                value={strategyDescription}
                onChange={(e) => setStrategyDescription(e.target.value)}
                placeholder="توضیحات استراتژی..."
                rows={3}
                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3.5 text-[var(--text-primary)] text-sm font-medium focus:border-[var(--accent)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-4 focus:ring-[var(--accent-soft)] transition-all resize-none"
              />
            </div>
          </div>

          <div className="flex gap-3 pt-4 border-t border-[var(--border-subtle)]">
            <button
              onClick={handleSaveStrategy}
              className="text-white px-7 py-3 rounded-[12px] text-sm font-extrabold transition-all shadow-[0_6px_16px_rgba(19,174,129,0.3)] hover:shadow-[0_10px_24px_rgba(19,174,129,0.4)] hover:-translate-y-0.5"
              style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}
            >
              💾 ذخیره
            </button>
            <button
              onClick={() => setShowStrategyForm(false)}
              className="bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] hover:border-[var(--border-accent)] text-[var(--text-secondary)] hover:text-[var(--accent)] px-7 py-3 rounded-[12px] text-sm font-bold transition-all"
            >
              ✕ لغو
            </button>
          </div>
        </div>
      )}

      {/* فرم نسخه */}
      {showVersionForm && selectedStrategy && (
        <div className="bg-[var(--bg-card)] border-2 border-[var(--accent)] rounded-[22px] p-6 shadow-lg">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[var(--border-subtle)]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
              style={{ background: 'linear-gradient(135deg, #7959D6, #A78BFA)' }}>
              {editingVersionId ? '✏️' : '➕'}
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-[var(--text-primary)]">
                {editingVersionId ? 'ویرایش نسخه' : `ساخت نسخه‌ی جدید برای «${selectedStrategy.name}»`}
              </h3>
              <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">نام، قوانین و وضعیت را وارد کنید</p>
            </div>
          </div>

          <div className="space-y-5 mb-6">
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">
                نام نسخه <span className="text-[var(--loss)]">*</span>
              </label>
              <input
                type="text"
                value={versionName}
                onChange={(e) => setVersionName(e.target.value)}
                placeholder="مثلاً SP2L_TP1.5"
                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3.5 text-[var(--text-primary)] text-sm font-semibold focus:border-[var(--accent)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-4 focus:ring-[var(--accent-soft)] transition-all"
              />
            </div>

            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">
                قوانین / توضیحات
              </label>
              <textarea
                value={versionRules}
                onChange={(e) => setVersionRules(e.target.value)}
                placeholder="قوانین این نسخه..."
                rows={4}
                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3.5 text-[var(--text-primary)] text-sm font-medium focus:border-[var(--accent)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-4 focus:ring-[var(--accent-soft)] transition-all resize-none"
              />
            </div>

            <div>
              <label className='text-[13px] text-[var(--text-primary)] font-bold block mb-2'>
                نوع آزمون
              </label>
              <select
                value={versionTestType}
                onChange={(e) => setVersionTestType(e.target.value)}
                className='w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3.5 text-[var(--text-primary)] text-sm font-semibold focus:border-[var(--accent)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-4 focus:ring-[var(--accent-soft)] transition-all cursor-pointer'>
                <option value=''>(بدون نوع)</option>
                {TEST_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            {(
              <div>
                <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">
                  وضعیت
                </label>
                <select
                  value={versionStatus}
                  onChange={(e) => setVersionStatus(e.target.value)}
                  className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3.5 text-[var(--text-primary)] text-sm font-semibold focus:border-[var(--accent)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-4 focus:ring-[var(--accent-soft)] transition-all cursor-pointer"
                >
                  {STATUS_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="flex gap-3 pt-4 border-t border-[var(--border-subtle)]">
            <button
              onClick={handleSaveVersion}
              className="text-white px-7 py-3 rounded-[12px] text-sm font-extrabold transition-all shadow-[0_6px_16px_rgba(19,174,129,0.3)] hover:shadow-[0_10px_24px_rgba(19,174,129,0.4)] hover:-translate-y-0.5"
              style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}
            >
              💾 ذخیره
            </button>
            <button
              onClick={() => setShowVersionForm(false)}
              className="bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] hover:border-[var(--border-accent)] text-[var(--text-secondary)] hover:text-[var(--accent)] px-7 py-3 rounded-[12px] text-sm font-bold transition-all"
            >
              ✕ لغو
            </button>
          </div>
        </div>
      )}

      {/* modale fork */}
      {showForkModal && forkFromVersion && (
        <div className='fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm'>
          <div className='bg-[var(--bg-card)] border-2 border-[var(--purple)] rounded-[22px] p-6 shadow-xl w-[560px] max-h-[90vh] overflow-y-auto'>
            <div className='flex items-center gap-3 mb-3 pb-4 border-b border-[var(--border-subtle)]'>
              <div className='w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white'
                style={{ background: 'linear-gradient(135deg, #7959D6, #A78BFA)' }}>
                🔱
              </div>
              <div>
                <h3 className='text-lg font-extrabold text-[var(--text-primary)]'>ایجاد نسخه مشتق (Fork)</h3>
                <p className='text-[12px] text-[var(--text-secondary)] mt-0.5'>از «{forkFromVersion.version_name}»</p>
              </div>
              <button onClick={() => setShowForkModal(false)} className='shrink-0 text-[var(--text-secondary)] hover:text-[var(--loss)] p-2 rounded-[8px] text-sm font-bold'>✕</button>
            </div>

            <div className='space-y-5'>
              <div>
                <label className='text-[13px] text-[var(--text-primary)] font-bold block mb-2'>نام نسخه جدید</label>
                <input
                  type='text'
                  value={forkVersionName}
                  onChange={(e) => setForkVersionName(e.target.value)}
                  className='w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3.5 text-[var(--text-primary)] text-sm font-semibold focus:border-[var(--accent)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-4 focus:ring-[var(--accent-soft)] transition-all'
                />
              </div>

              <div className='grid grid-cols-2 gap-4'>
                <div>
                  <label className='text-[13px] text-[var(--text-primary)] font-bold block mb-2'>نوع آزمون</label>
                  <select
                    value={forkTestType}
                    onChange={(e) => setForkTestType(e.target.value)}
                    className='w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3.5 text-[var(--text-primary)] text-sm font-semibold focus:border-[var(--accent)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-4 focus:ring-[var(--accent-soft)] transition-all cursor-pointer'>
                    <option value=''>(بدون نوع)</option>
                    {TEST_TYPE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className='text-[13px] text-[var(--text-primary)] font-bold block mb-2'>وضعیت</label>
                  <select
                    value={forkStatus}
                    onChange={(e) => setForkStatus(e.target.value)}
                    className='w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3.5 text-[var(--text-primary)] text-sm font-semibold focus:border-[var(--accent)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-4 focus:ring-[var(--accent-soft)] transition-all cursor-pointer'>
                    {STATUS_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className='text-[13px] text-[var(--text-primary)] font-bold block mb-2'>قوانین / توضیحات</label>
                <textarea
                  value={forkRulesNote}
                  onChange={(e) => setForkRulesNote(e.target.value)}
                  rows={4}
                />
              </div>
            </div>

            <div className='flex gap-3 pt-4 border-t border-[var(--border-subtle)]'>
              <button
                onClick={handleSubmitFork}
                className='text-white px-7 py-3 rounded-[12px] text-sm font-extrabold transition-all shadow-[0_6px_16px_rgba(121,89,214,0.3)] hover:shadow-[0_10px_24px_rgba(121,89,214,0.4)] hover:-translate-y-0.5'
                style={{ background: 'linear-gradient(135deg, #7959D6, #A78BFA)' }}     >
                🔱 ساخت Fork
              </button>
              <button
                onClick={() => setShowForkModal(false)}
                className='bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] hover:border-[var(--border-accent)] text-[var(--text-secondary)] hover:text-[var(--accent)] px-7 py-3 rounded-[12px] text-sm font-bold transition-all'>
                ✕ لغو
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* لیست استراتژی‌ها */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
          <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
            <div className="w-11 h-11 rounded-[14px] bg-[var(--accent-soft)] flex items-center justify-center text-xl">
              📚
            </div>
            <div>
              <h3 className="text-base font-extrabold text-[var(--text-primary)]">استراتژی‌ها</h3>
              <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">{filteredStrategies.length} استراتژی</p>
            </div>
          </div>

          {filteredStrategies.length === 0 ? (
            <div className="text-[var(--text-muted)] text-sm text-center py-12">
              {searchQuery ? 'نتیجه‌ای یافت نشد' : 'هنوز استراتژی‌ای نساخته‌اید'}
            </div>
          ) : (
            <div className="space-y-2.5">
              {filteredStrategies.map((strategy) => {
                const isSelected = selectedStrategy?.id === strategy.id;
                return (
                  <div
                    key={strategy.id}
                    onClick={() => handleSelectStrategy(strategy)}
                    className={`p-4 rounded-[14px] border-2 cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-[var(--accent-soft)] border-[var(--accent)] shadow-[0_4px_12px_rgba(63,124,255,0.15)]'
                        : 'bg-[var(--bg-card)] border-[var(--border-subtle)] hover:border-[var(--border-accent)] hover:bg-[var(--bg-input)] hover:shadow-sm'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="text-[15px] font-extrabold text-[var(--text-primary)] flex items-center gap-2">
                          🎯 {strategy.name}
                        </div>
                        {strategy.description && (
                          <div className="text-[12px] text-[var(--text-secondary)] mt-1.5 font-medium">
                            {strategy.description}
                          </div>
                        )}
                        <div className="text-[11px] text-[var(--text-muted)] mt-2 font-semibold">
                          {strategy.versions_count} نسخه
                        </div>
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenStrategyForm(strategy);
                          }}
                          className="text-[var(--accent)] hover:bg-[var(--accent-soft)] p-2 rounded-[8px] text-sm transition-all"
                          title="ویرایش"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteStrategy(strategy);
                          }}
                          className="text-[var(--loss)] hover:bg-[var(--loss-soft)] p-2 rounded-[8px] text-sm transition-all"
                          title="حذف"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* لیست نسخه‌ها */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
          {selectedStrategy ? (
            <>
              <div className="flex items-center justify-between gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-[14px] bg-[var(--purple-soft)] flex items-center justify-center text-xl">
                    🔖
                  </div>
                  <div>
                    <h3 className="text-base font-extrabold text-[var(--text-primary)]">نسخه‌های «{selectedStrategy.name}»</h3>
                    <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">{versions.length} نسخه</p>
                  </div>
                </div>
                <button
                  onClick={() => handleOpenVersionForm()}
                  className="text-white px-4 py-2 rounded-[10px] text-[12px] font-extrabold transition-all shadow-[0_4px_12px_rgba(121,89,214,0.3)] hover:shadow-[0_6px_16px_rgba(121,89,214,0.4)]"
                  style={{ background: 'linear-gradient(135deg, #7959D6, #A78BFA)' }}
                >
                  ➕ نسخه جدید
                </button>
              </div>

                            <div className='flex gap-2 mb-3 flex-wrap'>
                <button
                  onClick={() => setVersionTypeFilter('')}
                  className={`text-[11px] font-bold px-3 py-1.5 rounded-full border transition-all ${versionTypeFilter === '' ? 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--border-accent)]' : 'bg-[var(--bg-input)] text-[var(--text-secondary)] border-[var(--border-subtle)] hover:border-[var(--border-accent)]'}`}
                >
                  🗂
                </button>
                {TEST_TYPE_OPTIONS.map((t) => (
                  <button
                    key={t.value}
                    onClick={() => setVersionTypeFilter(versionTypeFilter === t.value ? '' : t.value)}
                    className={`text-[11px] font-bold px-3 py-1.5 rounded-full border transition-all ${versionTypeFilter === t.value ? 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--border-accent)]' : 'bg-[var(--bg-input)] text-[var(--text-secondary)] border-[var(--border-subtle)] hover:border-[var(--border-accent)]'}`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              {versions.length === 0 ? (
                <div className="text-[var(--text-muted)] text-sm text-center py-12">
                  هنوز نسخه‌ای نساخته‌اید
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredVersions.map((version) => (
                    <div
                      key={version.id}
                      className="bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[14px] p-4 hover:border-[var(--border-accent)] hover:bg-[var(--bg-card)] hover:shadow-sm transition-all"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1">
                          <div className="text-[15px] font-extrabold text-[var(--text-primary)]">
                            {version.version_name}
                  {version.test_type && (
                  <span className={`text-[11px] font-bold px-3 py-1 rounded-full border ${getTestTypeStyle(version.test_type)}`}>
                    {getTestTypeLabel(version.test_type)}
                  </span>
                  )}
                  {version.forked_from_version_id && (
                  <span className='text-[10px] text-[var(--purple-light)] font-semibold'>🔱 Fork</span>
                  )}
                          </div>
                          <div className="flex items-center gap-2 mt-2 flex-wrap">
                            <span className={`text-[11px] font-bold px-3 py-1 rounded-full border ${getStatusStyle(version.status)}`}>
                              {getStatusLabel(version.status)}
                            </span>
                            <span className="text-[11px] text-[var(--text-secondary)] font-semibold">
                              {version.trades_count} معامله
                            </span>
                          </div>
                        </div>
                        <div className="flex gap-1 shrink-0">
                          <button
                            onClick={() => handleOpenVersionForm(version)}
                            className="text-[var(--accent)] hover:bg-[var(--accent-soft)] p-2 rounded-[8px] text-sm transition-all"
                            title="ویرایش"
                          >
                            ✏️
                          </button>
                          <button
                            onClick={() => handleDeleteVersion(version)}
                            disabled={version.trades_count > 0}
                            className="text-[var(--loss)] hover:bg-[var(--loss-soft)] p-2 rounded-[8px] text-sm transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                            title={version.trades_count > 0 ? 'این نسخه معامله دارد' : 'حذف'}
                          >
                            🗑️
                          </button>
                          <button
                            onClick={() => handleForkVersion(version)}
                            className="text-[var(--purple-light)] hover:bg-[var(--purple-soft)] p-2 rounded-[8px] text-sm transition-all"
                            title="ایجاد نسخه مشتق (Fork)"
                          >
                            🔱
                          </button>
                        </div>
                      </div>

                      {version.rules_note && (
                        <div className="text-[12px] text-[var(--text-secondary)] bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[10px] p-3 mt-3 font-medium">
                          📝 {version.rules_note}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* 📊 آمار استراتژی */}
              <div className="mt-6 pt-5 border-t border-[var(--border-subtle)]">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">📊</span>
                    <h4 className="text-sm font-extrabold text-[var(--text-primary)]">آمار استراتژی</h4>
                  </div>
                  <button
                    onClick={() => { if (!showStats) loadStats(selectedStrategy!.id); else setShowStats(!showStats); }}
                    className={`text-xs font-bold px-4 py-2 rounded-[10px] transition-all ${
                      showStats
                        ? 'bg-[var(--accent-soft)] text-[var(--accent)]'
                        : 'bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)]'
                    }`}
                  >
                    {showStats ? '🔽 بستن' : '📊 نمایش آمار'}
                  </button>
                </div>

                {showStats && (
                  <>
                    {statsLoading ? (
                      <div className="text-[var(--text-muted)] text-xs text-center py-6 animate-pulse">⏳ در حال محاسبه آمار...</div>
                    ) : stats && stats.total_trades > 0 ? (
                      <div className="space-y-5">
                        {/* کارت‌های خلاصه */}
                        <div className="grid grid-cols-3 gap-2">
                          {[
                            { label: 'نرخ برد', value: `${stats.summary.win_rate}%`, color: '#13AE81' },
                            { label: 'فاکتور سود', value: stats.summary.profit_factor.toFixed(2), color: '#3F7CFF' },
                            { label: 'سود خالص', value: `USDT ${stats.summary.net_pnl.toFixed(0)}`, color: '#7959D6' },
                            { label: 'شارپ', value: stats.summary.sharpe_ratio.toFixed(2), color: '#D99B25' },
                            { label: 'افت سرمایه', value: `USDT ${stats.summary.max_drawdown.toFixed(0)}`, color: '#E45D72' },
                            { label: 'امید ریاضی', value: `USDT ${stats.summary.expectancy.toFixed(2)}`, color: '#13AE81' },
                          ].map((item) => (
                            <div key={item.label} className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[12px] p-3 text-center">
                              <div className="text-[10px] font-bold text-[var(--text-secondary)] mb-1">{item.label}</div>
                              <div className="text-[15px] font-extrabold" style={{ color: item.color }}>{item.value}</div>
                            </div>
                          ))}
                        </div>

                        {/* جزئیات معاملات */}
                        <div className="grid grid-cols-2 gap-3">
                          <div className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[12px] p-3">
                            <div className="text-[10px] font-bold text-[var(--text-secondary)] mb-2">📈 معاملات</div>
                            <div className="space-y-1.5">
                              <div className="flex justify-between text-[12px]">
                                <span className="text-[var(--text-secondary)]">کل</span>
                                <span className="font-bold text-[var(--text-primary)]">{stats.trade_counts.total}</span>
                              </div>
                              <div className="flex justify-between text-[12px]">
                                <span className="text-[var(--profit)]">سودده</span>
                                <span className="font-bold text-[var(--text-primary)]">{stats.trade_counts.winning}</span>
                              </div>
                              <div className="flex justify-between text-[12px]">
                                <span className="text-[var(--loss)]">زیان‌ده</span>
                                <span className="font-bold text-[var(--text-primary)]">{stats.trade_counts.losing}</span>
                              </div>
                              <div className="flex justify-between text-[12px]">
                                <span className="text-[var(--text-muted)]">سربه‌سر</span>
                                <span className="font-bold text-[var(--text-primary)]">{stats.trade_counts.breakeven}</span>
                              </div>
                            </div>
                          </div>
                          <div className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[12px] p-3">
                            <div className="text-[10px] font-bold text-[var(--text-secondary)] mb-2">📊 میانگین‌ها</div>
                            <div className="space-y-1.5">
                              <div className="flex justify-between text-[12px]">
                                <span className="text-[var(--profit)]">میانگین سود</span>
                                <span className="font-bold text-[var(--text-primary)]">{stats.averages.avg_win.toFixed(2)} USDT</span>
                              </div>
                              <div className="flex justify-between text-[12px]">
                                <span className="text-[var(--loss)]">میانگین زیان</span>
                                <span className="font-bold text-[var(--text-primary)]">−{stats.averages.avg_loss.toFixed(2)} USDT</span>
                              </div>
                              <div className="flex justify-between text-[12px]">
                                <span className="text-[var(--purple)]">میانگین هر معامله</span>
                                <span className="font-bold text-[var(--text-primary)]">{stats.averages.avg_trade.toFixed(2)} USDT</span>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* اکستریم‌ها */}
                        <div className="grid grid-cols-2 gap-3">
                          <div className="bg-[var(--profit-soft)] border border-[var(--profit-border)] rounded-[12px] p-3">
                            <div className="text-[10px] font-bold text-[var(--text-secondary)] mb-1">🏆 بهترین معامله</div>
                            <div className="text-[16px] font-extrabold text-[var(--profit)]">+{stats.extremes.largest_win.toFixed(2)} USDT</div>
                          </div>
                          <div className="bg-[var(--loss-soft)] border border-[var(--loss-border)] rounded-[12px] p-3">
                            <div className="text-[10px] font-bold text-[var(--text-secondary)] mb-1">💔 بدترین معامله</div>
                            <div className="text-[16px] font-extrabold text-[var(--loss)]">−{stats.extremes.largest_loss.toFixed(2)} USDT</div>
                          </div>
                        </div>

                        {/* نمودار Equity Curve */}
                        {equityData.length > 1 && (
                          <div>
                            <h5 className="text-[11px] font-bold text-[var(--text-secondary)] mb-2">📈 منحنی سرمایه (Equity Curve)</h5>
                            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[12px] p-3">
                              <ResponsiveContainer width="100%" height={180}>
                                <LineChart data={equityData}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#E5EBF3" />
                                  <XAxis dataKey="index" tick={{ fontSize: 10, fill: '#9AA8BF' }} />
                                  <YAxis tick={{ fontSize: 10, fill: '#9AA8BF' }} />
                                  <Tooltip
                                    contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid #E5EBF3' }}
                                    formatter={(value) => [`USDT ${Number(value ?? 0).toFixed(2)}`, 'سرمایه']}
                                    labelFormatter={(label) => `معامله #${label}`}
                                  />
                                  <Line
                                    type="monotone"
                                    dataKey="equity"
                                    stroke="#3F7CFF"
                                    strokeWidth={2}
                                    dot={false}
                                    activeDot={{ r: 4, fill: '#3F7CFF' }}
                                  />
                                </LineChart>
                              </ResponsiveContainer>
                            </div>
                          </div>
                        )}

                        {/* نمودار R-Multiple */}
                        {rMultipleHistogram.length > 0 && (
                          <div>
                            <h5 className="text-[11px] font-bold text-[var(--text-secondary)] mb-2">📊 توزیع R-Multiple</h5>
                            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[12px] p-3">
                              <ResponsiveContainer width="100%" height={160}>
                                <BarChart data={rMultipleHistogram}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#E5EBF3" />
                                  <XAxis dataKey="range" tick={{ fontSize: 8, fill: '#9AA8BF' }} />
                                  <YAxis tick={{ fontSize: 10, fill: '#9AA8BF' }} />
                                  <Tooltip
                                    contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid #E5EBF3' }}
                                    formatter={(value) => [Number(value ?? 0), 'تعداد']}
                                  />
                                  <Bar dataKey="count" fill="#3F7CFF" radius={[3, 3, 0, 0]} />
                                </BarChart>
                              </ResponsiveContainer>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : stats && stats.total_trades === 0 ? (
                      <div className="text-[var(--text-muted)] text-xs text-center py-6">
                        ⏳ هیچ معامله‌ای برای این استراتژی یافت نشد
                      </div>
                    ) : null}

                    <section className="mt-6 pt-5 border-t border-[var(--border-subtle)]">
                      <div className="mb-4">
                        <h4 className="text-sm font-extrabold text-[var(--text-primary)]">💰 عملکرد معاملات Real هر نسخه</h4>
                        <p className="text-xs text-[var(--text-secondary)] mt-1">
                          فقط معاملات Real بسته‌شده؛ سود خالص شامل PnL، کمیسیون و سواپ است. هر نسخه جداگانه سنجیده می‌شود.
                        </p>
                      </div>

                      <div className="flex items-end gap-3 flex-wrap mb-4">
                        <PersianDateInput label="از تاریخ" value={liveDateFrom} onChange={setLiveDateFrom} className="min-w-[170px]" />
                        <PersianDateInput label="تا تاریخ" value={liveDateTo} onChange={setLiveDateTo} className="min-w-[170px]" />
                        <button
                          onClick={() => selectedStrategy && loadLivePerformance(selectedStrategy.id, liveDateFrom, liveDateTo)}
                          disabled={livePerformanceLoading}
                          className="bg-[var(--accent-soft)] text-[var(--accent)] px-4 py-2 rounded-xl text-xs font-extrabold disabled:opacity-50"
                        >
                          {livePerformanceLoading ? 'در حال محاسبه…' : 'اعمال بازه'}
                        </button>
                        {(liveDateFrom || liveDateTo) && (
                          <button
                            onClick={() => {
                              setLiveDateFrom('');
                              setLiveDateTo('');
                              if (selectedStrategy) loadLivePerformance(selectedStrategy.id);
                            }}
                            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] px-2 py-2 text-xs font-bold"
                          >
                            پاک‌کردن بازه
                          </button>
                        )}
                      </div>

                      {livePerformanceError && (
                        <div className="text-xs text-[var(--loss)] mb-3">{livePerformanceError}</div>
                      )}
                      {livePerformanceLoading && !livePerformance ? (
                        <div className="text-xs text-[var(--text-muted)] text-center py-5">در حال دریافت معاملات Real…</div>
                      ) : livePerformance && (
                        <div className="overflow-x-auto rounded-xl border border-[var(--border-subtle)]">
                          <table className="w-full min-w-[850px] text-xs text-right">
                            <thead className="bg-[var(--bg-input)] text-[var(--text-secondary)]">
                              <tr>
                                <th className="p-3">نسخه</th>
                                <th className="p-3">معامله</th>
                                <th className="p-3">سود بروکر</th>
                                <th className="p-3">سود پراپ</th>
                                <th className="p-3">سود خالص</th>
                                <th className="p-3">نرخ برد</th>
                                <th className="p-3">Profit Factor</th>
                              </tr>
                            </thead>
                            <tbody>
                              {livePerformance.versions.map((version) => {
                                const pnlClass = version.net_pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]';
                                const money = (value: number) => `${value >= 0 ? '+' : ''}${value.toLocaleString('en-US', { maximumFractionDigits: 2 })} USDT`;
                                return (
                                  <tr key={version.version_id} className="border-t border-[var(--border-subtle)] text-[var(--text-primary)]">
                                    <td className="p-3">
                                      <div className="font-extrabold">{version.version_name}</div>
                                      <div className="text-[10px] text-[var(--text-muted)] mt-1">
                                        {version.forked_from_version_id ? `زیرنسخهٔ #${version.forked_from_version_id}` : 'نسخهٔ اصلی'} · {getStatusLabel(version.status)}
                                      </div>
                                    </td>
                                    <td className="p-3">{version.total_trades}</td>
                                    <td className={`p-3 font-bold ${version.by_type.real_personal.net_pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                                      {money(version.by_type.real_personal.net_pnl)} <span className="text-[10px] font-normal">({version.by_type.real_personal.trades})</span>
                                    </td>
                                    <td className={`p-3 font-bold ${version.by_type.real_prop.net_pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                                      {money(version.by_type.real_prop.net_pnl)} <span className="text-[10px] font-normal">({version.by_type.real_prop.trades})</span>
                                    </td>
                                    <td className={`p-3 font-black ${pnlClass}`}>{money(version.net_pnl)}</td>
                                    <td className="p-3">{version.win_rate.toFixed(1)}%</td>
                                    <td className="p-3">{version.profit_factor.toFixed(2)}</td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                          {livePerformance.versions.every((version) => version.total_trades === 0) && (
                            <div className="text-center text-xs text-[var(--text-muted)] py-5">
                              در این بازه معاملهٔ Real بسته‌شده‌ای برای این استراتژی ثبت نشده است.
                            </div>
                          )}
                        </div>
                      )}
                    </section>
                  </>
                )}
              </div>
            </>
          ) : (
            <div className="text-center py-16">
              <div className="text-6xl mb-4">🎯</div>
              <div className="text-[15px] font-bold text-[var(--text-primary)]">یک استراتژی را از لیست انتخاب کنید</div>
              <div className="text-[12px] text-[var(--text-muted)] mt-2">تا نسخه‌های آن را ببینید</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
