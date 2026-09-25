import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

export type ToastVariant = 'success' | 'error' | 'info' | 'warning';

export interface ToastItem {
  id: number;
  message: string;
  variant: ToastVariant;
  duration: number;
}

interface ToastContextValue {
  toast: (message: string, variant?: ToastVariant, duration?: number) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
  warning: (message: string) => void;
  dismiss: (id: number) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

/** دسترسی به سیستم Toast سراسری */
export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast باید داخل ToastProvider استفاده شود');
  return ctx;
}

const VARIANT_UI: Record<ToastVariant, { icon: string; color: string; border: string }> = {
  success: { icon: '✅', color: 'text-[#13AE81]', border: 'border-[#13AE81]/40' },
  error: { icon: '❌', color: 'text-[#E45D72]', border: 'border-[#E45D72]/40' },
  info: { icon: 'ℹ️', color: 'text-[#3F7CFF]', border: 'border-[#3F7CFF]/40' },
  warning: { icon: '⚠️', color: 'text-[#D99B25]', border: 'border-[#D99B25]/40' },
};

/**
 * ToastProvider — سیستم Toast سراسری (چندتایی، RTL، Dark Mode)
 */
export default function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: number) => {
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, variant: ToastVariant = 'success', duration = 3200) => {
      const id = Date.now() + Math.random();
      setItems((prev) => [...prev, { id, message, variant, duration }]);
      window.setTimeout(() => dismiss(id), duration);
    },
    [dismiss],
  );

  const value = useMemo<ToastContextValue>(
    () => ({
      toast,
      success: (m: string) => toast(m, 'success'),
      error: (m: string) => toast(m, 'error'),
      info: (m: string) => toast(m, 'info'),
      warning: (m: string) => toast(m, 'warning'),
      dismiss,
    }),
    [toast, dismiss],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        dir="rtl"
        className="fixed top-5 left-1/2 -translate-x-1/2 z-[9999] flex flex-col items-center gap-2.5 pointer-events-none max-w-[92vw]"
      >
        {items.map((item) => {
          const ui = VARIANT_UI[item.variant];
          return (
            <div
              key={item.id}
              role="status"
              aria-live="polite"
              className={`pointer-events-auto flex items-center gap-3 px-5 py-3.5 rounded-[14px] border shadow-lg backdrop-blur-xl bg-[var(--bg-card)]/95 ${ui.border}`}
            >
              <span className="text-lg shrink-0">{ui.icon}</span>
              <span className={`text-sm font-bold ${ui.color}`}>{item.message}</span>
              <button
                onClick={() => dismiss(item.id)}
                aria-label="بستن"
                className="mr-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-sm transition-colors shrink-0"
              >
                ✕
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
