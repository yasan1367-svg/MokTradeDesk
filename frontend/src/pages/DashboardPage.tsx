import { useCallback, useState, useEffect, useRef } from 'react';
import { Wallet, Target, Scale, TrendingDown, ClipboardList, TrendingUp, Trophy, TriangleAlert, RefreshCw, FileText, CalendarDays, Clock, ChevronDown } from 'lucide-react';
import { PieChart, Pie, Cell, BarChart, Bar, Tooltip, ResponsiveContainer, XAxis, YAxis, CartesianGrid, AreaChart, Area } from 'recharts';
import StatCard from '../components/ui/StatCard';
import KpiCard from '../components/ui/KpiCard';
import { Card, CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import ProgressBar from '../components/ui/ProgressBar';
import EquityCurveChart from '../components/charts/EquityCurveChart';
import WinLossPieChart from '../components/charts/WinLossPieChart';
import PnLDistributionChart from '../components/charts/PnLDistributionChart';
import {
  getDashboardData, getYesterdayData, getRealSummary, getAllVersions, exportDashboardPdf, getPropAlerts, markAlertRead,
  getFinanceSummary, getFinanceCashflow, getFinanceAccounts, getTrades,
  getSpendableAssets, getNetProfit, getAssetTrend,
} from '../api/client';
import type { TradeScope } from '../api/client';
import type { CurrencyCode } from '../api/client';
import { DashboardSkeleton } from '../components/Skeleton';
import { useToast } from '../components/ToastProvider';
import PersianDateInput from '../components/PersianDateInput';
import EmptyState from '../components/ui/EmptyState';
import InfoTooltip from '../components/ui/Tooltip';
import ErrorBoundary from '../components/ErrorBoundary';
import FinancialAssetBalances from '../components/FinancialAssetBalances';
import MarketSessionWidget from '../components/MarketSessionWidget';
import { gregorianToJalali, jalaliToGregorian } from '../utils/jalali';

// ── کمک‌تابع‌های هدر (فاز ۱۴.۲) ──
const JALALI_WEEKDAYS = ['یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه', 'شنبه'];

function getGreeting(hour: number): string {
  if (hour >= 5 && hour < 12) return 'صبح بخیر';
  if (hour >= 12 && hour < 17) return 'وقت بخیر';
  if (hour >= 17 && hour < 20) return 'عصر بخیر';
  return 'شب بخیر';
}

// ── فیلتر بازه زمانی (فاز ۱۴.۳) ──
type RangeKey = 'today' | 'yesterday' | 'week' | 'month' | 'quarter' | 'year' | 'all' | 'custom';

const RANGE_FILTERS: { key: RangeKey; label: string; icon: string }[] = [
  { key: 'today', label: 'امروز', icon: '📅' },
  { key: 'yesterday', label: 'دیروز', icon: '🌙' },
  { key: 'week', label: 'این هفته', icon: '🗓️' },
  { key: 'month', label: 'این ماه', icon: '📆' },
  { key: 'quarter', label: 'این فصل', icon: '🍂' },
  { key: 'year', label: 'امسال', icon: '🏵️' },
  { key: 'all', label: 'همه', icon: '♾️' },
  { key: 'custom', label: 'سفارشی', icon: '⚙️' },
];

// فاز ۴۴.۱: دامنهٔ معاملات — پیش‌فرض «واقعی» تا بک‌تست با نتایج زنده قاطی نشود
const SCOPE_FILTERS: { key: TradeScope; label: string }[] = [
  { key: 'real', label: 'واقعی' },
  { key: 'backtest', label: 'بک‌تست' },
  { key: 'forward', label: 'فوروارد' },
  { key: 'all', label: 'همه' },
];

function isoDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function jalaliToIso(jy: number, jm: number, jd: number): string {
  const [gy, gm, gd] = jalaliToGregorian(jy, jm, jd);
  return isoDate(new Date(gy, gm - 1, gd));
}

function computeRange(key: RangeKey, customFrom: string, customTo: string): { from?: string; to?: string } {
  const now = new Date();
  const [jy, jm] = gregorianToJalali(now.getFullYear(), now.getMonth() + 1, now.getDate());
  switch (key) {
    case 'today':
      return { from: isoDate(now), to: isoDate(now) };
    case 'yesterday': {
      const y = new Date(now);
      y.setDate(y.getDate() - 1);
      return { from: isoDate(y), to: isoDate(y) };
    }
    case 'week': {
      const s = new Date(now);
      s.setDate(s.getDate() - ((now.getDay() + 1) % 7)); // شروع هفته شمسی (شنبه)
      return { from: isoDate(s), to: isoDate(now) };
    }
    case 'month':
      return { from: jalaliToIso(jy, jm, 1), to: isoDate(now) };
    case 'quarter': {
      const sm = Math.floor((jm - 1) / 3) * 3 + 1; // ابتدای فصل شمسی
      return { from: jalaliToIso(jy, sm, 1), to: isoDate(now) };
    }
    case 'year':
      return { from: jalaliToIso(jy, 1, 1), to: isoDate(now) };
    case 'custom':
      return { from: customFrom || undefined, to: customTo || undefined };
    default:
      return {};
  }
}

// ── کارت آمار ریسک (فاز ۱۴.۴) ──
const MINI_TOOLTIP = {
  backgroundColor: 'var(--bg-card)',
  border: '1px solid var(--border-subtle)',
  borderRadius: '12px',
  color: 'var(--text-primary)',
  fontSize: '12px',
  direction: 'rtl' as const,
};

function MiniPie({ wins, losses, height = 80 }: { wins: number; losses: number; height?: number }) {
  const data = [
    { name: 'برد', value: wins, color: 'var(--profit)' },
    { name: 'باخت', value: losses, color: 'var(--loss)' },
  ];
  if (wins + losses === 0) {
    return <div className="text-xs text-[var(--text-secondary)] text-center py-4">داده نیست</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={22} outerRadius={34} paddingAngle={3}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.color} />
          ))}
        </Pie>
        <Tooltip contentStyle={MINI_TOOLTIP} formatter={(v: any, n: any) => [`${v} معامله`, n]} />
      </PieChart>
    </ResponsiveContainer>
  );
}

function MiniBars({ data, colors, height = 80, currency = 'USDT' }: { data: { label: string; value: number }[]; colors: string[]; height?: number; currency?: string }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 6, right: 6, left: 6, bottom: 0 }}>
        <XAxis dataKey="label" hide />
        <Tooltip contentStyle={MINI_TOOLTIP} formatter={(v: any) => [`${Number(v).toLocaleString()} ${currency} `, '']} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={colors[i % colors.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function DashboardPage({ onNavigate }: { onNavigate?: (page: string) => void }) {
  const loadIdRef = useRef(0);
  const backtestLoadIdRef = useRef(0);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  const [now, setNow] = useState(new Date());
  const [yesterday, setYesterday] = useState<any>(null);
  const [finance, setFinance] = useState<any>(null);
  const [realSummary, setRealSummary] = useState<any>(null);
  const [versions, setVersions] = useState<any[]>([]);
  const [backtestSummary, setBacktestSummary] = useState<any>(null);
  const [backtestLoading, setBacktestLoading] = useState(false);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(() => {
    const stored = Number(localStorage.getItem('mok_dashboard_version'));
    return Number.isInteger(stored) && stored > 0 ? stored : null;
  });

  // فیلتر بازه (localStorage)
  const [rangeKey, setRangeKey] = useState<RangeKey>(
    () => (localStorage.getItem('mok_dashboard_range') as RangeKey) || 'all',
  );
  const [customFrom, setCustomFrom] = useState<string>(() => localStorage.getItem('mok_dashboard_custom_from') || '');
  const [customTo, setCustomTo] = useState<string>(() => localStorage.getItem('mok_dashboard_custom_to') || '');

  // فاز ۴۴.۱ — دامنهٔ معاملات (واقعی/بک‌تست/فوروارد/همه)
  const [scope, setScope] = useState<TradeScope>(
    () => (localStorage.getItem('mok_dashboard_scope') as TradeScope) || 'real',
  );
  const [currency, setCurrency] = useState<CurrencyCode>(
    () => localStorage.getItem('mok_dashboard_currency') === 'IRR' ? 'IRR' : 'USDT',
  );

  // جدول‌های معاملات
  const [recentTrades, setRecentTrades] = useState<any[]>([]);

  const [refreshing, setRefreshing] = useState(false);

  const [alerts, setAlerts] = useState<any[]>([]);

  // ── گزارشهای فاز ۲۲ (بارگذاری تنبل / Lazy-Loading برای بهینه‌سازی سرعت و رم) ──
  const [spendable, setSpendable] = useState<any>(null);
  const [netProfit, setNetProfit] = useState<any>(null);
  const [assetTrend, setAssetTrend] = useState<any[]>([]);
  const financeLoadedRef = useRef(false);
  const [financeLoading, setFinanceLoading] = useState(false);

  // بارگذاری داده‌های مالی فقط در صورت نیاز (وقتی کاربر آکاردئون مالی را باز می‌کند)
  const loadFinanceData = useCallback(async () => {
    if (financeLoading) return;
    setFinanceLoading(true);
    try {
      const [sum, flow, accs, spendRes, npRes, trendRes] = await Promise.all([
        getFinanceSummary(),
        getFinanceCashflow({ currency }),
        getFinanceAccounts(),
        getSpendableAssets(),
        getNetProfit({ currency }),
        getAssetTrend(),
      ]);
      setFinance({ summary: sum.data, cashflow: flow.data, accounts: accs.data });
      setSpendable(spendRes.data);
      setNetProfit(npRes.data);
      setAssetTrend(trendRes.data.trend || []);
      financeLoadedRef.current = true;
    } catch {
      // غیربحرانی — عدم توقف داشبورد در صورت بروز خطای ماژول مالی
    } finally {
      setFinanceLoading(false);
    }
  }, [currency, financeLoading]);

  // بارگذاری نسخه‌های استراتژی برای خلاصهٔ Backtest
  useEffect(() => {
    let cancelled = false;
    getAllVersions()
      .then((res) => { if (!cancelled) setVersions(res.data || []); })
      .catch(() => { if (!cancelled) setVersions([]); });
    return () => { cancelled = true; };
  }, []);

  const loadDashboard = useCallback(
    async (showToast = false) => {
      const myId = ++loadIdRef.current;
      const r = computeRange(rangeKey, customFrom, customTo);
      setRefreshing(true);
      try {
        const [dash, yest, realSum, closed, alertsRes] = await Promise.all([
          getDashboardData({ date_from: r.from, date_to: r.to, scope, currency }),
          getYesterdayData({ scope, currency }),
          getRealSummary({ currency, date_from: r.from, date_to: r.to }),
          getTrades({ status: 'closed', limit: 10, sort_by: 'close_time', sort_order: 'desc', currency,
            date_from: r.from, date_to: r.to, scope, date_field: 'close_time' }),

          getPropAlerts({ unread_only: true }),
        ]);
        if (myId !== loadIdRef.current) return;
        setData(dash.data);
        setYesterday(yest.data);
        setRealSummary(realSum.data);
        setRecentTrades(closed.data.trades || []);

        setAlerts(alertsRes.data);
        setError(null);
        if (showToast) toast.success('داشبورد به‌روزرسانی شد');

        // اگر آکاردئون مالی قبلاً باز شده باشد، آن را هم به‌روز می‌کنیم
        if (financeLoadedRef.current) {
          loadFinanceData();
        }
      } catch (err: any) {
        if (myId !== loadIdRef.current) return;
        const msg = err?.response?.data?.detail || 'خطا در بارگذاری داشبورد';
        setError(msg);
        toast.error(msg);
      } finally {
        if (myId === loadIdRef.current) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    },
    [rangeKey, customFrom, customTo, scope, currency, toast, loadFinanceData],
  );

  useEffect(() => {
    loadDashboard();
    return () => { ++loadIdRef.current; };
  }, [loadDashboard]);

  useEffect(() => {
    const myId = ++backtestLoadIdRef.current;
    if (versions.length === 0) {
      setBacktestSummary(null);
      setBacktestLoading(false);
      return;
    }

    const selected = versions.find((version) => version.id === selectedVersionId);
    if (!selected) {
      const mostRecent = [...versions].sort((a, b) =>
        new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime() || b.id - a.id,
      )[0];
      setSelectedVersionId(mostRecent.id);
      return;
    }

    localStorage.setItem('mok_dashboard_version', String(selected.id));
    setBacktestLoading(true);
    getDashboardData({ scope: 'backtest', currency: 'USDT', version_id: selected.id })
      .then((res) => { if (myId === backtestLoadIdRef.current) setBacktestSummary(res.data); })
      .catch(() => { if (myId === backtestLoadIdRef.current) setBacktestSummary(null); })
      .finally(() => { if (myId === backtestLoadIdRef.current) setBacktestLoading(false); });

    return () => { ++backtestLoadIdRef.current; };
  }, [versions, selectedVersionId]);

  // ذخیرهٔ فیلتر در localStorage
  useEffect(() => {
    localStorage.setItem('mok_dashboard_range', rangeKey);
    localStorage.setItem('mok_dashboard_custom_from', customFrom);
    localStorage.setItem('mok_dashboard_custom_to', customTo);
    localStorage.setItem('mok_dashboard_scope', scope);
    localStorage.setItem('mok_dashboard_currency', currency);
  }, [rangeKey, customFrom, customTo, scope, currency]);

  // ساعت زنده (به‌روزرسانی هر ۱ دقیقه برای حذف بار پردازشی و ثانیه‌شمار)
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  if (loading) {
    return <DashboardSkeleton />;
  }

  if (error && !data) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-[var(--loss)] text-lg">❌ {error}</div>
      </div>
    );
  }

  if (!data) return null;

  const { summary, today, equity_curve, pnl_distribution, win_loss, periods, prop_progress } = data;
  const currencyProfit = netProfit?.by_currency?.[currency] || netProfit;

  const [jy, jm, jd] = gregorianToJalali(now.getFullYear(), now.getMonth() + 1, now.getDate());
  const jalaliDate = `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')}`;
  const weekday = JALALI_WEEKDAYS[now.getDay()];
  const clock = now.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' });
  const greeting = getGreeting(now.getHours());

  const handleNewTrade = () => {
    onNavigate?.('trades');
    window.dispatchEvent(new CustomEvent('mok-new-trade'));
    toast.info('فرم ثبت معامله جدید باز شد');
  };

  const handleExportPdf = async () => {
    try {
      const r = computeRange(rangeKey, customFrom, customTo);
      const res = await exportDashboardPdf({
        date_from: r.from, date_to: r.to, scope, currency,
        version_id: scope === 'backtest' ? selectedVersionId ?? undefined : undefined,
      });
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `dashboard_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(a); a.click();
      window.URL.revokeObjectURL(url); a.remove();
      toast.success('گزارش PDF دانلود شد');
    } catch {
      toast.error('خطا در دانلود گزارش PDF');
    }
  };

  const quickBtn =
    'dashboard-action dashboard-action-icon';

  const renderRangeFilter = (filter: typeof RANGE_FILTERS[number]) => (
    <button type="button" key={filter.key} onClick={(event) => { setRangeKey(filter.key); event.currentTarget.closest('details')?.removeAttribute('open'); }} className="dashboard-filter-button" aria-pressed={rangeKey === filter.key}>
      {filter.label}
    </button>
  );

  return (
    <div className="dashboard-root">
      <ErrorBoundary label="Dashboard header and filters">
      <div className="dashboard-toolbar">
      {/* هدر */}
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-greeting">سلام، {greeting} 👋</h1>
          <div className="dashboard-header-meta">
            <div className="dashboard-datetime">
              <span><CalendarDays size={14} aria-hidden="true" /> {weekday}، {jalaliDate}</span>
              <span className="tabular-nums"><Clock size={14} aria-hidden="true" /><bdi>{clock}</bdi></span>
            </div>
            <MarketSessionWidget />
          </div>
        </div>
        <div className="dashboard-actions">
          <InfoTooltip content="به‌روزرسانی داشبورد">
            <button onClick={() => loadDashboard(true)} disabled={refreshing} className={quickBtn} aria-label="به‌روزرسانی">
              <RefreshCw size={17} aria-hidden="true" className={refreshing ? 'animate-spin' : ''} />
            </button>
          </InfoTooltip>
          <button
            onClick={handleExportPdf}
            className="dashboard-action"
          >
            <FileText size={16} aria-hidden="true" /> گزارش PDF
          </button>
        </div>
      </div>

      {/* فیلتر بازه زمانی (فاز ۱۴.۳) */}
      <div className="dashboard-filters">
        <div className="dashboard-filter-group" role="group" aria-label="بازه زمانی">
          <span className="dashboard-filter-label">بازه زمانی</span>
          {RANGE_FILTERS.filter(filter => ['today', 'week', 'month', 'all'].includes(filter.key)).map(renderRangeFilter)}
          <details className="dashboard-filter-more">
            <summary className={['yesterday', 'quarter', 'year', 'custom'].includes(rangeKey) ? 'is-active' : undefined}>{['yesterday', 'quarter', 'year', 'custom'].includes(rangeKey) ? RANGE_FILTERS.find(filter => filter.key === rangeKey)?.label : 'بازه‌های بیشتر'}<ChevronDown size={13} aria-hidden="true" /></summary>
            <div>{RANGE_FILTERS.filter(filter => ['yesterday', 'quarter', 'year', 'custom'].includes(filter.key)).map(renderRangeFilter)}</div>
          </details>
        </div>
        {/* فاز ۴۴.۱: انتخاب دامنه (واقعی/بک‌تست/فوروارد/همه) */}
        <div className="dashboard-filter-group" role="group" aria-label="نوع معامله">
          <span className="dashboard-filter-label">نوع معامله</span>
          {SCOPE_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setScope(f.key)}
              className="dashboard-filter-button"
              aria-pressed={scope === f.key}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="dashboard-filter-group" role="group" aria-label="ارز">
          <span className="dashboard-filter-label">ارز</span>
          {(['USDT', 'IRR'] as CurrencyCode[]).map((value) => (
            <button
              key={value}
              onClick={() => setCurrency(value)}
              className="dashboard-filter-button"
              aria-pressed={currency === value}
            >
              {value}
            </button>
          ))}
        </div>
        {rangeKey === 'custom' && (
          <div className="dashboard-custom-range grid grid-cols-1 md:grid-cols-2 gap-3 pt-3 border-t border-[var(--border-subtle)]">
            <PersianDateInput label="از تاریخ" value={customFrom} onChange={setCustomFrom} />
            <PersianDateInput label="تا تاریخ" value={customTo} onChange={setCustomTo} />
          </div>
        )}
      </div>
      </div>

      <p className="dashboard-filter-note">شاخص‌های اصلی، منحنی سرمایه و آخرین معاملات تابع فیلترها هستند؛ عملکرد پول واقعی از بازه و ارز، و بک‌تست از نسخهٔ انتخاب‌شده استفاده می‌کند.</p>

      {/* ۵ KPI اصلی با متریک‌های کوانت و امید ریاضی */}
      {data && (
        <div className="dashboard-kpis">
          <KpiCard
            index={0}
            icon={<Wallet size={17} aria-hidden="true" />}
            label="سود و زیان خالص"
            value={<span dir="ltr" className="inline-block dir-ltr">{`${data.summary?.net_pnl >= 0 ? '+' : ''}${data.summary?.net_pnl?.toLocaleString() || 0} ${currency}`}</span>}
            valueColor="profit"
            subtitle={data.summary?.expectancy != null ? <span>امید ریاضی: <span dir="ltr" className="inline-block dir-ltr">{Number(data.summary.expectancy) >= 0 ? '+' : ''}{Number(data.summary.expectancy).toFixed(2)} {currency}</span></span> : undefined}
          />
          <KpiCard
            index={1}
            icon={<Target size={17} aria-hidden="true" />}
            label="نرخ برد"
            value={`${data.summary?.win_rate?.toFixed(1) || 0}%`}
            valueColor="accent"
            subtitle={`${data.summary?.wins ?? data.win_loss?.wins ?? data.summary?.winning_trades ?? 0}W / ${data.summary?.losses ?? data.win_loss?.losses ?? data.summary?.losing_trades ?? 0}L`}
          />
          <KpiCard
            index={2}
            icon={<Scale size={17} aria-hidden="true" />}
            label="فاکتور سود"
            value={
              data.summary?.profit_factor_status === 'no_data'
                ? '—'
                : data.summary?.profit_factor_status === 'no_losses'
                  ? 'بدون زیان'
                  : data.summary?.profit_factor?.toFixed(2) || '—'
            }
            valueColor="purple"
            hint={data.summary?.profit_factor_status}
            subtitle={data.summary?.avg_r_multiple != null ? <span>میانگین R: <span dir="ltr" className="inline-block dir-ltr">{Number(data.summary.avg_r_multiple) >= 0 ? '+' : ''}{Number(data.summary.avg_r_multiple).toFixed(2)} R</span></span> : undefined}
          />
          <KpiCard
            index={3}
            icon={<TrendingDown size={17} aria-hidden="true" />}
            label="افت سرمایه"
            value={`${data.summary?.max_dd?.toLocaleString() || 0} ${currency}`}
            valueColor="loss"
            hint={data.equity_metadata?.dd_definition || 'peak_to_trough'}
            subtitle={data.summary?.largest_loss ? <span>بزرگترین ضرر: <span dir="ltr" className="inline-block dir-ltr">-{Number(data.summary.largest_loss).toFixed(2)} {currency}</span></span> : undefined}
          />
          <KpiCard
            index={4}
            icon={<ClipboardList size={17} aria-hidden="true" />}
            label="معاملات بسته"
            value={data.summary?.closed_trades || 0}
            valueColor="warning"
            subtitle={data.summary?.breakeven_trades ? `${data.summary.breakeven_trades} سر‌به‌سر` : (data.summary?.total_trades ? `${data.summary.total_trades} کل ثبت‌شده` : undefined)}
          />
        </div>
      )}

      </ErrorBoundary>

      <div className="dashboard-overview" data-testid="dashboard-overview">
        <ErrorBoundary label="منحنی سرمایه"><Card>
          <CardHeader title="📉 منحنی سرمایه" subtitle={`${(equity_curve || []).length} روز`} />
          <EquityCurveChart data={equity_curve || []} height={240} currency={currency} />
        </Card></ErrorBoundary>
        <ErrorBoundary label="Today">
      {/* کارت وضعیت امروز (فاز ۱۴.۲ — بالای همه) */}
      <div className="dashboard-card dashboard-today relative p-5 overflow-hidden">
        <div
          className="absolute top-0 right-0 left-0 h-1"
          style={{ background: 'linear-gradient(90deg, var(--accent), var(--purple), var(--profit))' }}
        />
        <div
          className="absolute -top-24 -left-24 w-[300px] h-[300px] rounded-full pointer-events-none"
          style={{ background: 'radial-gradient(circle, rgba(63,124,255,0.08) 0%, transparent 70%)' }}
        />

        <div className="relative z-10">
          <div className="dashboard-card-header">
            <div className="dashboard-card-icon" style={{ background: 'rgba(63,124,255,0.10)' }}>
              <span style={{ color: 'var(--accent)' }}>📅</span>
            </div>
            <div>
              <h3 className="text-[13px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                وضعیت امروز
              </h3>
            </div>
          </div>
          <div
            className={`text-4xl font-extrabold ${today.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}
          >
            <span dir="ltr" className="inline-block dir-ltr">
              {today.pnl >= 0 ? '+' : ''}{today.pnl} {currency}
            </span>
          </div>
          <div className="flex items-center gap-4 mt-3 flex-wrap">
            <div className="text-sm text-[var(--text-secondary)]">
              <span className="font-bold">{today.trades_count}</span> معامله
            </div>
            <div className="text-sm text-[var(--text-secondary)]">
              نرخ برد امروز: <span className="font-bold">{today.win_rate.toFixed(1)}٪</span>
            </div>
            <div className="text-sm text-[var(--text-secondary)]">
              <span className="font-bold">{summary.closed_trades ?? today.trades_count}</span> معامله بسته
            </div>
            <div className="text-sm text-[var(--text-secondary)]">
              <span className="font-bold">{summary.total_trades}</span> کل معاملات
            </div>
          </div>
        </div>

        <div className="dashboard-periods relative z-10">
          <div className="text-center bg-[var(--bg-card-translucent)] backdrop-blur rounded-[16px] px-5 py-3 border border-[var(--border-subtle)] min-w-0">
            <div className="text-xs text-[var(--text-secondary)] font-bold">این ماه</div>
            <div className={`text-lg font-extrabold ${periods.month.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
              <span dir="ltr" className="inline-block dir-ltr">{periods.month.pnl >= 0 ? '+' : ''}{periods.month.pnl} {currency}</span>
            </div>
          </div>
          <div className="text-center bg-[var(--bg-card-translucent)] backdrop-blur rounded-[16px] px-5 py-3 border border-[var(--border-subtle)] min-w-0">
            <div className="text-xs text-[var(--text-secondary)] font-bold">این فصل</div>
            <div className={`text-lg font-extrabold ${periods.quarter.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
              <span dir="ltr" className="inline-block dir-ltr">{periods.quarter.pnl >= 0 ? '+' : ''}{periods.quarter.pnl} {currency}</span>
            </div>
          </div>
          <div className="text-center bg-[var(--bg-card-translucent)] backdrop-blur rounded-[16px] px-5 py-3 border border-[var(--border-subtle)] min-w-0">
            <div className="text-xs text-[var(--text-secondary)] font-bold">امسال</div>
            <div className={`text-lg font-extrabold ${periods.year.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
              <span dir="ltr" className="inline-block dir-ltr">{periods.year.pnl >= 0 ? '+' : ''}{periods.year.pnl} {currency}</span>
            </div>
          </div>
        </div>
      </div>

      </ErrorBoundary>
      </div>

      <div className="dashboard-pair" data-testid="prop-backtest-pair">
        <ErrorBoundary label="Active Prop Stage"><div className="dashboard-card dashboard-prop p-5">
          <div className="dashboard-card-header">
            <div className="dashboard-card-icon" style={{ background: 'rgba(63,124,255,0.10)' }}>
              <span style={{ color: 'var(--accent)' }}>🏢</span>
            </div>
            <div>
              <h3 className="text-[13px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>وضعیت پراپ</h3>
              {prop_progress.length > 0 && <div className="text-[11px] text-[var(--text-muted)] mt-0.5">{prop_progress.length} مرحله فعال</div>}
            </div>
          </div>
          {prop_progress.length === 0 ? (
            <div className="text-center">
              <EmptyState icon="🏢" title="مرحله فعالی وجود ندارد" />
              <button
                type="button"
                onClick={() => onNavigate?.('prop')}
                className="text-xs font-bold text-[var(--accent)] hover:text-[var(--accent-strong)] transition-colors"
              >
                به صفحه پراپ بروید ←
              </button>
            </div>
          ) : (
            <div className="space-y-5">
              {prop_progress.map((stage: any) => {
                const dailyDdPercent = stage.max_daily_dd_limit > 0
                  ? (stage.max_daily_loss / stage.max_daily_dd_limit) * 100
                  : 0;
                const totalDdPercent = stage.max_total_dd_limit > 0
                  ? (stage.max_total_dd / stage.max_total_dd_limit) * 100
                  : 0;
                const stageLabel = stage.stage_type === 'stage_1' ? 'مرحله ۱'
                  : stage.stage_type === 'stage_2' ? 'مرحله ۲'
                    : stage.stage_type === 'funded_real' ? 'فاندد' : stage.stage_type;
                const violations = stage.violations || [];
                return (
                  <div
                    key={stage.stage_id}
                    className={`rounded-[14px] border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-4 ${violations.length > 0 ? 'border-l-2 border-[var(--loss)] pl-3' : ''}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-bold text-[var(--text-primary)]">{stage.account_label || 'حساب پراپ'}</span>
                          <Badge variant={stage.ready_to_pass ? 'success' : violations.length > 0 ? 'danger' : 'info'}>
                            {`${stage.stage_type_icon || (stage.stage_type === 'stage_1' ? '🥇' : stage.stage_type === 'stage_2' ? '🥈' : '💰')} ${stageLabel}`}
                          </Badge>
                        </div>
                        {stage.firm_name && (
                          <div className="text-xs text-[var(--text-secondary)] mt-1">
                            {stage.stage_type_icon || '🏢'} {stage.firm_name}
                          </div>
                        )}
                      </div>
                      {stage.ready_to_pass && <Badge variant="success">آماده پاس شدن</Badge>}
                    </div>

                    <div className="text-right mt-4">
                      <div className="text-xl font-extrabold text-[var(--text-primary)]">
                        سود فعلی: {Number(stage.current_profit || 0).toLocaleString('en-US')} {currency}
                      </div>
                      {stage.stage_type === 'funded_real' ? (
                        <div className="text-xs text-[var(--profit)] mt-1 font-semibold">
                          حساب فعال فاندد (بدون محدودیت تارگت سود)
                        </div>
                      ) : (
                        <div className="text-xs text-[var(--text-secondary)] mt-1">
                          هدف: {Number(stage.profit_target || 0).toLocaleString('en-US')} {currency} · {Number(stage.profit_progress_percent || 0).toFixed(1)}٪
                        </div>
                      )}
                    </div>

                    {stage.stage_type !== 'funded_real' && (
                      <div className="mt-3">
                        <ProgressBar value={Math.min(Math.max(stage.profit_progress_percent || 0, 0), 100)} variant="profit" />
                      </div>
                    )}
                    <div className="text-xs text-[var(--text-secondary)] mt-2">
                      {stage.trading_days || 0} / {stage.min_trading_days || 0} روز
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-3">
                      <div className={`rounded-[10px] bg-[var(--bg-card)] px-3 py-2 text-xs ${dailyDdPercent > 50 ? 'text-[var(--warning)]' : 'text-[var(--text-secondary)]'}`}>
                        DD روزانه: {Number(stage.max_daily_loss || 0).toFixed(2)} / {Number(stage.max_daily_dd_limit || 0).toLocaleString('en-US')} {currency}
                      </div>
                      <div className={`rounded-[10px] bg-[var(--bg-card)] px-3 py-2 text-xs ${totalDdPercent > 50 ? 'text-[var(--warning)]' : 'text-[var(--text-secondary)]'}`}>
                        DD کل: {Number(stage.max_total_dd || 0).toFixed(2)} / {Number(stage.max_total_dd_limit || 0).toLocaleString('en-US')} {currency}
                      </div>
                    </div>

                    {violations.length > 0 && (
                      <div className="mt-3 text-xs text-[var(--loss)] font-semibold">
                        ⚠️ {violations[0]}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div></ErrorBoundary>
        <ErrorBoundary label="عملکرد بک‌تست">
        <div className="dashboard-card dashboard-backtest p-5">
          <div className="dashboard-card-header">
            <div className="dashboard-card-icon" style={{ background: 'rgba(63,124,255,0.10)' }}>
              <span style={{ color: 'var(--accent)' }}>📊</span>
            </div>
            <div className="flex items-center justify-between gap-3 flex-1">
              <h3 className="text-[13px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>عملکرد بک‌تست</h3>
              <select
                value={selectedVersionId ?? ''}
                onChange={(event) => setSelectedVersionId(Number(event.target.value) || null)}
                className="max-w-[220px] bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)]"
                aria-label="انتخاب نسخه برای عملکرد بک‌تست"
              >
                {versions.length === 0 && <option value="">نسخه‌ای موجود نیست</option>}
                {versions.map((version) => (
                  <option key={version.id} value={version.id}>
                    {version.strategy_name} — {version.version_name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {versions.length === 0 ? (
            <EmptyState icon="📊" title="نسخه‌ای برای بک‌تست وجود ندارد" />
          ) : backtestLoading ? (
            <div className="text-sm text-[var(--text-muted)] py-5 text-center">در حال بارگذاری عملکرد بک‌تست…</div>
          ) : backtestSummary ? (
            <>
              <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
                <StatCard
                  icon={<Wallet size={17} aria-hidden="true" />}
                  label="سود خالص بک‌تست"
                  value={`${Number(backtestSummary.summary?.net_pnl || 0).toLocaleString('en-US')} USDT`}
                  color={(backtestSummary.summary?.net_pnl || 0) >= 0 ? 'profit' : 'loss'}
                  sparkData={backtestSummary.sparkline || [0]}
                />
                <StatCard
                  icon={<TrendingUp size={17} aria-hidden="true" />}
                  label="نرخ برد"
                  value={`${Number(backtestSummary.summary?.win_rate || 0).toFixed(1)}٪`}
                  color="accent"
                  sparkData={[0]}
                />
                <StatCard
                  icon={<Trophy size={17} aria-hidden="true" />}
                  label="Profit Factor"
                  value={
                    backtestSummary.summary?.profit_factor_status === 'no_data'
                      ? '—'
                      : backtestSummary.summary?.profit_factor_status === 'no_losses' || Number(backtestSummary.summary?.profit_factor || 0) >= 999
                        ? 'بدون زیان'
                        : Number(backtestSummary.summary?.profit_factor || 0).toFixed(2)
                  }
                  color="purple"
                  sparkData={[0]}
                />
                <StatCard
                  icon={<TrendingDown size={17} aria-hidden="true" />}
                  label="افت سرمایه بک‌تست"
                  value={`${Number(backtestSummary.summary?.max_dd || 0).toLocaleString('en-US')} USDT`}
                  color="loss"
                  sparkData={[0]}
                />
              </div>
              <div className="flex flex-wrap items-center justify-between gap-3 mt-4">
                <span className="text-xs text-[var(--text-secondary)]">
                  {Number(backtestSummary.summary?.closed_trades || 0)} معامله · R-Multiple: {backtestSummary.summary?.avg_r_multiple == null ? '—' : Number(backtestSummary.summary.avg_r_multiple).toFixed(2)}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    if (selectedVersionId !== null) {
                      localStorage.setItem('analysis_selected_version', String(selectedVersionId));
                      onNavigate?.('analysis');
                    }
                  }}
                  className="text-xs font-bold text-[var(--accent)] hover:text-[var(--accent-strong)] transition-colors"
                >
                  برو به تحلیل کامل ←
                </button>
              </div>
            </>
          ) : (
            <EmptyState icon="📊" title="دادهٔ بک‌تستی برای نسخهٔ انتخاب‌شده موجود نیست" />
          )}
        </div>
      </ErrorBoundary>
      </div>
      <ErrorBoundary label="هشدارهای پراپ">{alerts.length > 0 && (
        <Card>
          <CardHeader title="🔔 هشدارهای پراپ" subtitle={`${alerts.length} هشدار فعال`} />
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {alerts.map((alert) => {
              const isDanger = alert.message.includes('🚨');
              const isWarning = alert.message.includes('⚠️');
              const bgColor = isDanger ? 'bg-[var(--loss-soft)] border-[var(--loss-border)]' : isWarning ? 'bg-[var(--warning-soft-alt)] border-[var(--warning-border)]' : 'bg-[var(--profit-soft)] border-[var(--profit-border)]';
              return (
                <div key={alert.id} className={`${bgColor} border rounded-[12px] px-4 py-3 flex items-center justify-between`}>
                  <span className={`text-[12px] font-medium ${isDanger ? 'text-[var(--loss)]' : isWarning ? 'text-[var(--warning)]' : 'text-[var(--profit)]'}`}>
                    {alert.message}
                  </span>
                  <button
                    onClick={async () => { try { await markAlertRead(alert.id); setAlerts(alerts.filter(a => a.id !== alert.id)); } catch {} }}
                    className="text-xs bg-[var(--bg-card)] px-3 py-1 rounded-full font-bold text-[var(--accent)] hover:bg-[var(--accent-soft)] transition-all"
                  >
                    ✓ خواندم
                  </button>
                </div>
              );
            })}
          </div>
        </Card>
      )}</ErrorBoundary>

      <section aria-labelledby="real-performance-title" data-testid="real-performance-section">
        <div className="dashboard-section-heading"><h2 id="real-performance-title">عملکرد پول واقعی</h2><p>مرحله ۳ پراپ + بروکر شخصی</p></div>
        <ErrorBoundary label="کارت‌های آماری">
      {(!realSummary || (realSummary.total_trades ?? 0) === 0) ? (
        <Card className="[&>div]:!py-6 [&>div>div:first-child]:!text-[40px] [&>div>div:first-child]:!mb-2">
          <EmptyState
            icon="📊"
            title="هنوز معاملات پول واقعی ندارید"
            description="معاملات مرحله ۳ پراپ یا بروکر شخصی شما اینجا نمایش داده می‌شوند."
          />
          <button
            type="button"
            onClick={() => onNavigate?.('prop')}
            className="mt-2 text-xs text-[var(--accent)] hover:text-[var(--accent-strong)] transition-colors"
          >
            برای مشاهده معاملات پول واقعی، به صفحه پراپ یا بروکر شخصی مراجعه کنید.
          </button>
        </Card>
      ) : (
      <>

      <div className="dashboard-real-stats grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
        <StatCard
          icon={<Wallet size={17} aria-hidden="true" />}
          label="سود خالص"
          value={<span dir="ltr" className="inline-block dir-ltr">{`${realSummary.net_pnl >= 0 ? '+' : ''}${realSummary.net_pnl} ${currency}`}</span>}
          change={`${realSummary.winning_trades}W / ${realSummary.losing_trades}L`}
          changeType={realSummary.net_pnl >= 0 ? 'up' : 'down'}
          color="profit"
          sparkData={realSummary.sparkline && realSummary.sparkline.length > 0 ? realSummary.sparkline : [0]}
        />
        <StatCard
          icon={<TrendingUp size={17} aria-hidden="true" />}
          label="نرخ برد"
          value={`${realSummary.win_rate.toFixed(1)}٪`}
          change={`${realSummary.winning_trades}W / ${realSummary.losing_trades}L`}
          changeType="neutral"
          color="accent"
          chart={<MiniPie wins={realSummary.winning_trades ?? 0} losses={realSummary.losing_trades ?? 0} />}
        />
        <StatCard
          icon={<Trophy size={17} aria-hidden="true" />}
          label="فاکتور سود"
          value={realSummary.profit_factor >= 999 ? '∞' : realSummary.profit_factor.toFixed(2)}
          change="—"
          changeType="neutral"
          color="purple"
          chart={<MiniBars
            data={[
              { label: 'سود ناخالص', value: realSummary.gross_profit ?? 0 },
              { label: 'زیان ناخالص', value: realSummary.gross_loss ?? 0 },
            ]}
            colors={['var(--profit)', 'var(--loss)']}
            currency={currency}
          />}
        />
        <StatCard
          icon={<TriangleAlert size={17} aria-hidden="true" />}
          label="حداکثر ضرر"
          value={`-${realSummary.max_dd} ${currency} `}
          change="—"
          changeType="neutral"
          color="loss"
          chart={<MiniBars
            data={[
              { label: 'مجموع زیان', value: realSummary.gross_loss ?? 0 },
              { label: 'حداکثر افت', value: realSummary.max_dd ?? 0 },
            ]}
            colors={['var(--loss)', 'var(--loss-border)']}
            currency={currency}
          />}
        />
      </div>
      </>
      )}
      </ErrorBoundary>
      </section>

      <details className="dashboard-detail" data-testid="dashboard-analysis-details">
        <summary>تحلیل تکمیلی <span className="text-xs font-normal text-[var(--text-secondary)]">برد و باخت، توزیع سود و زیان و اهداف</span></summary>
        <div className="dashboard-detail-body">
          <ErrorBoundary label="نمودارها"><div className="grid grid-cols-1 lg:grid-cols-2 gap-5"><Card>
          <CardHeader
            title="🥧 برد / باخت"
            subtitle={win_loss ? `${(win_loss.wins || 0) + (win_loss.losses || 0)} معامله بسته` : undefined}
          />
          <WinLossPieChart wins={win_loss?.wins ?? 0} losses={win_loss?.losses ?? 0} height={240} />
        </Card><Card>
          <CardHeader title="📊 توزیع سود/زیان" subtitle="تعداد معاملات در هر بازه" />
          <PnLDistributionChart data={pnl_distribution || []} height={240} />
        </Card></div></ErrorBoundary>
          <ErrorBoundary label="Prop goals">
        {/* پیشرفت اهداف (ماهانه/فصلی/سالانه) */}
        <Card>
          <CardHeader title="🎯 پیشرفت اهداف" subtitle="عملکرد واقعی بر اساس PnL" />
          <div className="space-y-6">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-xs text-[var(--text-secondary)]">عملکرد ماه جاری</span>
                <span className={`text-xs font-bold ${periods.month.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                  <span dir="ltr" className="inline-block dir-ltr">{periods.month.pnl >= 0 ? '+' : ''}{periods.month.pnl} {currency}</span>
                </span>
              </div>
              <ProgressBar
                value={Math.min(Math.abs(periods.month.change_percent), 100)}
                variant={periods.month.pnl >= 0 ? 'profit' : 'loss'}
              />
              <div className="flex justify-between mt-1.5">
                <span className="text-xs text-[var(--text-secondary)]">نسبت به ماه قبل</span>
                <span className={`text-xs font-bold ${periods.month.change_percent > 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                  {periods.month.change_percent > 0 ? '+' : ''}{periods.month.change_percent}٪
                </span>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="text-xs text-[var(--text-secondary)]">عملکرد فصل جاری</span>
                <span className={`text-xs font-bold ${periods.quarter.pnl >= 0 ? 'text-[var(--accent)]' : 'text-[var(--loss)]'}`}>
                  <span dir="ltr" className="inline-block dir-ltr">{periods.quarter.pnl >= 0 ? '+' : ''}{periods.quarter.pnl} {currency}</span>
                </span>
              </div>
              <ProgressBar
                value={periods.quarter.pnl !== 0 ? Math.min(Math.max((Math.abs(periods.quarter.pnl) / (Math.abs(data.summary?.net_pnl) || Math.abs(periods.quarter.pnl) || 1)) * 100, 15), 100) : 0}
                variant={periods.quarter.pnl >= 0 ? 'accent' : 'loss'}
              />
              <div className="flex justify-between mt-1.5">
                <span className="text-xs text-[var(--text-secondary)]">وضعیت فصل</span>
                <span className={`text-xs font-bold ${periods.quarter.pnl >= 0 ? 'text-[var(--accent)]' : 'text-[var(--loss)]'}`}>
                  {periods.quarter.pnl >= 0 ? 'سودده 🟢' : 'زیان‌ده 🔴'}
                </span>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="text-xs text-[var(--text-secondary)]">عملکرد سال جاری</span>
                <span className={`text-xs font-bold ${periods.year.pnl >= 0 ? 'text-[var(--warning)]' : 'text-[var(--loss)]'}`}>
                  <span dir="ltr" className="inline-block dir-ltr">{periods.year.pnl >= 0 ? '+' : ''}{periods.year.pnl} {currency}</span>
                </span>
              </div>
              <ProgressBar
                value={periods.year.pnl !== 0 ? Math.min(Math.max((Math.abs(periods.year.pnl) / (Math.abs(data.summary?.net_pnl) || Math.abs(periods.year.pnl) || 1)) * 100, 15), 100) : 0}
                variant={periods.year.pnl >= 0 ? 'warning' : 'loss'}
              />
              <div className="flex justify-between mt-1.5">
                <span className="text-xs text-[var(--text-secondary)]">وضعیت سالانه</span>
                <span className={`text-xs font-bold ${periods.year.pnl >= 0 ? 'text-[var(--warning)]' : 'text-[var(--loss)]'}`}>
                  {periods.year.pnl >= 0 ? 'سودده 🟢' : 'زیان‌ده 🔴'}
                </span>
              </div>
            </div>
          </div>
        </Card>
      </ErrorBoundary>
          <details className="dashboard-detail"><summary>مقایسه با روز گذشته</summary><div className="dashboard-detail-body"><ErrorBoundary label="Yesterday">
      {/* کارت روز گذشته (فاز ۱۴.۲) */}
      <div className="dashboard-card p-5">
        <div className="dashboard-card-header">
          <div className="dashboard-card-icon" style={{ background: 'rgba(63,124,255,0.10)' }}>
            <span style={{ color: 'var(--accent)' }}>🌙</span>
          </div>
          <div>
            <h3 className="text-[13px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
              {`روز گذشته${yesterday ? ` — ${yesterday.day_of_week} ${yesterday.date}` : ''}`}
            </h3>
            {yesterday && <div className="text-[11px] text-[var(--text-muted)] mt-0.5">{yesterday.total_trades} معامله</div>}
          </div>
        </div>
        {yesterday ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-secondary)]">سود / زیان</span>
                <span className={`text-xl font-extrabold ${yesterday.net_pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                  {yesterday.net_pnl >= 0 ? '+' : ''}{yesterday.net_pnl} {currency}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-[var(--text-secondary)]">Win Rate</span>
                <span className="font-bold text-[var(--text-primary)]">{yesterday.win_rate.toFixed(1)}٪</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-[var(--text-secondary)]">برد / باخت</span>
                <span className="font-bold">
                  <span className="text-[var(--profit)]">{yesterday.winning_trades}</span>
                  {' / '}
                  <span className="text-[var(--loss)]">{yesterday.losing_trades}</span>
                </span>
              </div>
              <div className="flex flex-wrap gap-2 pt-1">
                {(['prop', 'personal', 'simulation'] as const).map((k) => (
                  <span
                    key={k}
                    className="text-xs px-2.5 py-1 rounded-full bg-[var(--bg-base)] border border-[var(--border-subtle)] text-[var(--text-secondary)]"
                  >
                    {k === 'prop' ? '🏢 پراپ' : k === 'personal' ? '👤 شخصی' : '🧪 شبیه‌سازی'}: {yesterday.by_source?.[k]?.trades ?? 0}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <MiniBars
                data={[
                  { label: 'پراپ', value: Math.abs(yesterday.by_source?.prop?.pnl ?? 0) },
                  { label: 'شخصی', value: Math.abs(yesterday.by_source?.personal?.pnl ?? 0) },
                  { label: 'شبیه‌سازی', value: Math.abs(yesterday.by_source?.simulation?.pnl ?? 0) },
                ]}
                colors={['var(--accent)', 'var(--purple)', 'var(--profit)']}
                height={120}
                currency={currency}
              />
              <div className="text-xs text-[var(--text-secondary)] text-center mt-1">تفکیک بر اساس منبع (قدرمطلق سود/زیان)</div>
            </div>
          </div>
        ) : (
          <div className="text-[var(--text-muted)] text-center py-6 text-sm">داده‌ای برای روز گذشته نیست</div>
        )}
      </div>

      </ErrorBoundary></div></details>
        </div>
      </details>
      <details
        className="dashboard-detail"
        data-testid="dashboard-finance-details"
        onToggle={(e) => {
          if (e.currentTarget.open && !financeLoadedRef.current) {
            loadFinanceData();
          }
        }}
      >
        <summary>جزئیات مالی <span className="text-xs font-normal text-[var(--text-secondary)]">موجودی، جریان نقدی و دارایی شخصی</span></summary>
        <div className="dashboard-detail-body"><ErrorBoundary label="Finance"><div><div className="space-y-4">
          <div className="text-sm font-bold text-[var(--text-secondary)] pb-2 border-b border-[var(--border-subtle)] mt-5">وضعیت حال</div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Card>
          <CardHeader title="💰 موجودی کل" />
          {finance?.summary ? (
            <div>
              <div className="text-2xl font-extrabold text-[var(--text-primary)]">
                {Number(finance.summary.assets_by_currency?.[currency] || 0).toLocaleString()} {currency}
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1">
                {Object.entries(finance.summary.assets_by_currency || {})
                  .map(([c, v]: any) => `${Number(v).toLocaleString()} ${c}`)
                  .join(' | ')}
              </div>
            </div>
          ) : (
            <div className="text-[var(--text-muted)] text-sm py-4">در حال بارگذاری...</div>
          )}
        </Card>
        <Card>
          <CardHeader title="💵 جریان نقدی" subtitle={`۶ ماه اخیر · ${currency}`} />
          {finance?.cashflow?.length ? (
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={finance.cashflow.slice(-6)}>
                <XAxis dataKey="month" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} stroke="var(--text-secondary)" />
                <Tooltip contentStyle={MINI_TOOLTIP} />
                <Bar dataKey="income" fill="var(--profit)" radius={[4, 4, 0, 0]} name="درآمد" />
                <Bar dataKey="expense" fill="var(--loss)" radius={[4, 4, 0, 0]} name="هزینه" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-[var(--text-muted)] text-sm py-4">داده‌ای برای نمایش نیست</div>
          )}
        </Card>
        <Card>
          <CardHeader title="🏦 تفکیک حساب‌ها" />
          {finance?.accounts?.length ? (
            <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
              {finance.accounts.slice(0, 6).map((a: any) => (
                <div key={a.id} className="flex items-center justify-between text-sm gap-2">
                  <span className="text-[var(--text-secondary)] truncate">{a.name}</span>
                  <span className="font-bold text-[var(--text-primary)] shrink-0">
                    {Number(a.balance || 0).toLocaleString()}{' '}
                    <span className="text-xs text-[var(--text-secondary)]">{a.currency}</span>
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[var(--text-muted)] text-sm py-4">حسابی ثبت نشده</div>
          )}
        </Card>
          </div>
          <div className="text-sm font-bold text-[var(--text-secondary)] pb-2 border-b border-[var(--border-subtle)] mt-5">عملکرد</div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <Card>
            <CardHeader title="🧾 سود خالص" subtitle="سود Real منهای هزینه‌ها" />
            {netProfit ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-[var(--bg-elevated)] rounded-[14px] p-4">
                    <div className="text-xs text-[var(--text-secondary)] font-bold">سود Real</div>
                    <div className={`text-lg font-extrabold ${currencyProfit.real_pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                      {currencyProfit.real_pnl >= 0 ? '+' : ''}{Number(currencyProfit.real_pnl).toLocaleString('en-US')} {currency}
                    </div>
                  </div>
                  <div className="bg-[var(--bg-elevated)] rounded-[14px] p-4">
                    <div className="text-xs text-[var(--text-secondary)] font-bold">هزینه‌ها</div>
                    <div className="text-lg font-extrabold text-[var(--loss)]">
                      −{Number(currencyProfit.expenses).toLocaleString('en-US')} {currency}
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between bg-[var(--accent-soft)] rounded-[14px] px-4 py-3">
                  <span className="text-[13px] font-extrabold text-[var(--text-primary)]">سود خالص</span>
                  <span className={`text-xl font-black ${currencyProfit.net_profit >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                    {currencyProfit.net_profit >= 0 ? '+' : ''}{Number(currencyProfit.net_profit).toLocaleString('en-US')} {currency}
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-[var(--text-muted)] text-sm py-4">در حال بارگذاری…</div>
            )}
          </Card>
          <Card>
            <CardHeader title="💵 دارایی شخصی" subtitle="موجودی حساب‌ها به تفکیک ارز" />
            {spendable ? (
              <FinancialAssetBalances assets={spendable} />
            ) : (
              <div className="text-[var(--text-muted)] text-sm py-4">در حال بارگذاری…</div>
            )}
          </Card>
        <Card>
          <CardHeader title="📈 روند دارایی" subtitle="مجموع تجمعی USDT / IRR" />
          {assetTrend.length > 1 ? (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={assetTrend} margin={{ top: 6, right: 12, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="assetUsd" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="var(--text-secondary)" />
                <YAxis tick={{ fontSize: 11 }} stroke="var(--text-secondary)" />
                <Tooltip contentStyle={MINI_TOOLTIP} />
                <Area type="monotone" dataKey="total_usdt" stroke="var(--accent)" fill="url(#assetUsd)" strokeWidth={2} name="USDT" />
                <Area type="monotone" dataKey="total_irr" stroke="var(--warning)" fillOpacity={0} strokeWidth={2} name="IRR" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-[var(--text-muted)] text-sm py-6 text-center">دادهٔ کافی برای نمایش روند وجود ندارد</div>
          )}
        </Card>
          </div>
        </div></div></ErrorBoundary></div>
      </details>

      <section aria-labelledby="dashboard-trades-title" data-testid="dashboard-trades-section">
        <div className="dashboard-section-heading"><h2 id="dashboard-trades-title">آخرین معاملات</h2><p>فهرست ۱۰ معاملهٔ اخیر ثبت و بسته‌شده</p></div>
        <ErrorBoundary label="معاملات"><div className="dashboard-trade-tables w-full"><Card>
          <CardHeader
            title="🧾 آخرین معاملات"
            subtitle={recentTrades.length > 0 ? `${recentTrades.length} معامله` : undefined}
            action={
              <button
                onClick={() => onNavigate?.('trades')}
                className="text-xs font-bold text-[var(--accent)] hover:bg-[var(--accent-soft)] px-3 py-1.5 rounded-lg transition-all"
              >
                مشاهده همه →
              </button>
            }
          />
          {recentTrades.length === 0 ? (
            <EmptyState icon="🧾" title="معامله‌ای ثبت نشده" description="با ثبت اولین معامله، این جدول پر می‌شود" actionLabel="ثبت معامله" onAction={handleNewTrade} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                    <th className="text-right py-2.5 px-3">نماد</th>
                    <th className="text-right py-2.5 px-3">نوع</th>
                    <th className="text-right py-2.5 px-3">حجم</th>
                    <th className="text-right py-2.5 px-3">استراتژی</th>
                    <th className="text-right py-2.5 px-3">سود/زیان</th>
                    <th className="text-right py-2.5 px-3">ضریب R</th>
                    <th className="text-right py-2.5 px-3">تاریخ</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTrades.map((t) => {
                    const pnl = (t.pnl || 0) + (t.commission || 0) + (t.swap || 0);
                    return (
                      <tr key={t.id} className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--accent-soft)]/30 transition-colors">
                        <td className="py-2.5 px-3 font-bold text-[var(--text-primary)]">{t.symbol}</td>
                        <td className="py-2.5 px-3 text-[var(--text-secondary)]">{t.direction === "buy" ? "🟢 خرید" : "🔴 فروش"}</td>
                        <td className="py-2.5 px-3 text-[var(--text-secondary)] font-mono text-xs">{t.size ?? "—"}</td>
                        <td className="py-2.5 px-3 text-[var(--text-secondary)] truncate max-w-[140px]">{t.strategy_name || "—"}</td>
                        <td className={`py-2.5 px-3 font-bold ${pnl >= 0 ? "text-[var(--profit)]" : "text-[var(--loss)]"}`}>
                          <span dir="ltr" className="inline-block dir-ltr">
                            {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)} {currency}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-xs font-semibold text-right">
                          {t.r_multiple != null ? (
                            <span dir="ltr" className={`inline-block dir-ltr ${t.r_multiple >= 0 ? "text-[var(--profit)]" : "text-[var(--loss)]"}`}>
                              {t.r_multiple >= 0 ? "+" : ""}{Number(t.r_multiple).toFixed(2)} R
                            </span>
                          ) : (
                            <span className="text-[var(--text-secondary)]">—</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-xs text-[var(--text-secondary)]">
                          {t.close_time ? new Date(t.close_time).toLocaleDateString("fa-IR") : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card></div></ErrorBoundary>
      </section>
    </div>
  );
}
