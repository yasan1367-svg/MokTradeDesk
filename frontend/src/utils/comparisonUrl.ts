import { buildSearch } from './urlState';

/**
 * فاز ۴۸c — (de)serialize فیلترهای `ComparisonPage` در URL.
 * ورودی از URL می‌آید ⇒ **اعتبارسنجی کامل** لازم است (id معتبر، نوع تست whitelist، تاریخ ISO).
 */

export const COMPARISON_TEST_TYPES = ['BACKTEST', 'FORWARD', 'REAL_PERSONAL', 'REAL_PROP'] as const;
export const DEFAULT_COMPARISON_TEST_TYPE = 'BACKTEST';
export const MAX_COMPARE_SELECT = 5;

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export interface ComparisonUrlFilters {
  versionIds: number[];
  testType: string | null;
  symbol: string | null;
  dateFrom: string | null;
  dateTo: string | null;
}

export interface ComparisonFilterState {
  versionIds: number[];
  testType: string;
  symbol: string;
  dateFrom: string;
  dateTo: string;
}

/** استخراج امن فیلترها از query string (`versions=1,2&test_type=FORWARD&...`). */
export function parseComparisonFilters(search: string): ComparisonUrlFilters {
  const params = new URLSearchParams(search || '');

  const versionIds: number[] = [];
  (params.get('versions') || '').split(',').forEach((chunk) => {
    const id = Number(chunk.trim());
    if (!Number.isInteger(id) || id <= 0) return;        // غیرعددی/منفی ⇒ نادیده
    if (versionIds.includes(id)) return;                 // تکراری ⇒ نادیده
    if (versionIds.length >= MAX_COMPARE_SELECT) return; // سقف انتخاب
    versionIds.push(id);
  });

  const rawTestType = (params.get('test_type') || '').trim().toUpperCase();
  const rawSymbol = (params.get('symbol') || '').trim();
  const rawFrom = (params.get('date_from') || '').trim();
  const rawTo = (params.get('date_to') || '').trim();

  return {
    versionIds,
    testType: (COMPARISON_TEST_TYPES as readonly string[]).includes(rawTestType) ? rawTestType : null,
    symbol: rawSymbol ? rawSymbol.slice(0, 20) : null,
    dateFrom: DATE_RE.test(rawFrom) ? rawFrom : null,
    dateTo: DATE_RE.test(rawTo) ? rawTo : null,
  };
}

/** ساخت patch برای URL — مقادیر پیش‌فرض/خالی حذف می‌شوند تا URL تمیز بماند. */
export function buildComparisonPatch(
  filters: ComparisonFilterState,
): Record<string, string | null> {
  return {
    versions: filters.versionIds.length > 0 ? filters.versionIds.join(',') : null,
    test_type:
      filters.testType && filters.testType !== DEFAULT_COMPARISON_TEST_TYPE
        ? filters.testType
        : null,
    symbol: filters.symbol.trim() || null,
    date_from: filters.dateFrom || null,
    date_to: filters.dateTo || null,
  };
}

/** خروجی نهایی query string (بدون `?`) — تابع خالص برای تست. */
export function buildComparisonSearch(
  currentSearch: string,
  filters: ComparisonFilterState,
): string {
  return buildSearch(currentSearch, buildComparisonPatch(filters));
}
