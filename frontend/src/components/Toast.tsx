import { useEffect, useRef } from 'react';

export type ToastType = 'success' | 'error';

interface ToastProps {
  message: string;
  type?: ToastType;
  onClose: () => void;
  /** مدت نمایش به میلی‌ثانیه (پیش‌فرض: ۳۰۰۰) */
  duration?: number;
}

/**
 * Toast — پیام شناور موفقیت/خطا
 * - سازگار با Dark Mode (CSS variables)
 * - RTL
 * - Auto-dismiss بعد از `duration`
 */
export default function Toast({
  message,
  type = 'success',
  onClose,
  duration = 3000,
}: ToastProps) {
  // نگه‌داشتن آخرین onClose در ref تا تایمر با هر رندر ریست نشود
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => onCloseRef.current(), duration);
    return () => clearTimeout(timer);
  }, [message, duration]);

  if (!message) return null;

  const isSuccess = type === 'success';

  return (
    <div
      role="status"
      aria-live="polite"
      dir="rtl"
      className={`fixed top-5 left-1/2 -translate-x-1/2 z-[9999] flex items-center gap-3 px-5 py-3.5 rounded-[14px] border shadow-lg backdrop-blur-xl max-w-[92vw] ${
        isSuccess
          ? 'bg-[var(--bg-card)]/95 border-[var(--profit-border)]'
          : 'bg-[var(--bg-card)]/95 border-[var(--loss-border)]'
      }`}
    >
      <span className="text-lg shrink-0">{isSuccess ? '✅' : '❌'}</span>
      <span
        className={`text-sm font-bold ${isSuccess ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}
      >
        {message}
      </span>
      <button
        onClick={onClose}
        aria-label="بستن"
        className="mr-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-sm transition-colors shrink-0"
      >
        ✕
      </button>
    </div>
  );
}
