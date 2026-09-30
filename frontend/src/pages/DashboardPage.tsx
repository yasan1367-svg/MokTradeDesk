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
  getDashboardData, getYesterdayData, exportDashboardPdf, getPropAlerts, markAlertRead,
  getFinanceSummary, getFinanceCashflow, getFinanceAccounts, getTrades, getRiskAdvanced,
  getPropPayoutsStats, getBrokerPayoutsStats,
  getSpendableAssets, getNetProfit, getAssetTrend,
  listBackups, createBackup,
} from '../api/client';
import type { TradeScope } from '../api/client';
import { DashboardSkeleton } from '../components/Skeleton';
import { useToast } from '../components/ToastProvider';
import PersianDateInput from '../components/PersianDateInput';
import EmptyState from '../components/ui/EmptyState';
import InfoTooltip from '../components/ui/Tooltip';
import ErrorBoundary from '../components/ErrorBoundary';
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
type RiskTone = 'profit' | 'loss' | 'warning' | 'neutral';

const RISK_TONE_CLASS: Record<RiskTone, string> = {
  profit: 'text-[var(--profit)]',
  loss: 'text-[var(--loss)]',
  warning: 'text-[var(--warning)]',
  neutral: 'text-[var(--text-primary)]',
};

function sharpeTone(v: number): RiskTone {
  if (v > 1) return 'profit';
  if (v > 0.5) return 'warning';
  return 'loss';
}

function ruinTone(v: number): RiskTone {
  if (v < 0.05) return 'profit';
  if (v < 0.1) return 'warning';
  return 'loss';
}

function RiskStat({
  label, value, tip, tone = 'neutral', suffix = '',
}: { label: string; value: number | string; tip: string; tone?: RiskTone; suffix?: string }) {
  return (
    <div className="bg-[var(--bg-base)] border border-[var(--border-subtle)] rounded-[14px] p-3">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-[11px] font-bold text-[var(--text-secondary)]">{label}</span>
        <InfoTooltip content={tip}>
          <span className="text-[10px] text-[var(--text-muted)] cursor-help">ⓘ</span>
        </InfoTooltip>
      </div>
      <div className={`text-lg font-extrabold ${RISK_TONE_CLASS[tone]}`}>
        {value}{suffix}
      </div>
    </div>
  );
}

// ── مینی‌نمودار کارت‌های آماری (فاز ۱۴.۱) ──
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
    { name: 'برد', value: wins, color: '#13AE81' },
    { name: 'باخت', value: losses, color: '#E45D72' },
  ];
  if (wins + losses === 0) {
    return <div className="text-[11px] text-[var(--text-muted)] text-center py-4">داده نیست</div>;
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

function MiniBars({ data, colors, height = 80 }: { data: { label: string; value: number }[]; colors: string[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 6, right: 6, left: 6, bottom: 0 }}>
        <XAxis dataKey="label" hide />
        <Tooltip contentStyle={MINI_TOOLTIP} formatter={(v: any) => [`${Number(v).toLocaleString()} $`, '']} />
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

  // جدول‌های معاملات
  const [recentTrades, setRecentTrades] = useState<any[]>([]);
  const [openTrades, setOpenTrades] = useState<any[]>([]);
  const [risk, setRisk] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);

const [alerts, setAlerts] = useState<any[]>([]);
const [payouts, setPayouts] = useState<any>(null);

  // ── گزارشهای فاز ۲۲ ──
  const [spendable, setSpendable] = useState<any>(null);
  const [netProfit, setNetProfit] = useState<any>(null);
  const [assetTrend, setAssetTrend] = useState<any[]>([]);

  // ── آمار برداشت‌ها (فاز ۱۶) ──
  useEffect(() => {
    Promise.all([getPropPayoutsStats(), getBrokerPayoutsStats()])
      .then(([p, b]) => setPayouts({ prop: p.data, broker: b.data }))
      .catch(() => {});
  }, []);

  // ── آخرین Backup (فاز ۱۷) ──
  const [lastBackup, setLastBackup] = useState<any>(null);
  const [backupBusy, setBackupBusy] = useState(false);

  const loadLastBackup = useCallback(() => {
    listBackups().then((r) => setLastBackup((r.data || [])[0] || null)).catch(() => {});
  }, []);
  useEffect(() => { loadLastBackup(); }, [loadLastBackup]);

  const handleQuickBackup = async () => {
    setBackupBusy(true);
    try {
      await createBackup();
      toast.success('Backup ساخته شد');
      loadLastBackup();
    } catch {
      toast.error('خطا در ساخت Backup');
    } finally {
      setBackupBusy(false);
    }
  };

  // ── بارگذاری همهٔ ویجت‌ها (قابل Refresh) ──
  const loadDashboard = useCallback(
    async (showToast = false) => {
      const r = computeRange(rangeKey, customFrom, customTo);
      setRefreshing(true);
      try {
        const [dash, yest, sum, flow, accs, riskRes, closed, open, alertsRes, spendRes, npRes, trendRes] = await Promise.all([
          getDashboardData({ date_from: r.from, date_to: r.to, scope }),
          getYesterdayData({ scope }),
          getFinanceSummary(),
          getFinanceCashflow(),
          getFinanceAccounts(),
          getRiskAdvanced({ date_from: r.from, date_to: r.to, scope }),
          getTrades({ status: 'closed', limit: 10, sort_by: 'close_time', sort_order: 'desc' }),
          getTrades({ status: 'open', sort_by: 'open_time', sort_order: 'desc' }),
          getPropAlerts({ unread_only: true }),
          getSpendableAssets(),
          getNetProfit(),
          getAssetTrend(),
        ]);
        setData(dash.data);
        setYesterday(yest.data);
        setFinance({ summary: sum.data, cashflow: flow.data, accounts: accs.data });
        setRisk(riskRes.data);
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
    [rangeKey, customFrom, customTo, scope, toast],
  );

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  // ذخیرهٔ فیلتر در localStorage
  useEffect(() => {
    localStorage.setItem('mok_dashboard_range', rangeKey);
    localStorage.setItem('mok_dashboard_custom_from', customFrom);
    localStorage.setItem('mok_dashboard_custom_to', customTo);
    localStorage.setItem('mok_dashboard_scope', scope);
  }, [rangeKey, customFrom, customTo, scope]);

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

  const { summary, today, sparkline, equity_curve, pnl_distribution, win_loss, periods, prop_progress } = data;

  const getChangeType = (value: number): 'up' | 'down' | 'neutral' => {
    if (value > 0) return 'up';
    if (value < 0) return 'down';
    return 'neutral';
  };

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
      {/* هدر */}
      <div className="flex justify-between items-center flex-wrap gap-3">
        <div>
          <div className="text-[var(--text-primary)] text-2xl font-extrabold">سلام، {greeting} 👋</div>
          <div className="flex items-center gap-4 mt-1 text-sm text-[var(--text-secondary)]">
            <span>📅 {weekday}، {jalaliDate}</span>
            <span className="tabular-nums" dir="ltr">🕒 {clock}</span>
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
            className="bg-[#E45D72] hover:bg-[#E45D72]/80 text-white px-5 py-2.5 rounded-xl text-sm flex items-center gap-1 transition-all"
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
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                rangeKey === f.key
                  ? 'text-white shadow-[0_4px_12px_rgba(63,124,255,0.3)]'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-base)]'
              }`}
              style={rangeKey === f.key ? { background: 'linear-gradient(135deg, var(--accent), #5B8DEF)' } : {}}
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
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
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
        {rangeKey === 'custom' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 pt-3 border-t border-[var(--border-subtle)]">
            <PersianDateInput label="از تاریخ" value={customFrom} onChange={setCustomFrom} />
            <PersianDateInput label="تا تاریخ" value={customTo} onChange={setCustomTo} />
          </div>
        )}
      </div>

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
            {today.pnl >= 0 ? '+' : ''}{today.pnl} $
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
            <div className="text-[11px] text-[var(--text-secondary)] font-bold">این ماه</div>
            <div className={`text-lg font-extrabold ${periods.month.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
              {periods.month.pnl >= 0 ? '+' : ''}{periods.month.pnl} $
            </div>
          </div>
          <div className="text-center bg-[var(--bg-card-translucent)] backdrop-blur rounded-[16px] px-5 py-3 border border-[var(--border-subtle)] min-w-[120px]">
            <div className="text-[11px] text-[var(--text-secondary)] font-bold">این فصل</div>
            <div className={`text-lg font-extrabold ${periods.quarter.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
              {periods.quarter.pnl >= 0 ? '+' : ''}{periods.quarter.pnl} $
            </div>
          </div>
          <div className="text-center bg-[var(--bg-card-translucent)] backdrop-blur rounded-[16px] px-5 py-3 border border-[var(--border-subtle)] min-w-[120px]">
            <div className="text-[11px] text-[var(--text-secondary)] font-bold">امسال</div>
            <div className={`text-lg font-extrabold ${periods.year.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
              {periods.year.pnl >= 0 ? '+' : ''}{periods.year.pnl} $
            </div>
          </div>
        </div>
      </div>

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
                  {yesterday.net_pnl >= 0 ? '+' : ''}{yesterday.net_pnl} $
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
                    className="text-[11px] px-2.5 py-1 rounded-full bg-[var(--bg-base)] border border-[var(--border-subtle)] text-[var(--text-secondary)]"
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
                colors={['#3F7CFF', '#7959D6', '#13AE81']}
                height={120}
              />
              <div className="text-[11px] text-[var(--text-muted)] text-center mt-1">تفکیک بر اساس منبع (قدرمطلق سود/زیان)</div>
            </div>
          </div>
        ) : (
          <div className="text-[var(--text-muted)] text-center py-6 text-sm">داده‌ای برای روز گذشته نیست</div>
        )}
      </Card>

      {/* کارت آمار برداشت‌ها (فاز ۱۶) */}
      {payouts && (
        <ErrorBoundary label="برداشت‌ها">
          <Card>
            <CardHeader
              title="💸 آمار برداشت‌ها"
              subtitle="پراپ و بروکر"
              action={
                <button
                  onClick={() => onNavigate?.('payouts')}
                  className="text-xs font-bold text-[var(--accent)] hover:bg-[var(--accent-soft)] px-3 py-1.5 rounded-lg transition-all"
                >
                  مشاهده همه →
                </button>
              }
            />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-[var(--bg-elevated)] rounded-[14px] p-4">
                <div className="text-[11px] text-[var(--text-secondary)] font-bold">مجموع پراپ</div>
                <div className="text-base font-extrabold text-[var(--profit)]">
                  ${Number(payouts.prop?.total || 0).toLocaleString('en-US')}
                </div>
              </div>
              <div className="bg-[var(--bg-elevated)] rounded-[14px] p-4">
                <div className="text-[11px] text-[var(--text-secondary)] font-bold">تعداد پراپ</div>
                <div className="text-base font-extrabold text-[var(--text-primary)]">{payouts.prop?.count ?? 0}</div>
              </div>
              <div className="bg-[var(--bg-elevated)] rounded-[14px] p-4">
                <div className="text-[11px] text-[var(--text-secondary)] font-bold">مجموع بروکر</div>
                <div className="text-base font-extrabold text-[var(--accent)]">
                  ${Number(payouts.broker?.total || 0).toLocaleString('en-US')}
                </div>
              </div>
              <div className="bg-[var(--bg-elevated)] rounded-[14px] p-4">
                <div className="text-[11px] text-[var(--text-secondary)] font-bold">تعداد بروکر</div>
                <div className="text-base font-extrabold text-[var(--text-primary)]">{payouts.broker?.count ?? 0}</div>
              </div>
            </div>
          </Card>
        </ErrorBoundary>
      )}

      {/* کارت آخرین Backup (فاز ۱۷) */}
      <ErrorBoundary label="Backup">
        <Card>
          <CardHeader
            title="💾 آخرین Backup"
            subtitle="نسخهٔ پشتیبان دیتابیس"
            action={
              <div className="flex gap-2">
                <button
                  onClick={handleQuickBackup}
                  disabled={backupBusy}
                  className="text-xs font-bold text-white px-3 py-1.5 rounded-lg transition-all disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, var(--accent), #5B8DEF)' }}
                >
                  {backupBusy ? '⏳ …' : '➕ ساخت Backup'}
                </button>
                <button
                  onClick={() => onNavigate?.('settings')}
                  className="text-xs font-bold text-[var(--text-secondary)] hover:bg-[var(--accent-soft)] px-3 py-1.5 rounded-lg transition-all"
                >
                  مدیریت →
                </button>
              </div>
            }
          />
          {lastBackup ? (
            <div className="flex flex-wrap gap-4 text-sm">
              <div className="bg-[var(--bg-elevated)] rounded-[14px] px-4 py-3">
                <div className="text-[11px] text-[var(--text-secondary)] font-bold">فایل</div>
                <div className="font-mono text-[12px] text-[var(--text-primary)]">{lastBackup.filename}</div>
              </div>
              <div className="bg-[var(--bg-elevated)] rounded-[14px] px-4 py-3">
                <div className="text-[11px] text-[var(--text-secondary)] font-bold">تاریخ</div>
                <div className="text-[13px] font-extrabold text-[var(--text-primary)]">
                  {(() => {
                    const d = new Date(lastBackup.created_at);
                    if (isNaN(d.getTime())) return '—';
                    const [jy, jm, jd] = gregorianToJalali(d.getFullYear(), d.getMonth() + 1, d.getDate());
                    const hh = String(d.getHours()).padStart(2, '0');
                    const mm = String(d.getMinutes()).padStart(2, '0');
                    return `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')} - ${hh}:${mm}`;
                  })()}
                </div>
              </div>
              <div className="bg-[var(--bg-elevated)] rounded-[14px] px-4 py-3">
                <div className="text-[11px] text-[var(--text-secondary)] font-bold">حجم</div>
                <div className="text-[13px] font-extrabold text-[var(--text-primary)]">
                  {(Number(lastBackup.size || 0) / 1024).toFixed(1)} KB
                </div>
              </div>
            </div>
          ) : (
            <div className="text-[var(--text-secondary)] text-sm py-2">هنوز Backup‌ی ساخته نشده</div>
          )}
        </Card>
      </ErrorBoundary>

      {/* کارت‌های فاز ۲۲: دارایی قابل برداشت + سود خالص + روند دارایی */}
      <ErrorBoundary label="گزارش‌های مالی (فاز ۲۲)">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <Card>
            <CardHeader title="💵 دارایی قابل برداشت" subtitle="تفکیک منابع مالی" />
            {spendable ? (
              <div className="space-y-2">
                {([
                  ['prop_stage_3', '🏢 مرحلهٔ ۳ پراپ'],
                  ['broker', '📊 بروکر'],
                  ['exchange', '🔄 صرافی'],
                  ['trust_wallet', '₿ تراست ولت'],
                  ['bank', '🏦 بانک'],
                ] as const).map(([key, label]) => (
                  <div key={key} className="flex items-center justify-between bg-[var(--bg-elevated)] rounded-[12px] px-4 py-2.5">
                    <span className="text-[13px] text-[var(--text-secondary)] font-bold">{label}</span>
                    <span className="text-[14px] font-extrabold text-[var(--text-primary)]">
                      {Number(spendable[key]?.amount ?? 0).toLocaleString('en-US')}{' '}
                      <span className="text-[11px] text-[var(--text-secondary)]">{spendable[key]?.currency}</span>
                    </span>
                  </div>
                ))}
                <div className="flex items-center justify-between border-t border-[var(--border-subtle)] pt-3 mt-1">
                  <span className="text-[13px] font-extrabold text-[var(--text-primary)]">مجموع</span>
                  <span className="text-[14px] font-black text-[var(--accent)]">
                    {Number(spendable.total?.usd ?? 0).toLocaleString('en-US')} $
                    <span className="mr-2 text-[12px] text-[var(--text-secondary)]">
                      {Number(spendable.total?.irr ?? 0).toLocaleString('en-US')} IRR
                    </span>
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-[var(--text-muted)] text-sm py-4">در حال بارگذاری…</div>
            )}
          </Card>

          <Card>
            <CardHeader title="🧾 سود خالص" subtitle="سود Real منهای هزینه‌ها" />
            {netProfit ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-[var(--bg-elevated)] rounded-[14px] p-4">
                    <div className="text-[11px] text-[var(--text-secondary)] font-bold">سود Real</div>
                    <div className={`text-lg font-extrabold ${netProfit.real_pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                      {netProfit.real_pnl >= 0 ? '+' : ''}{Number(netProfit.real_pnl).toLocaleString('en-US')} $
                    </div>
                  </div>
                  <div className="bg-[var(--bg-elevated)] rounded-[14px] p-4">
                    <div className="text-[11px] text-[var(--text-secondary)] font-bold">هزینه‌ها</div>
                    <div className="text-lg font-extrabold text-[var(--loss)]">
                      −{Number(netProfit.expenses).toLocaleString('en-US')} $
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between bg-[var(--accent-soft)] rounded-[14px] px-4 py-3">
                  <span className="text-[13px] font-extrabold text-[var(--text-primary)]">سود خالص</span>
                  <span className={`text-xl font-black ${netProfit.net_profit >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                    {netProfit.net_profit >= 0 ? '+' : ''}{Number(netProfit.net_profit).toLocaleString('en-US')} $
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-[var(--text-muted)] text-sm py-4">در حال بارگذاری…</div>
            )}
          </Card>
        </div>

        <Card className="mt-5">
          <CardHeader title="📈 روند دارایی" subtitle="مجموع تجمعی USD / IRR" />
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
                <Area type="monotone" dataKey="total_usd" stroke="var(--accent)" fill="url(#assetUsd)" strokeWidth={2} name="USD" />
                <Area type="monotone" dataKey="total_irr" stroke="#F59E0B" fillOpacity={0} strokeWidth={2} name="IRR" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-[var(--text-muted)] text-sm py-6 text-center">دادهٔ کافی برای نمایش روند وجود ندارد</div>
          )}
        </Card>
      </ErrorBoundary>

      {/* کارت‌های آماری */}
      <ErrorBoundary label="کارت‌های آماری">
      {(!summary || (summary.total_trades ?? 0) === 0) ? (
        <Card>
          <EmptyState
            icon="📊"
            title="هنوز معامله‌ای ثبت نشده"
            description="برای مشاهدهٔ آمار، اولین معامله را ثبت کنید"
            actionLabel="افزودن معامله"
            onAction={handleNewTrade}
          />
        </Card>
      ) : (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          icon="💰"
          label="سود خالص"
          value={`${summary.net_pnl >= 0 ? '+' : ''}${summary.net_pnl} $`}
          change={periods.month.change_percent > 0 ? `+${periods.month.change_percent}٪` : `${periods.month.change_percent}٪`}
          changeType={getChangeType(periods.month.change_percent)}
          color="profit"
          sparkData={
            (equity_curve || []).length > 1
              ? (equity_curve || []).map((p: any) => p.equity)
              : (sparkline && sparkline.length > 0 ? sparkline : [0])
          }
        />
        <StatCard
          icon="📈"
          label="نرخ برد"
          value={`${summary.win_rate}٪`}
          change={`${win_loss?.wins ?? 0}W / ${win_loss?.losses ?? 0}L`}
          changeType="neutral"
          color="accent"
          chart={<MiniPie wins={win_loss?.wins ?? 0} losses={win_loss?.losses ?? 0} />}
        />
        <StatCard
          icon="⚠️"
          label="حداکثر ضرر"
          value={`-${summary.max_dd} $`}
          change="—"
          changeType="neutral"
          color="loss"
          chart={<MiniBars
            data={[
              { label: 'بزرگترین ضرر', value: summary.largest_loss ?? 0 },
              { label: 'حداکثر افت', value: summary.max_dd ?? 0 },
            ]}
            colors={['#E45D72', '#F0A6B2']}
          />}
        />
        <StatCard
          icon="🏆"
          label="فاکتور سود"
          value={summary.profit_factor}
          change="—"
          changeType="neutral"
          color="purple"
          chart={<MiniBars
            data={[
              { label: 'سود ناخالص', value: summary.gross_profit ?? 0 },
              { label: 'زیان ناخالص', value: summary.gross_loss ?? 0 },
            ]}
            colors={['#13AE81', '#E45D72']}
          />}
        />
      </div>
      )}
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

{/* پراپ + اهداف */}
      <ErrorBoundary label="پراپ و اهداف">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* وضعیت پراپ */}
        <Card>
          <CardHeader title="🏢 وضعیت پراپ" subtitle={prop_progress.length > 0 ? `${prop_progress.length} مرحله فعال` : undefined} />
          <div className="space-y-6">
            {prop_progress.length === 0 ? (
              <div className="text-[var(--text-muted)] text-center py-4 text-sm">مرحله فعالی وجود ندارد</div>
            ) : (
              prop_progress.slice(0, 3).map((stage: any) => (
                <div key={stage.stage_id}>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm font-bold text-[var(--text-primary)]">{stage.account_label}</span>
                    <Badge variant={stage.ready_to_pass ? 'success' : stage.violations.length > 0 ? 'danger' : 'info'}>
                      {stage.stage_type === 'stage_1' ? '🥇 مرحله ۱' :
                       stage.stage_type === 'stage_2' ? '🥈 مرحله ۲' :
                       stage.stage_type === 'funded_real' ? '💰 رییل' : stage.stage_type}
                    </Badge>
                  </div>
                  <ProgressBar
                    value={Math.min(stage.profit_progress_percent, 100)}
                    variant={stage.ready_to_pass ? 'profit' : stage.violations.length > 0 ? 'loss' : 'profit'}
                  />
                  <div className="flex justify-between mt-1.5">
                    <span className="text-[11px] text-[var(--text-muted)]">
                      {stage.trading_days}/{stage.min_trading_days} روز
                    </span>
                    <span className={`text-[11px] font-bold ${stage.ready_to_pass ? 'text-[var(--profit)]' : 'text-[var(--accent)]'}`}>
                      {Math.round(stage.profit_progress_percent)}٪ پیشرفت
                    </span>
                  </div>
                  {stage.violations.length > 0 && (
                    <div className="mt-2 text-[11px] text-[var(--loss)] font-semibold">
                      ⚠️ {stage.violations[0]}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </Card>

        {/* پیشرفت اهداف (ماهانه/فصلی/سالانه) */}
        <Card>
          <CardHeader title="🎯 پیشرفت اهداف" subtitle="عملکرد واقعی بر اساس PnL" />
          <div className="space-y-6">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-xs text-[var(--text-secondary)]">عملکرد ماه جاری</span>
                <span className={`text-xs font-bold ${periods.month.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                  {periods.month.pnl >= 0 ? '+' : ''}{periods.month.pnl} $
                </span>
              </div>
              <ProgressBar
                value={Math.min(Math.abs(periods.month.change_percent), 100)}
                variant={periods.month.pnl >= 0 ? 'profit' : 'loss'}
              />
              <div className="flex justify-between mt-1.5">
                <span className="text-[11px] text-[var(--text-muted)]">نسبت به ماه قبل</span>
                <span className={`text-[11px] font-bold ${periods.month.change_percent > 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                  {periods.month.change_percent > 0 ? '+' : ''}{periods.month.change_percent}٪
                </span>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="text-xs text-[var(--text-secondary)]">عملکرد فصل جاری</span>
                <span className={`text-xs font-bold ${periods.quarter.pnl >= 0 ? 'text-[var(--accent)]' : 'text-[var(--loss)]'}`}>
                  {periods.quarter.pnl >= 0 ? '+' : ''}{periods.quarter.pnl} $
                </span>
              </div>
              <ProgressBar
                value={Math.min(Math.abs(periods.quarter.pnl / (periods.month.pnl || 1) * 100), 100)}
                variant={periods.quarter.pnl >= 0 ? 'accent' : 'loss'}
              />
              <div className="flex justify-between mt-1.5">
                <span className="text-[11px] text-[var(--text-muted)]">از ابتدای فصل</span>
                <span className={`text-[11px] font-bold ${periods.quarter.pnl >= 0 ? 'text-[var(--accent)]' : 'text-[var(--loss)]'}`}>
                  {periods.quarter.pnl >= 0 ? '+' : ''}{periods.quarter.pnl} $
                </span>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="text-xs text-[var(--text-secondary)]">عملکرد سال جاری</span>
                <span className={`text-xs font-bold ${periods.year.pnl >= 0 ? 'text-[var(--warning)]' : 'text-[var(--loss)]'}`}>
                  {periods.year.pnl >= 0 ? '+' : ''}{periods.year.pnl} $
                </span>
              </div>
              <ProgressBar
                value={Math.min(Math.abs(periods.year.pnl / (periods.month.pnl || 1) * 100), 100)}
                variant={periods.year.pnl >= 0 ? 'warning' : 'loss'}
              />
              <div className="flex justify-between mt-1.5">
                <span className="text-[11px] text-[var(--text-muted)]">از ابتدای سال</span>
                <span className={`text-[11px] font-bold ${periods.year.pnl >= 0 ? 'text-[var(--warning)]' : 'text-[var(--loss)]'}`}>
                  {periods.year.pnl >= 0 ? '+' : ''}{periods.year.pnl} $
                </span>
              </div>
            </div>
          </div>
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
                    className="text-[11px] bg-[var(--bg-card)] px-3 py-1 rounded-full font-bold text-[var(--accent)] hover:bg-[var(--accent-soft)] transition-all"
                  >
                    ✓ خواندم
                  </button>
                </div>
              );
            })}
          </div>
        </Card>
      )}
      </div>
      </ErrorBoundary>

      {/* آمار ریسک پیشرفته (فاز ۱۴.۴) */}
      <ErrorBoundary label="آمار ریسک">
      <Card>
        <CardHeader
          title="🛡️ آمار ریسک پیشرفته"
          subtitle={risk && risk.has_enough_data ? `${risk.total_trades} معامله` : undefined}
        />
        {risk === null ? (
          <div className="text-[var(--text-muted)] text-sm py-6 text-center">در حال بارگذاری…</div>
        ) : !risk.has_enough_data ? (
          <EmptyState icon="🛡️" title="دادهٔ کافی برای تحلیل ریسک نیست" description="حداقل دو معاملهٔ بسته لازم است" />
        ) : (
          <div className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <RiskStat label="Sharpe" value={risk.sharpe_ratio} tip="بازده به ازای ریسک کل (سالیانه) — بالاتر از ۱ مطلوب" tone={sharpeTone(risk.sharpe_ratio)} />
              <RiskStat label="Sortino" value={risk.sortino_ratio} tip="مثل شارپ اما فقط نوسان نزولی را در نظر می‌گیرد" />
              <RiskStat label="Calmar" value={risk.calmar_ratio} tip="بازده سالیانه تقسیم بر حداکثر افت سرمایه" />
              <RiskStat label="Risk of Ruin" value={risk.risk_of_ruin} tip="احتمال از دست دادن کل سرمایه" tone={ruinTone(risk.risk_of_ruin)} />
              <RiskStat label="VaR 95%" value={risk.var_95} tip="حد ضرر مورد انتظار در ۹۵٪ موارد" tone="loss" suffix=" $" />
              <RiskStat label="CVaR 95%" value={risk.cvar_95} tip="میانگین زیان‌های فراتر از VaR" tone="loss" suffix=" $" />
              <RiskStat label="Max Consec. Losses" value={risk.max_consecutive_losses} tip="بیشترین ضررهای متوالی" tone="loss" />
              <RiskStat label="Max Consec. Wins" value={risk.max_consecutive_wins} tip="بیشترین بردهای متوالی" tone="profit" />
              <RiskStat label="Avg R-Multiple" value={risk.avg_r_multiple} tip="میانگین R هر معامله" tone={risk.avg_r_multiple >= 0 ? 'profit' : 'loss'} />
              <RiskStat label="Expectancy (R)" value={risk.expectancy_r} tip="امید ریاضی بر حسب R" tone={risk.expectancy_r >= 0 ? 'profit' : 'loss'} />
              <RiskStat label="Kelly" value={risk.kelly_criterion} tip="کسر بهینهٔ سرمایه برای هر معامله" tone={risk.kelly_criterion > 0 ? 'profit' : 'loss'} />
              <RiskStat label="Recovery Factor" value={risk.recovery_factor} tip="سود خالص تقسیم بر حداکثر افت" />
              <RiskStat label="Ulcer Index" value={risk.ulcer_index} tip="شدت و مدت افت‌ها — کمتر بهتر" />
              <RiskStat label="Max Drawdown" value={risk.max_drawdown} tip="بیشترین افت سرمایه از سقف" tone="loss" suffix=" $" />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div>
                <div className="text-sm font-bold text-[var(--text-primary)] mb-2">توزیع R-Multiple</div>
                {risk.r_multiple_distribution?.some((b: any) => b.count > 0) ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={risk.r_multiple_distribution} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                      <XAxis dataKey="range" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} stroke="var(--text-secondary)" />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} stroke="var(--text-secondary)" />
                      <Tooltip contentStyle={MINI_TOOLTIP} formatter={(v: any) => [`${v} معامله`, 'تعداد']} />
                      <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                        {risk.r_multiple_distribution.map((_: any, i: number) => (
                          <Cell key={i} fill={i < 3 ? '#E45D72' : i === 3 ? '#9AA8BF' : '#13AE81'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-[var(--text-muted)] text-sm py-6 text-center">داده‌ای برای R-Multiple ثبت نشده</div>
                )}
              </div>
              <div>
                <div className="text-sm font-bold text-[var(--text-primary)] mb-2">منحنی افت سرمایه (Drawdown)</div>
                {risk.drawdown_curve?.length > 1 ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <AreaChart data={risk.drawdown_curve} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#E45D72" stopOpacity={0.35} />
                          <stop offset="95%" stopColor="#E45D72" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                      <XAxis dataKey="index" stroke="var(--text-secondary)" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} />
                      <YAxis stroke="var(--text-secondary)" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                      <Tooltip contentStyle={MINI_TOOLTIP} formatter={(v: any) => [`${v} $`, 'افت']} labelFormatter={(l: any) => `معامله #${l}`} />
                      <Area type="monotone" dataKey="drawdown" stroke="#E45D72" strokeWidth={2} fill="url(#ddGradient)" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-[var(--text-muted)] text-sm py-6 text-center">داده کافی نیست</div>
                )}
              </div>
            </div>
          </div>
        )}
      </Card>
      </ErrorBoundary>

      {/* ویجت مالی (فاز ۱۴.۲) */}
      <ErrorBoundary label="ویجت مالی">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Card>
          <CardHeader title="💰 موجودی کل" />
          {finance?.summary ? (
            <div>
              <div className="text-2xl font-extrabold text-[var(--text-primary)]">
                {Object.values(finance.summary.assets_by_currency || {})
                  .reduce((a: number, b: any) => a + Number(b || 0), 0)
                  .toLocaleString()}
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
          <CardHeader title="💵 جریان نقدی" subtitle="۶ ماه اخیر" />
          {finance?.cashflow?.length ? (
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={finance.cashflow.slice(-6)}>
                <XAxis dataKey="month" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} stroke="var(--text-secondary)" />
                <Tooltip contentStyle={MINI_TOOLTIP} />
                <Bar dataKey="income" fill="#13AE81" radius={[4, 4, 0, 0]} name="درآمد" />
                <Bar dataKey="expense" fill="#E45D72" radius={[4, 4, 0, 0]} name="هزینه" />
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
                    <span className="text-[10px] text-[var(--text-secondary)]">{a.currency}</span>
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[var(--text-muted)] text-sm py-4">حسابی ثبت نشده</div>
          )}
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
                          {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)} $
                        </td>
                        <td className="py-2.5 px-2 text-[11px] text-[var(--text-secondary)]">
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
                          {hasPnl ? `${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)} $` : '—'}
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
