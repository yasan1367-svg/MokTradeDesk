/**
 * فاز ۵۳.۶.۳ — منبع یگانهٔ Theme.
 *
 * قبلاً `App.tsx::useTheme` فقط localStorage را می‌خواند/نوشت، در حالی که
 * `SettingsPage` مقدار theme را در API ذخیره می‌کرد ⇒ تناقض. اکنون هر دو از
 * همین ابزار استفاده می‌کنند و یک رویداد مشترک، state برنامه را همگام می‌کند.
 */
export type Theme = 'light' | 'dark';

export const THEME_KEY = 'moktrade-theme';

export function readStoredTheme(): Theme | null {
  if (typeof window === 'undefined') return null;
  const stored = localStorage.getItem(THEME_KEY);
  return stored === 'dark' || stored === 'light' ? stored : null;
}

/** Apply the selected theme to `<html>` and persist the user's explicit choice. */
export function applyTheme(theme: Theme): void {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  if (theme === 'dark') root.classList.add('dark');
  else root.classList.remove('dark');
  localStorage.setItem(THEME_KEY, theme);
}

/** Apply a saved theme, defaulting to light without consulting the OS preference. */
export function resolveInitialTheme(): Theme {
  return readStoredTheme() ?? 'light';
}

/** Set the document's root font size so rem-based styles follow the user's setting. */
export function applyFontSize(px: number): void {
  if (typeof document === 'undefined' || !Number.isFinite(px) || px <= 0) return;
  document.documentElement.style.fontSize = `${px}px`;
}
