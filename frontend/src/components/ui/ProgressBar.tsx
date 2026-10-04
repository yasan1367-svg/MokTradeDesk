interface ProgressBarProps {
  value: number;
  variant?: 'profit' | 'loss' | 'accent' | 'warning';
}

const VARIANTS = {
  accent: 'bg-gradient-to-r from-[var(--accent)] to-[var(--accent-strong)] shadow-[0_2px_6px_var(--accent-soft)]',
  profit: 'bg-gradient-to-r from-[var(--profit)] to-[var(--profit-border)] shadow-[0_2px_6px_var(--profit-soft)]',
  warning: 'bg-gradient-to-r from-[var(--warning)] to-[var(--warning-border)] shadow-[0_2px_6px_var(--warning-soft)]',
  loss: 'bg-gradient-to-r from-[var(--loss)] to-[var(--loss-border)] shadow-[0_2px_6px_var(--loss-soft)]',
};

export default function ProgressBar({ value, variant = 'accent' }: ProgressBarProps) {
  return (
    <div className="h-2 bg-[var(--bg-elevated)] rounded-full overflow-hidden shadow-[inset_0_1px_2px_rgba(0,0,0,0.04)]">
      <div
        className={`h-full rounded-full transition-all duration-500 ${VARIANTS[variant]}`}
        style={{ width: `${Math.min(value, 100)}%` }}
      />
    </div>
  );
}