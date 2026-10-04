import type { ReactNode } from 'react';

interface StatCardProps {
  icon: string;
  label: string;
  value: string | number;
  change?: string;
  changeType?: 'up' | 'down' | 'neutral';
  color?: 'profit' | 'loss' | 'accent' | 'purple' | 'warning';
  sparkData?: number[];
  /** نمودار سفارشی کارت (جایگزین sparkline) */
  chart?: ReactNode;
}

const COLOR_CONFIG = {
  profit: {
    value: 'text-[var(--profit)]',
    icon: 'bg-[var(--profit-soft)]',
    bar: 'bg-gradient-to-b from-[var(--profit)] to-[var(--profit-border)]',
    top: 'from-[var(--profit)] to-[var(--profit-border)]',
    glow: 'var(--profit)',
    hoverShadow: '0 20px 40px rgba(19,174,129,0.15), 0 8px 16px rgba(25,50,85,0.08)',
  },
  loss: {
    value: 'text-[var(--loss)]',
    icon: 'bg-[var(--loss-soft)]',
    bar: 'bg-gradient-to-b from-[var(--loss)] to-[var(--loss-border)]',
    top: 'from-[var(--loss)] to-[var(--loss-border)]',
    glow: 'var(--loss)',
    hoverShadow: '0 20px 40px rgba(228,93,114,0.15), 0 8px 16px rgba(25,50,85,0.08)',
  },
  accent: {
    value: 'text-[var(--text-primary)]',
    icon: 'bg-[var(--accent-soft)]',
    bar: 'bg-gradient-to-b from-[var(--accent)] to-[var(--accent-strong)]',
    top: 'from-[var(--accent)] to-[var(--accent-strong)]',
    glow: 'var(--accent)',
    hoverShadow: '0 20px 40px rgba(63,124,255,0.15), 0 8px 16px rgba(25,50,85,0.08)',
  },
  purple: {
    value: 'text-[var(--purple)]',
    icon: 'bg-[var(--purple-soft)]',
    bar: 'bg-gradient-to-b from-[var(--purple)] to-[var(--purple-border)]',
    top: 'from-[var(--purple)] to-[var(--purple-border)]',
    glow: 'var(--purple)',
    hoverShadow: '0 20px 40px rgba(121,89,214,0.15), 0 8px 16px rgba(25,50,85,0.08)',
  },
  warning: {
    value: 'text-[var(--warning)]',
    icon: 'bg-[var(--warning-soft)]',
    bar: 'bg-gradient-to-b from-[var(--warning)] to-[var(--warning-border)]',
    top: 'from-[var(--warning)] to-[var(--warning-border)]',
    glow: 'var(--warning)',
    hoverShadow: '0 20px 40px rgba(217,155,37,0.15), 0 8px 16px rgba(25,50,85,0.08)',
  },
};

export default function StatCard({
  icon,
  label,
  value,
  change,
  changeType = 'up',
  color = 'accent',
  sparkData = [30, 55, 40, 70, 60, 85, 75, 95],
  chart,
}: StatCardProps) {
  const cfg = COLOR_CONFIG[color];

  // نرمال‌سازی sparkData به بازهٔ ۱۲–۱۰۰٪ (رفع باگ مقیاس — فاز ۱۴.۱)
  const values = (sparkData || []).map((v) => (Number.isFinite(Number(v)) ? Number(v) : 0));
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 0;
  const span = max - min;
  const normalized = values.length === 0
    ? [60]
    : values.map((v) => (span === 0 ? 60 : 12 + ((v - min) / span) * 88));

  const changeBadgeClass =
    changeType === 'up'
      ? 'bg-[var(--profit-soft)] text-[var(--profit)]'
      : changeType === 'down'
        ? 'bg-[var(--loss-soft)] text-[var(--loss)]'
        : 'bg-[var(--bg-elevated)] text-[var(--text-secondary)]';

  const changeArrow = changeType === 'up' ? '▲' : changeType === 'down' ? '▼' : '–';

  return (
    <div
      className="group bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5 relative overflow-hidden cursor-pointer transition-all duration-300 shadow-md hover:-translate-y-1.5 hover:border-[var(--border-accent)]"
      onMouseEnter={(e) => { e.currentTarget.style.boxShadow = cfg.hoverShadow; }}
      onMouseLeave={(e) => { e.currentTarget.style.boxShadow = ''; }}
    >
      <div className={`absolute top-0 right-0 left-0 h-1 bg-gradient-to-r ${cfg.top} opacity-0 group-hover:opacity-100 transition-opacity`} />

      <div
        className="absolute -top-[60px] -left-[60px] w-[120px] h-[120px] rounded-full pointer-events-none transition-all duration-500 group-hover:-top-10 group-hover:-left-10 group-hover:w-40 group-hover:h-40"
        style={{ background: `radial-gradient(circle, ${cfg.glow}, transparent 70%)` }}
      />

      <div className="flex justify-between items-start mb-3.5 relative">
        <div className={`w-[46px] h-[46px] rounded-[14px] flex items-center justify-center text-[22px] ${cfg.icon}`}>
          {icon}
        </div>
        {change && (
          <div className={`text-[11px] font-bold px-2.5 py-1 rounded-full ${changeBadgeClass}`}>
            {changeArrow} {change}
          </div>
        )}
      </div>

      <div className="text-xs text-[var(--text-secondary)] mb-1.5 font-medium relative">{label}</div>
      <div className={`text-[30px] font-extrabold tracking-tight leading-tight ${cfg.value} relative`}>
        {value}
      </div>

      {chart ? (
        <div className="mt-3.5 relative">{chart}</div>
      ) : (
        <div className="flex items-end gap-[3px] h-[38px] mt-3.5 relative">
          {normalized.map((height, idx) => (
            <div
              key={idx}
              className={`flex-1 rounded-t-[3px] ${cfg.bar} opacity-50 group-hover:opacity-90 transition-all duration-300`}
              style={{ height: `${Math.max(0, Math.min(height, 100))}%` }}
            />
          ))}
        </div>
      )}
    </div>
  );
}