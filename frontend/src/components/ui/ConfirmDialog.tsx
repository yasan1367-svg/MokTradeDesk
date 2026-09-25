import { useEffect } from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * ConfirmDialog — دیالوگ تأیید سفارشی (جایگزین window.confirm)
 * - Esc برای بستن
 * - RTL و Dark Mode
 */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'تأیید',
  cancelLabel = 'انصراف',
  danger = true,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[600] flex items-center justify-center p-4" dir="rtl">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onCancel} />
      <div
        role="dialog"
        aria-modal="true"
        className="relative bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 w-full max-w-md shadow-2xl"
      >
        <div className="text-4xl mb-3 text-center">{danger ? '⚠️' : '❓'}</div>
        {title && <h3 className="text-center font-extrabold text-[var(--text-primary)] mb-2">{title}</h3>}
        <p className="text-center text-sm text-[var(--text-secondary)] mb-6">{message}</p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 bg-[var(--bg-base)] text-[var(--text-primary)] border border-[var(--border-subtle)] px-4 py-3 rounded-xl text-sm font-bold hover:bg-[var(--accent-soft)] transition-all"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            autoFocus
            className={`flex-1 text-white px-4 py-3 rounded-xl text-sm font-extrabold transition-all ${
              danger ? 'bg-[#E45D72] hover:bg-[#E45D72]/85' : 'bg-[#3F7CFF] hover:bg-[#3F7CFF]/85'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
