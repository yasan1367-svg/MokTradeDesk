import { describe, it, expect, vi, afterEach } from 'vitest';
import type { AxiosResponse } from 'axios';
import {
  api,
  getAnalysis,
  getVersionAnalysis,
  getAnalysisVersion,
  analyzeVersionScoped,
} from '../api/client';

const okResponse = { data: {} } as AxiosResponse;

afterEach(() => {
  vi.restoreAllMocks();
});

/**
 * فاز ۴۸b — `test_type` در فراخوانی‌های تحلیل نسخه.
 * باگ: `getAnalysis`/`getVersionAnalysis` (`GET /api/analytics/{id}`) پارامتر `test_type`
 * را نمی‌فرستادند ⇒ برای نسخه‌ای که هم تحلیل Backtest و هم Forward دارد، پاسخ قطعی نبود.
 */
describe('فاز ۴۸b — test_type در فراخوانی‌های تحلیل نسخه', () => {
  it('getAnalysis به‌صورت پیش‌فرض BACKTEST می‌فرستد', async () => {
    const spy = vi.spyOn(api, 'get').mockResolvedValue(okResponse);
    await getAnalysis(7);
    expect(spy).toHaveBeenCalledWith('/api/analytics/7?test_type=BACKTEST');
  });

  it('getAnalysis نوع صریح Forward را می‌فرستد', async () => {
    const spy = vi.spyOn(api, 'get').mockResolvedValue(okResponse);
    await getAnalysis(12, 'FORWARD');
    expect(spy).toHaveBeenCalledWith('/api/analytics/12?test_type=FORWARD');
  });

  it('getVersionAnalysis (همان endpoint) هم test_type می‌فرستد', async () => {
    const spy = vi.spyOn(api, 'get').mockResolvedValue(okResponse);
    await getVersionAnalysis(3, 'FORWARD');
    expect(spy).toHaveBeenCalledWith('/api/analytics/3?test_type=FORWARD');
  });

  it('getAnalysisVersion (مسیر scoped) بدون رگرسیون باقی مانده است', async () => {
    const spy = vi.spyOn(api, 'get').mockResolvedValue(okResponse);
    await getAnalysisVersion(5, 'FORWARD');
    expect(spy).toHaveBeenCalledWith('/api/analytics/analysis/version/5', {
      params: { test_type: 'FORWARD' },
    });
  });

  it('analyzeVersionScoped (مسیر scoped) بدون رگرسیون باقی مانده است', async () => {
    const spy = vi.spyOn(api, 'post').mockResolvedValue(okResponse);
    await analyzeVersionScoped(5, 'FORWARD');
    expect(spy).toHaveBeenCalledWith('/api/analytics/analyze/version/5', null, {
      params: { test_type: 'FORWARD' },
    });
  });
});
