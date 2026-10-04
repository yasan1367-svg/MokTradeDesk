interface BadgeProps {
  children: string;
  variant?: 'success' | 'danger' | 'info' | 'warning';
}

export default function Badge({ children, variant = 'success' }: BadgeProps) {
  const variants = {
    success: 'bg-[var(--profit-soft)] text-[var(--profit)]',
    danger: 'bg-[var(--loss-soft)] text-[var(--loss)]',
    info: 'bg-[var(--accent-soft)] text-[var(--accent)]',
    warning: 'bg-[var(--warning-soft)] text-[var(--warning)]',
  };

  return (
    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-[11px] font-bold ${variants[variant]}`}>
      {children}
    </span>
  );
}