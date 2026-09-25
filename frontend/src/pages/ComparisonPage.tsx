import { useState, useEffect } from 'react';
import ComparisonBarChart from '../components/charts/ComparisonBarChart';
import ComparisonRadarChart from '../components/charts/ComparisonRadarChart';

import {
  getAllVersions,
  getStrategies,
  compareVersionsWithDetails,
} from '../api/client';

interface Version {
  id: number;
  version_name: string;
  strategy_id: number;
  strategy_name: string;
  status: string;
  trades_count: number;
}

interface Strategy {
  id: number;
  name: string;
}

export default function ComparisonPage() {
  const [versions, setVersions] = useState<Version[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [filterStrategy, setFilterStrategy] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [comparison, setComparison] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeDetailTab, setActiveDetailTab] = useState<'session' | 'weekday' | 'hour' | 'custom'>('session');
  const [minTrades, setMinTrades] = useState<number>(20); // فیلتر هوشمند: حداقل تعداد معامله برای مقایسه

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [versionsRes, strategiesRes] = await Promise.all([
        getAllVersions(),
        getStrategies(),
      ]);
      setVersions(versionsRes.data);
      setStrategies(strategiesRes.data);
    } catch (err) {
      console.error('خطا:', err);
    }
  };

  const toggleVersion = (id: number) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((v) => v !== id));
    } else {
      if (selectedIds.length >= 5) {
        setError('حداکثر ۵ نسخه قابل مقایسه است');
        setTimeout(() => setError(null), 3000);
        return;
      }
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleCompare = async () => {
    if (selectedIds.length < 2) {
      setError('حداقل ۲ نسخه برای مقایسه انتخاب کنید');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await compareVersionsWithDetails(selectedIds, minTrades);
      setComparison(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در مقایسه');
    } finally {
      setLoading(false);
    }
  };

  const filteredVersions = versions.filter((v) => {
    if (filterStrategy && v.strategy_id !== filterStrategy) return false;
    if (searchQuery && !v.version_name.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !v.strategy_name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const getCellStyle = (item: any, allItems: any[], metric: string, higherIsBetter: boolean = true) => {
    if (allItems.length < 2) return 'text-[var(--text-primary)]';
    const values = allItems.map((i: any) => i[metric]);
    const maxVal = Math.max(...values);
    const minVal = Math.min(...values);
    const val = item[metric];
    if (higherIsBetter) {
      if (val === maxVal) return 'text-[var(--profit)] font-extrabold';
      if (val === minVal) return 'text-[var(--loss)] font-bold';
    } else {
      if (val === minVal) return 'text-[var(--profit)] font-extrabold';
      if (val === maxVal) return 'text-[var(--loss)] font-bold';
    }
    return 'text-[var(--text-primary)] font-semibold';
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-[var(--loss-soft)] border border-[var(--loss-border)] text-[var(--loss)] p-4 rounded-[14px] text-sm font-semibold shadow-sm">
          ❌ {error}
        </div>
      )}

      {/* ═══════════════════════════════════════════
          بخش انتخاب
      ═══════════════════════════════════════════ */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-11 h-11 rounded-[14px] bg-[var(--accent-soft)] flex items-center justify-center text-xl shadow-[0_4px_12px_rgba(63,124,255,0.12)]">
            ⚖️
          </div>
          <div>
            <h2 className="text-lg font-extrabold text-[var(--text-primary)]">انتخاب نسخه‌ها برای مقایسه</h2>
            <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">حداقل ۲ و حداکثر ۵ نسخه را انتخاب کنید</p>
          </div>
        </div>

        {/* فیلترها */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <div>
            <label className="text-[12px] text-[var(--text-secondary)] font-semibold block mb-1.5">استراتژی</label>
            <select
              value={filterStrategy || ''}
              onChange={(e) => setFilterStrategy(e.target.value ? Number(e.target.value) : null)}
              className="w-full bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[10px] px-4 py-2.5 text-[var(--text-primary)] text-sm font-medium focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-soft)]"
            >
              <option value="">همه‌ی استراتژی‌ها</option>
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="text-[12px] text-[var(--text-secondary)] font-semibold block mb-1.5">جستجو</label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="🔍 جستجوی نام نسخه یا استراتژی..."
              className="w-full bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[10px] px-4 py-2.5 text-[var(--text-primary)] text-sm font-medium focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-soft)]"
            />
          </div>
        </div>

        {/* فیلتر هوشمند: حداقل تعداد معامله */}
        <div className="flex items-center gap-3 mb-5 bg-[var(--warning-soft-alt)] border border-[var(--warning-border)] rounded-[10px] px-4 py-2.5">
          <label className="text-[12px] text-[var(--warning-strong)] font-bold whitespace-nowrap">
            ⚠️ حداقل تعداد معامله برای ورود به مقایسه:
          </label>
          <input
            type="number"
            min={0}
            value={minTrades}
            onChange={(e) => setMinTrades(Math.max(0, Number(e.target.value)))}
            className="w-24 bg-[var(--bg-card)] border border-[var(--warning-border)] rounded-[8px] px-3 py-1.5 text-[var(--warning-strong)] text-sm font-bold focus:outline-none focus:ring-2 focus:ring-[var(--warning-border)]"
          />
          <span className="text-[11px] text-[var(--warning-strong)]">نسخه‌های کمتر از این تعداد از مقایسه کنار گذاشته می‌شن</span>
        </div>

        {/* لیست نسخه‌ها */}
        <div className="max-h-72 overflow-y-auto border border-[var(--border-subtle)] rounded-[14px] p-2 mb-5 bg-[var(--bg-input)]">
          {filteredVersions.length === 0 ? (
            <div className="text-[var(--text-muted)] text-sm text-center py-8">نسخه‌ای یافت نشد</div>
          ) : (
            <div className="space-y-1.5">
              {filteredVersions.map((v) => {
                const isSelected = selectedIds.includes(v.id);
                const belowThreshold = minTrades > 0 && v.trades_count < minTrades;
                return (
                  <label
                    key={v.id}
                    className={`flex items-center justify-between p-3 rounded-[12px] cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-[var(--accent-soft)] border-2 border-[var(--accent)] shadow-[0_4px_12px_rgba(63,124,255,0.15)]'
                        : 'bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--border-accent)] hover:shadow-sm'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleVersion(v.id)}
                        className="w-5 h-5 accent-[#3F7CFF] cursor-pointer"
                      />
                      <div>
                        <div className="text-[14px] font-bold text-[var(--text-primary)]">
                          {v.strategy_name} / {v.version_name}
                        </div>
                        <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                          {v.trades_count} معامله • وضعیت: {v.status}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {belowThreshold && (
                        <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-[var(--warning-soft-alt)] text-[var(--warning-strong)] border border-[var(--warning-border)]">
                          کمتر از حدنصاب
                        </span>
                      )}
                      {isSelected && (
                        <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-[#3F7CFF] text-white">
                          انتخاب‌شده
                        </span>
                      )}
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex justify-between items-center flex-wrap gap-3">
          <div className="text-[13px] text-[var(--text-secondary)] font-medium">
            انتخاب‌شده: <span className="text-[var(--accent)] font-extrabold text-base">{selectedIds.length}</span> از ۵
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setSelectedIds([])}
              className="bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--border-accent)] text-[var(--text-secondary)] hover:text-[var(--accent)] px-5 py-2.5 rounded-[10px] text-sm font-bold transition-all"
            >
              ✕ پاک کردن
            </button>
            <button
              onClick={handleCompare}
              disabled={loading || selectedIds.length < 2}
              className="text-white px-7 py-2.5 rounded-[10px] text-sm font-extrabold transition-all shadow-[0_6px_16px_rgba(63,124,255,0.3)] hover:shadow-[0_10px_24px_rgba(63,124,255,0.4)] hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0"
              style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}
            >
              {loading ? '⏳ در حال مقایسه...' : '🚀 مقایسه کن'}
            </button>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════
          نتیجه
      ═══════════════════════════════════════════ */}
      {comparison && (
        <>
          {/* جدول مقایسه */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
            <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
              <div className="w-11 h-11 rounded-[14px] bg-[var(--accent-soft)] flex items-center justify-center text-xl">
                📋
              </div>
              <div>
                <h3 className="text-base font-extrabold text-[var(--text-primary)]">جدول مقایسه</h3>
                <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">{comparison.items.length} نسخه</p>
              </div>
            </div>

            {comparison.skipped && comparison.skipped.length > 0 && (
              <div className="mb-5 bg-[var(--warning-soft-alt)] border border-[var(--warning-border)] rounded-[12px] p-4">
                <div className="text-[13px] font-extrabold text-[var(--warning-strong)] mb-2">⚠️ این نسخه‌ها وارد مقایسه نشدن:</div>
                <ul className="space-y-1">
                  {comparison.skipped.map((s: any, idx: number) => (
                    <li key={idx} className="text-[12px] text-[var(--warning-strong)]">
                      • {s.version_name || `نسخه #${s.version_id}`} — {s.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="overflow-x-auto rounded-[14px] border border-[var(--border-subtle)]">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[var(--bg-elevated)]">
                    <th className="text-right py-4 px-5 text-[12px] text-[var(--text-secondary)] font-extrabold uppercase tracking-wider rounded-r-[14px]">
                      معیار
                    </th>
                    {comparison.items.map((item: any) => (
                      <th key={item.version_id} className="text-right py-4 px-5 rounded-l-[14px]">
                        <div className="font-extrabold text-[14px] text-[var(--text-primary)]">{item.version_name}</div>
                        <div className="text-[11px] text-[var(--text-secondary)] font-medium mt-0.5">{item.strategy_name}</div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                    <td className="py-4 px-5 text-[13px] text-[var(--text-secondary)] font-semibold">تعداد معاملات</td>
                    {comparison.items.map((item: any) => (
                      <td key={item.version_id} className="py-4 px-5 text-[14px] font-bold text-[var(--text-primary)]">
                        {item.total_trades}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                    <td className="py-4 px-5 text-[13px] text-[var(--text-secondary)] font-semibold">🥇 نرخ برد</td>
                    {comparison.items.map((item: any) => (
                      <td key={item.version_id} className={`py-4 px-5 text-[14px] ${getCellStyle(item, comparison.items, 'win_rate')}`}>
                        {item.win_rate}٪
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                    <td className="py-4 px-5 text-[13px] text-[var(--text-secondary)] font-semibold">💰 سود خالص</td>
                    {comparison.items.map((item: any) => (
                      <td key={item.version_id} className={`py-4 px-5 text-[14px] ${getCellStyle(item, comparison.items, 'net_pnl')}`}>
                        {item.net_pnl >= 0 ? '+' : ''}{item.net_pnl} $
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                    <td className="py-4 px-5 text-[13px] text-[var(--text-secondary)] font-semibold">🏆 فاکتور سود</td>
                    {comparison.items.map((item: any) => (
                      <td key={item.version_id} className={`py-4 px-5 text-[14px] ${getCellStyle(item, comparison.items, 'profit_factor')}`}>
                        {item.profit_factor}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                    <td className="py-4 px-5 text-[13px] text-[var(--text-secondary)] font-semibold">🛡️ حداکثر DD</td>
                    {comparison.items.map((item: any) => (
                      <td key={item.version_id} className={`py-4 px-5 text-[14px] ${getCellStyle(item, comparison.items, 'max_dd', false)}`}>
                        -{item.max_dd} $
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                    <td className="py-4 px-5 text-[13px] text-[var(--text-secondary)] font-semibold">🎯 Net R</td>
                    {comparison.items.map((item: any) => (
                      <td key={item.version_id} className={`py-4 px-5 text-[14px] ${getCellStyle(item, comparison.items, 'net_r')}`}>
                        {item.net_r} R
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                    <td className="py-4 px-5 text-[13px] text-[var(--text-secondary)] font-semibold">📐 اکسپکتنسی</td>
                    {comparison.items.map((item: any) => (
                      <td key={item.version_id} className={`py-4 px-5 text-[14px] ${getCellStyle(item, comparison.items, 'expectancy')}`}>
                        {item.expectancy} $ {item.expectancy_r !== null && item.expectancy_r !== undefined ? `(${item.expectancy_r} R)` : ''}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                    <td className="py-4 px-5 text-[13px] text-[var(--text-secondary)] font-semibold">📈 میانگین برد / باخت</td>
                    {comparison.items.map((item: any) => (
                      <td key={item.version_id} className="py-4 px-5 text-[14px] font-semibold text-[var(--text-primary)]">
                        +{item.avg_win} $ / -{item.avg_loss} $
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                    <td className="py-4 px-5 text-[13px] text-[var(--text-secondary)] font-semibold">🚀 بزرگ‌ترین برد / باخت</td>
                    {comparison.items.map((item: any) => (
                      <td key={item.version_id} className="py-4 px-5 text-[14px] font-semibold text-[var(--text-primary)]">
                        +{item.largest_win} $ / -{item.largest_loss} $
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                    <td className="py-4 px-5 text-[13px] text-[var(--text-secondary)] font-semibold">🔻 بیشترین باخت متوالی</td>
                    {comparison.items.map((item: any) => (
                      <td key={item.version_id} className={`py-4 px-5 text-[14px] ${getCellStyle(item, comparison.items, 'max_consecutive_losses', false)}`}>
                        {item.max_consecutive_losses}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                    <td className="py-4 px-5 text-[13px] text-[var(--text-secondary)] font-semibold">⚖️ نسبت میانگین برد به باخت</td>
                    {comparison.items.map((item: any) => (
                      <td key={item.version_id} className="py-4 px-5 text-[14px] font-semibold text-[var(--text-primary)]">
                        {item.consistency_analysis?.avg_win_avg_loss_ratio ?? '-'}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                    <td className="py-4 px-5 text-[13px] text-[var(--text-secondary)] font-semibold">📉 انحراف معیار سود (یکنواختی)</td>
                    {comparison.items.map((item: any) => (
                      <td key={item.version_id} className="py-4 px-5 text-[14px] font-semibold text-[var(--text-primary)]">
                        {item.consistency_analysis?.pnl_std_dev ?? '-'}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                    <td className="py-4 px-5 text-[13px] text-[var(--text-secondary)] font-semibold">🎲 وابستگی به معاملات بزرگ</td>
                    {comparison.items.map((item: any) => (
                      <td key={item.version_id} className="py-4 px-5 text-[14px] font-semibold text-[var(--text-primary)]">
                        {item.consistency_analysis?.top_trades_contribution_percent ?? '-'}٪ از ۳ معامله‌ی برتر
                      </td>
                    ))}
                  </tr>
                  <tr className="bg-[#EDF3FF]/50">
                    <td className="py-4 px-5 text-[13px] text-[var(--text-primary)] font-extrabold">⭐ Health Score</td>
                    {comparison.items.map((item: any) => (
                      <td key={item.version_id} className={`py-4 px-5 text-[16px] ${getCellStyle(item, comparison.items, 'health_score')}`}>
                        {item.health_score} / ۱۰۰
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
            {/* ═══════════════════════════════════════════
    نمودارهای مقایسه
═══════════════════════════════════════════ */}
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
  <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
    <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
      <div className="w-11 h-11 rounded-[14px] bg-[var(--accent-soft)] flex items-center justify-center text-xl">
        📊
      </div>
      <div>
        <h3 className="text-base font-extrabold text-[var(--text-primary)]">مقایسه‌ی نرخ برد</h3>
        <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">درصد معاملات برنده</p>
      </div>
    </div>
    <ComparisonBarChart items={comparison.items} metric="win_rate" />
  </div>

  <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
    <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
      <div className="w-11 h-11 rounded-[14px] bg-[var(--profit-soft)] flex items-center justify-center text-xl">
        💰
      </div>
      <div>
        <h3 className="text-base font-extrabold text-[var(--text-primary)]">مقایسه‌ی سود خالص</h3>
        <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">مجموع سود/زیان</p>
      </div>
    </div>
    <ComparisonBarChart items={comparison.items} metric="net_pnl" />
  </div>
</div>

<div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
  <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
    <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
      <div className="w-11 h-11 rounded-[14px] bg-[var(--purple-soft)] flex items-center justify-center text-xl">
        🏆
      </div>
      <div>
        <h3 className="text-base font-extrabold text-[var(--text-primary)]">مقایسه‌ی فاکتور سود</h3>
        <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">سود کل / ضرر کل</p>
      </div>
    </div>
    <ComparisonBarChart items={comparison.items} metric="profit_factor" />
  </div>

  <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
    <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
      <div className="w-11 h-11 rounded-[14px] bg-[var(--loss-soft)] flex items-center justify-center text-xl">
        ⚠️
      </div>
      <div>
        <h3 className="text-base font-extrabold text-[var(--text-primary)]">مقایسه‌ی حداکثر DD</h3>
        <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">کمتر بهتر</p>
      </div>
    </div>
    <ComparisonBarChart items={comparison.items} metric="max_dd" />
  </div>
</div>

{/* نمودار راداری */}
<div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md mb-6">
  <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
    <div className="w-11 h-11 rounded-[14px] bg-[var(--accent-soft)] flex items-center justify-center text-xl">
      🎯
    </div>
    <div>
      <h3 className="text-base font-extrabold text-[var(--text-primary)]">مقایسه‌ی کلی متریک‌ها</h3>
      <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">نمای راداری از تمام متریک‌ها</p>
    </div>
  </div>
  <ComparisonRadarChart items={comparison.items} />
</div>
          </div>

          {/* پیشنهاد هوشمند */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-11 h-11 rounded-[14px] bg-[var(--warning-soft)] flex items-center justify-center text-xl">
                💡
              </div>
              <div>
                <h3 className="text-base font-extrabold text-[var(--text-primary)]">پیشنهاد هوشمند</h3>
                <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">تحلیل خودکار بهترین نسخه</p>
              </div>
            </div>

            <div
              className="rounded-[18px] p-6 mb-5 border border-[var(--border-accent)] relative overflow-hidden"
              style={{ background: 'linear-gradient(135deg, #EDF3FF 0%, #F0F6FF 100%)' }}
            >
              <div className="absolute top-0 right-0 left-0 h-1" style={{ background: 'linear-gradient(90deg, #3F7CFF, #7959D6)' }} />
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                  <div className="text-[22px] font-extrabold text-[var(--text-primary)] mb-1">
                    🏆 {comparison.best_version_name}
                  </div>
                  <div className="text-[14px] text-[var(--text-secondary)] font-medium">
                    {comparison.recommendation}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-[11px] text-[var(--text-secondary)] font-semibold mb-1">Health Score</div>
                  <div className="text-[36px] font-extrabold accent-gradient-text leading-none">
                    {comparison.best_health_score} <span className="text-[16px]">/ ۱۰۰</span>
                  </div>
                </div>
              </div>
            </div>

            {/* دلایل */}
            {comparison.reasons && comparison.reasons.length > 0 && (
              <div>
                <h4 className="text-[14px] font-extrabold text-[var(--text-primary)] mb-3">📊 دلایل برتری:</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {comparison.reasons.map((reason: any, idx: number) => (
                    <div
                      key={idx}
                      className="flex items-start gap-3 bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[14px] p-4 hover:border-[var(--border-accent)] hover:shadow-sm transition-all"
                    >
                      <div className="w-10 h-10 rounded-[12px] bg-[var(--bg-card)] flex items-center justify-center text-xl shadow-sm shrink-0">
                        {reason.icon}
                      </div>
                      <span className="text-[13px] text-[var(--text-primary)] font-medium leading-relaxed pt-2">{reason.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* بهترین نسخه برای هر نماد */}
          {comparison.symbol_bests && comparison.symbol_bests.length > 0 && (
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-11 h-11 rounded-[14px] bg-[var(--profit-soft)] flex items-center justify-center text-xl">
                  🥇
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-[var(--text-primary)]">بهترین نسخه برای هر نماد</h3>
                  <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">بر اساس امتیاز کلی</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {comparison.symbol_bests.map((sb: any, idx: number) => (
                  <div
                    key={idx}
                    className="bg-gradient-to-bl from-[#E5F8F1] to-[#F0FDF9] border border-[var(--profit-border)] rounded-[18px] p-5 hover:shadow-md transition-all"
                  >
                    <div className="text-[15px] font-extrabold text-[var(--text-primary)] mb-4">{sb.symbol_label}</div>
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 rounded-[14px] bg-[var(--bg-card)] flex items-center justify-center text-2xl shadow-sm">
                        🥇
                      </div>
                      <div>
                        <div className="text-[15px] font-extrabold text-[var(--profit)]">{sb.best_version_name}</div>
                        <div className="text-[11px] text-[var(--text-secondary)] font-medium mt-0.5">{sb.best_strategy}</div>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-white/60 rounded-[10px] p-3">
                        <div className="text-[10px] text-[var(--text-secondary)] font-semibold mb-1">نرخ برد</div>
                        <div className="text-[16px] font-extrabold text-[var(--text-primary)]">{sb.win_rate}٪</div>
                      </div>
                      <div className="bg-white/60 rounded-[10px] p-3">
                        <div className="text-[10px] text-[var(--text-secondary)] font-semibold mb-1">سود خالص</div>
                        <div className={`text-[16px] font-extrabold ${sb.net_pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                          {sb.net_pnl >= 0 ? '+' : ''}{sb.net_pnl} $
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* مقایسه‌ی تفکیکی */}
          {comparison.detail_bests && (
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-11 h-11 rounded-[14px] bg-[var(--purple-soft)] flex items-center justify-center text-xl">
                  📈
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-[var(--text-primary)]">بهترین نسخه در هر بخش</h3>
                  <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">تفکیک‌شده بر اساس سشن، روز، ساعت و بازه</p>
                </div>
              </div>

              {/* تب‌ها */}
              <div className="flex gap-2 mb-5 flex-wrap">
                {[
                  { key: 'session', label: '🌍 سشن‌ها' },
                  { key: 'weekday', label: '📅 روزهای هفته' },
                  { key: 'hour', label: '🕐 ساعت‌ها' },
                  { key: 'custom', label: '⏰ بازه‌های سفارشی' },
                ].map((tab) => {
                  const isActive = activeDetailTab === tab.key;
                  return (
                    <button
                      key={tab.key}
                      onClick={() => setActiveDetailTab(tab.key as any)}
                      className={`px-5 py-2.5 rounded-[10px] text-[13px] font-bold transition-all ${
                        isActive
                          ? 'text-white shadow-[0_6px_16px_rgba(63,124,255,0.3)]'
                          : 'bg-[var(--bg-input)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-accent)] hover:text-[var(--accent)]'
                      }`}
                      style={isActive ? { background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' } : {}}
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              <div className="space-y-2.5">
                {comparison.detail_bests[activeDetailTab === 'custom' ? 'custom_interval' : activeDetailTab]?.map(
                  (detail: any, idx: number) => (
                    <div
                      key={idx}
                      className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[14px] p-4 flex justify-between items-center flex-wrap gap-4 hover:border-[var(--border-accent)] hover:bg-[var(--bg-card)] hover:shadow-sm transition-all"
                    >
                      <div className="text-[14px] font-extrabold text-[var(--text-primary)] min-w-[140px]">
                        {detail.name}
                      </div>
                      <div className="flex items-center gap-6 flex-wrap">
                        <div className="text-center">
                          <div className="text-[10px] text-[var(--text-secondary)] font-bold mb-1">نسخه برتر</div>
                          <div className="text-[14px] font-extrabold text-[var(--profit)]">{detail.best.version_name}</div>
                        </div>
                        <div className="text-center">
                          <div className="text-[10px] text-[var(--text-secondary)] font-bold mb-1">نرخ برد</div>
                          <div className="text-[14px] font-extrabold text-[var(--text-primary)]">{detail.best.win_rate}٪</div>
                        </div>
                        <div className="text-center">
                          <div className="text-[10px] text-[var(--text-secondary)] font-bold mb-1">سود</div>
                          <div className={`text-[14px] font-extrabold ${detail.best.net_pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                            {detail.best.net_pnl >= 0 ? '+' : ''}{detail.best.net_pnl} $
                          </div>
                        </div>
                        {detail.best.total_trades !== undefined && (
                          <div className="text-center">
                            <div className="text-[10px] text-[var(--text-secondary)] font-bold mb-1">معاملات</div>
                            <div className="text-[14px] font-extrabold text-[var(--text-primary)]">{detail.best.total_trades}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                )}
                {comparison.detail_bests[activeDetailTab === 'custom' ? 'custom_interval' : activeDetailTab]?.length === 0 && (
                  <div className="text-[var(--text-muted)] text-sm text-center py-8">
                    داده‌ای برای این بخش وجود ندارد
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}