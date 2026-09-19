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
    <div className={`bg-white border border-[#E5EBF3] rounded-[20px] p-5 shadow-md hover:shadow-lg transition-shadow ${className}`}>
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, action }: CardHeaderProps) {
  return (
    <div className="flex justify-between items-center mb-5 pb-3.5 border-b border-[#E5EBF3]">
      <div>
        <div className="text-[15px] font-bold flex items-center gap-2 text-[#1A2B47]">{title}</div>
        {subtitle && <div className="text-[11px] text-[#9AA8BF] mt-0.5">{subtitle}</div>}
      </div>
      {action}
    </div>
  );
}