import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface EquityCurveChartProps {
  trades?: any[];
  initialBalance?: number;
  height?: number;
  currency?: string;
  /** سری آماده از endpoint داشبورد: [{date, equity}] */
  data?: { date: string; equity: number }[];
}

export default function EquityCurveChart({ trades = [], initialBalance = 0, height = 250, data: series, currency = 'USDT' }: EquityCurveChartProps) {
  let data: { index: number; date: string; equity: number; pnl?: number }[];

  if (series && series.length > 0) {
    // استفادهٔ مستقیم از equity_curve آمادهٔ بک‌اند
    data = series.map((p, idx) => ({ index: idx, date: p.date, equity: p.equity }));
  } else {
    const sorted = [...trades]
      .filter((t) => t.close_time)
      .sort((a, b) => new Date(a.close_time).getTime() - new Date(b.close_time).getTime());

    let equity = initialBalance;
    data = sorted.map((t, idx) => {
      equity += t.pnl || 0;
      return {
        index: idx + 1,
        date: new Date(t.close_time).toLocaleDateString('fa-IR'),
        equity: Math.round(equity * 100) / 100,
        pnl: t.pnl || 0,
      };
    });

    data.unshift({
      index: 0,
      date: 'شروع',
      equity: initialBalance,
      pnl: 0,
    });
  }

  if (data.length < 2) {
    return (
      <div className="text-[var(--text-secondary)] text-center py-8 text-sm">
        داده‌ای برای نمایش منحنی سرمایه وجود ندارد
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--profit)" stopOpacity={0.3} />
            <stop offset="95%" stopColor="var(--profit)" stopOpacity={0} />
          </linearGradient>
          <filter id="equityGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
        <XAxis
  dataKey="index"
  stroke="var(--text-secondary)"
  style={{ fontSize: '11px', fontFamily: 'Vazirmatn' }}
  tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
/>
<YAxis
  stroke="var(--text-secondary)"
  style={{ fontSize: '11px', fontFamily: 'Vazirmatn' }}
  tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
/>
        <Tooltip
          contentStyle={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-accent)',
            borderRadius: '8px',
            padding: '8px 12px',
            boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
            color: 'var(--text-primary)',
            fontSize: '12px',
          }}
          formatter={(value: any) => [`${value} ${currency} `, 'سرمایه']}
          labelFormatter={(label) => `معامله #${label}`}
        />
        <Area
          type="monotone"
          dataKey="equity"
          stroke="none"
          strokeWidth={2}
          fill="url(#equityGradient)"
        />
        <Area
          type="monotone"
          dataKey="equity"
          stroke="var(--profit)"
          strokeWidth={2}
          filter="url(#equityGlow)"
          fill="none"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
