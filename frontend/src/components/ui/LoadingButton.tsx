import type { ButtonHTMLAttributes, ReactNode } from 'react';

interface LoadingButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  loadingText?: string;
  variant?: 'primary' | 'secondary' | 'danger';
  children: ReactNode;
}

/**
 * LoadingButton — دکمه با حالت Loading (اسپینر + غیرفعال‌سازی)
 */
export default function LoadingButton({
  loading = false,
  loadingText = 'در حال ذخیره...',
  variant = 'primary',
  children,
  disabled,
  className = '',
  ...rest
}: LoadingButtonProps) {
  const variantClass = {
    primary: 'text-white shadow-[0_6px_16px_rgba(63,124,255,0.3)]',
    secondary: 'bg-[var(--bg-base)] text-[var(--text-primary)] border border-[var(--border-subtle)]',
    danger: 'text-white shadow-[0_6px_16px_rgba(228,93,114,0.3)]',
  }[variant];

  const style =
    variant === 'primary'
      ? { background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }
      : variant === 'danger'
        ? { background: 'linear-gradient(135deg, #E45D72, #F07A8C)' }
        : {};

  return (
    <button
      {...rest}
      disabled={disabled || loading}
      style={style}
      className={`inline-flex items-center justify-center gap-2 px-6 py-3 rounded-[12px] text-sm font-extrabold transition-all disabled:opacity-60 disabled:cursor-not-allowed ${variantClass} ${className}`}
    >
      {loading ? (
        <>
          <span className="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
          {loadingText}
        </>
      ) : (
        children
      )}
    </button>
  );
}
