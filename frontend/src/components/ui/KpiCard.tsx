interface KpiCardProps {
  icon: string;
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
  return (
    <div
      className="kpi-card relative rounded-[16px] p-5 transition-all duration-300 cursor-default"
      style={{
        background: `linear-gradient(150deg, var(--bg-card) 55%, var(--kpi-${valueColor}-tint))`,
        borderTop: `3px solid var(--kpi-${valueColor}-tone)`,
        borderLeft: '1px solid var(--border-subtle)',
        borderRight: '1px solid var(--border-subtle)',
        borderBottom: '1px solid var(--border-subtle)',
        boxShadow: '0 2px 4px rgba(27,58,107,0.04), 0 8px 20px -6px rgba(27,58,107,0.10)',
        animationDelay: `${index * 0.05}s`,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 4px 8px rgba(27,58,107,0.06), 0 16px 32px -8px rgba(27,58,107,0.18)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = '0 2px 4px rgba(27,58,107,0.04), 0 8px 20px -6px rgba(27,58,107,0.10)';
      }}
    >
      {/* هدر: label سمت چپ، آیکن توی دایره سمت راست */}
      <div className="flex items-center justify-between gap-3 mb-3">
        <span
          className="text-[11px] font-semibold"
          style={{ color: 'var(--text-muted)' }}
        >
          {label}
        </span>
        <span
          className="w-8 h-8 rounded-[10px] flex items-center justify-center text-base shrink-0"
          style={{
            background: `var(--kpi-${valueColor}-tint)`,
            color: `var(--kpi-${valueColor}-tone)`,
          }}
        >
          {icon}
        </span>
      </div>

      {/* عدد بزرگ */}
      <div
        className="text-[24px] font-black tabular-nums leading-tight mb-1"
        style={{ color: `var(--kpi-${valueColor}-tone)` }}
        title={hint}
      >
        {value}
      </div>

      {/* زیرنویس */}
      {subtitle && (
        <div className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
          {subtitle}
        </div>
      )}
    </div>
  );
}