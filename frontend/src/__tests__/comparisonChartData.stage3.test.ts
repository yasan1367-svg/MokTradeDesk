import { describe, expect, it } from 'vitest';
import { measuredProfitFactor } from '../utils/comparisonChartData';
import { buildRadarData } from '../components/charts/ComparisonRadarChart';

describe('Comparison PF chart data', () => {
  it('keeps measured finite PF and leaves no-loss/unavailable values as gaps', () => {
    expect(measuredProfitFactor(2, 'finite')).toBe(2);
    expect(measuredProfitFactor(999, 'no_losses')).toBeNull();
    expect(measuredProfitFactor(0, 'no_usable_pnl')).toBeNull();
    expect(measuredProfitFactor(undefined, 'unavailable')).toBeNull();
  });

  it('keeps unavailable PF as a Radar gap, retains measured zero, and omits an unmeasurable PF axis', () => {
    const items = [
      { version_id: 1, version_name: 'finite', win_rate: 50, profit_factor: 0, profit_factor_status: 'finite', net_pnl: 0, max_dd: 0, health_score: 50 },
      { version_id: 2, version_name: 'missing', win_rate: 50, profit_factor: null, profit_factor_status: 'no_losses', net_pnl: 1, max_dd: 0, health_score: 50 },
    ];
    const mixed = buildRadarData(items);
    const pf = mixed.find((point) => point.metric === 'فاکتور سود');
    expect(pf?.version_1).toBe(0);
    expect(pf?.version_2).toBeNull();

    const allMissing = buildRadarData(items.map((item) => ({ ...item, profit_factor: null, profit_factor_status: 'unavailable' })));
    expect(allMissing.some((point) => point.metric === 'فاکتور سود')).toBe(false);
  });

  it('keys series by version id despite duplicate names and excludes negative PnL from Radar', () => {
    const items = [
      { version_id: 7, version_name: 'duplicate', win_rate: 50, profit_factor: null, profit_factor_status: 'no_losses', net_pnl: -50, max_dd: 10, health_score: 40 },
      { version_id: 8, version_name: 'duplicate', win_rate: 60, profit_factor: 0, profit_factor_status: 'finite', net_pnl: 20, max_dd: 5, health_score: 60 },
    ];
    const points = buildRadarData(items);
    expect(points.some((point) => point.metric === 'سود خالص')).toBe(false);
    expect(points.find((point) => point.metric === 'نرخ برد')?.version_7).toBeDefined();
    expect(points.find((point) => point.metric === 'نرخ برد')?.version_8).toBeDefined();
    expect(points.find((point) => point.metric === 'فاکتور سود')?.version_7).toBeNull();
  });
});