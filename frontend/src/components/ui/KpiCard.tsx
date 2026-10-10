import type { ReactNode } from 'react';

interface KpiCardProps {
  icon: ReactNode;
  label: string;
  value: string | number;
  valueColor?: 'profit' | 'loss' | 'neutral' | 'accent' | 'purple' | 'warning';
  subtitle?: string;
  hint?: string;
  index?: number;
}

export default function KpiCard({
  icon,
  label,
  value,
  valueColor = 'neutral',
  subtitle,
  hint,
  index = 0,
}: KpiCardProps) {
  const tone = `var(--kpi-${valueColor}-tone)`;
  const tint = `var(--kpi-${valueColor}-tint)`;

  return (
    <div
      className="app-card kpi-card relative p-5 cursor-default"
      style={{
        background: `linear-gradient(145deg, var(--bg-card) 55%, ${tint})`,
        borderTopWidth: 2,
        borderTopStyle: 'solid',
        borderTopColor: tone,
        animationDelay: `${index * 0.05}s`,
      }}
    >
      <div className="flex items-center justify-between gap-3 mb-3">
        <span className="text-[11px] font-semibold" style={{ color: 'var(--text-secondary)' }}>
          {label}
        </span>
        <span
          className="w-8 h-8 rounded-[10px] flex items-center justify-center text-base shrink-0"
          style={{ background: tint, color: tone }}
        >
          {icon}
        </span>
      </div>

      <div
        className="kpi-value font-extrabold tabular-nums leading-tight mb-1"
        style={{ color: tone, letterSpacing: '-0.5px' }}
        title={hint}
      >
        {value}
      </div>

      {subtitle && (
        <div className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
          {subtitle}
        </div>
      )}
    </div>
  );
}
