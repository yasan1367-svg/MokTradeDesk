interface MetricCardProps {
  label: string;
  value: string | number;
  sub?: string;
  color?: 'profit' | 'loss' | 'accent' | 'default';
  icon?: string;
}

export default function MetricCard({ label, value, sub, color = 'default', icon }: MetricCardProps) {
  const colorClass = {
    profit: 'text-[var(--profit)]',
    loss: 'text-[var(--loss)]',
    accent: 'text-[var(--accent)]',
    default: 'text-[var(--text-primary)]',
  }[color];

  return (
    <div className="glass-card p-5">
      <div className="flex justify-between items-start mb-2">
        <div className="text-[var(--text-secondary)] text-sm">{label}</div>
        {icon && <div className="text-xl">{icon}</div>}
      </div>
      <div className={`text-3xl font-bold ${colorClass}`}>{value}</div>
      {sub && <div className="text-[var(--text-secondary)] text-xs mt-2">{sub}</div>}
    </div>
  );
}