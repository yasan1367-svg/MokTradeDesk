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
    value: 'text-[#13AE81]',
    icon: 'bg-[#E5F8F1] shadow-[0_4px_12px_rgba(19,174,129,0.15)]',
    bar: 'bg-gradient-to-b from-[#13AE81] to-[#4DD9A9]',
    top: 'from-[#13AE81] to-[#4DD9A9]',
    glow: 'rgba(19,174,129,0.08)',
    hoverShadow: '0 20px 40px rgba(19,174,129,0.15), 0 8px 16px rgba(25,50,85,0.08)',
  },
  loss: {
    value: 'text-[#E45D72]',
    icon: 'bg-[#FFEDF0] shadow-[0_4px_12px_rgba(228,93,114,0.15)]',
    bar: 'bg-gradient-to-b from-[#E45D72] to-[#F0A6B2]',
    top: 'from-[#E45D72] to-[#F0A6B2]',
    glow: 'rgba(228,93,114,0.08)',
    hoverShadow: '0 20px 40px rgba(228,93,114,0.15), 0 8px 16px rgba(25,50,85,0.08)',
  },
  accent: {
    value: 'text-[#1A2B47]',
    icon: 'bg-[#EDF3FF] shadow-[0_4px_12px_rgba(63,124,255,0.12)]',
    bar: 'bg-gradient-to-b from-[#3F7CFF] to-[#5B8DEF]',
    top: 'from-[#3F7CFF] to-[#7959D6]',
    glow: 'rgba(63,124,255,0.08)',
    hoverShadow: '0 20px 40px rgba(63,124,255,0.15), 0 8px 16px rgba(25,50,85,0.08)',
  },
  purple: {
    value: 'text-[#7959D6]',
    icon: 'bg-[#F1ECFF] shadow-[0_4px_12px_rgba(121,89,214,0.15)]',
    bar: 'bg-gradient-to-b from-[#7959D6] to-[#A78BFA]',
    top: 'from-[#7959D6] to-[#A78BFA]',
    glow: 'rgba(121,89,214,0.08)',
    hoverShadow: '0 20px 40px rgba(121,89,214,0.15), 0 8px 16px rgba(25,50,85,0.08)',
  },
  warning: {
    value: 'text-[#D99B25]',
    icon: 'bg-[#FFF5DB] shadow-[0_4px_12px_rgba(217,155,37,0.15)]',
    bar: 'bg-gradient-to-b from-[#D99B25] to-[#F0BE5C]',
    top: 'from-[#D99B25] to-[#F0BE5C]',
    glow: 'rgba(217,155,37,0.08)',
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
      ? 'bg-[#E5F8F1] text-[#13AE81]'
      : changeType === 'down'
        ? 'bg-[#FFEDF0] text-[#E45D72]'
        : 'bg-[#F1F4F9] text-[#6B7A94]';

  const changeArrow = changeType === 'up' ? '▲' : changeType === 'down' ? '▼' : '–';

  return (
    <div
      className="group bg-white border border-[#E5EBF3] rounded-[22px] p-5 relative overflow-hidden cursor-pointer transition-all duration-300 shadow-md hover:-translate-y-1.5 hover:border-[#A9C1FA]"
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

      <div className="text-xs text-[#6B7A94] mb-1.5 font-medium relative">{label}</div>
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