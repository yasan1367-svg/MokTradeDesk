import { useCallback, useState, useEffect } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, Tooltip, ResponsiveContainer, XAxis, YAxis, CartesianGrid, AreaChart, Area } from 'recharts';
import StatCard from '../components/ui/StatCard';
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
  const [openTrades, setOpenTrades] = useState<any[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const [alerts, setAlerts] = useState<any[]>([]);

  // ── گزارشهای فاز ۲۲ ──
  const [spendable, setSpendable] = useState<any>(null);
  const [netProfit, setNetProfit] = useState<any>(null);
  const [assetTrend, setAssetTrend] = useState<any[]>([]);

  // بارگذاری نسخه‌های استراتژی برای خلاصهٔ Backtest
  useEffect(() => {
    getAllVersions()
      .then((res) => setVersions(res.data || []))
      .catch(() => setVersions([]));
  }, []);

  const loadDashboard = useCallback(
    async (showToast = false) => {
      const r = computeRange(rangeKey, customFrom, customTo);
      setRefreshing(true);
      try {
        const [dash, yest, realSum, sum, flow, accs, closed, open, alertsRes, spendRes, npRes, trendRes] = await Promise.all([
          getDashboardData({ date_from: r.from, date_to: r.to, scope, currency }),
          getYesterdayData({ scope, currency }),
          getRealSummary({ currency }),
          getFinanceSummary(),
          getFinanceCashflow({ currency }),
          getFinanceAccounts(),
          getTrades({ status: 'closed', limit: 10, sort_by: 'close_time', sort_order: 'desc', currency }),
          getTrades({ status: 'open', sort_by: 'open_time', sort_order: 'desc', currency }),
          getPropAlerts({ unread_only: true }),
          getSpendableAssets(),
          getNetProfit({ currency }),
          getAssetTrend(),
        ]);
        setData(dash.data);
        setYesterday(yest.data);
        setRealSummary(realSum.data);
        setFinance({ summary: sum.data, cashflow: flow.data, accounts: accs.data });
        setRecentTrades(closed.data.trades || []);
        setOpenTrades(open.data.trades || []);
        setAlerts(alertsRes.data);
        setSpendable(spendRes.data);
        setNetProfit(npRes.data);
        setAssetTrend(trendRes.data.trend || []);
        setError(null);
        if (showToast) toast.success('داشبورد به‌روزرسانی شد');
      } catch (err: any) {
        const msg = err?.response?.data?.detail || 'خطا در بارگذاری داشبورد';
        setError(msg);
        toast.error(msg);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [rangeKey, customFrom, customTo, scope, currency, toast],
  );

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (versions.length === 0) {
      setBacktestSummary(null);
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
    let cancelled = false;
    setBacktestLoading(true);
    getDashboardData({ scope: 'backtest', currency: 'USDT', version_id: selected.id })
      .then((res) => { if (!cancelled) setBacktestSummary(res.data); })
      .catch(() => { if (!cancelled) setBacktestSummary(null); })
      .finally(() => { if (!cancelled) setBacktestLoading(false); });

    return () => { cancelled = true; };
  }, [versions, selectedVersionId]);

  // ذخیرهٔ فیلتر در localStorage
  useEffect(() => {
    localStorage.setItem('mok_dashboard_range', rangeKey);
    localStorage.setItem('mok_dashboard_custom_from', customFrom);
    localStorage.setItem('mok_dashboard_custom_to', customTo);
    localStorage.setItem('mok_dashboard_scope', scope);
    localStorage.setItem('mok_dashboard_currency', currency);
  }, [rangeKey, customFrom, customTo, scope, currency]);

  // ساعت زنده
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
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
  const clock = now.toLocaleTimeString('fa-IR');
  const greeting = getGreeting(now.getHours());

  const handleNewTrade = () => {
    onNavigate?.('trades');
    window.dispatchEvent(new CustomEvent('mok-new-trade'));
    toast.info('فرم ثبت معامله جدید باز شد');
  };

  const openSearch = () => {
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }));
  };

  const handleExportPdf = async () => {
    try {
      const res = await exportDashboardPdf();
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
    'w-10 h-10 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] flex items-center justify-center cursor-pointer text-base text-[var(--text-secondary)] transition-all hover:bg-[var(--accent-soft)] hover:border-[var(--border-accent)] hover:text-[var(--accent)] disabled:opacity-50';

  return (
    <div className="space-y-7">
      <ErrorBoundary label="Dashboard header and filters">
      {/* هدر */}
      <div className="flex justify-between items-center flex-wrap gap-3">
        <div>
          <div className="text-[var(--text-primary)] text-2xl font-extrabold">سلام، {greeting} 👋</div>
          <div className="mt-1 flex flex-col items-start gap-1 text-sm text-[var(--text-secondary)] sm:flex-row sm:items-center sm:gap-4">
            <div className="flex items-center gap-4">
              <span>📅 {weekday}، {jalaliDate}</span>
              <span className="tabular-nums" dir="ltr">🕒 {clock}</span>
            </div>
            <MarketSessionWidget />
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <InfoTooltip content="معامله جدید (Ctrl+N)">
            <button onClick={handleNewTrade} className={quickBtn} aria-label="معامله جدید">➕</button>
          </InfoTooltip>
          <InfoTooltip content="تراکنش مالی">
            <button onClick={() => onNavigate?.('finance')} className={quickBtn} aria-label="تراکنش مالی">💳</button>
          </InfoTooltip>
          <InfoTooltip content="حساب مالی جدید">
            <button onClick={() => onNavigate?.('finance')} className={quickBtn} aria-label="حساب جدید">🏦</button>
          </InfoTooltip>
          <InfoTooltip content="جستجوی سریع (Ctrl+K)">
            <button onClick={openSearch} className={quickBtn} aria-label="جستجو">🔍</button>
          </InfoTooltip>
          <InfoTooltip content="به‌روزرسانی داشبورد">
            <button onClick={() => loadDashboard(true)} disabled={refreshing} className={quickBtn} aria-label="به‌روزرسانی">
              <span className={refreshing ? 'inline-block animate-spin' : ''}>🔄</span>
            </button>
          </InfoTooltip>
          <button
            onClick={handleExportPdf}
            className="bg-[var(--loss)] hover:bg-[var(--loss)]/80 text-white px-5 py-2.5 rounded-xl text-sm flex items-center gap-1 transition-all"
          >
            📄 گزارش PDF
          </button>
        </div>
      </div>

      {/* فیلتر بازه زمانی (فاز ۱۴.۳) */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-4">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-bold text-[var(--text-secondary)] ml-1">🔎 بازه:</span>
          {RANGE_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setRangeKey(f.key)}
              className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${
                rangeKey === f.key
                  ? 'text-white shadow-[0_4px_12px_rgba(63,124,255,0.3)]'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-base)]'
              }`}
              style={rangeKey === f.key ? { background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' } : {}}
            >
              {f.icon} {f.label}
            </button>
          ))}
        </div>
        {/* فاز ۴۴.۱: انتخاب دامنه (واقعی/بک‌تست/فوروارد/همه) */}
        <div className="flex items-center gap-2 flex-wrap mt-3 pt-3 border-t border-[var(--border-subtle)]">
          <span className="text-xs font-bold text-[var(--text-secondary)] ml-1">🎯 دامنه:</span>
          {SCOPE_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setScope(f.key)}
              className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${
                scope === f.key
                  ? 'text-white shadow-[0_4px_12px_rgba(121,89,255,0.3)]'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-base)]'
              }`}
              style={scope === f.key ? { background: 'linear-gradient(135deg, var(--purple), var(--accent))' } : {}}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 flex-wrap mt-3 pt-3 border-t border-[var(--border-subtle)]">
          <span className="text-xs font-bold text-[var(--text-secondary)] ml-1">💱 ارز:</span>
          {(['USDT', 'IRR'] as CurrencyCode[]).map((value) => (
            <button
              key={value}
              onClick={() => setCurrency(value)}
              className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${currency === value ? 'text-white' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-base)]'}`}
              style={currency === value ? { background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' } : {}}
            >
              {value}
            </button>
          ))}
        </div>
        {rangeKey === 'custom' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 pt-3 border-t border-[var(--border-subtle)]">
            <PersianDateInput label="از تاریخ" value={customFrom} onChange={setCustomFrom} />
            <PersianDateInput label="تا تاریخ" value={customTo} onChange={setCustomTo} />
          </div>
        )}
      </div>

      </ErrorBoundary>

      {/* کارت‌های آماری — پول واقعی (فاز ۱۰-C-۳-A) */}
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
      <div className="text-xs text-[var(--text-secondary)] font-bold mb-2 text-center">
        پول واقعی — مرحله ۳ پراپ + بروکر شخصی
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          icon="💰"
          label="سود خالص"
          value={`${realSummary.net_pnl >= 0 ? '+' : ''}${realSummary.net_pnl} ${currency} `}
          change={`${realSummary.winning_trades}W / ${realSummary.losing_trades}L`}
          changeType={realSummary.net_pnl >= 0 ? 'up' : 'down'}
          color="profit"
          sparkData={realSummary.sparkline && realSummary.sparkline.length > 0 ? realSummary.sparkline : [0]}
        />
        <StatCard
          icon="📈"
          label="نرخ برد"
          value={`${realSummary.win_rate}٪`}
          change={`${realSummary.winning_trades}W / ${realSummary.losing_trades}L`}
          changeType="neutral"
          color="accent"
          chart={<MiniPie wins={realSummary.winning_trades ?? 0} losses={realSummary.losing_trades ?? 0} />}
        />
        <StatCard
          icon="🏆"
          label="فاکتور سود"
          value={realSummary.profit_factor}
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
          icon="⚠️"
          label="حداکثر ضرر"
          value={`-${realSummary.max_dd} ${currency} `}
          change="—"
          changeType="neutral"
          color="loss"
          chart={<MiniBars
            data={[
              { label: 'بزرگترین ضرر', value: realSummary.gross_loss ?? 0 },
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

      <ErrorBoundary label="Today">
      {/* کارت وضعیت امروز (فاز ۱۴.۲ — بالای همه) */}
      <div
        className="relative rounded-[28px] p-8 flex justify-between items-center flex-wrap gap-7 overflow-hidden shadow-lg border border-[var(--border-accent)]"
        style={{ background: 'linear-gradient(135deg, var(--bg-card) 0%, var(--accent-soft) 100%)' }}
      >
        <div
          className="absolute top-0 right-0 left-0 h-1"
          style={{ background: 'linear-gradient(90deg, var(--accent), var(--purple), var(--profit))' }}
        />
        <div
          className="absolute -top-24 -left-24 w-[300px] h-[300px] rounded-full pointer-events-none"
          style={{ background: 'radial-gradient(circle, rgba(63,124,255,0.08) 0%, transparent 70%)' }}
        />

        <div className="relative z-10">
          <div className="text-xs text-[var(--text-secondary)] font-bold mb-1">📅 وضعیت امروز</div>
          <div
            className={`text-4xl font-extrabold ${today.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}
          >
                  {today.pnl >= 0 ? '+' : ''}{today.pnl} {currency}
          </div>
          <div className="flex items-center gap-4 mt-3 flex-wrap">
            <div className="text-sm text-[var(--text-secondary)]">
              <span className="font-bold">{today.trades_count}</span> معامله
            </div>
            <div className="text-sm text-[var(--text-secondary)]">
              نرخ برد امروز: <span className="font-bold">{today.win_rate}٪</span>
            </div>
            <div className="text-sm text-[var(--text-secondary)]">
              <span className="font-bold">{summary.open_trades}</span> معامله باز
            </div>
            <div className="text-sm text-[var(--text-secondary)]">
              <span className="font-bold">{summary.total_trades}</span> کل معاملات
            </div>
          </div>
        </div>

        <div className="relative z-10 flex gap-4 flex-wrap">
          <div className="text-center bg-[var(--bg-card-translucent)] backdrop-blur rounded-[16px] px-5 py-3 border border-[var(--border-subtle)] min-w-[120px]">
            <div className="text-xs text-[var(--text-secondary)] font-bold">این ماه</div>
            <div className={`text-lg font-extrabold ${periods.month.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
              {periods.month.pnl >= 0 ? '+' : ''}{periods.month.pnl} {currency}
            </div>
          </div>
          <div className="text-center bg-[var(--bg-card-translucent)] backdrop-blur rounded-[16px] px-5 py-3 border border-[var(--border-subtle)] min-w-[120px]">
            <div className="text-xs text-[var(--text-secondary)] font-bold">این فصل</div>
            <div className={`text-lg font-extrabold ${periods.quarter.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
              {periods.quarter.pnl >= 0 ? '+' : ''}{periods.quarter.pnl} {currency}
            </div>
          </div>
          <div className="text-center bg-[var(--bg-card-translucent)] backdrop-blur rounded-[16px] px-5 py-3 border border-[var(--border-subtle)] min-w-[120px]">
            <div className="text-xs text-[var(--text-secondary)] font-bold">امسال</div>
            <div className={`text-lg font-extrabold ${periods.year.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
              {periods.year.pnl >= 0 ? '+' : ''}{periods.year.pnl} {currency}
            </div>
          </div>
        </div>
      </div>

      </ErrorBoundary>

      <ErrorBoundary label="Yesterday">
      {/* کارت روز گذشته (فاز ۱۴.۲) */}
      <Card>
        <CardHeader
          title={`🌙 روز گذشته${yesterday ? ` — ${yesterday.day_of_week} ${yesterday.date}` : ''}`}
          subtitle={yesterday ? `${yesterday.total_trades} معامله` : undefined}
        />
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
                <span className="font-bold text-[var(--text-primary)]">{yesterday.win_rate}٪</span>
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
      </Card>

      </ErrorBoundary>

      <ErrorBoundary label="Active Prop Stage">
        <Card>
          <CardHeader title="🏢 وضعیت پراپ" subtitle={prop_progress.length > 0 ? `${prop_progress.length} مرحله فعال` : undefined} />
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
                      <div className="text-xs text-[var(--text-secondary)] mt-1">
                        هدف: {Number(stage.profit_target || 0).toLocaleString('en-US')} {currency} · {Number(stage.profit_progress_percent || 0).toFixed(1)}٪
                      </div>
                    </div>

                    <div className="mt-3">
                      <ProgressBar value={Math.min(Math.max(stage.profit_progress_percent || 0, 0), 100)} variant="profit" />
                    </div>
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
        </Card>

{alerts.length > 0 && (
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
      )}
      </ErrorBoundary>

      <ErrorBoundary label="Finance">
        <Card>
        <CardHeader title="💰 مالی" />
        <div className="space-y-4">
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
        </div>
        </Card>
      </ErrorBoundary>

      <ErrorBoundary label="Prop goals">
        {/* پیشرفت اهداف (ماهانه/فصلی/سالانه) */}
        <Card>
          <CardHeader title="🎯 پیشرفت اهداف" subtitle="عملکرد واقعی بر اساس PnL" />
          <div className="space-y-6">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-xs text-[var(--text-secondary)]">عملکرد ماه جاری</span>
                <span className={`text-xs font-bold ${periods.month.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                  {periods.month.pnl >= 0 ? '+' : ''}{periods.month.pnl} {currency}
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
                  {periods.quarter.pnl >= 0 ? '+' : ''}{periods.quarter.pnl} {currency}
                </span>
              </div>
              <ProgressBar
                value={Math.min(Math.abs(periods.quarter.pnl / (periods.month.pnl || 1) * 100), 100)}
                variant={periods.quarter.pnl >= 0 ? 'accent' : 'loss'}
              />
              <div className="flex justify-between mt-1.5">
                <span className="text-xs text-[var(--text-secondary)]">از ابتدای فصل</span>
                <span className={`text-xs font-bold ${periods.quarter.pnl >= 0 ? 'text-[var(--accent)]' : 'text-[var(--loss)]'}`}>
                  {periods.quarter.pnl >= 0 ? '+' : ''}{periods.quarter.pnl} {currency}
                </span>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="text-xs text-[var(--text-secondary)]">عملکرد سال جاری</span>
                <span className={`text-xs font-bold ${periods.year.pnl >= 0 ? 'text-[var(--warning)]' : 'text-[var(--loss)]'}`}>
                  {periods.year.pnl >= 0 ? '+' : ''}{periods.year.pnl} {currency}
                </span>
              </div>
              <ProgressBar
                value={Math.min(Math.abs(periods.year.pnl / (periods.month.pnl || 1) * 100), 100)}
                variant={periods.year.pnl >= 0 ? 'warning' : 'loss'}
              />
              <div className="flex justify-between mt-1.5">
                <span className="text-xs text-[var(--text-secondary)]">از ابتدای سال</span>
                <span className={`text-xs font-bold ${periods.year.pnl >= 0 ? 'text-[var(--warning)]' : 'text-[var(--loss)]'}`}>
                  {periods.year.pnl >= 0 ? '+' : ''}{periods.year.pnl} {currency}
                </span>
              </div>
            </div>
          </div>
        </Card>
      </ErrorBoundary>

      {/* عملکرد بک‌تست نسخهٔ انتخاب‌شده */}
      <ErrorBoundary label="عملکرد بک‌تست">
        <Card>
          <CardHeader
            title="📊 عملکرد بک‌تست"
            action={(
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
            )}
          />
          {versions.length === 0 ? (
            <EmptyState icon="📊" title="نسخه‌ای برای بک‌تست وجود ندارد" />
          ) : backtestLoading ? (
            <div className="text-sm text-[var(--text-muted)] py-5 text-center">در حال بارگذاری عملکرد بک‌تست…</div>
          ) : backtestSummary ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <StatCard
                  icon="💰"
                  label="سود خالص بک‌تست"
                  value={`${Number(backtestSummary.summary?.net_pnl || 0).toLocaleString('en-US')} USDT`}
                  color={(backtestSummary.summary?.net_pnl || 0) >= 0 ? 'profit' : 'loss'}
                  sparkData={backtestSummary.sparkline || [0]}
                />
                <StatCard
                  icon="📈"
                  label="نرخ برد"
                  value={`${Number(backtestSummary.summary?.win_rate || 0).toFixed(1)}٪`}
                  color="accent"
                  sparkData={[0]}
                />
                <StatCard
                  icon="🏆"
                  label="Profit Factor"
                  value={Number(backtestSummary.summary?.profit_factor || 0).toFixed(2)}
                  color="purple"
                  sparkData={[0]}
                />
              </div>
              <div className="flex flex-wrap items-center justify-between gap-3 mt-4">
                <span className="text-xs text-[var(--text-secondary)]">
                  {Number(backtestSummary.summary?.closed_trades || 0)} معامله · R-Multiple: {Number(backtestSummary.summary?.avg_r_multiple || 0).toFixed(2)}
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
        </Card>
      </ErrorBoundary>

      {/* نمودارهای پایه (فاز ۱۴.۱) */}
      <ErrorBoundary label="نمودارها">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Card>
          <CardHeader title="📉 منحنی سرمایه" subtitle={`${(equity_curve || []).length} روز`} />
          <EquityCurveChart data={equity_curve || []} height={240} />
        </Card>
        <Card>
          <CardHeader
            title="🥧 برد / باخت"
            subtitle={win_loss ? `${(win_loss.wins || 0) + (win_loss.losses || 0)} معامله بسته` : undefined}
          />
          <WinLossPieChart wins={win_loss?.wins ?? 0} losses={win_loss?.losses ?? 0} height={240} />
        </Card>
        <Card>
          <CardHeader title="📊 توزیع سود/زیان" subtitle="تعداد معاملات در هر بازه" />
          <PnLDistributionChart data={pnl_distribution || []} height={240} />
        </Card>
      </div>
      </ErrorBoundary>

      {/* جدول‌های معاملات (فاز ۱۴.۳) */}
      <ErrorBoundary label="معاملات">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* آخرین معاملات */}
        <Card>
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
                    <th className="text-right py-2.5 px-2">نماد</th>
                    <th className="text-right py-2.5 px-2">نوع</th>
                    <th className="text-right py-2.5 px-2">استراتژی</th>
                    <th className="text-right py-2.5 px-2">سود/زیان</th>
                    <th className="text-right py-2.5 px-2">تاریخ</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTrades.map((t) => {
                    const pnl = (t.pnl || 0) + (t.commission || 0) + (t.swap || 0);
                    return (
                      <tr key={t.id} className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--accent-soft)]/30 transition-colors">
                        <td className="py-2.5 px-2 font-bold text-[var(--text-primary)]">{t.symbol}</td>
                        <td className="py-2.5 px-2 text-[var(--text-secondary)]">{t.direction === 'buy' ? '🟢 خرید' : '🔴 فروش'}</td>
                        <td className="py-2.5 px-2 text-[var(--text-secondary)] truncate max-w-[120px]">{t.strategy_name || '—'}</td>
                        <td className={`py-2.5 px-2 font-bold ${pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                          {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)} {currency}
                        </td>
                        <td className="py-2.5 px-2 text-xs text-[var(--text-secondary)]">
                          {t.close_time ? new Date(t.close_time).toLocaleDateString('fa-IR') : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        {/* معاملات باز */}
        <Card>
          <CardHeader
            title="📂 معاملات باز"
            subtitle={openTrades.length > 0 ? `${openTrades.length} معامله` : undefined}
          />
          {openTrades.length === 0 ? (
            <EmptyState icon="📂" title="معاملهٔ بازی وجود ندارد" description="همهٔ معاملات بسته شده‌اند" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                    <th className="text-right py-2.5 px-2">نماد</th>
                    <th className="text-right py-2.5 px-2">نوع</th>
                    <th className="text-right py-2.5 px-2">استراتژی</th>
                    <th className="text-right py-2.5 px-2">سود/زیان لحظه‌ای</th>
                  </tr>
                </thead>
                <tbody>
                  {openTrades.map((t) => {
                    const pnl = (t.pnl || 0) + (t.commission || 0) + (t.swap || 0);
                    const hasPnl = t.pnl !== null && t.pnl !== undefined;
                    return (
                      <tr key={t.id} className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--accent-soft)]/30 transition-colors">
                        <td className="py-2.5 px-2 font-bold text-[var(--text-primary)]">{t.symbol}</td>
                        <td className="py-2.5 px-2 text-[var(--text-secondary)]">{t.direction === 'buy' ? '🟢 خرید' : '🔴 فروش'}</td>
                        <td className="py-2.5 px-2 text-[var(--text-secondary)] truncate max-w-[120px]">{t.strategy_name || '—'}</td>
                        <td className={`py-2.5 px-2 font-bold ${!hasPnl ? 'text-[var(--text-secondary)]' : pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                          {hasPnl ? `${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)} ${currency} ` : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
      </ErrorBoundary>
    </div>
  );
}
