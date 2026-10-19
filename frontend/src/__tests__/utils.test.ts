import { describe, it, expect } from 'vitest';
import {
  currentJalaliYear,
  gregorianToJalali,
  JALALI_MONTHS_FA,
} from '../utils/jalali';

describe('jalali utils', () => {
  it('تاریخ‌های میلادی شناخته‌شده را درست تبدیل می‌کند', () => {
    expect(gregorianToJalali(2025, 3, 21)).toEqual([1404, 1, 1]);
    expect(gregorianToJalali(2026, 3, 21)).toEqual([1405, 1, 1]);
    expect(gregorianToJalali(2025, 1, 1)).toEqual([1403, 10, 12]);
  });

  it('تابع روز اول هر ماه شمسی درست است', () => {
    expect(gregorianToJalali(2025, 3, 21)[1]).toBe(1);
    expect(gregorianToJalali(2025, 4, 21)[1]).toBe(2);
  });

  it('۱۲ ماه شمسی با نام صحیح دارد', () => {
    expect(JALALI_MONTHS_FA).toHaveLength(12);
    expect(JALALI_MONTHS_FA[0]).toBe('فروردین');
    expect(JALALI_MONTHS_FA[11]).toBe('اسفند');
  });

  it('currentJalaliYear یک عدد صحیح در بازه منطقی برمی‌گرداند', () => {
    const year = currentJalaliYear();
    expect(Number.isInteger(year)).toBe(true);
    expect(year).toBeGreaterThanOrEqual(1400);
    expect(year).toBeLessThanOrEqual(1500);
  });
});
