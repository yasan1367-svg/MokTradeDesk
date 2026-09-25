import { useState, useEffect } from 'react';
import StatCard from '../components/ui/StatCard';
import { Card, CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import ProgressBar from '../components/ui/ProgressBar';
import { getDashboardData, exportDashboardPdf, getPropAlerts, markAlertRead } from '../api/client';
import { DashboardSkeleton } from '../components/Skeleton';

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

const [alerts, setAlerts] = useState<any[]>([]);
  useEffect(() => {
    getDashboardData()
      .then((res) => {
        setData(res.data);
        setLoading(false);
      })
      .catch((err: any) => {
        setError(err.response?.data?.detail || 'خطا در بارگذاری داشبورد');
        setLoading(false);
      });
    // بارگذاری هشدارها
    getPropAlerts({ unread_only: true }).then((r) => setAlerts(r.data)).catch(() => {});
  }, []);

  if (loading) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-[var(--loss)] text-lg">❌ {error}</div>
      </div>
    );
  }

  if (!data) return null;

  const { summary, today, sparkline, periods, prop_progress } = data;

  const getChangeType = (value: number): 'up' | 'down' | 'neutral' => {
    if (value > 0) return 'up';
    if (value < 0) return 'down';
    return 'neutral';
  };

  return (
    <div className="space-y-7">
      {/* هدر */}
      <div className="flex justify-between items-center">
        <h2 className="text-[var(--text-primary)] text-2xl font-extrabold">📊 داشبورد</h2>
        <button
          onClick={async () => {
            try {
              const res = await exportDashboardPdf();
              const blob = new Blob([res.data], { type: 'application/pdf' });
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `dashboard_${new Date().toISOString().slice(0, 10)}.pdf`;
              document.body.appendChild(a); a.click();
              window.URL.revokeObjectURL(url); a.remove();
            } catch { /* ignore */ }
          }}
          className="bg-[#E45D72] hover:bg-[#E45D72]/80 text-white px-5 py-2.5 rounded-xl text-sm flex items-center gap-1 transition-all"
        >
          📄 دانلود گزارش PDF
        </button>
      </div>

      {/* کارت‌های آماری */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          icon="💰"
          label="سود خالص"
          value={`${summary.net_pnl >= 0 ? '+' : ''}${summary.net_pnl} $`}
          change={periods.month.change_percent > 0 ? `+${periods.month.change_percent}٪` : `${periods.month.change_percent}٪`}
          changeType={getChangeType(periods.month.change_percent)}
          color="profit"
          sparkData={sparkline.length > 0 ? sparkline : [0]}
        />
        <StatCard
          icon="📈"
          label="نرخ برد"
          value={`${summary.win_rate}٪`}
          change="—"
          changeType="neutral"
          color="accent"
          sparkData={sparkline.length > 0 ? sparkline : [0]}
        />
        <StatCard
          icon="⚠️"
          label="حداکثر ضرر"
          value={`-${summary.max_dd} $`}
          change="—"
          changeType="neutral"
          color="loss"
          sparkData={sparkline.length > 0 ? sparkline : [0]}
        />
        <StatCard
          icon="🏆"
          label="فاکتور سود"
          value={summary.profit_factor}
          change="—"
          changeType="neutral"
          color="purple"
          sparkData={sparkline.length > 0 ? sparkline : [0]}
        />
      </div>

      {/* Hero Card — امروز */}
      <div
        className="relative rounded-[28px] p-8 flex justify-between items-center flex-wrap gap-7 overflow-hidden shadow-lg border border-[var(--border-accent)]"
        style={{ background: 'linear-gradient(135deg, #FFFFFF 0%, #F0F6FF 100%)' }}
      >
        <div
          className="absolute top-0 right-0 left-0 h-1"
          style={{ background: 'linear-gradient(90deg, #3F7CFF, #7959D6, #13AE81)' }}
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
          <div className="flex items-center gap-4 mt-3">
            <div className="text-sm text-[var(--text-secondary)]">
              <span className="font-bold">{today.trades_count}</span> معامله
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
          <div className="text-center bg-white/70 backdrop-blur rounded-[16px] px-5 py-3 border border-[var(--border-subtle)] min-w-[120px]">
            <div className="text-[11px] text-[var(--text-secondary)] font-bold">این ماه</div>
            <div className={`text-lg font-extrabold ${periods.month.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
              {periods.month.pnl >= 0 ? '+' : ''}{periods.month.pnl} $
            </div>
          </div>
          <div className="text-center bg-white/70 backdrop-blur rounded-[16px] px-5 py-3 border border-[var(--border-subtle)] min-w-[120px]">
            <div className="text-[11px] text-[var(--text-secondary)] font-bold">این فصل</div>
            <div className={`text-lg font-extrabold ${periods.quarter.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
              {periods.quarter.pnl >= 0 ? '+' : ''}{periods.quarter.pnl} $
            </div>
          </div>
          <div className="text-center bg-white/70 backdrop-blur rounded-[16px] px-5 py-3 border border-[var(--border-subtle)] min-w-[120px]">
            <div className="text-[11px] text-[var(--text-secondary)] font-bold">امسال</div>
            <div className={`text-lg font-extrabold ${periods.year.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
              {periods.year.pnl >= 0 ? '+' : ''}{periods.year.pnl} $
            </div>
          </div>
        </div>
      </div>
{/* پراپ + اهداف */}
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
    </div>
  );
}
