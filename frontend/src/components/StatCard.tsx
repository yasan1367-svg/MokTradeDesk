interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  color?: 'profit' | 'loss' | 'accent' | 'default';
}

export default function StatCard({ label, value, sub, color = 'default' }: StatCardProps) {
  const colorClass = {
    profit: 'text-[var(--profit)]',
    loss: 'text-[var(--loss)]',
    accent: 'text-[var(--accent)]',
    default: 'text-[var(--text-primary)]',
  }[color];

  return (
    <div className="glass-card p-5">
      <div className="text-[var(--text-secondary)] text-sm mb-2">{label}</div>
      <div className={`text-3xl font-bold ${colorClass}`}>{value}</div>
      {sub && <div className="text-[var(--text-secondary)] text-xs mt-2">{sub}</div>}
    </div>
  );
}