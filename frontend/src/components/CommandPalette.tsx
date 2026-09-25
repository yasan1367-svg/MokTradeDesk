import { useEffect, useMemo, useRef, useState } from 'react';

export interface CommandItem {
  id: string;
  label: string;
  icon: string;
  hint?: string;
  run: () => void;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  items: CommandItem[];
}

/**
 * CommandPalette — جستجوی سریع سراسری (Ctrl+K)
 * ناوبری با ↑↓ و انتخاب با ↵
 */
export default function CommandPalette({ open, onClose, items }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (i) => i.label.toLowerCase().includes(q) || (i.hint ?? '').toLowerCase().includes(q),
    );
  }, [items, query]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setActive(0);
      const t = window.setTimeout(() => inputRef.current?.focus(), 30);
      return () => window.clearTimeout(t);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActive((a) => Math.min(a + 1, Math.max(filtered.length - 1, 0)));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActive((a) => Math.max(a - 1, 0));
      } else if (e.key === 'Enter') {
        const item = filtered[active];
        if (item) {
          e.preventDefault();
          item.run();
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, filtered, active, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[700] flex items-start justify-center pt-[12vh] p-4" dir="rtl">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        className="relative w-full max-w-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[20px] shadow-2xl overflow-hidden"
      >
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-[var(--border-subtle)]">
          <span className="text-lg">🔍</span>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActive(0);
            }}
            placeholder="جستجوی سریع... (صفحه یا عملیات)"
            className="flex-1 bg-transparent outline-none text-sm text-[var(--text-primary)] placeholder:text-[var(--text-secondary)]"
          />
          <kbd className="text-[10px] px-2 py-1 rounded bg-[var(--bg-base)] border border-[var(--border-subtle)] text-[var(--text-secondary)] font-mono">ESC</kbd>
        </div>

        <div className="max-h-[52vh] overflow-y-auto py-2">
          {filtered.length === 0 ? (
            <div className="text-center py-10 text-sm text-[var(--text-secondary)]">نتیجه‌ای یافت نشد</div>
          ) : (
            filtered.map((item, idx) => (
              <button
                key={item.id}
                onMouseEnter={() => setActive(idx)}
                onClick={() => {
                  item.run();
                  onClose();
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 text-right transition-colors ${
                  idx === active ? 'bg-[var(--accent-soft)]' : 'hover:bg-[var(--bg-base)]'
                }`}
              >
                <span className="text-lg w-6 text-center shrink-0">{item.icon}</span>
                <span className="flex-1 text-sm font-bold text-[var(--text-primary)]">{item.label}</span>
                {item.hint && (
                  <span className="text-[10px] text-[var(--text-secondary)] font-mono shrink-0">{item.hint}</span>
                )}
              </button>
            ))
          )}
        </div>

        <div className="px-4 py-2.5 border-t border-[var(--border-subtle)] text-[10px] text-[var(--text-secondary)] flex gap-4">
          <span>↑↓ حرکت</span>
          <span>↵ انتخاب</span>
          <span>Ctrl+K باز کردن</span>
        </div>
      </div>
    </div>
  );
}
