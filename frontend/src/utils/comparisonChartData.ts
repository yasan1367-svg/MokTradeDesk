export interface ComparisonChartMetric {
  version_id: number;
  version_name: string;
  strategy_name: string;
  win_rate: number;
  profit_factor: number | null;
  profit_factor_status: string;
  net_pnl: number;
  max_dd: number;
  health_score: number;
}

export function measuredProfitFactor(value: unknown, status: unknown): number | null {
  const numeric = typeof value === 'number' ? value : Number(value);
  return status === 'finite' && Number.isFinite(numeric) ? numeric : null;
}