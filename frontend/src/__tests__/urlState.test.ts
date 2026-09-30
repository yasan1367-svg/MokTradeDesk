import { describe, it, expect, beforeEach } from 'vitest';
import { buildSearch, readParam, writeSearch } from '../utils/urlState';
import {
  MAX_COMPARE_SELECT,
  buildComparisonPatch,
  buildComparisonSearch,
  parseComparisonFilters,
} from '../utils/comparisonUrl';

/**
 * فاز ۴۸c — تست‌های ماندگاری فیلترها در URL.
 * توجه: `URLSearchParams` کاما را به `%2C` کد می‌کند (در parse معادل `,` است).
 */

describe('urlState — buildSearch', () => {
  it('کلید جدید اضافه می‌کند و کلیدهای دیگر را حفظ می‌کند', () => {
    expect(buildSearch('?page=comparison&a=1', { versions: '1,2' })).toBe(
      'page=comparison&a=1&versions=1%2C2',
    );
  });

  it('مقدار null / undefined / خالی ⇒ حذف کلید', () => {
    expect(buildSearch('?page=comparison&versions=1,2&symbol=XAU', { versions: null })).toBe(
      'page=comparison&symbol=XAU',
    );
    expect(buildSearch('?a=1&b=2', { a: '', b: undefined })).toBe('');
  });

  it('patch خالی ⇒ search بدون تغییر', () => {
    expect(buildSearch('?page=analysis', {})).toBe('page=analysis');
    expect(buildSearch('', {})).toBe('');
  });
});

describe('urlState — readParam', () => {
  it('مقدار پارامتر را می‌خواند و برای کلید ناموجود null می‌دهد', () => {
    expect(readParam('page', '?page=analysis&x=1')).toBe('analysis');
    expect(readParam('nope', '?page=analysis')).toBeNull();
  });
});

describe('urlState — writeSearch (jsdom)', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/');
  });

  it('URL را بدون افزودن ورودی تاریخچه آپدیت می‌کند', () => {
    window.history.replaceState(null, '', '/?page=comparison');
    writeSearch({ versions: '3,4' });
    expect(window.location.search).toBe('?page=comparison&versions=3%2C4');
  });

  it('با مقدار null پارامتر را از URL پاک می‌کند', () => {
    window.history.replaceState(null, '', '/?page=comparison&versions=3,4');
    writeSearch({ versions: null });
    expect(window.location.search).toBe('?page=comparison');
  });
});

describe('comparisonUrl — parseComparisonFilters (ورودی نامعتبر = نادیده)', () => {
  it('idهای معتبر را می‌خواند و غیرعددی/منفی/صفر/تکراری را دور می‌ریزد', () => {
    const f = parseComparisonFilters('?versions=3,1,3,abc,-2,0,7');
    expect(f.versionIds).toEqual([3, 1, 7]);
  });

  it('سقف انتخاب (MAX_COMPARE_SELECT) را اعمال می‌کند', () => {
    const f = parseComparisonFilters('?versions=1,2,3,4,5,6,7,8');
    expect(f.versionIds).toHaveLength(MAX_COMPARE_SELECT);
    expect(f.versionIds).toEqual([1, 2, 3, 4, 5]);
  });

  it('test_type فقط از whitelist پذیرفته می‌شود', () => {
    expect(parseComparisonFilters('?test_type=forward').testType).toBe('FORWARD');
    expect(parseComparisonFilters('?test_type=real_prop').testType).toBe('REAL_PROP');
    expect(parseComparisonFilters('?test_type=HACK;DROP').testType).toBeNull();
    expect(parseComparisonFilters('?test_type=').testType).toBeNull();
  });

  it('نماد trim می‌شود و تاریخ فقط ISO معتبر پذیرفته می‌شود', () => {
    const f = parseComparisonFilters('?symbol= xauusd &date_from=2025-01-01&date_to=01/02/2025');
    expect(f.symbol).toBe('xauusd');
    expect(f.dateFrom).toBe('2025-01-01');
    expect(f.dateTo).toBeNull();
  });

  it('search خالی ⇒ همه‌چیز پیش‌فرض', () => {
    expect(parseComparisonFilters('')).toEqual({
      versionIds: [],
      testType: null,
      symbol: null,
      dateFrom: null,
      dateTo: null,
    });
  });
});

describe('comparisonUrl — buildComparisonPatch / buildComparisonSearch', () => {
  it('test_type پیش‌فرض (BACKTEST) و مقادیر خالی در URL نوشته نمی‌شوند', () => {
    expect(
      buildComparisonPatch({
        versionIds: [1, 2],
        testType: 'BACKTEST',
        symbol: '   ',
        dateFrom: '',
        dateTo: '',
      }),
    ).toEqual({ versions: '1,2', test_type: null, symbol: null, date_from: null, date_to: null });
  });

  it('نوع تست غیرپیش‌فرض + نماد + تاریخ‌ها نوشته می‌شوند', () => {
    expect(
      buildComparisonSearch('?page=comparison', {
        versionIds: [5],
        testType: 'FORWARD',
        symbol: 'XAUUSD',
        dateFrom: '2025-01-01',
        dateTo: '2025-02-01',
      }),
    ).toBe('page=comparison&versions=5&test_type=FORWARD&symbol=XAUUSD&date_from=2025-01-01&date_to=2025-02-01');
  });

  it('انتخاب خالی ⇒ کلید versions حذف می‌شود', () => {
    expect(
      buildComparisonSearch('?versions=1,2&symbol=XAU', {
        versionIds: [],
        testType: 'BACKTEST',
        symbol: '',
        dateFrom: '',
        dateTo: '',
      }),
    ).toBe('');
  });

  it('رفت‌وبرگشت (round-trip): خروجی build قابل parse است', () => {
    const filters = { versionIds: [2, 9], testType: 'REAL_PERSONAL', symbol: 'EURUSD', dateFrom: '2025-03-01', dateTo: '' };
    const parsed = parseComparisonFilters(`?${buildComparisonSearch('', filters)}`);
    expect(parsed).toEqual({
      versionIds: [2, 9],
      testType: 'REAL_PERSONAL',
      symbol: 'EURUSD',
      dateFrom: '2025-03-01',
      dateTo: null,
    });
  });
});