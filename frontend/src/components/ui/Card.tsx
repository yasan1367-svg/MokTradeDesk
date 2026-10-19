import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
}

interface CardHeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <div className={`app-card p-5 ${className}`}>
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, action }: CardHeaderProps) {
  return (
    <div className="card-heading flex justify-between items-center flex-wrap gap-3 mb-5">
      <div className="min-w-0">
        <div className="text-[15px] font-bold flex items-center gap-2 text-[var(--text-primary)]">{title}</div>
        {subtitle && <div className="text-[11px] text-[var(--text-muted)] mt-0.5">{subtitle}</div>}
      </div>
      {action}
    </div>
  );
}
