import { useState, useEffect } from 'react';
import { getRiskMetrics } from '../api/client';
import { RiskSkeleton } from '../components/Skeleton';

const getStatusStyle = (status: string) => {
  if (status === 'danger') return { bg: 'bg-[var(--loss-soft)]', text: 'text-[var(--loss)]', border: 'border-[var(--loss-border)]', icon: '🔴' };
  if (status === 'warning') return { bg: 'bg-[var(--warning-soft-alt)]', text: 'text-[var(--warning)]', border: 'border-[var(--warning-border)]', icon: '🟡' };
  return { bg: 'bg-[var(--profit-soft)]', text: 'text-[var(--profit)]', border: 'border-[var(--profit-border)]', icon: '🟢' };
};

export default function RiskManagementPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getRiskMetrics()
      .then((res) => { setData(res.data); setLoading(false); })
      .catch((err: any) => { setError(err.response?.data?.detail || 'خطا در بارگذاری'); setLoading(false); });
  }, []);

  if (loading) return <RiskSkeleton />;
  if (error) return <div className="text-center py-16 text-[var(--loss)]">❌ {error}</div>;
  if (!data) return null;

  const { performance_ratios, risk_metrics, status } = data;
  const ss = getStatusStyle(status);

  return (
    <div className="space-y-6">
      {/* وضعیت کلی */}
      <div className={`rounded-[22px] p-6 border-2 ${ss.bg} ${ss.border}`}>
        <div className="flex items-center gap-4 flex-wrap">
          <div className={`w-16 h-16 rounded-full flex items-center justify-center text-3xl ${ss.bg} border-2 ${ss.border}`}>
            {ss.icon}
          </div>
          <div>
            <div className={`text-lg font-extrabold ${ss.text}`}>
              {status === 'safe' ? 'وضعیت ریسک: امن' : status === 'warning' ? 'وضعیت ریسک: هشدار' : 'وضعیت ریسک: خطر'}
            </div>
            <div className="text-sm text-[var(--text-secondary)] mt-1">
              {status === 'safe' ? 'همه شاخص‌های ریسک در محدوده‌ی امن قرار دارند.' :
               status === 'warning' ? 'برخی شاخص‌ها نیاز به توجه دارند.' :
               'خطرناک — نیاز به اقدام فوری!'}
            </div>
          </div>
        </div>
      </div>

      {/* کارت‌های شاخص */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5 shadow-md">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-[12px] bg-[var(--bg-input)] flex items-center justify-center text-lg">📈</div>
            <span className="text-[12px] text-[var(--text-secondary)] font-bold">Sharpe Ratio</span>
          </div>
          <div className="text-[22px] font-extrabold text-[var(--text-primary)]">{performance_ratios.sharpe_ratio}</div>
          <div className={`text-[11px] font-bold mt-1 ${performance_ratios.sharpe_ratio >= 1 ? 'text-[var(--profit)]' : performance_ratios.sharpe_ratio >= 0.5 ? 'text-[var(--warning)]' : 'text-[var(--loss)]'}`}>
            {performance_ratios.sharpe_ratio >= 1 ? '🟢 خوب' : performance_ratios.sharpe_ratio >= 0.5 ? '🟡 متوسط' : '🔴 ضعیف'}
          </div>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5 shadow-md">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-[12px] bg-[var(--bg-input)] flex items-center justify-center text-lg">📉</div>
            <span className="text-[12px] text-[var(--text-secondary)] font-bold">Sortino Ratio</span>
          </div>
          <div className="text-[22px] font-extrabold text-[var(--text-primary)]">{performance_ratios.sortino_ratio}</div>
          <div className={`text-[11px] font-bold mt-1 ${performance_ratios.sortino_ratio >= 1 ? 'text-[var(--profit)]' : performance_ratios.sortino_ratio >= 0.5 ? 'text-[var(--warning)]' : 'text-[var(--loss)]'}`}>
            {performance_ratios.sortino_ratio >= 1 ? '🟢 خوب' : performance_ratios.sortino_ratio >= 0.5 ? '🟡 متوسط' : '🔴 ضعیف'}
          </div>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5 shadow-md">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-[12px] bg-[var(--bg-input)] flex items-center justify-center text-lg">💀</div>
            <span className="text-[12px] text-[var(--text-secondary)] font-bold">Risk of Ruin</span>
          </div>
          <div className="text-[22px] font-extrabold text-[var(--text-primary)]">
            {risk_metrics.risk_of_ruin == null ? '—' : `${(risk_metrics.risk_of_ruin * 100).toFixed(2)}٪`}
          </div>
          <div className={`text-[11px] font-bold mt-1 ${risk_metrics.risk_of_ruin == null ? 'text-[var(--text-secondary)]' : risk_metrics.risk_of_ruin < 0.05 ? 'text-[var(--profit)]' : risk_metrics.risk_of_ruin < 0.2 ? 'text-[var(--warning)]' : 'text-[var(--loss)]'}`}>
            {risk_metrics.risk_of_ruin == null ? 'دادهٔ R کافی نیست' : risk_metrics.risk_of_ruin < 0.05 ? '🟢 کم' : risk_metrics.risk_of_ruin < 0.2 ? '🟡 متوسط' : '🔴 زیاد'}
          </div>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5 shadow-md">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-[12px] bg-[var(--bg-input)] flex items-center justify-center text-lg">⚖️</div>
            <span className="text-[12px] text-[var(--text-secondary)] font-bold">Expectancy (R)</span>
          </div>
          <div className="text-[22px] font-extrabold text-[var(--text-primary)]">{performance_ratios.expectancy_r}</div>
          <div className={`text-[11px] font-bold mt-1 ${performance_ratios.expectancy_r > 0.5 ? 'text-[var(--profit)]' : performance_ratios.expectancy_r > 0 ? 'text-[var(--warning)]' : 'text-[var(--loss)]'}`}>
            {performance_ratios.expectancy_r > 0.5 ? '🟢 خوب' : performance_ratios.expectancy_r > 0 ? '🟡 مثبت' : '🔴 منفی'}
          </div>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-6">
        {/* Risk Metrics */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
          <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
            <div className="w-11 h-11 rounded-[14px] bg-[var(--loss-soft)] flex items-center justify-center text-xl">⚠️</div>
            <div>
              <h3 className="text-base font-extrabold text-[var(--text-primary)]">شاخص‌های ریسک</h3>
              <p className="text-[12px] text-[var(--text-secondary)]">بر اساس {risk_metrics.total_trades} معامله</p>
            </div>
          </div>
          <div className="space-y-3">
            <RiskRow label="حداکثر ضرر متوالی" value={`${risk_metrics.max_consecutive_losses} مرتبه`} status={risk_metrics.max_consecutive_losses > 5 ? 'danger' : risk_metrics.max_consecutive_losses > 3 ? 'warning' : 'safe'} />
            <RiskRow label="عمق Drawdown" value={`USDT ${risk_metrics.max_drawdown_depth.toFixed(2)}`} status={risk_metrics.max_drawdown_depth > 2000 ? 'danger' : risk_metrics.max_drawdown_depth > 1000 ? 'warning' : 'safe'} />
            <RiskRow label="مدت Drawdown" value={`${risk_metrics.max_drawdown_duration} معامله`} status={risk_metrics.max_drawdown_duration > 10 ? 'danger' : risk_metrics.max_drawdown_duration > 5 ? 'warning' : 'safe'} />
            <RiskRow label="Exposure باز" value={`USDT ${risk_metrics.open_exposure.toFixed(2)} (${risk_metrics.open_risk_percent.toFixed(1)}٪)`} status={risk_metrics.open_risk_percent > 20 ? 'danger' : risk_metrics.open_risk_percent > 10 ? 'warning' : 'safe'} />
            <RiskRow label="VaR 95%" value={`USDT ${risk_metrics.var_95.toFixed(2)} (${risk_metrics.var_95_percent.toFixed(2)}٪)`} status={risk_metrics.var_95_percent > 5 ? 'danger' : risk_metrics.var_95_percent > 2 ? 'warning' : 'safe'} />
            <RiskRow label="CVaR 95%" value={`USDT ${risk_metrics.cvar_95.toFixed(2)} (${risk_metrics.cvar_95_percent.toFixed(2)}٪)`} status={risk_metrics.cvar_95_percent > 5 ? 'danger' : risk_metrics.cvar_95_percent > 2 ? 'warning' : 'safe'} />
          </div>
        </div>
      </div>

      {/* Performance Ratios */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
        <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
          <div className="w-11 h-11 rounded-[14px] bg-[var(--profit-soft)] flex items-center justify-center text-xl">🏆</div>
          <div>
            <h3 className="text-base font-extrabold text-[var(--text-primary)]">نسبت‌های عملکردی</h3>
            <p className="text-[12px] text-[var(--text-secondary)]">تحلیل جامع بازده و ریسک</p>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <PerfItem label="Win Rate" value={`${performance_ratios.win_rate}٪`} color={performance_ratios.win_rate >= 50 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'} />
          <PerfItem label="Profit Factor" value={performance_ratios.profit_factor} color={performance_ratios.profit_factor >= 1.5 ? 'text-[var(--profit)]' : performance_ratios.profit_factor >= 1 ? 'text-[var(--warning)]' : 'text-[var(--loss)]'} />
          <PerfItem label="Avg R-Multiple" value={performance_ratios.avg_r_multiple} color={performance_ratios.avg_r_multiple >= 1 ? 'text-[var(--profit)]' : performance_ratios.avg_r_multiple > 0 ? 'text-[var(--warning)]' : 'text-[var(--loss)]'} />
          <PerfItem label="R:R Ratio" value={performance_ratios.rr_ratio} color={performance_ratios.rr_ratio >= 2 ? 'text-[var(--profit)]' : 'text-[var(--warning)]'} />
          <PerfItem label="Avg Win" value={`USDT ${performance_ratios.avg_win}`} color="text-[var(--profit)]" />
          <PerfItem label="Avg Loss" value={`USDT ${performance_ratios.avg_loss}`} color="text-[var(--loss)]" />
          <PerfItem label="Expectancy" value={`USDT ${performance_ratios.expectancy}`} color={performance_ratios.expectancy > 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'} />
          <PerfItem label="Expectancy (R)" value={performance_ratios.expectancy_r} color={performance_ratios.expectancy_r > 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'} />
        </div>
      </div>
    </div>
  );
}
// ── کامپوننت‌های کمکی ──
function RiskRow({ label, value, status }: any) {
  const color = status === 'danger' ? 'text-[var(--loss)]' : status === 'warning' ? 'text-[var(--warning)]' : 'text-[var(--profit)]';
  const icon = status === 'danger' ? '🔴' : status === 'warning' ? '🟡' : '🟢';
  return (
    <div className="flex justify-between items-center bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[12px] px-4 py-3">
      <span className="text-[13px] font-bold text-[var(--text-primary)]">{icon} {label}</span>
      <span className={`text-[14px] font-extrabold ${color}`}>{value}</span>
    </div>
  );
}

function PerfItem({ label, value, color }: any) {
  return (
    <div className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[14px] p-4 text-center">
      <div className="text-[11px] text-[var(--text-secondary)] font-bold mb-1.5">{label}</div>
      <div className={`text-[16px] font-extrabold ${color}`}>{value}</div>
    </div>
  );
}
