import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import ComparisonBarChart from '../components/charts/ComparisonBarChart';
import ComparisonRadarChart from '../components/charts/ComparisonRadarChart';
import EmptyState from '../components/ui/EmptyState';
import Skeleton from '../components/Skeleton';
import { useToast } from '../components/ToastProvider';

import {
  getAllVersions,
  getStrategies,
  compareVersions,
  analyzeVersionScoped,
} from '../api/client';
import type { CompareResponse, VersionComparisonItem, Strategy, StrategyVersion } from '../api/client';
// فاز ۴۸c — ماندگاری فیلترها در URL (پروژه react-router ندارد ⇒ History API خام)
import {
  COMPARISON_TEST_TYPES,
  DEFAULT_COMPARISON_TEST_TYPE,
  MAX_COMPARE_SELECT,
  buildComparisonPatch,
  parseComparisonFilters,
} from '../utils/comparisonUrl';
import { writeSearch } from '../utils/urlState';
import { measuredProfitFactor } from '../utils/comparisonChartData';

type Version = StrategyVersion & { strategy_name: string };

const TEST_TYPE_LABELS: Record<string, string> = {
  BACKTEST: 'بک‌تست',
  FORWARD: 'فوروارد',
  REAL_PERSONAL: 'واقعی شخصی',
  REAL_PROP: 'واقعی پراپ',
};

// فاز ۴۸c — گزینه‌ها از whitelist مشترک URL می‌آیند (منبع واحد حقیقت)
const TEST_TYPES = COMPARISON_TEST_TYPES.map((value) => ({
  value,
  label: TEST_TYPE_LABELS[value] ?? value,
}));

const MAX_SELECT = MAX_COMPARE_SELECT;

/** فاز ۴۸c — تأخیر نوشتن فیلترها در URL (ms): هر تایپ/فیلتر یک replaceState نسازد */
const URL_SYNC_DEBOUNCE_MS = 500;

/**
 * فاز ۴۸a.۶ — صفحه‌ی مقایسه/رتبه‌بندی نسخه‌ها (قرارداد جدید).
 * قرارداد بک‌اند: `{comparison, test_type, filters, best}` — هر item: rank/score/metrics/reasons[/error]
 */
export default function ComparisonPage() {
  const toast = useToast();
  const toastRef = useRef(toast);
  const compareGeneration = useRef(0);
  const loadGeneration = useRef(0);
  const mounted = useRef(true);

  // فاز ۴۸c — مقدار اولیهٔ فیلترها از URL خوانده می‌شود (refresh ⇒ بازیابی فیلترها)
  const initialFilters = useMemo(
    () => parseComparisonFilters(typeof window === 'undefined' ? '' : window.location.search),
    [],
  );

  // ── داده‌های پایه ──
  const [versions, setVersions] = useState<Version[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);

  // ── انتخاب‌ها و فیلترها ──
  const [selectedIds, setSelectedIds] = useState<number[]>(initialFilters.versionIds);
  const [filterStrategy, setFilterStrategy] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [testType, setTestType] = useState<string>(
    initialFilters.testType ?? DEFAULT_COMPARISON_TEST_TYPE,
  );
  const [symbol, setSymbol] = useState(initialFilters.symbol ?? '');
  const [dateFrom, setDateFrom] = useState(initialFilters.dateFrom ?? '');
  const [dateTo, setDateTo] = useState(initialFilters.dateTo ?? '');

  // ── نتیجه ──
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [drawerVersion, setDrawerVersion] = useState<VersionComparisonItem | null>(null);
  const [appliedSnapshot, setAppliedSnapshot] = useState<{ ids: number[]; testType: string; symbol: string; dateFrom: string; dateTo: string } | null>(null);
  const [resultCurrent, setResultCurrent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reanalyzingId, setReanalyzingId] = useState<number | null>(null);
  const [reanalyzingAll, setReanalyzingAll] = useState(false);

  useEffect(() => { toastRef.current = toast; }, [toast]);

  const invalidateComparison = () => {
    compareGeneration.current += 1;
    setResult(null);
    setAppliedSnapshot(null);
    setResultCurrent(false);
    setDrawerVersion(null);
    setLoading(false);
    setError(null);
  };

  /** فاز ۴۸c — نوشتن فوری فیلترها در URL (بدون debounce) */
  const updateUrl = () => {
    writeSearch(
      buildComparisonPatch({ versionIds: selectedIds, testType, symbol, dateFrom, dateTo }),
    );
  };

  // فاز ۴۸c — Sync خودکار فیلترها با URL (debounce تا هر تایپ یک replaceState نسازد)
  useEffect(() => {
    const timer = setTimeout(updateUrl, URL_SYNC_DEBOUNCE_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIds, testType, symbol, dateFrom, dateTo]);

  const loadData = useCallback(async () => {
    const generation = ++loadGeneration.current;
    try {
      const [versionsRes, strategiesRes] = await Promise.all([getAllVersions(), getStrategies()]);
      if (mounted.current && generation === loadGeneration.current) {
        setVersions(versionsRes.data || []);
        setStrategies(strategiesRes.data || []);
      }
    } catch (err) {
      if (mounted.current && generation === loadGeneration.current) {
        console.error('خطا:', err);
        toastRef.current.error('خطا در بارگذاری نسخه‌ها');
      }
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    queueMicrotask(() => { if (mounted.current) void loadData(); });
    return () => {
      mounted.current = false;
      compareGeneration.current += 1;
      loadGeneration.current += 1;
    };
  }, [loadData]);

  // نگاشت version_id ⇒ «استراتژی / نسخه»
  const labelOf = (versionId: number) => {
    const v = versions.find((x) => x.id === versionId);
    return v ? `${v.strategy_name} / ${v.version_name}` : `نسخه #${versionId}`;
  };

  const strategyOf = (versionId: number) =>
    versions.find((x) => x.id === versionId)?.strategy_name ?? '—';

  const toggleVersion = (id: number) => {
    if (selectedIds.includes(id)) {
      invalidateComparison();
      setSelectedIds(selectedIds.filter((v) => v !== id));
      return;
    }
    if (selectedIds.length >= MAX_SELECT) {
      toast.warning(`حداکثر ${MAX_SELECT} نسخه قابل مقایسه است`);
      return;
    }
    invalidateComparison();
    setSelectedIds([...selectedIds, id]);
  };

  const changeTestType = (value: string) => { invalidateComparison(); setTestType(value); };
  const changeSymbol = (value: string) => { invalidateComparison(); setSymbol(value); };
  const changeDateFrom = (value: string) => { invalidateComparison(); setDateFrom(value); };
  const changeDateTo = (value: string) => { invalidateComparison(); setDateTo(value); };

  const handleCompare = async () => {
    if (selectedIds.length < 2) {
      toast.error('حداقل ۲ نسخه انتخاب کن');
      return;
    }
    // فاز ۴۸c — فیلترها قبل از فراخوانی API در URL تثبیت می‌شوند (بدون انتظار debounce)
    updateUrl();
    const generation = ++compareGeneration.current;
    const snapshot = { ids: [...selectedIds], testType, symbol: symbol.trim(), dateFrom, dateTo };
    setAppliedSnapshot(null);
    setResult(null);
    setDrawerVersion(null);
    setError(null);
    setResultCurrent(false);
    setLoading(true);
    setAppliedSnapshot(snapshot);
    try {
      const r = await compareVersions({
        version_ids: snapshot.ids,
        test_type: snapshot.testType,
        symbol: snapshot.symbol || undefined,
        date_from: snapshot.dateFrom || undefined,
        date_to: snapshot.dateTo || undefined,
      });
      if (mounted.current && generation === compareGeneration.current) {
        setResult(r.data);
        setResultCurrent(true);
      }
    } catch (err: any) {
      if (mounted.current && generation === compareGeneration.current) {
        const message = err?.response?.data?.detail || 'خطا در مقایسه';
        setError(message);
        toast.error(message);
      }
    } finally {
      if (mounted.current && generation === compareGeneration.current) setLoading(false);
    }
  };

  const clearComparison = () => {
    invalidateComparison();
    setSelectedIds([]);
  };

  const handleReanalyzeVersion = async (versionId: number) => {
    try {
      setReanalyzingId(versionId);
      await analyzeVersionScoped(versionId, testType);
      toastRef.current.success(`تحلیل ${labelOf(versionId)} به‌روز شد`);
      await handleCompare();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'خطا در تحلیل نسخه';
      toastRef.current.error(msg);
    } finally {
      setReanalyzingId(null);
    }
  };

  const handleReanalyzeAllErrors = async (errorVersionIds: number[]) => {
    try {
      setReanalyzingAll(true);
      for (const vid of errorVersionIds) {
        await analyzeVersionScoped(vid, testType);
      }
      toastRef.current.success('تمامی نسخه‌های نیازمند تحلیل با موفقیت تحلیل شدند');
      await handleCompare();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'خطا در تحلیل برخی نسخه‌ها';
      toastRef.current.error(msg);
    } finally {
      setReanalyzingAll(false);
    }
  };

  const filteredVersions = versions.filter((v) => {
    if (filterStrategy && v.strategy_id !== filterStrategy) return false;
    if (
      searchQuery &&
      !v.version_name.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !v.strategy_name.toLowerCase().includes(searchQuery.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  // آرایهٔ flat برای نمودارهای موجود (Bar/Radar) — معادل `metrics` تودرتو را باز می‌کند
  const chartItems = (result?.comparison ?? [])
    .filter((i) => !i.error && i.metrics)
    .map((i) => {
      const m = i.metrics || {};
      return {
        version_id: i.version_id,
        version_name: labelOf(i.version_id),
        strategy_name: strategyOf(i.version_id),
        win_rate: Number(m.win_rate ?? 0),
        profit_factor: measuredProfitFactor(m.profit_factor, m.profit_factor_status),
        net_pnl: Number(m.net_pnl ?? 0),
        max_dd: Number(m.max_dd ?? 0),
        health_score: Number(i.score ?? 0), // Radar نام health_score می‌خواهد ⇒ از score پر می‌شود
        profit_factor_status: m.profit_factor_status ?? 'unavailable',
      };
    });

  const scoreBadgeClass = (rank?: number) => {
    if (rank === 1)
      return 'bg-[var(--warning-soft)] text-[var(--warning-strong)] border-[var(--warning-border)]';
    if (rank === 2)
      return 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--border-accent)]';
    return 'bg-[var(--bg-input)] text-[var(--text-secondary)] border-[var(--border-subtle)]';
  };

  // فاز ۵۲ — رنگ نشان وضعیت نمونه
  const sampleStatusClass = (status?: string) => {
    if (status === 'کافی')
      return 'bg-[var(--profit-soft)] text-[var(--profit)] border-[var(--profit-border)]';
    if (status === 'ناکافی')
      return 'bg-[var(--warning-soft)] text-[var(--warning-strong)] border-[var(--warning-border)]';
    if (status === 'خیلی کم')
      return 'bg-[var(--loss-soft)] text-[var(--loss)] border-[var(--loss-border)]';
    return 'bg-[var(--bg-input)] text-[var(--text-secondary)] border-[var(--border-subtle)]';
  };

  return (
    <div dir="rtl" className="p-7">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-extrabold text-[var(--text-primary)]">📊 مقایسه نسخه‌ها</h1>
        <p className="text-[13px] text-[var(--text-secondary)] mt-1">
          انتخاب ۲ تا {MAX_SELECT} نسخه + فیلتر نماد/تاریخ ⇒ رتبه‌بندی بر اساس Score
        </p>
      </div>
      {error && <div role="alert" className="mb-4 rounded-xl border border-[var(--loss-border)] bg-[var(--loss-soft)] p-3 text-sm text-[var(--loss)]">{error}</div>}
      {result && !resultCurrent && <div role="status" className="mb-4 rounded-xl border border-[var(--warning-border)] bg-[var(--warning-soft)] p-3 text-sm text-[var(--warning-strong)]">فیلترها تغییر کرده‌اند؛ نتیجهٔ قبلی با فیلترهای ثبت‌شده در زیر نشان داده می‌شود و نتیجهٔ جاری نیست.</div>}
      {result && appliedSnapshot && <div className="mb-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-3 text-xs text-[var(--text-secondary)]" data-testid="applied-filters">فیلترهای نتیجه: نسخه‌ها {appliedSnapshot.ids.map(labelOf).join('، ')} · نوع واقعی معامله {result.test_type} · نماد {appliedSnapshot.symbol || 'همه'} · از {appliedSnapshot.dateFrom || 'ابتدا'} تا {appliedSnapshot.dateTo || 'اکنون'}</div>}

      {/* پنل فیلتر */}
      <div className="app-card p-6 shadow-md mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-5">
          <div>
            <label className="block text-[12px] font-bold text-[var(--text-secondary)] mb-2">استراتژی</label>
            <select
              value={filterStrategy ?? ''}
              onChange={(e) => setFilterStrategy(e.target.value ? Number(e.target.value) : null)}
              className="w-full bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[13px] text-[var(--text-primary)] focus:outline-none focus:border-[var(--border-accent)]"
            >
              <option value="">همه</option>
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[12px] font-bold text-[var(--text-secondary)] mb-2">جستجو</label>
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="نام نسخه / استراتژی"
              className="w-full bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[13px] text-[var(--text-primary)] focus:outline-none focus:border-[var(--border-accent)]"
            />
          </div>

          <div>
            <label className="block text-[12px] font-bold text-[var(--text-secondary)] mb-2">نوع تست</label>
            <select
              value={testType}
              onChange={(e) => changeTestType(e.target.value)}
              className="w-full bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[13px] text-[var(--text-primary)] focus:outline-none focus:border-[var(--border-accent)]"
            >
              {TEST_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[12px] font-bold text-[var(--text-secondary)] mb-2">نماد (اختیاری)</label>
            <input
              value={symbol}
              onChange={(e) => changeSymbol(e.target.value)}
              placeholder="XAUUSD"
              className="w-full bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[13px] text-[var(--text-primary)] focus:outline-none focus:border-[var(--border-accent)]"
            />
          </div>

          <div>
            <label className="block text-[12px] font-bold text-[var(--text-secondary)] mb-2">از تاریخ</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => changeDateFrom(e.target.value)}
              className="w-full bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[13px] text-[var(--text-primary)] focus:outline-none focus:border-[var(--border-accent)]"
            />
          </div>

          <div>
            <label className="block text-[12px] font-bold text-[var(--text-secondary)] mb-2">تا تاریخ</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => changeDateTo(e.target.value)}
              className="w-full bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[13px] text-[var(--text-primary)] focus:outline-none focus:border-[var(--border-accent)]"
            />
          </div>
        </div>

        {/* لیست نسخه‌ها (چندتایی) */}
        <div className="max-h-72 overflow-y-auto border border-[var(--border-subtle)] rounded-[14px] p-2 mb-5 bg-[var(--bg-input)]">
          {filteredVersions.length === 0 ? (
            <div className="text-[var(--text-muted)] text-sm text-center py-8">نسخه‌ای یافت نشد</div>
          ) : (
            <div className="space-y-1.5">
              {filteredVersions.map((v) => {
                const isSelected = selectedIds.includes(v.id);
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
                        className="w-5 h-5 accent-[var(--accent)] cursor-pointer"
                      />
                      <div className="text-xs text-[var(--text-secondary)]">
                      {Object.entries(v.trade_counts_by_test_type ?? {}).map(([type, count]) => `${type === 'unspecified' ? 'نامشخص/legacy' : TEST_TYPE_LABELS[type.toUpperCase()] ?? type}: ${count}`).join(' · ') || 'دادهٔ بسته در scope مشخصی نیست'}
                      </div>
                      <div>
                        <div className="text-[14px] font-bold text-[var(--text-primary)]">
                          {v.strategy_name} / {v.version_name}
                        </div>
                        <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                          {v.trades_count} معامله • وضعیت: {v.status}
                        </div>
                      </div>
                    </div>
                    {isSelected && (
                      <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-[var(--accent)] text-white">انتخاب‌شده</span>
                    )}
                  </label>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex justify-between items-center flex-wrap gap-3">
          <div className="text-[13px] text-[var(--text-secondary)] font-medium">
            انتخاب‌شده: <span className="text-[var(--accent)] font-extrabold text-base">{selectedIds.length}</span> از {MAX_SELECT}
          </div>
          <div className="flex gap-2">
            <button
              onClick={clearComparison}
              className="bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--border-accent)] text-[var(--text-secondary)] hover:text-[var(--accent)] px-5 py-2.5 rounded-[10px] text-sm font-bold transition-all"
            >
              ✕ پاک کردن
            </button>
            <button
              onClick={handleCompare}
              disabled={loading || selectedIds.length < 2}
              className="text-white px-6 py-2.5 rounded-[10px] text-sm font-extrabold shadow-[0_6px_16px_rgba(63,124,255,0.3)] hover:shadow-[0_10px_24px_rgba(63,124,255,0.4)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}
            >
              {loading ? 'در حال مقایسه...' : '🔍 مقایسه'}
            </button>
          </div>
        </div>
      </div>

      {/* حالت بارگذاری */}
      {loading && (
        <div className="space-y-4">
          <Skeleton variant="card" className="h-32" />
          <Skeleton variant="card" className="h-72" />
        </div>
      )}


      {/* حالت خالی */}
      {!loading && !result && (
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] shadow-md">
          <EmptyState
            icon="📊"
            title="هنوز مقایسه‌ای انجام نشده"
            description="۲ تا ۵ نسخه را انتخاب کن و «مقایسه» را بزن."
          />
        </div>
      )}
      {!loading && result && (
        <>
          {/* بهترین نسخه */}
          {result.best && (
            <div className="app-card p-6 shadow-md mb-6">
              <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
                <div className="w-11 h-11 rounded-[14px] bg-[var(--warning-soft)] flex items-center justify-center text-xl">🏆</div>
                <div>
                    <h3 className="text-base font-extrabold text-[var(--text-primary)]">{result.best_ties && result.best_ties.length > 1 ? 'نسخه‌های هم‌رتبهٔ نخست' : 'بهترین نسخه'}</h3>
                    <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">بالاترین Score در دامنهٔ همین مقایسه؛ نه پیش‌بینی عملکرد آینده</p>
                </div>
              </div>
              <div
                className="rounded-[18px] p-6 border border-[var(--border-accent)] relative overflow-hidden"
                style={{ background: 'linear-gradient(135deg, var(--accent-soft) 0%, var(--accent-light) 100%)' }}
              >
                <div className="absolute top-0 right-0 left-0 h-1" style={{ background: 'linear-gradient(90deg, var(--accent), var(--purple))' }} />
                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div>
                    <div className="text-[20px] font-extrabold text-[var(--text-primary)] mb-1">
                      🏆 {(result.best_ties && result.best_ties.length > 1 ? result.best_ties : [result.best]).map((x) => labelOf(x.version_id)).join(' • ')}
                    </div>
                    <div className="text-[13px] text-[var(--text-secondary)] font-medium">
                      {strategyOf(result.best.version_id)} • نوع تست: {result.test_type}
                    </div>
                  </div>
                    <div className="text-center">
                    <div className="text-[11px] text-[var(--text-secondary)] font-semibold mb-1">Score</div>
                    <div className="text-[36px] font-extrabold accent-gradient-text leading-none">
                      {result.best.score?.toFixed(1) ?? '—'} <span className="text-[16px]">/ ۱۰۰</span>
                    </div>
                  </div>
                </div>
                {(result.best?.reasons ?? []).filter((reason) => reason.text.includes('معیار تعیین‌کننده') || reason.text.includes('اجزای امتیاز') || reason.text.includes('Expectancy بر پایه')).map((reason, index) => (
                  <div key={`best-explanation-${index}`} className="mt-3 text-[12px] leading-6 text-[var(--text-secondary)]">
                    {reason.icon} {reason.text}
                  </div>
                ))}
              </div>
            </div>
          )}
          {/* جدول رتبه‌بندی */}
          {result.comparison.length > 0 && (
            <div className="app-card p-6 shadow-md mb-6">
              <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
                <div className="w-11 h-11 rounded-[14px] bg-[var(--accent-soft)] flex items-center justify-center text-xl">📋</div>
                <div>
                  <h3 className="text-base font-extrabold text-[var(--text-primary)]">جدول رتبه‌بندی</h3>
                  <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">
                    {result.comparison.length} نسخه • نوع تست: {result.test_type}
                    {result.filters.symbol ? ` • نماد: ${result.filters.symbol}` : ''}
                  </p>
                </div>
              </div>

              {result.comparison.some((i) => i.error) && testType !== 'REAL_PERSONAL' && testType !== 'REAL_PROP' && (
                <div className="mb-4 flex items-center justify-between flex-wrap gap-3 rounded-xl border border-[var(--warning-border)] bg-[var(--warning-soft)] p-3.5 text-xs text-[var(--warning-strong)]">
                  <div className="flex items-center gap-2 font-bold">
                    <span>⚠️</span>
                    <span>برخی از نسخه‌ها کهنه هستند یا تحلیل نشده‌اند و نیاز به تحلیل مجدد دارند.</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleReanalyzeAllErrors(result.comparison.filter((i) => i.error).map((i) => i.version_id))}
                    disabled={loading || reanalyzingAll || reanalyzingId !== null}
                    className="px-3.5 py-2 rounded-[10px] bg-[var(--accent)] text-white text-xs font-extrabold hover:bg-[var(--accent-strong)] transition-all shadow-sm disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
                  >
                    {reanalyzingAll ? '⏳ در حال تحلیل همه...' : '🔄 تحلیل همه و به‌روزرسانی مقایسه'}
                  </button>
                </div>
              )}

              <div className="overflow-x-auto rounded-[14px] border border-[var(--border-subtle)]">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-[var(--bg-elevated)]">
                      {['رتبه', 'نسخه', 'Score', 'نرخ برد', 'فاکتور سود', 'سود خالص', 'حداکثر DD', 'وضعیت نمونه', 'جزئیات Score', 'دلایل'].map((h) => (
                        <th key={h} className="text-right py-4 px-4 text-[12px] text-[var(--text-secondary)] font-extrabold uppercase tracking-wider whitespace-nowrap">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.comparison.map((item) => {
                      const m = item.metrics || {};
                      const reasons = item.reasons ?? [];
                      return (
                        <tr key={item.version_id} className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                          <td className="py-4 px-4">
                            <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full border text-[13px] font-extrabold ${scoreBadgeClass(item.rank)}`}>
                                {item.rank ?? '—'}{item.rank_tie ? ' = ' : ''}
                            </span>
                          </td>
                          <td className="py-4 px-4">
                            <div className="text-[13px] font-extrabold text-[var(--text-primary)]">{labelOf(item.version_id)}</div>
                            <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">{strategyOf(item.version_id)}</div>
                          </td>
                          {item.error ? (
                            <td colSpan={8} className="py-4 px-4 text-[12px] font-bold text-[var(--warning-strong)]">
                              <div className="flex items-center justify-between flex-wrap gap-2">
                                <span>⚠️ {item.error}</span>
                                {testType !== 'REAL_PERSONAL' && testType !== 'REAL_PROP' && (
                                  <button
                                    type="button"
                                    onClick={() => handleReanalyzeVersion(item.version_id)}
                                    disabled={loading || reanalyzingId === item.version_id || reanalyzingAll}
                                    className="px-3 py-1.5 rounded-[8px] bg-[var(--accent)] text-white text-[11px] font-bold hover:bg-[var(--accent-strong)] transition-all shadow-sm disabled:opacity-50 cursor-pointer flex items-center gap-1"
                                  >
                                    {reanalyzingId === item.version_id ? '⏳ در حال تحلیل...' : '🔄 تحلیل مجدد این نسخه'}
                                  </button>
                                )}
                              </div>
                            </td>
                          ) : (
                            <>
                              <td className="py-4 px-4 text-[15px] font-extrabold accent-gradient-text">
                                {item.score?.toFixed(1) ?? '—'}
                              </td>
                              <td className="py-4 px-4 text-[13px] font-bold text-[var(--text-primary)]">
                                {m.win_rate?.toFixed(1) ?? '—'}٪
                              </td>
                              <td className="py-4 px-4 text-[13px] font-bold text-[var(--text-primary)]">
                                {m.profit_factor_status === 'no_losses' ? 'بدون باخت' : m.profit_factor_status === 'no_usable_pnl' ? 'بدون PnL قابل استفاده' : m.profit_factor?.toFixed(2) ?? '—'}
                              </td>
                              <td className={`py-4 px-4 text-[13px] font-bold ${(m.net_pnl ?? 0) >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                                {(m.net_pnl ?? 0) >= 0 ? '+' : ''}{(m.net_pnl ?? 0).toFixed(0)} USDT
                              </td>
                              <td className="py-4 px-4 text-[13px] font-bold text-[var(--loss)]">
                                -{(m.max_dd ?? 0).toFixed(0)} USDT
                              </td>
                              {/* فاز ۵۲ — وضعیت نمونه + هشدارها */}
                              <td className="py-4 px-4">
                                <div className="flex items-center gap-2">
                                  <span
                                    className={`inline-flex items-center px-2.5 py-1 rounded-full border text-[11px] font-extrabold whitespace-nowrap ${sampleStatusClass(item.sample_status)}`}
                                  >
                                    {item.sample_status ?? '—'}
                                  </span>
                                  {(item.warnings ?? []).length > 0 && (
                                    <span
                                      className="text-[var(--warning-strong)] text-[13px] cursor-help"
                                      title={(item.warnings ?? []).join('\n')}
                                    >
                                      ⚠️
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="py-4 px-4 text-[11px] text-[var(--text-secondary)] min-w-[190px]">
                                <div>DD: {item.components?.dd_available ? 'معتبر' : 'ناموجود؛ fallback خنثی ۵۰'}</div>
                                <div>Expectancy: {item.components?.r_eligible ? 'gross price R' : 'غیرواجد؛ fallback خنثی ۵۰'}</div>
                                <div>R قیمت؛ بدون commission/swap</div>
                                <div>پوشش R: {typeof item.components?.r_coverage_percent === 'number' ? `${item.components.r_coverage_percent}%` : 'metadata ناموجود'}</div>
                                {typeof item.components?.r_valid_count === 'number' && <div>R معتبر: {item.components.r_valid_count}</div>}
                                <div>جریمه پوشش: {Number(item.components?.r_penalty_exact ?? item.components?.r_penalty ?? 0).toFixed(2)}</div>
                                <div>PF: {String(item.components?.pf_status ?? 'نامشخص')}؛ امتیاز PF: {item.components?.pf_score ?? '—'}</div>
                              </td>
                              <td className="py-4 px-4">
                                <div className="space-y-1">
                                  {reasons.slice(0, 2).map((r, i) => (
                                    <div key={i} className="text-[11px] text-[var(--text-secondary)] flex items-center gap-1.5">
                                      <span>{r.icon}</span>
                                      <span className="truncate max-w-[180px]">{r.text}</span>
                                    </div>
                                  ))}
                                </div>
                                <button
                                  onClick={() => setDrawerVersion(item)}
                                  className="mt-2 text-[11px] font-bold text-[var(--accent)] hover:underline"
                                >
                                  مشاهده همه
                                </button>
                              </td>
                            </>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          {/* نمودارها */}
          {chartItems.length > 0 && (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                {([
                  { title: 'مقایسه‌ی نرخ برد', sub: 'درصد معاملات برنده', icon: '📊', metric: 'win_rate' },
                  { title: 'مقایسه‌ی سود خالص', sub: 'مجموع سود/زیان', icon: '💰', metric: 'net_pnl' },
                  { title: 'مقایسه‌ی فاکتور سود', sub: 'سود کل / ضرر کل', icon: '🏆', metric: 'profit_factor' },
                  { title: 'مقایسه‌ی حداکثر DD', sub: 'کمتر بهتر', icon: '⚠️', metric: 'max_dd' },
                ] as const).map((c) => (
                  <div key={c.metric} className="app-card p-6 shadow-md">
                    <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
                      <div className="w-11 h-11 rounded-[14px] bg-[var(--accent-soft)] flex items-center justify-center text-xl">{c.icon}</div>
                      <div>
                        <h3 className="text-base font-extrabold text-[var(--text-primary)]">{c.title}</h3>
                        <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">{c.sub}</p>
                      </div>
                    </div>
                    <ComparisonBarChart items={chartItems} metric={c.metric} />
                  </div>
                ))}
              </div>

              <div className="app-card p-6 shadow-md mb-6">
                <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
                  <div className="w-11 h-11 rounded-[14px] bg-[var(--accent-soft)] flex items-center justify-center text-xl">🎯</div>
                  <div>
                    <h3 className="text-base font-extrabold text-[var(--text-primary)]">مقایسه‌ی کلی متریک‌ها</h3>
                    <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">هر محور به بیشینهٔ مجموعهٔ همین مقایسه نسبت‌سنجی شده است؛ ۱۰۰ الزاماً مقدار مطلق بهتر نیست. مبالغ منفی فقط در Bar با واحد USDT نمایش داده می‌شوند.</p>
                  </div>
                </div>
                <ComparisonRadarChart items={chartItems} />
              </div>
            </>
          )}
        </>
      )}

      {/* Drawer دلایل */}
      {drawerVersion && (
        <div className="fixed inset-0 z-50 flex" dir="rtl">
          <div className="flex-1 bg-black/40" onClick={() => setDrawerVersion(null)} />
          <div className="w-full max-w-md h-full overflow-y-auto bg-[var(--bg-card)] border-r border-[var(--border-subtle)] shadow-2xl p-6">
            <div className="flex items-start justify-between gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
              <div>
                <h3 className="text-base font-extrabold text-[var(--text-primary)]">
                  دلایل — {labelOf(drawerVersion.version_id)}
                </h3>
                <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">
                  رتبه {drawerVersion.rank ?? '—'} • Score {drawerVersion.score?.toFixed(1) ?? '—'}
                </p>
              </div>
              <button
                onClick={() => setDrawerVersion(null)}
                className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-lg transition-colors"
                aria-label="بستن"
              >
                ✕
              </button>
            </div>
            {/* فاز ۵۲ — وضعیت نمونه، هشدارها و اجزای امتیاز */}
            <div className="mb-5">
              <div className="flex items-center gap-2 mb-3">
                <span
                  className={`inline-flex items-center px-2.5 py-1 rounded-full border text-[11px] font-extrabold ${sampleStatusClass(drawerVersion.sample_status)}`}
                >
                  وضعیت نمونه: {drawerVersion.sample_status ?? '—'}
                </span>
              </div>
              {(drawerVersion.warnings ?? []).length > 0 && (
                <div className="space-y-2 mb-4">
                  {(drawerVersion.warnings ?? []).map((w, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 bg-[var(--warning-soft)] border border-[var(--warning-border)] rounded-[12px] px-3 py-2 text-[12px] font-bold text-[var(--warning-strong)]"
                    >
                      <span>⚠️</span>
                      <span>{w}</span>
                    </div>
                  ))}
                </div>
              )}
              {drawerVersion.components && (
                <div className="grid grid-cols-2 gap-2">
                  {([
                    ['Expectancy (gross price R; بدون commission/swap)', drawerVersion.components.expectancy_score],
                    ['نرخ برد', drawerVersion.components.win_rate_score],
                    ['فاکتور سود', drawerVersion.components.pf_score],
                    ['Drawdown', drawerVersion.components.dd_score],
                    ['جریمهٔ نمونه', drawerVersion.components.sample_penalty],
                    ['جریمهٔ پوشش R', drawerVersion.components.r_penalty],
                  ] as const).map(([label, value]) => (
                    <div key={label} className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[12px] px-3 py-2">
                      <div className="text-[10px] font-bold text-[var(--text-secondary)] mb-0.5">{label}</div>
                      <div className="text-[13px] font-extrabold text-[var(--text-primary)]">{value ?? '—'}</div>
                    </div>
                  ))}
                </div>
              )}
              {drawerVersion.components && (
                <div className="mt-3 text-[11px] leading-6 text-[var(--text-secondary)]">
                  <div>DD: {drawerVersion.components.dd_available ? 'درصد معتبر' : 'ناموجود؛ امتیاز خنثی ۵۰ به‌عنوان fallback'}</div>
                  <div>Expectancy: {drawerVersion.components.r_eligible ? 'واجد شرایط؛ gross price R' : 'غیرواجد شرایط؛ امتیاز خنثی ۵۰ به‌عنوان fallback'}</div>
                  <div>پوشش R: {typeof drawerVersion.components.r_coverage_percent === 'number' ? `${drawerVersion.components.r_coverage_percent}%` : 'metadata ناموجود'}
                    {typeof drawerVersion.components.r_valid_count === 'number' ? ` (${drawerVersion.components.r_valid_count} مقدار معتبر)` : ''}</div>
                  <div>R این امتیاز مبتنی بر حرکت قیمت است و commission/swap را شامل نمی‌شود.</div>
                </div>
              )}
            </div>
            <div className="space-y-3">
              {(drawerVersion.reasons ?? []).map((r, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[14px] p-4"
                >
                  <div className="w-10 h-10 rounded-[12px] bg-[var(--bg-card)] flex items-center justify-center text-xl shadow-sm shrink-0">
                    {r.icon}
                  </div>
                  <span className="text-[13px] text-[var(--text-primary)] font-medium leading-relaxed pt-2">{r.text}</span>
                </div>
              ))}
              {(drawerVersion.reasons ?? []).length === 0 && (
                <div className="text-[var(--text-muted)] text-sm text-center py-8">دلیلی ثبت نشده است</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
