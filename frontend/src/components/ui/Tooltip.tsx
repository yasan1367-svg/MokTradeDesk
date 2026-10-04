import type { ReactNode } from 'react';

interface TooltipProps {
  content: string;
  children: ReactNode;
  side?: 'top' | 'bottom' | 'left' | 'right';
}

/**
 * Tooltip — راهنمای شناور سبک (بدون وابستگی خارجی)
 * RTL-aware و سازگار با Dark Mode
 */
export default function Tooltip({ content, children, side = 'top' }: TooltipProps) {
  const position = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  }[side];

  return (
    <span className="relative inline-flex group">
      {children}
      <span
        role="tooltip"
        className={`pointer-events-none absolute z-[100] whitespace-nowrap rounded-lg px-2.5 py-1.5 text-[11px] font-bold text-white bg-[var(--bg-sidebar)] opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-150 shadow-lg ${position}`}
      >
        {content}
      </span>
    </span>
  );
}
