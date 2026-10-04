interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  actionLabel?: string;
  actionIcon?: string;
  onAction?: () => void;
}

/**
 * EmptyState — نمایش حالت خالی با دکمه‌ی اقدام (افزودن)
 */
export default function EmptyState({
  icon = '📭',
  title,
  description,
  actionLabel,
  actionIcon = '➕',
  onAction,
}: EmptyStateProps) {
  return (
    <div className="text-center py-16 text-[var(--text-secondary)]" dir="rtl">
      <div className="text-5xl mb-4 opacity-80">{icon}</div>
      <div className="font-extrabold text-base text-[var(--text-primary)]">{title}</div>
      {description && <div className="text-sm mt-2">{description}</div>}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-6 text-white px-6 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_var(--accent-soft)] hover:shadow-[0_10px_24px_var(--accent-soft)] hover:-translate-y-0.5 transition-all"
          style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}
        >
          {actionIcon} {actionLabel}
        </button>
      )}
    </div>
  );
}
