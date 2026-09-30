/**
 * فاز ۴۸c — ابزار مشترک query-string.
 *
 * ⚠️ پروژه **react-router ندارد** (ناوبری با `useState` در `App.tsx` است) ⇒ برای ماندگاری
 * فیلترها در URL از History API خام استفاده می‌کنیم. همهٔ نوشتن‌ها `replaceState` است
 * تا هر تایپ/تغییر فیلتر یک ورودی تاریخچه نسازد.
 */

/**
 * ساخت query string جدید از query فعلی + تغییرات (بدون `?` ابتدایی).
 * مقدار `null` / `undefined` / رشتهٔ خالی ⇒ کلید **حذف** می‌شود (کلیدهای دیگر دست‌نخورده می‌مانند).
 */
export function buildSearch(
  currentSearch: string,
  patch: Record<string, string | null | undefined>,
): string {
  const params = new URLSearchParams(currentSearch || '');
  Object.keys(patch).forEach((key) => {
    const value = patch[key];
    if (value === null || value === undefined || value === '') params.delete(key);
    else params.set(key, String(value));
  });
  return params.toString();
}

/** خواندن یک پارامتر از query (پیش‌فرض: `window.location.search`). */
export function readParam(key: string, currentSearch?: string): string | null {
  const search = currentSearch ?? (typeof window === 'undefined' ? '' : window.location.search);
  return new URLSearchParams(search).get(key);
}

/** نوشتن patch در URL بدون افزودن ورودی به تاریخچهٔ مرورگر. */
export function writeSearch(patch: Record<string, string | null | undefined>): void {
  if (typeof window === 'undefined') return;
  const qs = buildSearch(window.location.search, patch);
  const url = `${window.location.pathname}${qs ? `?${qs}` : ''}${window.location.hash}`;
  window.history.replaceState(null, '', url);
}
