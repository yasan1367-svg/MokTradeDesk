import type { ReactNode } from 'react';

interface KpiCardProps {
  icon: string;
  label: string;
  value: string | number;
  valueColor?: 'profit' | 'loss' | 'neutral' | 'accent';
  subtitle?: string;
  hint?: string;
}

export default function KpiCard({
  icon,
  label,
  value,
  valueColor = 'neutral',
  subtitle,
  hint,
}: KpiCardProps) {
  const colorMap = {
    profit: 'var(--profit)',
    loss: 'var(--loss)',
    accent: 'var(--accent)',
    neutral: 'var(--text-primary)',
  };

  const borderMap = {
    profit: 'var(--profit)',
    loss: 'var(--loss)',
    accent: 'var(--accent)',
    neutral: 'var(--border-subtle)',
  };

  return (
    <div
      className="relative rounded-[18px] p-5 transition-all hover:shadow-lg hover:-translate-y-0.5"
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-subtle)',
        borderTop: `3px solid ${borderMap[valueColor]}`,
        boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">{icon}</span>
        <span
          className="text-[11px] font-bold uppercase tracking-wider"
          style={{ color: 'var(--text-secondary)' }}
        >
          {label}
        </span>
      </div>

      <div
        className="text-[26px] font-black tabular-nums mb-1"
        style={{ color: colorMap[valueColor] }}
        title={hint}
      >
        {value}
      </div>

      {subtitle && (
        <div className="text-[12px] font-medium" style={{ color: 'var(--text-secondary)' }}>
          {subtitle}
        </div>
      )}
    </div>
  );
}