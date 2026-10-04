/**
 * فاز ۵۳.۶.۳ — منبع یگانهٔ Theme.
 *
 * قبلاً `App.tsx::useTheme` فقط localStorage را می‌خواند/نوشت، در حالی که
 * `SettingsPage` مقدار theme را در API ذخیره می‌کرد ⇒ تناقض. اکنون هر دو از
 * همین ابزار استفاده می‌کنند و یک رویداد مشترک، state برنامه را همگام می‌کند.
 */
export type Theme = 'light' | 'dark';

export const THEME_KEY = 'moktrade-theme';
export const THEME_EVENT = 'moktrade-theme-changed';

export function readStoredTheme(): Theme | null {
  if (typeof window === 'undefined') return null;
  const stored = localStorage.getItem(THEME_KEY);
  return stored === 'dark' || stored === 'light' ? stored : null;
}

/** اعمال theme روی `<html>` + ذخیره در localStorage + اطلاع‌رسانی به مصرف‌کنندگان. */
export function applyTheme(theme: Theme, notify = true): void {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  if (theme === 'dark') root.classList.add('dark');
  else root.classList.remove('dark');
  localStorage.setItem(THEME_KEY, theme);
  if (notify) window.dispatchEvent(new CustomEvent<Theme>(THEME_EVENT, { detail: theme }));
}

/** theme اولیه: localStorage → system preference → dark (فاز ۱۰-الف: پیش‌فرض تاریک). */
export function resolveInitialTheme(): Theme {
  const stored = readStoredTheme();
  if (stored) return stored;
  if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'dark';
}
